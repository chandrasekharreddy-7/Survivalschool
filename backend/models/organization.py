"""Organization model"""
from datetime import datetime
from backend.database import db
import uuid


class Organization(db.Model):
    """Organization model for multi-tenancy"""
    __tablename__ = 'organizations'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    type = db.Column(db.String(50), default='school')  # school, college, institution
    status = db.Column(db.String(20), default='active', index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = db.relationship('User', back_populates='organization', cascade='all, delete-orphan')
    classrooms = db.relationship('Classroom', back_populates='organization', cascade='all, delete-orphan')
    games = db.relationship('Game', back_populates='organization', cascade='all, delete-orphan')
    questions = db.relationship('Question', back_populates='organization', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Organization {self.code} - {self.name}>'

    @staticmethod
    def generate_code() -> str:
        """Generate unique organization code"""
        return str(uuid.uuid4())[:8].upper()

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'type': self.type,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
        }
