"""Notification model"""
from datetime import datetime
from backend.database import db


class Notification(db.Model):
    """User notification"""
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    type = db.Column(db.String(50), nullable=False)  # game_invitation, game_result, achievement
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = db.relationship('User', back_populates='notifications')

    def __repr__(self):
        return f'<Notification {self.type} for User {self.user_id}>'

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'type': self.type,
            'title': self.title,
            'message': self.message,
            'read': self.read,
            'created_at': self.created_at.isoformat(),
        }
