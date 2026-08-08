"""Audit logging models"""
from datetime import datetime
from backend.database import db
import json


class AuditLog(db.Model):
    """Audit log for tracking user actions"""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100), nullable=False, index=True)
    entity = db.Column(db.String(100), nullable=False)  # e.g., 'game', 'question', 'user'
    entity_id = db.Column(db.Integer)
    changes = db.Column(db.Text)  # JSON of changes
    ip_address = db.Column(db.String(45))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relationships
    actor = db.relationship('User')

    def __repr__(self):
        return f'<AuditLog {self.action} on {self.entity} at {self.timestamp}>'

    def set_changes(self, changes: dict):
        """Set changes as JSON"""
        self.changes = json.dumps(changes)

    def get_changes(self):
        """Get changes from JSON"""
        if self.changes:
            return json.loads(self.changes)
        return {}
