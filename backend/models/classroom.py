"""Classroom model"""
from datetime import datetime
from backend.database import db


class Classroom(db.Model):
    """Classroom model"""
    __tablename__ = 'classrooms'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False, index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(80))
    grade = db.Column(db.String(20))
    academic_year = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = db.relationship('Organization', back_populates='classrooms')
    teacher = db.relationship('User', back_populates='classrooms', foreign_keys=[teacher_id])
    students = db.relationship('ClassroomStudent', back_populates='classroom', cascade='all, delete-orphan')
    games = db.relationship('Game', back_populates='classroom', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Classroom {self.name}>'

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'subject': self.subject,
            'grade': self.grade,
            'academic_year': self.academic_year,
            'student_count': len(self.students),
            'created_at': self.created_at.isoformat(),
        }


class ClassroomStudent(db.Model):
    """Classroom Student association"""
    __tablename__ = 'classroom_students'

    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    status = db.Column(db.String(20), default='active', index=True)  # active, inactive, removed
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    classroom = db.relationship('Classroom', back_populates='students')
    student = db.relationship('User', back_populates='classroom_students')

    __table_args__ = (
        db.UniqueConstraint('classroom_id', 'student_id', name='unique_classroom_student'),
    )

    def __repr__(self):
        return f'<ClassroomStudent {self.student_id} in {self.classroom_id}>'
