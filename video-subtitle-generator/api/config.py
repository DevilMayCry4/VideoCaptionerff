"""
Flask应用配置文件
"""

import os
from datetime import timedelta

class Config:
    """基础配置类"""
    
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///video_subtitle.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    AUDIO_FOLDER = os.environ.get('AUDIO_FOLDER') or 'audio'
    SUBTITLE_FOLDER = os.environ.get('SUBTITLE_FOLDER') or 'subtitles'
    
    # 允许的文件扩展名
    ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.wmv'}
    ALLOWED_VIDEO_MIME_TYPES = {
        'video/mp4',
        'video/quicktime',
        'video/x-msvideo',
        'video/x-ms-wmv'
    }
    
    # Whisper配置
    WHISPER_MODEL = os.environ.get('WHISPER_MODEL') or 'base'
    WHISPER_LANGUAGE = os.environ.get('WHISPER_LANGUAGE') or 'auto'
    WHISPER_DEVICE = os.environ.get('WHISPER_DEVICE') or 'auto'
    
    # 处理配置
    MAX_WORKERS = int(os.environ.get('MAX_WORKERS', 4))
    PROCESS_TIMEOUT = int(os.environ.get('PROCESS_TIMEOUT', 3600))  # 1小时
    
    # Redis配置（用于异步任务）
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_DB = int(os.environ.get('REDIS_DB', 0))
    
    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.log')
    
    # CORS配置
    CORS_ORIGINS = [
        'http://localhost:3000',
        'http://localhost:5173',
        'http://127.0.0.1:3000',
        'http://127.0.0.1:5173'
    ]

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    TESTING = False
    
class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    TESTING = False
    
class TestingConfig(Config):
    """测试环境配置"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# 配置映射
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}