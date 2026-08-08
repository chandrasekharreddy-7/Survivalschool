"""API Routes"""
from flask import Blueprint, request, jsonify, g
from backend.services import AuthService, GameService, QuestionService, AnalyticsService, AIService
from backend.models import (
    User, UserRole, Organization, Classroom, Game, GamePlayer, GameMode,
    QuestionType, Question
)
from backend.database import db
from datetime import datetime

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')
auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register new user"""
    data = request.get_json()
    
    try:
        # Validate input
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password required'}), 400
        
        # Get or create organization
        org_code = data.get('organization_code', 'default')
        org = Organization.query.filter_by(code=org_code).first()
        if not org:
            org = Organization(
                code=org_code,
                name=data.get('organization_name', org_code),
                type='school'
            )
            db.session.add(org)
            db.session.commit()
        
        role = UserRole(data.get('role', 'student'))
        user, token = AuthService.register(
            username=data.get('username', data.get('email').split('@')[0]),
            email=data.get('email'),
            password=data.get('password'),
            organization_id=org.id,
            role=role
        )
        
        return jsonify({
            'success': True,
            'user': user.to_dict(),
            'token': token
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Registration failed'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user"""
    data = request.get_json()
    
    try:
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password required'}), 400
        
        user, token = AuthService.login(
            email=data.get('email'),
            password=data.get('password')
        )
        
        return jsonify({
            'success': True,
            'user': user.to_dict(),
            'token': token
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 401
    except Exception as e:
        return jsonify({'error': 'Login failed'}), 500


@auth_bp.route('/me', methods=['GET'])
@AuthService.require_auth
def get_current_user():
    """Get current user profile"""
    user = AuthService.get_current_user()
    return jsonify(user.to_dict()), 200


# ============================================================================
# GAME ROUTES
# ============================================================================

@api_bp.route('/games', methods=['POST'])
@AuthService.require_auth
@AuthService.require_role(UserRole.TEACHER)
def create_game():
    """Create a new game"""
    user = AuthService.get_current_user()
    data = request.get_json()
    
    try:
        game = GameService.create_game(
            organization_id=user.organization_id,
            classroom_id=data.get('classroom_id'),
            host_id=user.id,
            title=data.get('title'),
            subject=data.get('subject'),
            topic=data.get('topic'),
            difficulty=data.get('difficulty', 'medium'),
            mode=GameMode(data.get('mode', 'classic_survival')),
            question_count=data.get('question_count', 10),
            time_per_question=data.get('time_per_question', 30),
            max_players=data.get('max_players', 100)
        )
        
        return jsonify({
            'success': True,
            'game': game.to_dict(),
            'room_code': game.room_code,
            'join_pin': game.join_pin
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Game creation failed'}), 500


@api_bp.route('/games/<room_code>', methods=['GET'])
@AuthService.require_auth
def get_game(room_code):
    """Get game details"""
    game = GameService.get_game_by_code(room_code)
    if not game:
        return jsonify({'error': 'Game not found'}), 404
    
    # Get players
    players = GamePlayer.query.filter_by(game_id=game.id).all()
    
    return jsonify({
        'game': game.to_dict(),
        'players': [p.to_dict() for p in players],
        'player_count': len(players)
    }), 200


@api_bp.route('/games/<int:game_id>/join', methods=['POST'])
@AuthService.require_auth
def join_game(game_id):
    """Join a game"""
    user = AuthService.get_current_user()
    data = request.get_json()
    
    try:
        game = Game.query.get(game_id)
        if not game:
            return jsonify({'error': 'Game not found'}), 404
        
        player = GameService.add_player(
            game=game,
            user=user,
            nickname=data.get('nickname', user.display_name)
        )
        
        return jsonify({
            'success': True,
            'player': player.to_dict()
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Failed to join game'}), 500


@api_bp.route('/games/<int:game_id>/results', methods=['GET'])
@AuthService.require_auth
def get_game_results(game_id):
    """Get game results"""
    game = Game.query.get(game_id)
    if not game:
        return jsonify({'error': 'Game not found'}), 404
    
    results = GameService.get_game_results(game)
    return jsonify({'results': results}), 200


# ============================================================================
# QUESTION ROUTES
# ============================================================================

@api_bp.route('/questions', methods=['POST'])
@AuthService.require_auth
@AuthService.require_role(UserRole.TEACHER, UserRole.ADMIN)
def create_question():
    """Create a new question"""
    user = AuthService.get_current_user()
    data = request.get_json()
    
    try:
        question = QuestionService.create_question(
            organization_id=user.organization_id,
            subject=data.get('subject'),
            topic=data.get('topic'),
            question_text=data.get('question_text'),
            question_type=QuestionType(data.get('question_type', 'mcq')),
            options=data.get('options', []),
            correct_answer=data.get('correct_answer'),
            difficulty=data.get('difficulty', 'medium'),
            explanation=data.get('explanation', ''),
            ai_generated=False
        )
        
        return jsonify({
            'success': True,
            'question': question.to_dict()
        }), 201
    except Exception as e:
        return jsonify({'error': 'Question creation failed'}), 500


@api_bp.route('/questions/generate', methods=['POST'])
@AuthService.require_auth
@AuthService.require_role(UserRole.TEACHER, UserRole.ADMIN)
def generate_questions():
    """Generate questions using AI"""
    user = AuthService.get_current_user()
    data = request.get_json()
    
    try:
        ai_service = AIService()
        questions = ai_service.generate_questions(
            subject=data.get('subject'),
            grade=data.get('grade'),
            topic=data.get('topic'),
            count=data.get('count', 5),
            difficulty=data.get('difficulty', 'medium')
        )
        
        # Validate questions
        validated = ai_service.validate_and_score_questions(questions)
        
        return jsonify({
            'success': True,
            'questions': validated
        }), 200
    except Exception as e:
        return jsonify({'error': f'Generation failed: {str(e)}'}), 500


@api_bp.route('/questions/topic', methods=['GET'])
@AuthService.require_auth
def get_questions_by_topic():
    """Get questions by subject and topic"""
    user = AuthService.get_current_user()
    subject = request.args.get('subject')
    topic = request.args.get('topic')
    
    if not subject or not topic:
        return jsonify({'error': 'Subject and topic required'}), 400
    
    questions = QuestionService.get_questions_by_topic(
        organization_id=user.organization_id,
        subject=subject,
        topic=topic,
        approved_only=True
    )
    
    return jsonify({
        'questions': [q.to_dict() for q in questions]
    }), 200


# ============================================================================
# ANALYTICS ROUTES
# ============================================================================

@api_bp.route('/analytics/student/<int:student_id>', methods=['GET'])
@AuthService.require_auth
def get_student_analytics(student_id):
    """Get student analytics"""
    user = AuthService.get_current_user()
    
    # Only allow student to view own analytics or teacher/admin to view classroom
    if user.role == UserRole.STUDENT and user.id != student_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    stats = AnalyticsService.get_student_stats(student_id)
    if not stats:
        return jsonify({'error': 'Student not found'}), 404
    
    return jsonify(stats), 200


@api_bp.route('/analytics/classroom/<int:classroom_id>', methods=['GET'])
@AuthService.require_auth
@AuthService.require_role(UserRole.TEACHER, UserRole.ADMIN)
def get_classroom_analytics(classroom_id):
    """Get classroom analytics"""
    stats = AnalyticsService.get_classroom_stats(classroom_id)
    return jsonify(stats), 200


@api_bp.route('/analytics/game/<int:game_id>', methods=['GET'])
@AuthService.require_auth
def get_game_analytics(game_id):
    """Get game analytics"""
    analytics = AnalyticsService.get_game_analytics(game_id)
    if not analytics:
        return jsonify({'error': 'Game not found'}), 404
    return jsonify(analytics), 200


# ============================================================================
# CLASSROOM ROUTES
# ============================================================================

@api_bp.route('/classrooms', methods=['POST'])
@AuthService.require_auth
@AuthService.require_role(UserRole.TEACHER)
def create_classroom():
    """Create a new classroom"""
    user = AuthService.get_current_user()
    data = request.get_json()
    
    try:
        classroom = Classroom(
            organization_id=user.organization_id,
            teacher_id=user.id,
            name=data.get('name'),
            subject=data.get('subject'),
            grade=data.get('grade'),
            academic_year=data.get('academic_year')
        )
        db.session.add(classroom)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'classroom': classroom.to_dict()
        }), 201
    except Exception as e:
        return jsonify({'error': 'Classroom creation failed'}), 500


@api_bp.route('/classrooms/<int:classroom_id>', methods=['GET'])
@AuthService.require_auth
def get_classroom(classroom_id):
    """Get classroom details"""
    classroom = Classroom.query.get(classroom_id)
    if not classroom:
        return jsonify({'error': 'Classroom not found'}), 404
    
    return jsonify(classroom.to_dict()), 200
