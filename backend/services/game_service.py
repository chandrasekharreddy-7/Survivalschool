"""Game service for game management"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from backend.models import (
    Game, GamePlayer, GameRound, GameStatus, GameMode,
    Question, Answer, User, Classroom
)
from backend.database import db
import json


class GameService:
    """Game management and state machine"""

    # Valid state transitions
    VALID_TRANSITIONS = {
        GameStatus.CREATED: [GameStatus.WAITING],
        GameStatus.WAITING: [GameStatus.STARTING, GameStatus.CREATED],
        GameStatus.STARTING: [GameStatus.ACTIVE],
        GameStatus.ACTIVE: [GameStatus.PAUSED, GameStatus.FINISHED],
        GameStatus.PAUSED: [GameStatus.ACTIVE, GameStatus.FINISHED],
        GameStatus.FINISHED: [],
    }

    @staticmethod
    def create_game(organization_id: int, classroom_id: int, host_id: int,
                   title: str, subject: str, topic: str, difficulty: str,
                   mode: GameMode, question_count: int, time_per_question: int,
                   max_players: int = 100) -> Game:
        """Create a new game"""
        # Verify classroom exists and belongs to organization
        classroom = Classroom.query.filter_by(
            id=classroom_id,
            organization_id=organization_id
        ).first()
        if not classroom:
            raise ValueError('Classroom not found')

        # Generate unique codes
        room_code = Game.generate_room_code()
        while Game.query.filter_by(room_code=room_code).first():
            room_code = Game.generate_room_code()

        join_pin = Game.generate_join_pin()
        while Game.query.filter_by(join_pin=join_pin).first():
            join_pin = Game.generate_join_pin()

        game = Game(
            organization_id=organization_id,
            classroom_id=classroom_id,
            host_id=host_id,
            room_code=room_code,
            join_pin=join_pin,
            title=title,
            subject=subject,
            topic=topic,
            difficulty=difficulty,
            mode=mode,
            question_count=question_count,
            time_per_question=time_per_question,
            max_players=max_players,
            status=GameStatus.CREATED
        )

        db.session.add(game)
        db.session.commit()
        return game

    @staticmethod
    def get_game_by_code(room_code: str) -> Optional[Game]:
        """Get game by room code"""
        return Game.query.filter_by(room_code=room_code).first()

    @staticmethod
    def get_game_by_pin(join_pin: str) -> Optional[Game]:
        """Get game by join PIN"""
        return Game.query.filter_by(join_pin=join_pin).first()

    @staticmethod
    def add_player(game: Game, user: User, nickname: str) -> GamePlayer:
        """Add player to game"""
        # Check if game is in valid state
        if game.status not in [GameStatus.CREATED, GameStatus.WAITING, GameStatus.STARTING]:
            raise ValueError(f'Cannot join game with status {game.status.value}')

        # Check player limit
        active_players = GamePlayer.query.filter_by(
            game_id=game.id,
            status='active'
        ).count()
        if active_players >= game.max_players:
            raise ValueError('Game is full')

        # Check if player already joined
        existing = GamePlayer.query.filter_by(
            game_id=game.id,
            user_id=user.id
        ).first()
        if existing:
            raise ValueError('Player already joined this game')

        player = GamePlayer(
            game_id=game.id,
            user_id=user.id,
            nickname=nickname,
            status='active',
            score=0,
            lives=3 if game.mode == GameMode.THREE_LIVES else 1,
            streak=0,
            best_streak=0
        )

        db.session.add(player)
        db.session.commit()
        return player

    @staticmethod
    def transition_game_state(game: Game, new_status: GameStatus) -> bool:
        """Transition game to new state (state machine)"""
        current = game.status
        valid_next = GameService.VALID_TRANSITIONS.get(current, [])

        if new_status not in valid_next:
            raise ValueError(
                f'Invalid state transition from {current.value} to {new_status.value}'
            )

        game.status = new_status

        # Set timestamps
        if new_status == GameStatus.STARTING:
            game.started_at = datetime.utcnow()
        elif new_status == GameStatus.FINISHED:
            game.ended_at = datetime.utcnow()

        db.session.commit()
        return True

    @staticmethod
    def submit_answer(game: Game, player: GamePlayer, round_obj: GameRound,
                     answer_text: str, response_time_ms: int) -> Tuple[Answer, bool, int]:
        """Submit answer and return (answer_obj, is_correct, score)"""
        question = round_obj.question

        # Validate submission
        if game.status != GameStatus.ACTIVE:
            raise ValueError('Game is not active')

        if player.status == 'eliminated':
            raise ValueError('Player is eliminated')

        # Check for duplicate submission (idempotency)
        existing = Answer.query.filter_by(
            game_id=game.id,
            round_id=round_obj.id,
            player_id=player.id
        ).first()
        if existing:
            return existing, existing.is_correct, existing.score_earned

        # Check correct answer
        correct_answer = question.get_correct_answer()
        is_correct = GameService._compare_answers(answer_text, correct_answer)

        # Calculate score
        score = GameService._calculate_score(
            is_correct, response_time_ms, game.time_per_question,
            question.difficulty, player.streak
        )

        # Create answer record
        answer = Answer(
            game_id=game.id,
            round_id=round_obj.id,
            question_id=question.id,
            player_id=player.id,
            answer=answer_text,
            is_correct=is_correct,
            response_time_ms=response_time_ms,
            score_earned=score if is_correct else 0
        )

        # Update player
        if is_correct:
            player.score += score
            player.streak += 1
            if player.streak > player.best_streak:
                player.best_streak = player.streak
        else:
            player.streak = 0
            if game.mode == GameMode.THREE_LIVES:
                player.lives -= 1
                if player.lives <= 0:
                    player.status = 'eliminated'
                    player.eliminated_at = datetime.utcnow()
            elif game.mode in [GameMode.CLASSIC_SURVIVAL, GameMode.STREAK]:
                player.status = 'eliminated'
                player.eliminated_at = datetime.utcnow()

        db.session.add(answer)
        db.session.commit()
        return answer, is_correct, score if is_correct else 0

    @staticmethod
    def _compare_answers(user_answer: str, correct_answer: Any) -> bool:
        """Compare user answer with correct answer (case-insensitive)"""
        if isinstance(correct_answer, list):
            return str(user_answer).strip().lower() in [str(x).strip().lower() for x in correct_answer]
        return str(user_answer).strip().lower() == str(correct_answer).strip().lower()

    @staticmethod
    def _calculate_score(is_correct: bool, response_time_ms: int, time_limit_ms: int,
                        difficulty: str, streak: int) -> int:
        """Calculate score for correct answer"""
        if not is_correct:
            return 0

        # Base score
        base = 100

        # Speed bonus (up to 50)
        time_ratio = min(response_time_ms / time_limit_ms, 1.0)
        speed_bonus = int((1.0 - time_ratio) * 50)

        # Difficulty multiplier
        difficulty_multiplier = {
            'easy': 1.0,
            'medium': 1.25,
            'hard': 1.5
        }.get(difficulty, 1.0)

        # Streak bonus
        streak_bonus = 0
        if streak >= 10:
            streak_bonus = int((base + speed_bonus) * 0.30)
        elif streak >= 5:
            streak_bonus = int((base + speed_bonus) * 0.20)
        elif streak >= 3:
            streak_bonus = int((base + speed_bonus) * 0.10)

        score = int((base + speed_bonus + streak_bonus) * difficulty_multiplier)
        return score

    @staticmethod
    def get_game_results(game: Game) -> Dict[str, Any]:
        """Get final game results"""
        players = GamePlayer.query.filter_by(game_id=game.id).all()
        
        # Rank players by score
        ranked = sorted(
            [(p, p.score, p.best_streak) for p in players],
            key=lambda x: (-x[1], -x[2])
        )

        results = []
        for rank, (player, score, streak) in enumerate(ranked, 1):
            answers = Answer.query.filter_by(
                game_id=game.id,
                player_id=player.id
            ).all()
            correct = sum(1 for a in answers if a.is_correct)
            total = len(answers)
            accuracy = (correct / total * 100) if total > 0 else 0

            results.append({
                'rank': rank,
                'player': player.to_dict(),
                'score': score,
                'accuracy': round(accuracy, 2),
                'streak': streak,
                'questions_answered': total,
                'correct_answers': correct,
            })

        return results
