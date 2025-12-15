#!/usr/bin/env python3
"""
视频字幕生成器 - Flask后端主应用
基于 faster-whisper 和 ffmpeg 技术栈
"""

import os
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import ffmpeg

from src.models.process_record import ProcessRecord, db
from src.services.file_service import FileService
from src.services.audio_service import AudioService
from src.services.subtitle_service import SubtitleService
from src.utils.validators import validate_video_file
from src.utils.response import success_response, error_response

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 创建Flask应用
def create_app():
    app = Flask(__name__)
    
    # 配置CORS
    CORS(app, origins=['http://localhost:3000', 'http://localhost:5173'])
    
    # 加载配置
    app.config.from_object('config.Config')
    
    # 初始化数据库
    db.init_app(app)
    with app.app_context():
        db.create_all()
    
    return app

app = create_app()

# 服务实例
file_service = FileService()
audio_service = AudioService()
subtitle_service = SubtitleService()
import threading

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """
    上传视频文件
    
    Returns:
        JSON响应包含任务ID和文件信息
    """
    try:
        if 'file' not in request.files:
            return error_response('INVALID_FILE', '没有上传文件')
        
        file = request.files['file']
        if file.filename == '':
            return error_response('INVALID_FILE', '文件名为空')
        
        # 验证文件
        is_valid, error_msg = validate_video_file(file)
        if not is_valid:
            return error_response('INVALID_FILE', error_msg)
        
        # 保存文件
        task_id = str(uuid.uuid4())
        original_filename = secure_filename(file.filename)
        
        # 保存上传文件
        file_path = file_service.save_uploaded_file(file, task_id)
        
        # 创建处理记录
        record = ProcessRecord(
            id=task_id,
            original_filename=original_filename,
            stored_filename=f"{task_id}_{original_filename}",
            file_path=file_path,
            status='pending',
            progress=0
        )
        db.session.add(record)
        db.session.commit()
        
        logger.info(f"文件上传成功: {original_filename}, 任务ID: {task_id}")
        
        return success_response({
            'task_id': task_id,
            'filename': original_filename,
            'status': 'pending',
            'message': '文件上传成功，等待处理'
        })
        
    except RequestEntityTooLarge:
        return error_response('FILE_TOO_LARGE', '文件大小超过限制')
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        return error_response('INTERNAL_ERROR', '文件上传失败')

@app.route('/api/extract-audio', methods=['POST'])
def extract_audio():
    """
    从视频中提取音频
    
    Request Body:
        task_id: 任务ID
        
    Returns:
        JSON响应包含音频文件路径和处理状态
    """
    try:
        data = request.get_json()
        if not data or 'task_id' not in data:
            return error_response('INVALID_REQUEST', '缺少任务ID')
        
        task_id = data['task_id']
        
        # 获取处理记录
        record = ProcessRecord.query.get(task_id)
        if not record:
            return error_response('TASK_NOT_FOUND', '任务不存在')
        
        # 更新状态
        record.status = 'extracting'
        record.progress = 30
        db.session.commit()
        
        # 提取音频
        audio_filename = f"{task_id}.wav"
        audio_path = os.path.join(audio_service.audio_folder, audio_filename)
        audio_service.extract_audio(record.file_path, audio_path)
        
        # 更新记录
        record.audio_path = audio_path
        record.status = 'transcribing'
        record.progress = 60
        db.session.commit()
        
        logger.info(f"音频提取成功: 任务ID {task_id}")
        
        return success_response({
            'task_id': task_id,
            'audio_path': audio_path,
            'status': 'transcribing',
            'progress': 60,
            'message': '音频提取成功，开始生成字幕'
        })
        
    except Exception as e:
        logger.error(f"音频提取失败: {str(e)}")
        
        # 更新失败状态
        if 'record' in locals():
            record.status = 'failed'
            record.error_message = str(e)
            db.session.commit()
        
        return error_response('AUDIO_EXTRACTION_FAILED', f'音频提取失败: {str(e)}')

@app.route('/api/generate-subtitle', methods=['POST'])
def generate_subtitle():
    """
    生成字幕文件
    
    Request Body:
        task_id: 任务ID
        
    Returns:
        JSON响应包含字幕文件路径和内容
    """
    try:
        data = request.get_json()
        if not data or 'task_id' not in data:
            return error_response('INVALID_REQUEST', '缺少任务ID')
        
        task_id = data['task_id']
        
        # 获取处理记录
        record = ProcessRecord.query.get(task_id)
        if not record:
            return error_response('TASK_NOT_FOUND', '任务不存在')
        
        if not record.audio_path:
            return error_response('AUDIO_NOT_FOUND', '音频文件不存在')
        
        # 生成字幕
        subtitle_result = subtitle_service.generate_subtitle(record.audio_path, task_id)
        
        # 更新记录
        record.subtitle_path = subtitle_result['subtitle_path']
        record.status = 'completed'
        record.progress = 100
        db.session.commit()
        
        logger.info(f"字幕生成成功: 任务ID {task_id}")
        
        return success_response({
            'task_id': task_id,
            'subtitle_path': subtitle_result['subtitle_path'],
            'content': subtitle_result['content'],
            'status': 'completed',
            'progress': 100,
            'message': '字幕生成完成'
        })
        
    except Exception as e:
        logger.error(f"字幕生成失败: {str(e)}")
        
        # 更新失败状态
        if 'record' in locals():
            record.status = 'failed'
            record.error_message = str(e)
            db.session.commit()
        
        return error_response('SUBTITLE_GENERATION_FAILED', f'字幕生成失败: {str(e)}')

