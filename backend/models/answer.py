"""Answer model"""
from datetime import datetime
from backend.database import db


class Answer(db.Model):
    """Player answer to a question"""
    __tablename__ = 'answers'

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False, index=True)
    round_id = db.Column(db.Integer, db.ForeignKey('game_rounds.id'), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False, index=True)
    player_id = db.Column(db.Integer, db.ForeignKey('game_players.id'), nullable=False, index=True)
    answer = db.Column(db.Text, nullable=False)  # User's answer
    is_correct = db.Column(db.Boolean, nullable=False)
    response_time_ms = db.Column(db.Integer)  # Time taken to answer
    score_earned = db.Column(db.Integer, default=0)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    game = db.relationship('Game', back_populates='answers')
    round = db.relationship('GameRound', back_populates='answers')
    question = db.relationship('Question')
    player = db.relationship('GamePlayer', back_populates='answers')

    __table_args__ = (
        db.Index('idx_game_round_player', 'game_id', 'round_id', 'player_id'),
        db.Index('idx_player_question', 'player_id', 'question_id'),
    )

    def __repr__(self):
        return f'<Answer Player {self.player_id} - Round {self.round_id} - {"Correct" if self.is_correct else "Incorrect"}>'

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'answer': self.answer,
            'is_correct': self.is_correct,
            'response_time_ms': self.response_time_ms,
            'score_earned': self.score_earned,
            'submitted_at': self.submitted_at.isoformat(),
        }
