"""User model"""
from datetime import datetime
from enum import Enum
from backend.database import db
from werkzeug.security import generate_password_hash, check_password_hash


class UserRole(str, Enum):
    """User role enumeration"""
    ADMIN = 'admin'
    TEACHER = 'teacher'
    STUDENT = 'student'


class User(db.Model):
    """User model"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), default=UserRole.STUDENT, nullable=False, index=True)
    display_name = db.Column(db.String(120))
    avatar_url = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relationships
    organization = db.relationship('Organization', back_populates='users')
    classrooms = db.relationship('Classroom', back_populates='teacher', foreign_keys='Classroom.teacher_id')
    classroom_students = db.relationship('ClassroomStudent', back_populates='student')
    games = db.relationship('Game', back_populates='host')
    game_players = db.relationship('GamePlayer', back_populates='user')
    answers = db.relationship('Answer', back_populates='player')
    progress = db.relationship('StudentProgress', back_populates='student', uselist=False)
    achievements = db.relationship('StudentAchievement', back_populates='student')
    notifications = db.relationship('Notification', back_populates='user')

    def __repr__(self):
        return f'<User {self.username} ({self.role.value})>'

    def set_password(self, password: str) -> None:
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify password"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role.value,
            'display_name': self.display_name,
            'avatar_url': self.avatar_url,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
        }