@app.route('/api/status/<task_id>', methods=['GET'])
def get_status(task_id: str):
    """
    查询任务状态
    
    Args:
        task_id: 任务ID
        
    Returns:
        JSON响应包含任务状态信息
    """
    try:
        record = ProcessRecord.query.get(task_id)
        if not record:
            return error_response('TASK_NOT_FOUND', '任务不存在')
        
        return success_response({
            'task_id': task_id,
            'status': record.status,
            'progress': record.progress,
            'message': record.error_message or get_status_message(record.status),
            'error_code': record.error_message,
            'filename': record.original_filename,
            'created_at': record.created_at.isoformat(),
            'updated_at': record.updated_at.isoformat()
        })
        
    except Exception as e:
        logger.error(f"查询状态失败: {str(e)}")
        return error_response('INTERNAL_ERROR', '查询状态失败')

@app.route('/api/download/<task_id>', methods=['GET'])
def download_subtitle(task_id: str):
    """
    下载字幕文件
    
    Args:
        task_id: 任务ID
        
    Returns:
        字幕文件下载
    """
    try:
        record = ProcessRecord.query.get(task_id)
        if not record:
            return error_response('TASK_NOT_FOUND', '任务不存在')
        
        if not record.subtitle_path or not os.path.exists(record.subtitle_path):
            return error_response('SUBTITLE_NOT_FOUND', '字幕文件不存在')
        
        # 生成下载文件名
        base_filename = os.path.splitext(record.original_filename)[0]
        download_filename = f"{base_filename}.srt"
        
        return send_file(
            record.subtitle_path,
            as_attachment=True,
            download_name=download_filename,
            mimetype='text/plain'
        )
        
    except Exception as e:
        logger.error(f"下载字幕失败: {str(e)}")
        return error_response('DOWNLOAD_FAILED', '下载字幕文件失败')

def get_status_message(status: str) -> str:
    """获取状态对应的描述信息"""
    status_messages = {
        'pending': '等待处理',
        'processing': '正在初始化',
        'extracting': '正在提取音频',
        'transcribing': '正在生成字幕',
        'completed': '处理完成',
        'failed': '处理失败'
    }
    return status_messages.get(status, '未知状态')


@app.route('/api/uploads', methods=['GET'])
def list_uploads():
    """
    列出服务器上传目录下的视频文件
    """
    try:
        info = file_service.list_uploaded_videos()
        if 'error' in info:
            return error_response('LIST_FAILED', info.get('error', '列举失败'))
        return success_response(info)
    except Exception as e:
        logger.error(f"列出上传文件失败: {str(e)}")
        return error_response('INTERNAL_ERROR', '列出上传文件失败')


def _process_task_background(task_id: str, file_path: str):
    """后台执行提取音频与生成字幕流程（同步调用服务）。"""
    try:
        # 更新记录状态
        record = ProcessRecord.query.get(task_id)
        if not record:
            logger.error(f"找不到记录 {task_id} 用于处理")
            return

        record.status = 'extracting'
        record.progress = 20
        db.session.commit()

        # 提取音频
        audio_filename = f"{task_id}.wav"
        audio_path = os.path.join(audio_service.audio_folder, audio_filename)
        audio_service.extract_audio(file_path, audio_path)

        record.audio_path = audio_path
        record.status = 'transcribing'
        record.progress = 60
        db.session.commit()

        # 生成字幕
        subtitle_result = subtitle_service.generate_subtitle(audio_path, task_id)

        record.subtitle_path = subtitle_result.get('subtitle_path')
        record.status = 'completed'
        record.progress = 100
        db.session.commit()
        logger.info(f"后台处理完成: {task_id}")

    except Exception as e:
        logger.error(f"后台处理失败 {task_id}: {str(e)}")
        if 'record' in locals() and record:
            record.status = 'failed'
            record.error_message = str(e)
            db.session.commit()


@app.route('/api/process-existing', methods=['POST'])
def process_existing():
    """
    基于服务器上已存在的上传文件启动处理流程。
    请求体: { "filename": "xxx.mp4" } 或 { "file_path": "/absolute/path" }
    返回: task_id
    """
    try:
        data = request.get_json() or {}
        filename = data.get('filename')
        file_path = data.get('file_path')

        if not filename and not file_path:
            return error_response('INVALID_REQUEST', '缺少 filename 或 file_path')

        if filename:
            file_path = os.path.join(file_service.upload_folder, filename)

        if not os.path.exists(file_path):
            return error_response('FILE_NOT_FOUND', '指定的文件在服务端不存在')

        # 创建任务记录
        task_id = str(uuid.uuid4())
        original_filename = os.path.basename(file_path)

        record = ProcessRecord(
            id=task_id,
            original_filename=original_filename,
            stored_filename=original_filename,
            file_path=file_path,
            status='pending',
            progress=0
        )
        db.session.add(record)
        db.session.commit()

        # 在后台线程中处理，避免阻塞API
        t = threading.Thread(target=_process_task_background, args=(task_id, file_path), daemon=True)
        t.start()

        return success_response({'task_id': task_id, 'message': '处理已在后台开始'})

    except Exception as e:
        logger.error(f"启动已存在文件处理失败: {str(e)}")
        return error_response('INTERNAL_ERROR', '启动处理失败')

@app.errorhandler(413)
def request_entity_too_large(error):
    """处理文件过大错误"""
    return error_response('FILE_TOO_LARGE', '文件大小超过限制')

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return success_response({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

if __name__ == '__main__':
    # 确保必要的目录存在
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('audio', exist_ok=True)
    os.makedirs('subtitles', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # 启动应用
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('FLASK_PORT', '5000')),
        debug=os.getenv('FLASK_ENV') == 'development'
    )