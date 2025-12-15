"""
文件验证工具函数
"""

import os
import mimetypes
from typing import Tuple, Optional
from werkzeug.datastructures import FileStorage

# 常量定义
ALLOWED_EXTENSIONS = {'.mp4', '.mov', '.avi', '.wmv'}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB

def validate_video_file(file: FileStorage) -> Tuple[bool, Optional[str]]:
    """
    验证视频文件
    
    Args:
        file: Flask文件对象
        
    Returns:
        (是否有效, 错误信息)
    """
    if not file or not hasattr(file, 'filename'):
        return False, "文件对象无效"
    
    if not file.filename:
        return False, "文件名为空"
    
    # 检查文件内容
    try:
        file.stream.seek(0, os.SEEK_END)
        file_size = file.stream.tell()
        file.stream.seek(0)  # 重置文件指针
        
        if file_size == 0:
            return False, "文件为空"
    except Exception:
        return False, "无法读取文件内容"
    
    # 检查文件扩展名
    filename = file.filename.lower()
    allowed_extensions = {'.mp4', '.mov', '.avi', '.wmv'}
    
    file_ext = os.path.splitext(filename)[1]
    if file_ext not in allowed_extensions:
        return False, f"不支持的视频格式，支持的格式: {', '.join(allowed_extensions)}"
    
    # 检查文件大小
    try:
        file.stream.seek(0, os.SEEK_END)
        file_size = file.stream.tell()
        file.stream.seek(0)  # 重置文件指针
        
        if file_size > MAX_FILE_SIZE:
            return False, f"文件大小超过限制（{MAX_FILE_SIZE // (1024 * 1024)}MB）"
    except Exception:
        return False, "无法获取文件大小"
    
    # 检查MIME类型
    allowed_mime_types = {
        'video/mp4',
        'video/quicktime',
        'video/x-msvideo',
        'video/x-ms-wmv'
    }
    
    # 如果文件对象有content_type属性，使用它
    if hasattr(file, 'content_type') and file.content_type:
        if file.content_type not in allowed_mime_types:
            # MIME类型不匹配，但扩展名正确，给出警告但不拒绝
            pass  # 允许通过，因为很多文件可能没有正确的MIME类型
    
    return True, ''

def validate_file_size(file_path: str, max_size_mb: int = 500) -> Tuple[bool, Optional[str]]:
    """
    验证文件大小
    
    Args:
        file_path: 文件路径
        max_size_mb: 最大文件大小（MB）
        
    Returns:
        (是否有效, 错误信息)
    """
    try:
        file_size = os.path.getsize(file_path)
        max_size_bytes = max_size_mb * 1024 * 1024
        
        if file_size > max_size_bytes:
            return False, f"文件大小超过限制（{max_size_mb}MB）"
        
        return True, ''
    except OSError:
        return False, "无法获取文件大小"

def get_file_info(file_path: str) -> dict:
    """
    获取文件信息
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件信息字典
    """
    try:
        stat = os.stat(file_path)
        return {
            'size': stat.st_size,
            'created': stat.st_ctime,
            'modified': stat.st_mtime,
            'extension': os.path.splitext(file_path)[1].lower(),
            'mime_type': mimetypes.guess_type(file_path)[0]
        }
    except OSError:
        return {}

def is_video_file(filename: str) -> bool:
    """
    判断是否为视频文件
    
    Args:
        filename: 文件名
        
    Returns:
        是否为视频文件
    """
    if not filename:
        return False
    
    video_extensions = {'.mp4', '.mov', '.avi', '.wmv', '.mkv', '.flv', '.webm'}
    file_ext = os.path.splitext(filename.lower())[1]
    
    return file_ext in video_extensions

def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除危险字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        安全的文件名
    """
    import re
    
    # 移除路径分隔符
    filename = filename.replace('/', '').replace('\\', '')
    
    # 移除特殊字符
    filename = re.sub(r'[<>:"|?*]', '', filename)
    
    # 限制长度
    max_length = 255
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = name[:max_length - len(ext)] + ext
    
    return filename.strip()