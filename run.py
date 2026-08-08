"""Application entry point"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from backend.app import create_app
from backend.sockets import init_redis

if __name__ == '__main__':
    app, socketio = create_app()
    
    # Initialize Redis
    init_redis(app)
    
    # Get host and port from config
    host = app.config.get('SERVER_HOST', '0.0.0.0')
    port = app.config.get('SERVER_PORT', 5000)
    debug = app.config.get('DEBUG', False)
    
    print(f'🎮 SurvivalSchool Backend')
    print(f'📡 Starting on {host}:{port}')
    print(f'🔗 WebSocket enabled')
    
    socketio.run(app, host=host, port=port, debug=debug)
