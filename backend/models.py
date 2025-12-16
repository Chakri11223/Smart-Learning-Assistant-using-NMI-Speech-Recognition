from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    verified = db.Column(db.Boolean, default=False, nullable=False)
    verification_code = db.Column(db.String(10), nullable=True)
    verification_expires = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Streak Tracking
    current_streak = db.Column(db.Integer, default=0)
    last_activity_date = db.Column(db.Date, nullable=True)
    max_streak = db.Column(db.Integer, default=0)
    
    # Relationships
    quiz_scores = db.relationship('QuizScore', backref='user', lazy=True, cascade='all, delete-orphan')
    chat_history = db.relationship('ChatHistory', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set the password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if the provided password matches the hash"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'verified': self.verified,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class QuizScore(db.Model):
    __tablename__ = 'quiz_scores'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    session_id = db.Column(db.String(255), nullable=True, index=True)  # For anonymous users
    quiz_title = db.Column(db.String(500), nullable=True)
    total_questions = db.Column(db.Integer, nullable=False)
    correct_answers = db.Column(db.Integer, nullable=False)
    score_percentage = db.Column(db.Float, nullable=False)
    answers_data = db.Column(db.JSON, nullable=True)  # Store detailed answers
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def to_dict(self):
        """Convert quiz score to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'quiz_title': self.quiz_title,
            'total_questions': self.total_questions,
            'correct_answers': self.correct_answers,
            'score_percentage': self.score_percentage,
            'answers_data': self.answers_data,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ChatSession(db.Model):
    __tablename__ = 'chat_sessions'
    
    id = db.Column(db.String(36), primary_key=True)  # UUID
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    title = db.Column(db.String(255), nullable=True)
    mode = db.Column(db.String(50), default='chat')  # 'chat', 'interview', 'feynman'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship
    messages = db.relationship('ChatHistory', backref='session', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'mode': self.mode,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ChatHistory(db.Model):
    __tablename__ = 'chat_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)  # Nullable for anonymous
    session_id = db.Column(db.String(255), db.ForeignKey('chat_sessions.id'), nullable=True, index=True)
    user_message = db.Column(db.Text, nullable=False)
    ai_response = db.Column(db.Text, nullable=False)
    context = db.Column(db.String(100), nullable=True)  # e.g., 'quiz_generator', 'voice_qa', 'video_summarizer'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def to_dict(self):
        """Convert chat history to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'user_message': self.user_message,
            'ai_response': self.ai_response,
            'context': self.context,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.String(36), primary_key=True)  # UUID
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)  # Extracted text content
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'filename': self.filename,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class FocusAreaDismissal(db.Model):
    __tablename__ = 'focus_area_dismissals'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    quiz_score_id = db.Column(db.Integer, db.ForeignKey('quiz_scores.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class LearningPath(db.Model):
    __tablename__ = 'learning_paths'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    topic = db.Column(db.String(255), nullable=False)
    level = db.Column(db.String(50), nullable=False)
    total_steps = db.Column(db.Integer, default=0)
    completed_steps = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    steps = db.relationship('LearningPathStep', backref='learning_path', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'topic': self.topic,
            'level': self.level,
            'total_steps': self.total_steps,
            'completed_steps': self.completed_steps,
            'progress': round((self.completed_steps / self.total_steps * 100), 1) if self.total_steps > 0 else 0,
            'created_at': self.created_at.isoformat()
        }

class LearningPathStep(db.Model):
    __tablename__ = 'learning_path_steps'

    id = db.Column(db.Integer, primary_key=True)
    learning_path_id = db.Column(db.Integer, db.ForeignKey('learning_paths.id'), nullable=False, index=True)
    step_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    details = db.Column(db.Text, nullable=True)
    video_query = db.Column(db.String(255), nullable=True)
    video_link = db.Column(db.String(500), nullable=True)
    video_title = db.Column(db.String(255), nullable=True)
    video_thumbnail = db.Column(db.String(500), nullable=True)
    video_views = db.Column(db.String(50), nullable=True)
    coding_link = db.Column(db.String(500), nullable=True)
    
    # Granular Progress
    video_watched = db.Column(db.Boolean, default=False)
    code_practiced = db.Column(db.Boolean, default=False)
    
    is_completed = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'step_number': self.step_number,
            'title': self.title,
            'details': self.details,
            'video_query': self.video_query,
            'video_link': self.video_link,
            'video_title': self.video_title,
            'video_thumbnail': self.video_thumbnail,
            'video_views': self.video_views,
            'coding_link': self.coding_link,
            'is_completed': self.is_completed
        }

class FeynmanScore(db.Model):
    __tablename__ = 'feynman_scores'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    session_id = db.Column(db.String(36), db.ForeignKey('chat_sessions.id'), nullable=False, index=True)
    topic = db.Column(db.String(255), nullable=False)
    persona = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, nullable=False)  # 0-100
    clarity_score = db.Column(db.Integer, nullable=False)
    depth_score = db.Column(db.Integer, nullable=False)
    feedback = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'topic': self.topic,
            'persona': self.persona,
            'score': self.score,
            'clarity_score': self.clarity_score,
            'depth_score': self.depth_score,
            'feedback': self.feedback,
            'created_at': self.created_at.isoformat()
        }

class VideoSummary(db.Model):
    __tablename__ = 'video_summaries'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    video_url = db.Column(db.String(500), nullable=True)
    title = db.Column(db.String(255), nullable=False)
    summary_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'video_url': self.video_url,
            'title': self.title,
            'summary_text': self.summary_text,
            'created_at': self.created_at.isoformat()
        }

class CommunityTopic(db.Model):
    __tablename__ = 'community_topics'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    likes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship('User', backref='topics')
    comments = db.relationship('CommunityComment', backref='topic', cascade='all, delete-orphan', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.name if self.user else 'Unknown',
            'title': self.title,
            'content': self.content,
            'likes': self.likes,
            'created_at': self.created_at.isoformat(),
            'comment_count': len(self.comments)
        }

class CommunityComment(db.Model):
    __tablename__ = 'community_comments'

    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('community_topics.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to user
    user = db.relationship('User', backref='comments')

    def to_dict(self):
        return {
            'id': self.id,
            'topic_id': self.topic_id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else 'Unknown',
            'content': self.content,
            'created_at': self.created_at.isoformat()
        }