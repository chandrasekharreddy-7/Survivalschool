"""Flask application factory"""
from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
from backend.config import get_config
from backend.database import db, init_db
import logging
from logging.handlers import RotatingFileHandler
import os


def create_app(config_class=None):
    """Create and configure Flask application"""
    if config_class is None:
        config_class = get_config()

    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    CORS(app, origins=app.config.get('CORS_ORIGINS', ['http://localhost:3000']))

    socketio = SocketIO(
        app,
        cors_allowed_origins=app.config.get('CORS_ORIGINS', ['http://localhost:3000']),
        ping_timeout=60,
        ping_interval=25,
        async_mode='threading'
    )

    # Setup logging
    _setup_logging(app)

    # Register blueprints
    from backend.routes import api_bp, auth_bp
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)

    # Register socket events
    from backend.sockets import register_socket_events
    register_socket_events(socketio)

    # Initialize database
    with app.app_context():
        init_db(app)

    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health():
        return {'status': 'healthy'}, 200

    return app, socketio


def _setup_logging(app):
    """Configure logging"""
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler(
            'logs/survivalschool.log',
            maxBytes=10240000,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(app.config.get('LOG_LEVEL', 'INFO'))
        app.logger.addHandler(file_handler)
        app.logger.setLevel(app.config.get('LOG_LEVEL', 'INFO'))
        app.logger.info('SurvivalSchool startup')
