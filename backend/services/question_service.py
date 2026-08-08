"""Question service"""
from typing import List, Optional, Dict, Any
from backend.models import Question, QuestionType, Organization, User
from backend.database import db
import json


class QuestionService:
    """Question management service"""

    @staticmethod
    def create_question(organization_id: int, subject: str, topic: str,
                       question_text: str, question_type: QuestionType,
                       options: List[str], correct_answer: str,
                       difficulty: str = 'medium', explanation: str = '',
                       ai_generated: bool = False, ai_quality_score: float = 0) -> Question:
        """Create a new question"""
        question = Question(
            organization_id=organization_id,
            subject=subject,
            topic=topic,
            question_text=question_text,
            question_type=question_type,
            difficulty=difficulty,
            explanation=explanation,
            ai_generated=ai_generated,
            ai_quality_score=ai_quality_score,
            approved=not ai_generated  # Manual questions auto-approved
        )
        question.set_options(options)
        question.correct_answer = correct_answer if isinstance(correct_answer, str) else json.dumps(correct_answer)

        db.session.add(question)
        db.session.commit()
        return question

    @staticmethod
    def get_questions_by_topic(organization_id: int, subject: str, topic: str,
                              approved_only: bool = True,
                              limit: int = 100) -> List[Question]:
        """Get questions by subject and topic"""
        query = Question.query.filter_by(
            organization_id=organization_id,
            subject=subject,
            topic=topic
        )
        if approved_only:
            query = query.filter_by(approved=True)
        return query.limit(limit).all()

    @staticmethod
    def approve_question(question: Question, approved_by: User) -> Question:
        """Approve a question for use"""
        question.approved = True
        question.approved_by = approved_by.id
        db.session.commit()
        return question

    @staticmethod
    def get_random_questions(organization_id: int, subject: str, topic: str,
                            count: int = 10, difficulty: Optional[str] = None) -> List[Question]:
        """Get random questions for a game"""
        from sqlalchemy import func
        query = Question.query.filter_by(
            organization_id=organization_id,
            subject=subject,
            topic=topic,
            approved=True
        )
        if difficulty:
            query = query.filter_by(difficulty=difficulty)
        return query.order_by(func.random()).limit(count).all()
