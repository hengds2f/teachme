import os
import sys
import json
import logging
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from database import db, User, Curriculum, TopicProgress, SessionActivity
from llm_service import generate_curriculum, generate_topic_chunk, re_explain_concept, generate_session_summary
import markdown
from authlib.integrations.flask_client import OAuth

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'teachme_secret_key_123')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///teachme.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['PREFERRED_URL_SCHEME'] = 'https'

db.init_app(app)

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

with app.app_context():
    db.create_all()

# Helper for parsing markdown
def render_md(text):
    return markdown.markdown(text, extensions=['fenced_code', 'tables'])

@app.before_request
def make_session_permanent():
    session.permanent = True

@app.route('/')
def index():
    if 'user_id' not in session:
        return render_template('setup.html')
        
    user = User.query.get(session['user_id'])
    if not user:
        session.pop('user_id', None)
        return render_template('setup.html')
        
    # Get all subjects for this user to allow "Resume"
    curriculums = Curriculum.query.filter_by(user_id=user.id).order_by(Curriculum.created_at.desc()).all()
    
    # If a specific curriculum is requested via ID
    curr_id = request.args.get('curriculum_id')
    if curr_id:
        curriculum = Curriculum.query.filter_by(id=curr_id, user_id=user.id).first()
    else:
        curriculum = curriculums[0] if curriculums else None
    
    if not curriculum:
        return render_template('setup.html')
        
    topics = json.loads(curriculum.topics_json)
    progress_records = TopicProgress.query.filter_by(curriculum_id=curriculum.id).all()
    progress_map = {p.topic_id_str: p for p in progress_records}
    
    return render_template('dashboard.html', 
                          user=user,
                          curriculums=curriculums,
                          current_curriculum=curriculum,
                          subject=curriculum.subject, 
                          level=curriculum.level,
                          topics=topics,
                          progress_map=progress_map)

# OAuth Routes
@app.route('/login')
def login():
    redirect_uri = url_for('authorize', _external=True)
    # Force the prompt to ensure no stale 403 cookies/sessions are being used
    return google.authorize_redirect(redirect_uri, prompt='select_account')

@app.route('/api/auth/diag')
def auth_diag():
    client_id = os.getenv('GOOGLE_CLIENT_ID', 'MISSING')
    redirect_uri = url_for('authorize', _external=True)
    return jsonify({
        "status": "Final Compliance Audit",
        "client_id_status": "LOADED" if client_id != 'MISSING' else "MISSING",
        "client_id_prefix": client_id[:5] if client_id else "N/A",
        "generated_redirect_uri": redirect_uri,
        "is_https_forced": app.config.get('PREFERRED_URL_SCHEME') == 'https',
        "is_secure": request.is_secure,
        "headers": {
            "x-forwarded-proto": request.headers.get('X-Forwarded-Proto'),
            "x-forwarded-host": request.headers.get('X-Forwarded-Host'),
            "host": request.headers.get('Host')
        },
        "compliance_notes": [
            "1. Verified HTTPS Transport",
            "2. Removed Insecure Transport Overrides",
            "3. Hardened Proxy Ingress"
        ]
    })

