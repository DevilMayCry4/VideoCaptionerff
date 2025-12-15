"""
音频处理服务
使用ffmpeg从视频中提取音频
"""

import os
import subprocess
import logging
from typing import Optional, Dict, Any
import ffmpeg

logger = logging.getLogger(__name__)

class AudioService:
    """音频处理服务类"""
    
    def __init__(self, audio_folder: str = 'audio'):
        """
        初始化音频服务
        
        Args:
            audio_folder: 音频文件存储目录
        """
        self.audio_folder = audio_folder
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """确保必要的目录存在"""
        os.makedirs(self.audio_folder, exist_ok=True)
    
    def extract_audio(self, video_path: str, output_path: str, 
                     sample_rate: int = 16000, channels: int = 1) -> str:
        """
        从视频中提取音频
        
        Args:
            video_path: 视频文件路径
            output_path: 输出音频文件路径
            sample_rate: 音频采样率（默认16kHz）
            channels: 音频通道数（默认单声道）
            
        Returns:
            提取的音频文件路径
            
        Raises:
            FileNotFoundError: 输入文件不存在
            Exception: 音频提取失败
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        try:
            logger.info(f"开始提取音频: {video_path} -> {output_path}")
            
            # 使用ffmpeg-python库提取音频
            (
                ffmpeg
                .input(video_path)
                .output(
                    output_path,
                    vn=None,  # 无视频
                    acodec='pcm_s16le',  # 16位PCM编码
                    ar=sample_rate,  # 采样率
                    ac=channels,  # 通道数
                    loglevel='error'  # 只显示错误信息
                )
                .overwrite_output()  # 覆盖已存在的文件
                .run()
            )
            
            # 验证音频文件
            if not os.path.exists(output_path):
                raise RuntimeError("音频文件生成失败")
            
            logger.info(f"音频提取成功: {output_path}")
            
            return output_path
            
        except Exception as e:
            error_msg = f"音频提取失败: {str(e)}"
            logger.error(error_msg)
            
            # 清理失败的文件
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except:
                    pass
            
            raise Exception(error_msg)
    
    def get_audio_info(self, audio_path: str) -> Dict[str, Any]:
        """
        获取音频文件信息
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            音频信息字典
            
        Raises:
            FileNotFoundError: 文件不存在
            Exception: 获取信息失败
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
            
        try:
            # 使用ffprobe获取音频信息
            probe = ffmpeg.probe(audio_path)
            
            # 获取音频流信息
            audio_streams = [stream for stream in probe['streams'] if stream['codec_type'] == 'audio']
            
            # 获取格式信息
            format_info = probe.get('format', {})
            
            if audio_streams:
                audio_stream = audio_streams[0]
                return {
                    'duration': float(audio_stream.get('duration', 0)),
                    'sample_rate': int(audio_stream.get('sample_rate', 0)),
                    'channels': int(audio_stream.get('channels', 0)),
                    'codec': audio_stream.get('codec_name', ''),
                    'size': int(format_info.get('size', 0))
                }
            else:
                # 没有音频流，返回基本信息
                return {
                    'duration': float(format_info.get('duration', 0)),
                    'sample_rate': 0,
                    'channels': 0,
                    'codec': '',
                    'size': int(format_info.get('size', 0))
                }
            
        except Exception as e:
            logger.error(f"获取音频信息失败: {str(e)}")
            raise Exception(f"获取音频信息失败: {str(e)}")
    
    def _get_audio_info(self, audio_path: str) -> Dict[str, Any]:
        """
        获取音频文件信息（内部方法）
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            音频信息字典
        """
        try:
            return self.get_audio_info(audio_path)
        except:
            return {}
    
    def validate_audio_file(self, audio_path: str) -> bool:
        """
        验证音频文件是否有效
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            是否有效
        """
        if not os.path.exists(audio_path):
            return False
        
        try:
            # 尝试读取音频文件信息
            info = self._get_audio_info(audio_path)
            
            # 检查基本信息
            if not info or info.get('duration', 0) <= 0:
                return False
            
            if info.get('sample_rate', 0) <= 0:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"音频文件验证失败: {str(e)}")
            return False
    
    def get_audio_duration(self, audio_path: str) -> float:
        """
        获取音频时长
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            音频时长（秒）
        """
        info = self._get_audio_info(audio_path)
        return info.get('duration', 0.0)
    
    def delete_audio_file(self, audio_path: str) -> bool:
        """
        删除音频文件
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            是否删除成功
        """
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
                logger.info(f"音频文件删除成功: {audio_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"音频文件删除失败: {audio_path}, 错误: {str(e)}")
            return False
    
    def get_supported_formats(self) -> Dict[str, Any]:
        """
        获取支持的音频格式信息
        
        Returns:
            支持的格式信息
        """
        return {
            'output_format': 'WAV',
            'codec': 'PCM_S16LE',
            'sample_rates': [8000, 16000, 22050, 44100, 48000],
            'channels': [1, 2],
            'default_sample_rate': 16000,
            'default_channels': 1
        }