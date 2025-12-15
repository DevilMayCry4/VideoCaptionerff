"""
字幕生成服务
使用faster-whisper模型生成字幕
"""

import os
import logging
from typing import Dict, Any, List, Optional
from faster_whisper import WhisperModel
import srt
from datetime import timedelta

logger = logging.getLogger(__name__)

class SubtitleService:
    """字幕生成服务类"""
    
    def __init__(self, subtitle_folder: str = 'subtitles', 
                 model_size: str = 'base',
                 device: str = 'auto',
                 compute_type: str = 'auto'):
        """
        初始化字幕服务
        
        Args:
            subtitle_folder: 字幕文件存储目录
            model_size: Whisper模型大小（tiny, base, small, medium, large）
            device: 计算设备（cpu, cuda, auto）
            compute_type: 计算类型（int8, int8_float16, int16, float32, auto）
        """
        self.subtitle_folder = subtitle_folder
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model = None
        self._ensure_directories()
        self._load_model()
    
    def _ensure_directories(self) -> None:
        """确保必要的目录存在"""
        os.makedirs(self.subtitle_folder, exist_ok=True)
    
    def _load_model(self) -> None:
        """加载Whisper模型"""
        try:
            logger.info(f"正在加载Whisper模型: {self.model_size}")
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
            logger.info(f"Whisper模型加载成功: {self.model_size}")
        except Exception as e:
            logger.error(f"Whisper模型加载失败: {str(e)}")
            raise RuntimeError(f"模型加载失败: {str(e)}")
    
    def generate_subtitle(self, audio_path: str, task_id: str,
                         language: Optional[str] = None,
                         beam_size: int = 5,
                         best_of: int = 5,
                         temperature: float = 0.0) -> Dict[str, Any]:
        """
        生成字幕文件
        
        Args:
            audio_path: 音频文件路径
            task_id: 任务ID
            language: 语言代码（如 'zh', 'en'），None表示自动检测
            beam_size: 束搜索大小
            best_of: 最佳候选数
            temperature: 采样温度
            
        Returns:
            字幕生成结果字典
            
        Raises:
            ValueError: 参数错误
            RuntimeError: 字幕生成失败
        """
        if not os.path.exists(audio_path):
            raise ValueError(f"音频文件不存在: {audio_path}")
        
        if not task_id:
            raise ValueError("任务ID不能为空")
        
        if not self.model:
            raise RuntimeError("Whisper模型未加载")
        
        # 生成字幕文件名
        subtitle_filename = f"{task_id}.srt"
        subtitle_path = os.path.join(self.subtitle_folder, subtitle_filename)
        
        try:
            logger.info(f"开始生成字幕: {audio_path}")
            
            # 转录音频
            segments, info = self.model.transcribe(
                audio_path,
                language=language,
                beam_size=beam_size,
                best_of=best_of,
                temperature=temperature,
                word_timestamps=True,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    max_speech_duration_s=30
                )
            )
            
            logger.info(f"检测到的语言: {info.language} (概率: {info.language_probability:.2f})")
            
            # 转换为SRT格式
            subtitle_content = self._convert_to_srt(segments)
            
            # 保存字幕文件
            self._save_srt_file(subtitle_content, subtitle_path)
            
            # 验证字幕文件
            if not self._validate_srt_file(subtitle_path):
                raise RuntimeError("生成的字幕文件无效")
            
            logger.info(f"字幕生成成功: {subtitle_path}")
            
            return {
                'subtitle_path': subtitle_path,
                'content': subtitle_content,
                'language': info.language,
                'language_probability': info.language_probability,
                'duration': info.duration,
                'segments_count': len(subtitle_content.split('\n\n'))
            }
            
        except Exception as e:
            error_msg = f"字幕生成失败: {str(e)}"
            logger.error(error_msg)
            
            # 清理失败的文件
            if os.path.exists(subtitle_path):
                try:
                    os.remove(subtitle_path)
                except:
                    pass
            
            raise RuntimeError(error_msg)
    
    def _convert_to_srt(self, segments) -> str:
        """
        将转录结果转换为SRT格式
        
        Args:
            segments: Whisper转录结果段
            
        Returns:
            SRT格式字幕内容
        """
        subtitles = []
        
        for i, segment in enumerate(segments, 1):
            # 转换时间戳
            start_time = timedelta(seconds=segment.start)
            end_time = timedelta(seconds=segment.end)
            
            # 创建SRT字幕对象
            subtitle = srt.Subtitle(
                index=i,
                start=start_time,
                end=end_time,
                content=segment.text.strip()
            )
            
            subtitles.append(subtitle)
        
        # 生成SRT内容
        srt_content = srt.compose(subtitles)
        return srt_content
    
    def _save_srt_file(self, content: str, file_path: str) -> None:
        """
        保存SRT文件
        
        Args:
            content: SRT内容
            file_path: 文件路径
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"SRT文件保存成功: {file_path}")
        except Exception as e:
            logger.error(f"SRT文件保存失败: {str(e)}")
            raise IOError(f"SRT文件保存失败: {str(e)}")
    
    def _validate_srt_file(self, file_path: str) -> bool:
        """
        验证SRT文件是否有效
        
        Args:
            file_path: SRT文件路径
            
        Returns:
            是否有效
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 尝试解析SRT内容
            subtitles = list(srt.parse(content))
            
            # 基本验证
            if not subtitles:
                logger.warning("SRT文件为空或格式错误")
                return False
            
            # 验证字幕段
            for subtitle in subtitles:
                if not subtitle.content.strip():
                    logger.warning("发现空字幕内容")
                    continue
                
                if subtitle.end <= subtitle.start:
                    logger.warning(f"字幕时间戳错误: {subtitle.index}")
                    return False
            
            logger.info(f"SRT文件验证成功: {len(subtitles)} 个字幕段")
            return True
            
        except Exception as e:
            logger.error(f"SRT文件验证失败: {str(e)}")
            return False
    
    def convert_to_webvtt(self, srt_path: str, webvtt_path: Optional[str] = None) -> str:
        """
        将SRT文件转换为WebVTT格式
        
        Args:
            srt_path: SRT文件路径
            webvtt_path: WebVTT文件路径，如果为None则自动生成
            
        Returns:
            WebVTT文件路径
        """
        if not os.path.exists(srt_path):
            raise ValueError(f"SRT文件不存在: {srt_path}")
        
        if not webvtt_path:
            base_name = os.path.splitext(srt_path)[0]
            webvtt_path = f"{base_name}.vtt"
        
        try:
            # 读取SRT内容
            with open(srt_path, 'r', encoding='utf-8') as f:
                srt_content = f.read()
            
            # 解析SRT
            subtitles = list(srt.parse(srt_content))
            
            # 转换为WebVTT格式
            webvtt_lines = ["WEBVTT", ""]
            
            for subtitle in subtitles:
                # 转换时间戳格式
                start_time = self._srt_time_to_webvtt(subtitle.start)
                end_time = self._srt_time_to_webvtt(subtitle.end)
                
                webvtt_lines.append(f"{start_time} --> {end_time}")
                webvtt_lines.append(subtitle.content.strip())
                webvtt_lines.append("")
            
            webvtt_content = "\n".join(webvtt_lines)
            
            # 保存WebVTT文件
            with open(webvtt_path, 'w', encoding='utf-8') as f:
                f.write(webvtt_content)
            
            logger.info(f"WebVTT文件生成成功: {webvtt_path}")
            return webvtt_path
            
        except Exception as e:
            error_msg = f"WebVTT转换失败: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _srt_time_to_webvtt(self, time_delta: timedelta) -> str:
        """
        将SRT时间格式转换为WebVTT时间格式
        
        Args:
            time_delta: 时间差对象
            
        Returns:
            WebVTT时间格式字符串
        """
        total_seconds = time_delta.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        milliseconds = int((total_seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息
        
        Returns:
            模型信息字典
        """
        return {
            'model_size': self.model_size,
            'device': self.device,
            'compute_type': self.compute_type,
            'loaded': self.model is not None
        }
    
    def delete_subtitle_file(self, subtitle_path: str) -> bool:
        """
        删除字幕文件
        
        Args:
            subtitle_path: 字幕文件路径
            
        Returns:
            是否删除成功
        """
        try:
            if os.path.exists(subtitle_path):
                os.remove(subtitle_path)
                logger.info(f"字幕文件删除成功: {subtitle_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"字幕文件删除失败: {subtitle_path}, 错误: {str(e)}")
            return False