#!/usr/bin/env python3
"""
批量视频字幕生成脚本
功能：扫描目录视频 -> 提取音频 -> 语音识别 -> 生成SRT字幕
"""

import os
import sys
import time
import argparse
import logging
import shutil
import subprocess
import datetime
import traceback
import threading
from typing import List, Optional, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# 尝试导入依赖库
try:
    import ffmpeg
    from faster_whisper import WhisperModel
    from tqdm import tqdm
except ImportError as e:
    print(f"错误: 缺少必要依赖库 ({e})")
    print("请运行: pip install -r requirements.txt")
    sys.exit(1)

# 配置日志
class LoggerWriter:
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level

    def write(self, message):
        if message.strip():
            self.logger.log(self.level, message.strip())

    def flush(self):
        pass

def setup_logging(log_file: str = None):
    """配置日志记录"""
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    return logging.getLogger(__name__)

logger = logging.getLogger(__name__)

class SubtitleGenerator:
    """视频字幕生成器"""
    
    SUPPORTED_FORMATS = {'.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm'}
    
    def __init__(self, args):
        self.input_dir = os.path.abspath(args.input_dir)
        self.model_size = args.model_size
        self.device = args.device
        self.compute_type = args.compute_type
        self.beam_size = args.beam_size
        self.workers = args.workers
        self.force_cpu = args.force_cpu
        self.vad = args.vad
        self.vad_min_silence_duration_ms = args.vad_min_silence_duration_ms

        # MacOS 环境自动检测与修正
        if sys.platform == "darwin":
            if self.device == "cuda":
                logger.warning("MacOS 不支持 CUDA 加速，已强制切换为 CPU 模式")
                self.force_cpu = True
            elif self.device == "auto" and not self.force_cpu:
                # 在 auto 模式下，如果是 Mac，直接默认用 CPU，避免 auto 尝试加载 CUDA 库导致报错
                logger.info("检测到 MacOS 环境，默认使用 CPU 模式")
                self.force_cpu = True
            
            # MacOS 上 compute_type 建议使用 int8 或 float32，避免 float16 可能的问题
            if self.compute_type == "default" or self.compute_type == "auto":
                self.compute_type = "int8"
        
        # 统计信息
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': None,
            'end_time': None
        }
        
        # 模型实例（用于单线程模式或主线程加载）
        self.model = None
        
        # 线程锁（如果需要）
        self.model_lock = threading.Lock()

    def load_model(self):
        """加载Whisper模型"""
        try:
            device = "cpu" if self.force_cpu else self.device
            logger.info(f"正在加载模型: {self.model_size} (Device: {device}, Compute: {self.compute_type})...")
            
            self.model = WhisperModel(
                self.model_size,
                device=device,
                compute_type=self.compute_type
            )
            logger.info("模型加载成功")
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            if not self.force_cpu and device != "cpu":
                logger.warning("尝试降级到CPU模式...")
                self.force_cpu = True
                self.device = "cpu"
                self.compute_type = "int8" # CPU通常使用int8
                try:
                    self.load_model()
                except RuntimeError:
                     # 避免递归死循环，如果重试还是失败，则抛出异常
                     raise RuntimeError("CPU模式重试加载失败")
            else:
                raise RuntimeError("无法加载模型，程序退出")

    def scan_files(self) -> List[str]:
        """递归扫描视频文件"""
        video_files = []
        logger.info(f"正在扫描目录: {self.input_dir}")
        
        for root, _, files in os.walk(self.input_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in self.SUPPORTED_FORMATS:
                    video_files.append(os.path.join(root, file))
        
        return video_files

    def extract_audio(self, video_path: str, temp_audio_path: str) -> bool:
        """使用ffmpeg提取音频"""
        try:
            # 检查ffmpeg是否存在
            subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            
            # 提取音频: 16kHz, 单声道, wav格式
            # 使用 -y 覆盖已存在文件
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vn', # 无视频
                '-acodec', 'pcm_s16le', 
                '-ar', '16000', 
                '-ac', '1',
                '-y', 
                '-loglevel', 'error',
                temp_audio_path
            ]
            
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg处理错误: {e}")
            return False
        except FileNotFoundError:
            logger.error("未找到ffmpeg命令，请确保已安装ffmpeg")
            return False
        except Exception as e:
            logger.error(f"音频提取异常: {e}")
            return False

    def format_timestamp(self, seconds: float) -> str:
        """格式化时间戳为SRT格式 (HH:MM:SS,mmm)"""
        td = datetime.timedelta(seconds=seconds)
        # 转换为总秒数和微秒
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        millis = int(td.microseconds / 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def generate_srt_content(self, segments) -> str:
        """生成SRT字幕内容"""
        srt_content = []
        for i, segment in enumerate(segments, start=1):
            start_time = self.format_timestamp(segment.start)
            end_time = self.format_timestamp(segment.end)
            text = segment.text.strip()
            
            srt_content.append(f"{i}\n{start_time} --> {end_time}\n{text}\n")
        
        return "\n".join(srt_content)

    def process_single_file(self, video_path: str):
        """处理单个文件"""
        start_time = time.time()
        file_name = os.path.basename(video_path)
        
        # 确定输出路径
        video_dir = os.path.dirname(video_path)
        subtitle_dir = os.path.join(video_dir, 'subtitles')
        
        # 确保subtitles目录存在
        try:
            os.makedirs(subtitle_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"创建字幕目录失败: {e}")
            return False

        subtitle_path = os.path.join(subtitle_dir, os.path.splitext(file_name)[0] + ".srt")
        temp_audio_path = os.path.join(subtitle_dir, f".temp_{os.path.splitext(file_name)[0]}_{int(time.time())}.wav")
        
        logger.info(f"开始处理: {file_name}")
        
        try:
            # 1. 提取音频
            if not self.extract_audio(video_path, temp_audio_path):
                raise RuntimeError("音频提取失败")
            
            # 2. 语音识别
            # 如果是多线程且共享模型，需要加锁（faster-whisper本身可能是线程安全的，但为了保险起见或控制并发推理数）
            # 注意：faster-whisper 的 transcribe 方法通常会释放 GIL，但在显存受限时并行运行可能导致 OOM
            # 如果 workers=1，不需要锁。如果 workers>1，假设用户有足够显存或使用 CPU
            
            segments_generator, info = self.model.transcribe(
                temp_audio_path, 
                beam_size=self.beam_size,
                word_timestamps=False, # 简单起见，暂不开启词级时间戳，除非需要更精细对齐
                vad_filter=self.vad,
                vad_parameters=dict(min_silence_duration_ms=self.vad_min_silence_duration_ms) if self.vad else None
            )
            
            # 强制转换生成器为列表以获取所有段落
            segments = list(segments_generator)
            
            # 3. 生成SRT
            srt_content = self.generate_srt_content(segments)
            
            # 4. 保存文件
            with open(subtitle_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
                
            duration = time.time() - start_time
            logger.info(f"完成: {file_name} (耗时: {duration:.2f}s, 语言: {info.language}, 概率: {info.language_probability:.2f})")
            return True

        except Exception as e:
            logger.error(f"处理文件失败 {file_name}: {str(e)}")
            logger.debug(traceback.format_exc())
            return False
        finally:
            # 5. 清理临时文件
            if os.path.exists(temp_audio_path):
                try:
                    os.remove(temp_audio_path)
                except:
                    pass

    def run(self):
        """运行主流程"""
        self.stats['start_time'] = datetime.datetime.now()
        logger.info("=== 批量字幕生成任务开始 ===")
        logger.info(f"输入目录: {self.input_dir}")
        logger.info(f"并发数: {self.workers}")
        
        # 1. 扫描文件
        files = self.scan_files()
        self.stats['total'] = len(files)
        logger.info(f"共发现 {len(files)} 个视频文件")
        
        if not files:
            logger.warning("未找到视频文件，任务结束")
            return

        # 2. 加载模型 (主线程加载一次)
        self.load_model()
        
        # 3. 处理文件
        # 使用tqdm显示进度
        pbar = tqdm(total=len(files), unit="file", desc="Processing")
        
        if self.workers <= 1:
            # 单线程顺序处理
            for file_path in files:
                success = self.process_single_file(file_path)
                if success:
                    self.stats['success'] += 1
                else:
                    self.stats['failed'] += 1
                pbar.update(1)
        else:
            # 多线程并行处理
            # 注意：在GPU模式下，多线程共享同一个WhisperModel实例可能不安全或效率低
            # 官方建议：Model instantiation is not thread-safe, but the transcribe method is thread-safe.
            # 只要在主线程初始化模型，子线程调用 transcribe 即可。
            # 但要注意显存占用，如果是 large 模型，并行推理可能导致 OOM。
            logger.warning("启用多线程模式，请确保显存/内存充足")
            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                future_to_file = {executor.submit(self.process_single_file, f): f for f in files}
                for future in as_completed(future_to_file):
                    file = future_to_file[future]
                    try:
                        success = future.result()
                        if success:
                            self.stats['success'] += 1
                        else:
                            self.stats['failed'] += 1
                    except Exception as e:
                        logger.error(f"任务异常 {file}: {e}")
                        self.stats['failed'] += 1
                    pbar.update(1)
        
        pbar.close()
        
        self.stats['end_time'] = datetime.datetime.now()
        self.print_report()

    def print_report(self):
        """打印汇总报告"""
        duration = self.stats['end_time'] - self.stats['start_time']
        logger.info("\n=== 处理汇总报告 ===")
        logger.info(f"开始时间: {self.stats['start_time']}")
        logger.info(f"结束时间: {self.stats['end_time']}")
        logger.info(f"总耗时: {duration}")
        logger.info(f"文件总数: {self.stats['total']}")
        logger.info(f"成功: {self.stats['success']}")
        logger.info(f"失败: {self.stats['failed']}")
        logger.info("====================")

def main():
    parser = argparse.ArgumentParser(description="视频字幕自动生成工具")
    
    parser.add_argument("--input_dir", "-i", type=str, default="uploads",
                        help="输入视频目录 (默认: uploads)")
    parser.add_argument("--model_size", "-m", type=str, default="large-v2",
                        choices=["tiny", "base", "small", "medium", "large", "large-v2", "large-v3", "large-v3-turbo"],
                        help="Whisper模型大小 (默认: large-v2)")
    parser.add_argument("--device", "-d", type=str, default="auto",
                        choices=["cpu", "cuda", "auto"],
                        help="计算设备 (默认: auto)")
    parser.add_argument("--compute_type", "-c", type=str, default="default",
                        choices=["int8", "int8_float16", "int16", "float16", "float32", "default"],
                        help="计算精度类型 (默认: default)")
    parser.add_argument("--beam_size", "-b", type=int, default=5,
                        help="Beam search大小 (默认: 5)")
    parser.add_argument("--workers", "-w", type=int, default=1,
                        help="并发处理线程数 (默认: 1, 建议GPU模式下保持1)")
    parser.add_argument("--force_cpu", action="store_true",
                        help="强制使用CPU模式 (当GPU不可用或显存不足时)")
    parser.add_argument("--log_file", "-l", type=str, default="subtitle_gen.log",
                        help="日志文件路径 (默认: subtitle_gen.log)")
    parser.add_argument("--vad", action="store_true",
                        help="启用语音活动检测 (VAD) 过滤静音片段")
    parser.add_argument("--vad_min_silence_duration_ms", type=int, default=2000,
                        help="VAD 最小静音时长 (毫秒)，默认 2000ms")
    
    args = parser.parse_args()
    
    # 确保输入目录存在
    if not os.path.exists(args.input_dir):
        print(f"错误: 输入目录 '{args.input_dir}' 不存在")
        sys.exit(1)
    
    # 设置日志
    setup_logging(args.log_file)

    # 打印执行参数
    logger.info("=== 任务参数配置 ===")
    for arg, value in vars(args).items():
        logger.info(f"{arg}: {value}")
    logger.info("====================")
    
    # 运行生成器
    try:
        generator = SubtitleGenerator(args)
        generator.run()
    except KeyboardInterrupt:
        print("\n任务被用户中断")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"程序发生严重错误: {e}")
        logger.debug(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
