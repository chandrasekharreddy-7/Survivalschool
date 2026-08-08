"""Authentication service"""
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, g, current_app, jsonify
from backend.models import User, UserRole, Organization
from backend.database import db
from typing import Optional, Tuple, Dict, Any


class AuthService:
    """Authentication and authorization service"""

    @staticmethod
    def register(username: str, email: str, password: str, 
                 organization_id: int, role: UserRole = UserRole.STUDENT) -> Tuple[User, str]:
        """Register a new user"""
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            raise ValueError('Email already registered')
        if User.query.filter_by(username=username).first():
            raise ValueError('Username already taken')

        # Create new user
        user = User(
            username=username,
            email=email,
            organization_id=organization_id,
            role=role,
            display_name=username,
            is_active=True
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        # Generate JWT token
        token = AuthService.generate_token(user.id)
        return user, token

    @staticmethod
    def login(email: str, password: str) -> Tuple[User, str]:
        """Login user and return JWT token"""
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            raise ValueError('Invalid email or password')
        
        if not user.is_active:
            raise ValueError('User account is inactive')

        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()

        # Generate JWT token
        token = AuthService.generate_token(user.id)
        return user, token

    @staticmethod
    def generate_token(user_id: int, expires_in: Optional[timedelta] = None) -> str:
        """Generate JWT token for user"""
        if expires_in is None:
            expires_in = current_app.config['JWT_EXPIRATION']

        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + expires_in,
            'iat': datetime.utcnow()
        }

        token = jwt.encode(
            payload,
            current_app.config['JWT_SECRET'],
            algorithm=current_app.config['JWT_ALGORITHM']
        )
        return token

    @staticmethod
    def verify_token(token: str) -> Optional[int]:
        """Verify JWT token and return user_id"""
        try:
            payload = jwt.decode(
                token,
                current_app.config['JWT_SECRET'],
                algorithms=[current_app.config['JWT_ALGORITHM']]
            )
            return payload.get('user_id')
        except jwt.ExpiredSignatureError:
            raise ValueError('Token has expired')
        except jwt.InvalidTokenError:
            raise ValueError('Invalid token')

    @staticmethod
    def get_current_user() -> Optional[User]:
        """Get current authenticated user from request context"""
        return g.get('current_user')

    @staticmethod
    def require_auth(f):
        """Decorator to require authentication"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({'error': 'Missing authorization header'}), 401

            try:
                token = auth_header.split(' ')[1]
                user_id = AuthService.verify_token(token)
                user = User.query.get(user_id)
                if not user:
                    return jsonify({'error': 'User not found'}), 401
                g.current_user = user
            except (ValueError, IndexError) as e:
                return jsonify({'error': str(e)}), 401

            return f(*args, **kwargs)
        return decorated_function

    @staticmethod
    def require_role(*roles: UserRole):
        """Decorator to require specific role(s)"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                user = AuthService.get_current_user()
                if not user or user.role not in roles:
                    return jsonify({'error': 'Insufficient permissions'}), 403
                return f(*args, **kwargs)
            return decorated_function
        return decorator
