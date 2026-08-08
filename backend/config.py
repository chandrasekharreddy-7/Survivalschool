import os
from datetime import timedelta


class Config:
    """Base configuration"""
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = False
    TESTING = False

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://survivalschool:survivalschool@localhost:5432/survivalschool'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
    }

    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    # JWT
    JWT_SECRET = os.getenv('JWT_SECRET', 'dev-jwt-secret-change-in-production')
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRATION = timedelta(hours=24)

    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')

    # Sarvam AI
    SARVAM_API_KEY = os.getenv('SARVAM_API_KEY')
    SARVAM_API_URL = os.getenv('SARVAM_API_URL', 'https://api.sarvam.ai')

    # Server
    SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
    SERVER_PORT = int(os.getenv('SERVER_PORT', 5000))

    # Features
    AI_ENABLED = os.getenv('AI_ENABLED', 'True').lower() == 'true'
    AI_VALIDATION_ENABLED = os.getenv('AI_VALIDATION_ENABLED', 'True').lower() == 'true'

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    REDIS_URL = 'redis://localhost:6379/1'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False


def get_config():
    """Get configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'development')
    if env == 'production':
        return ProductionConfig
    elif env == 'testing':
        return TestingConfig
    return DevelopmentConfig
