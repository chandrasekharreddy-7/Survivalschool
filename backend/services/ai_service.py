"""Sarvam AI Integration Service"""
import requests
import json
from typing import List, Dict, Any, Optional
from backend.models import Question, QuestionType
from backend.config import Config
from datetime import datetime


class AIProvider:
    """Base AI Provider interface"""

    def generate_questions(self, subject: str, grade: str, topic: str,
                          count: int, difficulty: str, **kwargs) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def validate_question(self, question: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class SarvamAIProvider(AIProvider):
    """Sarvam AI implementation"""

    def __init__(self, api_key: str, api_url: str):
        self.api_key = api_key
        self.api_url = api_url
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }

    def generate_questions(self, subject: str, grade: str, topic: str,
                          count: int, difficulty: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Generate questions using Sarvam AI
        
        Args:
            subject: Subject area (e.g., "Mathematics")
            grade: Grade level (e.g., "10")
            topic: Specific topic (e.g., "Algebra")
            count: Number of questions to generate
            difficulty: Difficulty level (easy/medium/hard)
        
        Returns:
            List of generated question dictionaries
        """
        prompt = self._build_generation_prompt(
            subject, grade, topic, count, difficulty
        )

        try:
            response = requests.post(
                f'{self.api_url}/generate',
                json={
                    'prompt': prompt,
                    'max_tokens': 2000,
                    'temperature': 0.7,
                    'top_p': 0.9,
                },
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            questions = self._parse_generated_questions(result.get('text', ''))
            return questions
        except requests.RequestException as e:
            raise RuntimeError(f'AI generation failed: {str(e)}')

    def validate_question(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and score question quality
        """
        issues = []
        score = 100

        # Check for ambiguous wording
        text = question.get('question_text', '').lower()
        ambiguous_words = ['might', 'could', 'perhaps', 'somewhat', 'roughly']
        if any(word in text for word in ambiguous_words):
            issues.append('Potentially ambiguous wording')
            score -= 10

        # Check options validity
        options = question.get('options', [])
        if len(options) < 2:
            issues.append('Insufficient answer options')
            score -= 20

        # Check correct answer
        correct = question.get('correct_answer')
        if not correct:
            issues.append('Missing correct answer')
            score -= 30
        elif correct not in options:
            issues.append('Correct answer not in options')
            score -= 20

        # Check explanation
        if not question.get('explanation'):
            issues.append('Missing explanation')
            score -= 10

        return {
            'valid': score >= 70,
            'score': max(0, score),
            'issues': issues,
        }

    def _build_generation_prompt(self, subject: str, grade: str, topic: str,
                                 count: int, difficulty: str) -> str:
        """
        Build the prompt for AI question generation
        """
        return f"""
Generate {count} multiple-choice questions for a classroom assessment.

Subject: {subject}
Grade: {grade}
Topic: {topic}
Difficulty: {difficulty}

For each question, provide in JSON format:
{{
  "question_text": "The question here",
  "options": ["Option A", "Option B", "Option C", "Option D"],
  "correct_answer": "Option A",
  "explanation": "Why Option A is correct..."
}}

Return only valid JSON, no other text. Generate questions that are:
- Clear and unambiguous
- Educationally appropriate
- Differentiated by difficulty level
- Not duplicates of common exam questions

Return an array of questions.
"""

    def _parse_generated_questions(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse AI response into structured questions
        """
        questions = []
        try:
            # Try to extract JSON array
            start = text.find('[')
            end = text.rfind(']') + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
                parsed = json.loads(json_str)
                if isinstance(parsed, list):
                    questions = parsed
                elif isinstance(parsed, dict) and 'questions' in parsed:
                    questions = parsed['questions']
        except json.JSONDecodeError:
            pass
        return questions


class LocalAIProvider(AIProvider):
    """Local/mock AI provider for development"""

    def generate_questions(self, subject: str, grade: str, topic: str,
                          count: int, difficulty: str, **kwargs) -> List[Dict[str, Any]]:
        """Generate mock questions for development"""
        return [
            {
                'question_text': f'Sample {subject} question {i + 1}',
                'options': ['Option A', 'Option B', 'Option C', 'Option D'],
                'correct_answer': 'Option A',
                'explanation': 'This is a sample question for development'
            }
            for i in range(count)
        ]

    def validate_question(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """Mock validation"""
        return {'valid': True, 'score': 85, 'issues': []}


class AIService:
    """High-level AI service wrapper"""

    def __init__(self, provider: Optional[AIProvider] = None):
        if provider is None:
            # Use Sarvam AI if configured, else local provider
            if Config.SARVAM_API_KEY and Config.AI_ENABLED:
                provider = SarvamAIProvider(
                    api_key=Config.SARVAM_API_KEY,
                    api_url=Config.SARVAM_API_URL
                )
            else:
                provider = LocalAIProvider()
        self.provider = provider

    def generate_questions(self, subject: str, grade: str, topic: str,
                          count: int, difficulty: str = 'medium') -> List[Dict[str, Any]]:
        """Generate questions through provider"""
        try:
            questions = self.provider.generate_questions(
                subject, grade, topic, count, difficulty
            )
            return questions
        except Exception as e:
            raise RuntimeError(f'Question generation failed: {str(e)}')

    def validate_and_score_questions(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate questions and add quality scores"""
        validated = []
        for question in questions:
            validation = self.provider.validate_question(question)
            question['quality_validation'] = validation
            validated.append(question)
        return validated
