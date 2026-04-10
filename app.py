import os
import sys
import json
import logging
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from database import db, User, Curriculum, TopicProgress, SessionActivity
from llm_service import generate_curriculum, generate_topic_chunk, re_explain_concept, generate_session_summary
import markdown

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.config['SECRET_KEY'] = 'teachme_secret_key_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///teachme.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True

db.init_app(app)

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
    user_id_from_url = request.args.get('user_id')
    
    if 'user_id' not in session and user_id_from_url:
        session['user_id'] = user_id_from_url
        
    if 'user_id' not in session:
        return render_template('setup.html')
        
    user = User.query.get(session['user_id'])
    if not user:
        session.pop('user_id', None)
        return render_template('setup.html')
        
    curriculum = Curriculum.query.filter_by(user_id=user.id).order_by(Curriculum.id.desc()).first()
    
    if not curriculum:
        return render_template('setup.html')
        
    topics = json.loads(curriculum.topics_json)
    progress_records = TopicProgress.query.filter_by(curriculum_id=curriculum.id).all()
    
    progress_map = {p.topic_id_str: p for p in progress_records}
    
    return render_template('dashboard.html', 
                          user=user, 
                          subject=curriculum.subject, 
                          level=curriculum.level,
                          topics=topics,
                          progress_map=progress_map)

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

@app.route('/api/debug/curriculum')
def debug_curriculum():
    if 'user_id' not in session:
        return jsonify({"error": "No user in session"}), 401
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({"error": "User not found"}), 404
    curriculum = Curriculum.query.filter_by(user_id=user.id).order_by(Curriculum.id.desc()).first()
    if not curriculum:
        return jsonify({"error": "No curriculum found"}), 404
    
    return jsonify({
        "subject": curriculum.subject,
        "level": curriculum.level,
        "raw_topics": json.loads(curriculum.topics_json)
    })
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