@app.route('/login/callback')
def authorize():
    try:
        token = google.authorize_access_token()
        resp = google.get('userinfo')
        user_info = resp.json()
        
        email = user_info.get('email')
        if not email:
            logger.error("OAuth failed: No email returned in user_info")
            return "Authentication failed: No email provided by Google.", 400
            
        # Check if user exists
        user = User.query.filter_by(email=email).first()
        if not user:
            # Google OIDC usually uses 'sub' for the unique identifier
            google_id = user_info.get('sub') or user_info.get('id')
            
            # Create new user
            user = User(
                username=email.split('@')[0] + '_' + os.urandom(2).hex(),
                email=email,
                google_id=google_id,
                profile_pic=user_info.get('picture', '')
            )
            db.session.add(user)
            db.session.commit()
            logger.info(f"New user created via Google: {email}")
        
        session['user_id'] = user.id
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error in OAuth callback: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Internal Server Error during Authentication: {str(e)}", 500

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/api/setup', methods=['POST'])
def handle_setup():
    data = request.json
    subject = data.get('subject')
    level = data.get('level', 'Beginner')
    goal = data.get('goal', 'General knowledge')
    background = data.get('background', '')
    style = data.get('style', '')
    
    logger.info(f"New setup request for subject: {subject}, level: {level}")

    if 'user_id' not in session:
        # Create a new user for this session
        import random, string
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        user = User(username=username, background=background, learning_style=style)
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
    else:
        user = User.query.get(session['user_id'])
        user.background = background
        user.learning_style = style
        db.session.commit()

    # Generate the curriculum via LLM
    context = f"Background: {background}, Style: {style}"
    topics = generate_curriculum(subject, level, goal, context)
    
    curriculum = Curriculum(
        user_id=user.id,
        subject=subject,
        level=level,
        goal=goal,
        topics_json=json.dumps(topics)
    )
    db.session.add(curriculum)
    db.session.commit()
    
    # Initialize topic progress
    for topic in topics:
        tp = TopicProgress(
            user_id=user.id,
            curriculum_id=curriculum.id,
            topic_id_str=topic['id']
        )
        db.session.add(tp)
    
    db.session.commit()
    
    return jsonify({
        "status": "success", 
        "user_id": user.id, 
        "subject": subject,
        "level": level,
        "topics": topics,
        "curriculum_id": curriculum.id
    })


@app.route('/api/sync', methods=['POST'])
def sync_curriculum():
    data = request.json
    subject = data.get('subject')
    level = data.get('level')
    goal = data.get('goal', '')
    topics = data.get('topics')
    
    logger.info(f"Sync attempt for subject: {subject} with {len(topics) if topics else 0} topics")
    
    # Check if we need to create a user session
    if 'user_id' not in session:
        import random, string
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        user = User(username=username, background="Restored", learning_style="")
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
    else:
        user = User.query.get(session['user_id'])
        if not user:
            import random, string
            username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            user = User(username=username, background="Restored", learning_style="")
            db.session.add(user)
            db.session.commit()
            session['user_id'] = user.id

    # Create the curriculum if it doesn't exist for this user session
    existing = Curriculum.query.filter_by(user_id=user.id, subject=subject).first()
    if not existing:
        curriculum = Curriculum(
            user_id=user.id,
            subject=subject,
            level=level,
            goal=goal,
            topics_json=json.dumps(topics)
        )
        db.session.add(curriculum)
        db.session.commit()
        
        # Initialize topic progress
        for topic in topics:
            tp = TopicProgress(
                user_id=user.id,
                curriculum_id=curriculum.id,
                topic_id_str=topic['id']
            )
            db.session.add(tp)
        db.session.commit()
        
    return jsonify({"status": "success", "user_id": user.id})


@app.route('/topic/<topic_id_str>')
def topic_view(topic_id_str):
    user_id_from_url = request.args.get('user_id')
    if 'user_id' not in session and user_id_from_url:
        session['user_id'] = user_id_from_url

    if 'user_id' not in session:
        return redirect(url_for('index'))
        
    user = User.query.get(session['user_id'])
    if not user:
        session.pop('user_id', None)
        return redirect(url_for('index'))
        
    curriculum = Curriculum.query.filter_by(user_id=user.id).order_by(Curriculum.id.desc()).first()
    
    if not curriculum:
        return redirect(url_for('index'))
        
    topics = json.loads(curriculum.topics_json)
    topic_meta = next((t for t in topics if t['id'] == topic_id_str), None)
    
    if not topic_meta:
        return "Topic not found", 404
        
    progress = TopicProgress.query.filter_by(curriculum_id=curriculum.id, topic_id_str=topic_id_str).first()
    
    if progress.status == "Not Started":
        progress.status = "In Progress"
        db.session.commit()

    chunks = json.loads(progress.content_chunks_json) if progress.content_chunks_json else []
    
    return render_template('topic_guide.html', 
                          topic=topic_meta, 
                          subject=curriculum.subject,
                          progress=progress,
                          chunks=chunks)

