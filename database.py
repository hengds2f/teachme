from flask_sqlalchemy import SQLAlchemy
import json
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    # Context profile captured and updated over time
    background = db.Column(db.Text, default="")
    learning_style = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Curriculum(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    level = db.Column(db.String(50), nullable=True)
    goal = db.Column(db.Text, nullable=True)
    # JSON array of the 17 topics structured logically 
    # e.g., [{"id": "01", "title": "Intro", "tier": "Foundations", "description": "..."}, ...]
    topics_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TopicProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    curriculum_id = db.Column(db.Integer, db.ForeignKey('curriculum.id'), nullable=False)
    topic_id_str = db.Column(db.String(10), nullable=False) # e.g. "01"
    status = db.Column(db.String(20), default="Not Started") # "Not Started", "In Progress", "Completed"
    # To store generated content chunks persistently so they aren't lost
    # JSON array of content blocks created
    content_chunks_json = db.Column(db.Text, default="[]")
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)

class SessionActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_date = db.Column(db.DateTime, default=datetime.utcnow)
    summary_text = db.Column(db.Text, nullable=True) # Generated at end of session
