"""
文件处理服务
"""

import os
import uuid
import logging
from typing import Optional, Dict, Any
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from src.utils.validators import validate_video_file, get_file_info

logger = logging.getLogger(__name__)

class FileService:
    """文件处理服务类"""
    
    def __init__(self, upload_folder: str = 'uploads'):
        """
        初始化文件服务
        
        Args:
            upload_folder: 上传文件存储目录
        """
        self.upload_folder = upload_folder
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """确保必要的目录存在"""
        os.makedirs(self.upload_folder, exist_ok=True)
    
    def save_uploaded_file(self, file: FileStorage, task_id: str) -> str:
        """
        保存上传的文件
        
        Args:
            file: Flask文件对象
            task_id: 任务ID
            
        Returns:
            保存的文件路径
            
        Raises:
            ValueError: 文件验证失败
            IOError: 文件保存失败
        """
        # 验证文件
        is_valid, error_msg = validate_video_file(file)
        if not is_valid:
            raise ValueError(f"文件验证失败: {error_msg}")
        
        # 生成安全的文件名
        original_filename = file.filename
        safe_filename = secure_filename(original_filename)
        
        # 生成唯一文件名
        file_ext = os.path.splitext(safe_filename)[1]
        unique_filename = f"{task_id}{file_ext}"
        
        # 构建完整路径
        file_path = os.path.join(self.upload_folder, unique_filename)
        
        try:
            # 保存文件
            file.save(file_path)
            
            # 验证文件完整性
            if not os.path.exists(file_path):
                raise IOError("文件保存失败")
            
            # 获取文件信息
            file_info = get_file_info(file_path)
            logger.info(f"文件保存成功: {file_path}, 大小: {file_info.get('size', 0)} bytes")
            
            return file_path
            
        except Exception as e:
            logger.error(f"文件保存失败: {str(e)}")
            # 清理失败的文件
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
            raise IOError(f"文件保存失败: {str(e)}")
    
    def get_file_size(self, file_path: str) -> int:
        """
        获取文件大小
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件大小（字节）
        """
        try:
            return os.path.getsize(file_path)
        except OSError:
            return 0
    
    def delete_file(self, file_path: str) -> bool:
        """
        删除文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否删除成功
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"文件删除成功: {file_path}")
                return True
            return True  # 文件不存在也返回True，表示"删除"成功
        except Exception as e:
            logger.error(f"文件删除失败: {file_path}, 错误: {str(e)}")
            return False
    
    def get_file_extension(self, filename: str) -> str:
        """
        获取文件扩展名
        
        Args:
            filename: 文件名
            
        Returns:
            文件扩展名（包含点）
        """
        return os.path.splitext(filename)[1]
    
    def ensure_directory_exists(self, directory_path: str) -> None:
        """
        确保目录存在
        
        Args:
            directory_path: 目录路径
        """
        os.makedirs(directory_path, exist_ok=True)
    
    def cleanup_task_files(self, task_id: str) -> Dict[str, bool]:
        """
        清理任务相关的所有文件
        
        Args:
            task_id: 任务ID
            
        Returns:
            清理结果字典
        """
        results = {
            'upload': False,
            'audio': False,
            'subtitle': False
        }
        
        # 查找并删除上传文件
        for filename in os.listdir(self.upload_folder):
            if filename.startswith(task_id):
                file_path = os.path.join(self.upload_folder, filename)
                results['upload'] = self.delete_file(file_path)
                break
        
        # 查找并删除音频文件
        audio_folder = 'audio'
        if os.path.exists(audio_folder):
            for filename in os.listdir(audio_folder):
                if filename.startswith(task_id):
                    file_path = os.path.join(audio_folder, filename)
                    results['audio'] = self.delete_file(file_path)
                    break
        
        # 查找并删除字幕文件
        subtitle_folder = 'subtitles'
        if os.path.exists(subtitle_folder):
            for filename in os.listdir(subtitle_folder):
                if filename.startswith(task_id):
                    file_path = os.path.join(subtitle_folder, filename)
                    results['subtitle'] = self.delete_file(file_path)
                    break
        
        return results
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        获取存储信息
        
        Returns:
            存储信息字典
        """
        try:
            total_size = 0
            file_count = 0
            
            # 统计上传目录
            for root, dirs, files in os.walk(self.upload_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        total_size += os.path.getsize(file_path)
                        file_count += 1
                    except OSError:
                        pass
            
            # 获取磁盘空间信息
            stat = os.statvfs(self.upload_folder)
            free_space = stat.f_bavail * stat.f_frsize
            total_space = stat.f_blocks * stat.f_frsize
            used_space = total_space - free_space
            
            return {
                'upload_folder': self.upload_folder,
                'total_files': file_count,
                'total_size': total_size,
                'disk_space': {
                    'total': total_space,
                    'used': used_space,
                    'free': free_space,
                    'usage_percent': (used_space / total_space * 100) if total_space > 0 else 0
                }
            }
            
        except Exception as e:
            logger.error(f"获取存储信息失败: {str(e)}")
            return {
                'error': str(e),
                'upload_folder': self.upload_folder
            }

    def list_uploaded_videos(self) -> Dict[str, Any]:
        """
        列举上传目录下的视频文件（按扩展名过滤）

        Returns:
            包含文件列表及其元信息的字典
        """
        try:
            allowed_ext = {'.mp4', '.mov', '.avi', '.wmv'}
            files = []
            for entry in os.listdir(self.upload_folder):
                full = os.path.join(self.upload_folder, entry)
                if os.path.isfile(full):
                    _, ext = os.path.splitext(entry)
                    if ext.lower() in allowed_ext:
                        try:
                            stat = os.stat(full)
                            files.append({
                                'filename': entry,
                                'path': full,
                                'size': stat.st_size,
                                'modified_at': stat.st_mtime
                            })
                        except OSError:
                            continue

            return {
                'upload_folder': self.upload_folder,
                'total_files': len(files),
                'files': sorted(files, key=lambda x: x['filename'])
            }
        except Exception as e:
            logger.error(f"列举上传文件失败: {str(e)}")
            return {'error': str(e), 'upload_folder': self.upload_folder}