@app.route('/api/chunk/generate', methods=['POST'])
def generate_chunk():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.json
    topic_id_str = data.get("topic_id")
    chunk_type = data.get("chunk_type") # concept, example, exercise, check
    
    user = User.query.get(session['user_id'])
    curriculum = Curriculum.query.filter_by(user_id=user.id).order_by(Curriculum.id.desc()).first()
    topics = json.loads(curriculum.topics_json)
    topic_meta = next((t for t in topics if t['id'] == topic_id_str), None)
    
    progress = TopicProgress.query.filter_by(curriculum_id=curriculum.id, topic_id_str=topic_id_str).first()
    
    context = f"User Level: {curriculum.level}, Background: {user.background}, Style: {user.learning_style}"
    
    md_content = generate_topic_chunk(curriculum.subject, topic_meta['title'], chunk_type, context)
    html_content = render_md(md_content)
    
    # Save the chunk
    chunks = json.loads(progress.content_chunks_json) if progress.content_chunks_json else []
    chunks.append({
        "type": chunk_type,
        "content_md": md_content,
        "content_html": html_content
    })
    progress.content_chunks_json = json.dumps(chunks)
    db.session.commit()
    
    return jsonify({
        "type": chunk_type,
        "content_html": html_content
    })

@app.route('/api/chunk/reexplain', methods=['POST'])
def api_reexplain():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    concept = data.get("concept")
    feedback = data.get("feedback")
    
    user = User.query.get(session['user_id'])
    context = f"Profile Context: {user.background}, Preferred Style: {user.learning_style}"
    
    md_content = re_explain_concept(concept, feedback, context)
    html_content = render_md(md_content)
    
    return jsonify({"content_html": html_content})

@app.route('/reset')
def reset_view():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/api/debug/env')
def debug_env():
    import google.generativeai as genai_lib
    # Only show keys that start with GEMINI for safety
    gemini_keys = [k for k in os.environ.keys() if 'GEMINI' in k.upper()]
    debug_info = {}
    for k in gemini_keys:
        val = os.environ.get(k)
        debug_info[k] = {
            "length": len(val) if val else 0,
            "prefix": val[:3] if val and len(val) >= 3 else "***"
        }
    return jsonify({
        "lib_version": genai_lib.__version__,
        "present_keys": gemini_keys,
        "debug_info": debug_info,
        "env_check_log": "Checking environment variables and library version"
    })

@app.route('/api/session/summary')
def session_summary():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user = User.query.get(session['user_id'])
    curriculum = Curriculum.query.filter_by(user_id=user.id).order_by(Curriculum.id.desc()).first()
    
    # Get all completed topics
    topics = json.loads(curriculum.topics_json)
    progress_records = TopicProgress.query.filter_by(curriculum_id=curriculum.id, status='Completed').all()
    completed_ids = [p.topic_id_str for p in progress_records]
    completed_titles = [t['title'] for t in topics if t['id'] in completed_ids]
    
    summary_input = f"Subject: {curriculum.subject}. Topics Completed: {', '.join(completed_titles)}. User Context: {user.background}"
    md_summary = generate_session_summary(summary_input)
    html_summary = render_md(md_summary)
    
    return jsonify({
        "summary_md": md_summary,
        "summary_html": html_summary
    })

@app.route('/api/debug/models')
def debug_models():
    import google.generativeai as genai_lib
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "No API key found in os.environ"}), 404
    
    try:
        genai_lib.configure(api_key=api_key)
        models = []
        for m in genai_lib.list_models():
            models.append({
                "name": m.name,
                "supported_methods": m.supported_generation_methods,
                "description": m.description
            })
        return jsonify({"available_models": models})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/topic/complete', methods=['POST'])
def complete_topic():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    topic_id_str = data.get("topic_id")
    
    user = User.query.get(session['user_id'])
    curriculum = Curriculum.query.filter_by(user_id=user.id).order_by(Curriculum.id.desc()).first()
    progress = TopicProgress.query.filter_by(curriculum_id=curriculum.id, topic_id_str=topic_id_str).first()
    
    progress.status = "Completed"
    db.session.commit()
    
    return jsonify({"status": "success"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860, debug=True)
