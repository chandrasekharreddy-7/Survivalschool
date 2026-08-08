"""Game models"""
from datetime import datetime
from enum import Enum
from backend.database import db
import secrets
import string


class GameMode(str, Enum):
    """Game mode enumeration"""
    CLASSIC_SURVIVAL = 'classic_survival'  # Wrong answer = elimination
    THREE_LIVES = 'three_lives'            # Wrong answer removes one life
    STREAK = 'streak'                      # Maintain streak
    TIME_RUSH = 'time_rush'                # Shorter time limits
    PRACTICE = 'practice'                  # No elimination
    TEAM = 'team'                          # Team competition
    TOURNAMENT = 'tournament'              # Multi-stage
    TEACHER_CHALLENGE = 'teacher_challenge'  # Teacher selected


class GameStatus(str, Enum):
    """Game status enumeration"""
    CREATED = 'created'
    WAITING = 'waiting'
    STARTING = 'starting'
    ACTIVE = 'active'
    PAUSED = 'paused'
    FINISHED = 'finished'


class Game(db.Model):
    """Game model"""
    __tablename__ = 'games'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False, index=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False, index=True)
    host_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    room_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    join_pin = db.Column(db.String(10), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(80))
    topic = db.Column(db.String(120))
    difficulty = db.Column(db.String(20), default='medium')  # easy, medium, hard
    mode = db.Column(db.Enum(GameMode), default=GameMode.CLASSIC_SURVIVAL, nullable=False)
    max_players = db.Column(db.Integer, default=100)
    question_count = db.Column(db.Integer, default=10)
    time_per_question = db.Column(db.Integer, default=30)  # seconds
    status = db.Column(db.Enum(GameStatus), default=GameStatus.CREATED, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    started_at = db.Column(db.DateTime)
    ended_at = db.Column(db.DateTime)

    # Relationships
    organization = db.relationship('Organization', back_populates='games')
    classroom = db.relationship('Classroom', back_populates='games')
    host = db.relationship('User', back_populates='games')
    players = db.relationship('GamePlayer', back_populates='game', cascade='all, delete-orphan')
    rounds = db.relationship('GameRound', back_populates='game', cascade='all, delete-orphan')
    answers = db.relationship('Answer', back_populates='game', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Game {self.room_code} - {self.title}>'

    @staticmethod
    def generate_room_code() -> str:
        """Generate unique room code (e.g., SS-7K9P)"""
        chars = string.ascii_uppercase + string.digits
        code = 'SS-' + ''.join(secrets.choice(chars) for _ in range(4))
        return code

    @staticmethod
    def generate_join_pin() -> str:
        """Generate unique join PIN (e.g., 5832)"""
        return ''.join(secrets.choice(string.digits) for _ in range(4))

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'room_code': self.room_code,
            'join_pin': self.join_pin,
            'title': self.title,
            'subject': self.subject,
            'topic': self.topic,
            'difficulty': self.difficulty,
            'mode': self.mode.value,
            'status': self.status.value,
            'player_count': len(self.players),
            'question_count': self.question_count,
            'time_per_question': self.time_per_question,
            'created_at': self.created_at.isoformat(),
        }


class GamePlayer(db.Model):
    """Game participant"""
    __tablename__ = 'game_players'

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    nickname = db.Column(db.String(80), nullable=False)
    status = db.Column(db.String(20), default='active', index=True)  # active, eliminated, completed
    score = db.Column(db.Integer, default=0)
    lives = db.Column(db.Integer, default=3)
    streak = db.Column(db.Integer, default=0)
    best_streak = db.Column(db.Integer, default=0)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    eliminated_at = db.Column(db.DateTime)
    final_rank = db.Column(db.Integer)
    reconnect_count = db.Column(db.Integer, default=0)

    # Relationships
    game = db.relationship('Game', back_populates='players')
    user = db.relationship('User', back_populates='game_players')
    answers = db.relationship('Answer', back_populates='player')

    def __repr__(self):
        return f'<GamePlayer {self.nickname} in Game {self.game_id}>'

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'nickname': self.nickname,
            'status': self.status,
            'score': self.score,
            'lives': self.lives,
            'streak': self.streak,
            'best_streak': self.best_streak,
            'final_rank': self.final_rank,
        }


class GameRound(db.Model):
    """Game round/question"""
    __tablename__ = 'game_rounds'

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False, index=True)
    round_number = db.Column(db.Integer, nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)
    eliminated_count = db.Column(db.Integer, default=0)

    # Relationships
    game = db.relationship('Game', back_populates='rounds')
    question = db.relationship('Question')
    answers = db.relationship('Answer', back_populates='round')

    def __repr__(self):
        return f'<GameRound {self.round_number} in Game {self.game_id}>'
