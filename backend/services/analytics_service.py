"""Analytics service"""
from datetime import datetime, timedelta
from typing import Dict, Any, List
from backend.models import (
    Answer, Game, GamePlayer, Question, StudentProgress, User
)
from backend.database import db
from sqlalchemy import func


class AnalyticsService:
    """Analytics and reporting service"""

    @staticmethod
    def get_student_stats(student_id: int, subject: Optional[str] = None) -> Dict[str, Any]:
        """Get student statistics"""
        progress = StudentProgress.query.filter_by(student_id=student_id).first()
        if not progress:
            return {}

        # Get recent games
        recent_games = db.session.query(Game).join(
            GamePlayer
        ).filter(
            GamePlayer.user_id == student_id
        ).order_by(
            Game.created_at.desc()
        ).limit(10).all()

        return {
            'total_games': len(recent_games),
            'accuracy': progress.accuracy,
            'xp': progress.xp,
            'level': progress.level,
            'best_streak': progress.best_streak,
            'current_streak': progress.current_streak,
            'recent_games': [g.to_dict() for g in recent_games],
        }

    @staticmethod
    def get_classroom_stats(classroom_id: int) -> Dict[str, Any]:
        """Get classroom statistics"""
        # Get all games in classroom
        games = Game.query.filter_by(classroom_id=classroom_id).all()
        
        total_games = len(games)
        total_players = GamePlayer.query.filter(
            GamePlayer.game_id.in_([g.id for g in games])
        ).count()

        # Average accuracy across all games
        avg_accuracy = db.session.query(
            func.avg(func.cast(
                func.sum(
                    func.cast(Answer.is_correct, db.Integer)
                ) / func.count(Answer.id) * 100,
                db.Float
            ))
        ).filter(
            Answer.game_id.in_([g.id for g in games])
        ).scalar() or 0

        return {
            'total_games': total_games,
            'total_players': total_players,
            'average_accuracy': round(avg_accuracy, 2),
            'games': [g.to_dict() for g in games[-5:]],  # Last 5 games
        }

    @staticmethod
    def get_game_analytics(game_id: int) -> Dict[str, Any]:
        """Get detailed game analytics"""
        game = Game.query.get(game_id)
        if not game:
            return {}

        players = GamePlayer.query.filter_by(game_id=game_id).all()
        answers = Answer.query.filter_by(game_id=game_id).all()

        # Answer distribution by question
        answer_distribution = {}
        for answer in answers:
            if answer.question_id not in answer_distribution:
                answer_distribution[answer.question_id] = {'correct': 0, 'incorrect': 0}
            if answer.is_correct:
                answer_distribution[answer.question_id]['correct'] += 1
            else:
                answer_distribution[answer.question_id]['incorrect'] += 1

        # Player stats
        player_stats = []
        for player in players:
            player_answers = [a for a in answers if a.player_id == player.id]
            correct = sum(1 for a in player_answers if a.is_correct)
            total = len(player_answers)
            accuracy = (correct / total * 100) if total > 0 else 0
            avg_response_time = sum(a.response_time_ms for a in player_answers) // total if total > 0 else 0

            player_stats.append({
                'player': player.to_dict(),
                'accuracy': round(accuracy, 2),
                'avg_response_time': avg_response_time,
                'questions_answered': total,
            })

        return {
            'game': game.to_dict(),
            'total_players': len(players),
            'total_answers': len(answers),
            'answer_distribution': answer_distribution,
            'player_stats': player_stats,
        }

    @staticmethod
    def update_student_progress(student_id: int) -> StudentProgress:
        """Recalculate student progress based on recent answers"""
        progress = StudentProgress.query.filter_by(student_id=student_id).first()
        if not progress:
            progress = StudentProgress(student_id=student_id)
            db.session.add(progress)

        # Get all answers from last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        answers = Answer.query.join(GamePlayer).filter(
            GamePlayer.user_id == student_id,
            Answer.submitted_at >= thirty_days_ago
        ).all()

        if answers:
            total = len(answers)
            correct = sum(1 for a in answers if a.is_correct)
            avg_response_time = sum(a.response_time_ms for a in answers) // total

            progress.questions_attempted = total
            progress.correct_answers = correct
            progress.accuracy = (correct / total * 100) if total > 0 else 0
            progress.average_response_time = avg_response_time
            progress.last_practiced = datetime.utcnow()

        db.session.commit()
        return progress
