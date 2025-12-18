#!/usr/bin/env python3
"""
SRT 字幕翻译脚本
功能：读取 SRT 文件 -> 识别日语 -> 调用 DeepL API 翻译 -> 生成双语/中文 SRT
"""

import os
import sys
import argparse
import logging
import json
import time
import random
import requests
import srt
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional

# 配置日志
def setup_logging(log_file: str = None):
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

class DeepLTranslator:
    """DeepL 字幕翻译器"""
    
    def __init__(self, args):
        self.input_file = args.input_file
        self.output_file = args.output_file
        self.auth_key = args.auth_key
        # DeepL API URL (根据 key 类型自动选择 free 或 pro)
        if self.auth_key.endswith(":fx"):
            self.base_url = "https://api-free.deepl.com/v2/translate"
        else:
            self.base_url = "https://api.deepl.com/v2/translate"
            
        self.batch_size = args.batch_size
        self.workers = args.workers
        self.bilingual = args.bilingual
        self.min_delay = args.min_delay
        self.max_delay = args.max_delay

    def load_subtitles(self) -> List[srt.Subtitle]:
        """加载 SRT 文件"""
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return list(srt.parse(content))
        except Exception as e:
            logger.error(f"读取字幕文件失败: {e}")
            sys.exit(1)

    def translate_batch(self, texts: List[str]) -> List[str]:
        """批量翻译文本 (DeepL)"""
        if not texts:
            return []
            
        # 随机延时
        if self.max_delay > 0:
            time.sleep(random.uniform(self.min_delay, self.max_delay))
        
        # DeepL 支持一次传多个 text 参数
        payload = {
            "text": texts,
            "source_lang": "JA", # 源语言：日语
            "target_lang": "ZH", # 目标语言：中文
        }
        
        headers = {
            "Authorization": f"DeepL-Auth-Key {self.auth_key}",
            "Content-Type": "application/json" # 或者使用 x-www-form-urlencoded
        }
        
        # requests 传 list 给 data 时如果是 json 格式更方便
        # DeepL API 推荐使用 POST json
        
        try:
            response = requests.post(self.base_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            # DeepL 返回格式: {"translations": [{"detected_source_language":"JA", "text":"..."}, ...]}
            
            if "translations" in result:
                return [item["text"] for item in result["translations"]]
            else:
                logger.error(f"API 响应异常: {result}")
                return [""] * len(texts)
                
        except Exception as e:
            logger.error(f"DeepL API 请求失败: {e}")
            return [""] * len(texts)

    def process(self):
        """执行翻译流程"""
        logger.info(f"正在读取字幕文件: {self.input_file}")
        subs = self.load_subtitles()
        logger.info(f"共加载 {len(subs)} 条字幕")
        
        # 分批处理
        batches = []
        for i in range(0, len(subs), self.batch_size):
            batch_subs = subs[i:i + self.batch_size]
            batch_texts = [s.content.replace('\n', ' ') for s in batch_subs]
            batches.append((i, batch_texts))
            
        translated_map = {}
        
        logger.info("开始调用 DeepL 翻译...")
        pbar = tqdm(total=len(subs))
        
        # 多线程并发请求
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            future_to_batch = {
                executor.submit(self.translate_batch, texts): (start_idx, texts) 
                for start_idx, texts in batches
            }
            
            for future in as_completed(future_to_batch):
                start_idx, original_texts = future_to_batch[future]
                try:
                    translated_texts = future.result()
                    
                    # 填充结果
                    for j, trans_text in enumerate(translated_texts):
                        idx = start_idx + j
                        if idx < len(subs):
                            translated_map[idx] = trans_text
                            
                    pbar.update(len(original_texts))
                except Exception as e:
                    logger.error(f"批次处理失败: {e}")
                    pbar.update(len(original_texts))
                    
        pbar.close()
        
        # 重组字幕
        new_subs = []
        for i, sub in enumerate(subs):
            trans = translated_map.get(i, "")
            if not trans:
                trans = sub.content # 翻译失败保留原文
            
            if self.bilingual:
                new_content = f"{trans}\n{sub.content}"
            else:
                new_content = trans
                
            new_sub = srt.Subtitle(
                index=sub.index,
                start=sub.start,
                end=sub.end,
                content=new_content
            )
            new_subs.append(new_sub)
            
        # 保存
        output_path = self.output_file
        if not output_path:
            name, ext = os.path.splitext(self.input_file)
            output_path = f"{name}_chs_deepl{ext}"
            
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(srt.compose(new_subs))
            
        logger.info(f"翻译完成，已保存至: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="SRT 字幕翻译工具 (DeepL)")
    parser.add_argument("input_file", help="输入 SRT 文件路径")
    parser.add_argument("--output_file", "-o", help="输出 SRT 文件路径")
    parser.add_argument("--auth_key", "-k", required=True, help="DeepL Auth Key (以 :fx 结尾为免费版)")
    parser.add_argument("--batch_size", "-b", type=int, default=20, help="每批次翻译条数 (DeepL 建议较大 batch)")
    parser.add_argument("--workers", "-w", type=int, default=5, help="并发请求数")
    parser.add_argument("--bilingual", action="store_true", help="输出双语字幕")
    parser.add_argument("--min_delay", type=float, default=0.5, help="最小延时")
    parser.add_argument("--max_delay", type=float, default=1.5, help="最大延时")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"错误: 文件不存在 {args.input_file}")
        sys.exit(1)
        
    setup_logging()
    
    translator = DeepLTranslator(args)
    translator.process()

if __name__ == "__main__":
    main()
