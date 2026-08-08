"""Socket.IO event handlers for real-time gameplay"""
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from flask import request, g
from backend.services import AuthService, GameService, AnalyticsService
from backend.models import Game, GamePlayer, GameRound, Question, Answer, GameStatus
from backend.database import db
from datetime import datetime, timedelta
import redis
import json

# Redis for game state synchronization
redis_client = None


def init_redis(app):
    """Initialize Redis connection"""
    global redis_client
    redis_client = redis.from_url(app.config['REDIS_URL'])


def register_socket_events(socketio):
    """Register Socket.IO event handlers"""

    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        print(f'Client connected: {request.sid}')
        emit('connect_response', {'data': 'Connected to server'})

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        print(f'Client disconnected: {request.sid}')

    @socketio.on('authenticate')
    def handle_authenticate(data):
        """Authenticate socket connection"""
        try:
            token = data.get('token')
            user_id = AuthService.verify_token(token)
            g.user_id = user_id
            g.socket_id = request.sid
            emit('authenticated', {'success': True})
        except ValueError:
            emit('authenticated', {'success': False, 'error': 'Invalid token'})
            disconnect()

    @socketio.on('join_game')
    def handle_join_game(data):
        """Handle player joining game"""
        try:
            user_id = g.get('user_id')
            if not user_id:
                emit('error', {'message': 'Not authenticated'})
                return

            room_code = data.get('room_code')
            game = GameService.get_game_by_code(room_code)
            if not game:
                emit('error', {'message': 'Game not found'})
                return

            from backend.models import User
            user = User.query.get(user_id)
            nickname = data.get('nickname', user.display_name)

            player = GameService.add_player(game, user, nickname)
            join_room(f'game_{game.id}')

            # Broadcast player joined
            socketio.emit('player_joined', {
                'game_id': game.id,
                'player': player.to_dict(),
                'total_players': GamePlayer.query.filter_by(game_id=game.id).count()
            }, room=f'game_{game.id}')

            emit('join_success', {'game': game.to_dict(), 'player': player.to_dict()})
        except ValueError as e:
            emit('error', {'message': str(e)})

    @socketio.on('start_game')
    def handle_start_game(data):
        """Handle game start (teacher only)"""
        try:
            game_id = data.get('game_id')
            game = Game.query.get(game_id)
            if not game:
                emit('error', {'message': 'Game not found'})
                return

            # Transition state
            GameService.transition_game_state(game, GameStatus.STARTING)
            
            # Countdown
            socketio.emit('countdown', {'count': 3}, room=f'game_{game.id}')
            
            # After countdown, start game
            def start_after_countdown():
                GameService.transition_game_state(game, GameStatus.ACTIVE)
                socketio.emit('game_started', {'game': game.to_dict()}, room=f'game_{game.id}')
                emit_next_question(game)

            socketio.start_background_task(start_after_countdown)
        except Exception as e:
            emit('error', {'message': str(e)})

    @socketio.on('submit_answer')
    def handle_submit_answer(data):
        """Handle answer submission"""
        try:
            user_id = g.get('user_id')
            game_id = data.get('game_id')
            round_id = data.get('round_id')
            answer_text = data.get('answer')
            response_time_ms = data.get('response_time_ms', 0)

            game = Game.query.get(game_id)
            if not game or game.status != GameStatus.ACTIVE:
                emit('error', {'message': 'Game not active'})
                return

            player = GamePlayer.query.filter_by(game_id=game_id, user_id=user_id).first()
            if not player:
                emit('error', {'message': 'Player not found'})
                return

            round_obj = GameRound.query.get(round_id)
            if not round_obj:
                emit('error', {'message': 'Round not found'})
                return

            # Submit answer (server-authoritative)
            answer, is_correct, score = GameService.submit_answer(
                game, player, round_obj, answer_text, response_time_ms
            )

            # Emit to all players in game
            socketio.emit('answer_received', {
                'player_id': player.id,
                'is_correct': is_correct,
                'score_earned': score
            }, room=f'game_{game.id}')

            emit('answer_confirmed', {'is_correct': is_correct, 'score': score})

        except ValueError as e:
            emit('error', {'message': str(e)})

    @socketio.on('pause_game')
    def handle_pause_game(data):
        """Pause game (teacher only)"""
        try:
            game_id = data.get('game_id')
            game = Game.query.get(game_id)
            GameService.transition_game_state(game, GameStatus.PAUSED)
            socketio.emit('game_paused', {'game': game.to_dict()}, room=f'game_{game.id}')
        except Exception as e:
            emit('error', {'message': str(e)})

    @socketio.on('resume_game')
    def handle_resume_game(data):
        """Resume game (teacher only)"""
        try:
            game_id = data.get('game_id')
            game = Game.query.get(game_id)
            GameService.transition_game_state(game, GameStatus.ACTIVE)
            socketio.emit('game_resumed', {'game': game.to_dict()}, room=f'game_{game.id}')
        except Exception as e:
            emit('error', {'message': str(e)})

    @socketio.on('end_game')
    def handle_end_game(data):
        """End game (teacher only)"""
        try:
            game_id = data.get('game_id')
            game = Game.query.get(game_id)
            GameService.transition_game_state(game, GameStatus.FINISHED)
            
            # Get results
            results = GameService.get_game_results(game)
            
            socketio.emit('game_finished', {
                'game': game.to_dict(),
                'results': results
            }, room=f'game_{game.id}')
        except Exception as e:
            emit('error', {'message': str(e)})


def emit_next_question(game):
    """Emit next question to all players"""
    # Get current round number
    current_round = GameRound.query.filter_by(game_id=game.id).order_by(
        GameRound.round_number.desc()
    ).first()
    round_number = (current_round.round_number if current_round else 0) + 1

    if round_number > game.question_count:
        # Game finished
        return

    # Get random question
    questions = GameService.get_game_questions(game)
    question = questions[round_number - 1] if round_number <= len(questions) else None

    if not question:
        return

    # Create game round
    round_obj = GameRound(
        game_id=game.id,
        question_id=question.id,
        round_number=round_number,
        started_at=datetime.utcnow()
    )
    db.session.add(round_obj)
    db.session.commit()

    # Emit question (without answer)
    socketio.emit('question_started', {
        'round': round_number,
        'total_rounds': game.question_count,
        'question': {
            'id': question.id,
            'text': question.question_text,
            'type': question.question_type.value,
            'options': question.get_options(),
            'time_limit': game.time_per_question
        }
    }, room=f'game_{game.id}')
