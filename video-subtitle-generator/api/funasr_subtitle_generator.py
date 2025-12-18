#!/usr/bin/env python3
"""
FunASR 批量视频字幕生成脚本
功能：扫描目录视频 -> 提取高质量音频(44.1k/192k mp3) -> FunASR识别 -> 生成SRT字幕
"""

import os
import sys
import time
import argparse
import logging
import subprocess
import datetime
import traceback
import json
from tqdm import tqdm

# 尝试导入依赖库
try:
    from funasr import AutoModel
except ImportError as e:
    print(f"错误: 缺少必要依赖库 ({e})")
    print("请运行: pip install funasr modelscope torch torchaudio")
    sys.exit(1)

# 配置日志
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

class FunASRSubtitleGenerator:
    """FunASR 视频字幕生成器"""
    
    SUPPORTED_FORMATS = {'.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm'}
    
    def __init__(self, args):
        self.input_dir = os.path.abspath(args.input_dir)
        self.model_name = args.model_name
        self.device = args.device
        self.output_dir_name = "subtitles_funasr"
        
        # 统计信息
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None
        }
        
        self.model = None

    def load_model(self):
        """加载 FunASR 模型"""
        try:
            logger.info(f"正在加载 FunASR 模型: {self.model_name} (Device: {self.device})...")
            
            # 自动检测设备
            if self.device == "auto":
                import torch
                if torch.cuda.is_available():
                    self.device = "cuda:0"
                elif torch.backends.mps.is_available():
                     if sys.platform == "darwin":
                         self.device = "cpu"
                     else:
                         self.device = "cpu"
                else:
                    self.device = "cpu"
            
            logger.info(f"使用设备: {self.device}")

            # FunASR Nano 特殊加载逻辑：
            # 由于该模型使用 remote_code 加载自定义模型结构，AutoModel 在某些环境下可能无法正确自动注册 FunASRNano 类
            # 我们可以尝试直接从下载的模型目录中加载
            
            from modelscope.hub.snapshot_download import snapshot_download
            model_dir = snapshot_download(self.model_name)
            logger.info(f"模型已下载至: {model_dir}")
            
            # 必须指定 remote_code 以加载模型定义
            # 且需要 trust_remote_code=True
            self.model = AutoModel(
                model=model_dir,
                vad_model="fsmn-vad",
                punc_model="ct-punc",
                device=self.device,
                trust_remote_code=True,
                remote_code=f"{model_dir}/model.py" # 显式指定 remote_code 路径
            )
            logger.info("模型加载成功")
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise RuntimeError("无法加载模型，程序退出")

    def scan_files(self):
        """扫描视频文件"""
        video_files = []
        for root, _, files in os.walk(self.input_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in self.SUPPORTED_FORMATS:
                    video_files.append(os.path.join(root, file))
        return video_files

    def extract_audio(self, video_path: str, temp_audio_path: str) -> bool:
        """提取高质量音频 (44.1kHz, 192kbps MP3)"""
        try:
            # ffmpeg -i input -ar 44100 -ab 192k -vn -y output.mp3
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vn', # 无视频
                '-ar', '44100', 
                '-ab', '192k',
                '-ac', '1', # 语音识别单声道足矣，虽然 44.1k 立体声是高质量音乐标准，但 ASR 还是单声道好
                '-y', 
                '-loglevel', 'error',
                temp_audio_path
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg 错误: {e}")
            return False
        except Exception as e:
            logger.error(f"音频提取异常: {e}")
            return False

    def format_timestamp(self, millis: float) -> str:
        """格式化毫秒为 SRT 格式 (HH:MM:SS,mmm)"""
        seconds = millis / 1000
        td = datetime.timedelta(seconds=seconds)
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        ms = int(td.microseconds / 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"

    def generate_srt(self, res) -> str:
        """从 FunASR 结果生成 SRT 内容"""
        # FunASR generate 结果通常是列表，每个元素是一个 dict
        # 包含 'text' 和 'sentence_info' (如果有 timestamps)
        if not res:
            return ""
        
        item = res[0]
        srt_lines = []
        
        # 检查是否有 sentence_info (VAD 分段结果)
        if 'sentence_info' in item:
            segments = item['sentence_info']
            for i, seg in enumerate(segments, start=1):
                # seg 结构通常为 {'text': ..., 'start': ms, 'end': ms, ...}
                start = seg.get('start', 0)
                end = seg.get('end', 0)
                text = seg.get('text', '').strip()
                
                start_str = self.format_timestamp(start)
                end_str = self.format_timestamp(end)
                
                srt_lines.append(f"{i}\n{start_str} --> {end_str}\n{text}\n")
        else:
            # 如果没有详细时间戳，只能把全文当作一条字幕（或者失败）
            text = item.get('text', '')
            logger.warning("未检测到详细时间戳，将生成单条字幕")
            srt_lines.append(f"1\n00:00:00,000 --> 00:00:10,000\n{text}\n")
            
        return "\n".join(srt_lines)

    def process_single_file(self, video_path: str):
        """处理单个文件"""
        file_name = os.path.basename(video_path)
        video_dir = os.path.dirname(video_path)
        subtitle_dir = os.path.join(video_dir, self.output_dir_name)
        
        os.makedirs(subtitle_dir, exist_ok=True)
        
        subtitle_path = os.path.join(subtitle_dir, os.path.splitext(file_name)[0] + ".srt")
        # 临时音频文件使用 mp3
        temp_audio_path = os.path.join(subtitle_dir, f".temp_{os.path.splitext(file_name)[0]}_{int(time.time())}.mp3")
        
        logger.info(f"处理文件: {file_name}")
        
        try:
            # 1. 提取音频
            if not self.extract_audio(video_path, temp_audio_path):
                raise RuntimeError("音频提取失败")
            
            # 2. 识别
            # generate 支持 input 为文件路径
            res = self.model.generate(
                input=temp_audio_path,
                batch_size_s=300, # 动态 batch，按秒
                hotwords=[], 
                merge_vad=True, # 合并 VAD 片段
                merge_length_s=15, # 最大合并长度
            )
            
            # 3. 生成 SRT
            srt_content = self.generate_srt(res)
            
            # 4. 保存
            with open(subtitle_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
                
            logger.info(f"生成字幕成功: {subtitle_path}")
            return True
            
        except Exception as e:
            logger.error(f"处理失败 {file_name}: {e}")
            traceback.print_exc()
            return False
        finally:
            if os.path.exists(temp_audio_path):
                try:
                    os.remove(temp_audio_path)
                except:
                    pass

    def run(self):
        """运行主流程"""
        self.stats['start_time'] = datetime.datetime.now()
        logger.info("=== FunASR 批量字幕生成任务 ===")
        
        files = self.scan_files()
        self.stats['total'] = len(files)
        logger.info(f"发现视频文件: {len(files)} 个")
        
        if not files:
            return

        self.load_model()
        
        pbar = tqdm(total=len(files))
        for file in files:
            success = self.process_single_file(file)
            if success:
                self.stats['success'] += 1
            else:
                self.stats['failed'] += 1
            pbar.update(1)
        pbar.close()
        
        self.stats['end_time'] = datetime.datetime.now()
        logger.info(f"任务结束. 成功: {self.stats['success']}, 失败: {self.stats['failed']}")

def main():
    parser = argparse.ArgumentParser(description="FunASR 字幕生成工具")
    parser.add_argument("--input_dir", "-i", type=str, default="uploads", help="视频目录")
    parser.add_argument("--model_name", "-m", type=str, default="FunAudioLLM/Fun-ASR-Nano-2512", help="FunASR 模型名称/路径")
    parser.add_argument("--device", "-d", type=str, default="auto", help="设备 (cpu/cuda/auto)")
    parser.add_argument("--log_file", "-l", type=str, default="funasr_gen.log", help="日志文件")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_dir):
        print(f"目录不存在: {args.input_dir}")
        sys.exit(1)
        
    setup_logging(args.log_file)
    
    generator = FunASRSubtitleGenerator(args)
    generator.run()

if __name__ == "__main__":
    main()
