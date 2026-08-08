"""Question models"""
from datetime import datetime
from enum import Enum
from backend.database import db
import json


class QuestionType(str, Enum):
    """Question type enumeration"""
    MCQ = 'mcq'                    # Multiple Choice
    TRUE_FALSE = 'true_false'      # True/False
    MULTI_SELECT = 'multi_select'  # Multiple select
    FILL_BLANK = 'fill_blank'      # Fill in blank (future)
    ORDERING = 'ordering'          # Ordering (future)
    MATCHING = 'matching'          # Matching (future)
    IMAGE = 'image'                # Image-based (future)


class Question(db.Model):
    """Question model"""
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False, index=True)
    subject = db.Column(db.String(80), nullable=False, index=True)
    topic = db.Column(db.String(120), nullable=False, index=True)
    subtopic = db.Column(db.String(120))
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.Enum(QuestionType), default=QuestionType.MCQ, nullable=False)
    options = db.Column(db.Text)  # JSON string
    correct_answer = db.Column(db.Text, nullable=False)  # JSON or string
    explanation = db.Column(db.Text)
    difficulty = db.Column(db.String(20), default='medium')  # easy, medium, hard
    ai_generated = db.Column(db.Boolean, default=False, index=True)
    ai_quality_score = db.Column(db.Float)  # 0-100
    approved = db.Column(db.Boolean, default=False, index=True)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = db.relationship('Organization', back_populates='questions')
    approver = db.relationship('User')
    feedbacks = db.relationship('QuestionFeedback', back_populates='question', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Question {self.id} - {self.subject}/{self.topic}>'

    def get_options(self):
        """Parse options JSON"""
        if self.options:
            return json.loads(self.options)
        return []

    def set_options(self, options):
        """Set options as JSON"""
        self.options = json.dumps(options)

    def get_correct_answer(self):
        """Parse correct answer JSON"""
        try:
            return json.loads(self.correct_answer)
        except (json.JSONDecodeError, TypeError):
            return self.correct_answer

    def to_dict(self, include_answer=False):
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'subject': self.subject,
            'topic': self.topic,
            'subtopic': self.subtopic,
            'question_text': self.question_text,
            'question_type': self.question_type.value,
            'options': self.get_options(),
            'difficulty': self.difficulty,
            'explanation': self.explanation,
            'ai_generated': self.ai_generated,
        }
        if include_answer:
            data['correct_answer'] = self.get_correct_answer()
        return data


class QuestionFeedback(db.Model):
    """Question feedback from students"""
    __tablename__ = 'question_feedbacks'

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False, index=True)
    feedback_type = db.Column(db.String(50), nullable=False)  # unclear, incorrect, too_easy, too_hard
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    question = db.relationship('Question', back_populates='feedbacks')

    def __repr__(self):
        return f'<QuestionFeedback {self.feedback_type} for Question {self.question_id}>'
