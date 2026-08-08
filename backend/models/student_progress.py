"""Student progress and achievement models"""
from datetime import datetime
from backend.database import db


class StudentProgress(db.Model):
    """Student progress tracking"""
    __tablename__ = 'student_progress'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True, index=True)
    subject = db.Column(db.String(80))
    topic = db.Column(db.String(120))
    questions_attempted = db.Column(db.Integer, default=0)
    correct_answers = db.Column(db.Integer, default=0)
    accuracy = db.Column(db.Float, default=0.0)  # percentage
    average_response_time = db.Column(db.Integer, default=0)  # ms
    current_streak = db.Column(db.Integer, default=0)
    best_streak = db.Column(db.Integer, default=0)
    mastery_score = db.Column(db.Float, default=0.0)  # 0-100
    improvement_rate = db.Column(db.Float, default=0.0)  # percentage
    xp = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)
    last_practiced = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    student = db.relationship('User', back_populates='progress')

    def __repr__(self):
        return f'<StudentProgress Student {self.student_id}>'

    def calculate_accuracy(self):
        """Calculate accuracy percentage"""
        if self.questions_attempted == 0:
            return 0.0
        return round((self.correct_answers / self.questions_attempted) * 100, 2)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'questions_attempted': self.questions_attempted,
            'correct_answers': self.correct_answers,
            'accuracy': self.accuracy,
            'average_response_time': self.average_response_time,
            'current_streak': self.current_streak,
            'best_streak': self.best_streak,
            'mastery_score': self.mastery_score,
            'xp': self.xp,
            'level': self.level,
        }


class Achievement(db.Model):
    """Achievement definition"""
    __tablename__ = 'achievements'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    description = db.Column(db.Text)
    icon = db.Column(db.String(255))  # URL or icon name
    criteria = db.Column(db.Text)  # JSON criteria

    def __repr__(self):
        return f'<Achievement {self.name}>'


class StudentAchievement(db.Model):
    """Student achievement earned"""
    __tablename__ = 'student_achievements'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievements.id'), nullable=False)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    student = db.relationship('User', back_populates='achievements')
    achievement = db.relationship('Achievement')

    __table_args__ = (
        db.UniqueConstraint('student_id', 'achievement_id', name='unique_student_achievement'),
    )

    def __repr__(self):
        return f'<StudentAchievement {self.achievement_id} for Student {self.student_id}>'
