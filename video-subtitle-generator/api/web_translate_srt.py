#!/usr/bin/env python3
"""
DeepL Web 翻译脚本 (无 Key 版本)
功能：读取 SRT 文件 -> 识别日语 -> 使用 Playwright 模拟浏览器调用 DeepL 网页版翻译 -> 生成双语/中文 SRT
注意：仅供学习研究，DeepL 网页版有严格的反爬策略和字符限制。
"""

import os
import sys
import argparse
import logging
import time
import random
import srt
import urllib.parse
from tqdm import tqdm
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from typing import List

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

class DeepLWebTranslator:
    """DeepL 网页版翻译器"""
    
    def __init__(self, args):
        self.input_file = args.input_file
        self.output_file = args.output_file
        self.batch_size = 1 # 网页版建议每次只翻少量文本，或者合并成一段不超过限制的文本
        self.bilingual = args.bilingual
        self.headless = not args.show_browser
        self.max_chars = 1500 # 保守一点，虽然网页版限制是 3000/5000，但太长容易失败
        
        # 浏览器实例
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def start_browser(self):
        """启动浏览器"""
        logger.info("正在启动浏览器...")
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.page = self.context.new_page()
        
        # 预加载 DeepL 页面，设置语言方向
        try:
            # 直接进入 JA -> ZH 模式
            self.page.goto("https://www.deepl.com/zh/translator#ja/zh/")
            # 等待输入框加载
            self.page.wait_for_selector("[data-testid='translator-source-input']", timeout=15000)
            logger.info("DeepL 网页加载成功")
        except Exception as e:
            logger.error(f"无法访问 DeepL: {e}")
            self.close_browser()
            sys.exit(1)

    def close_browser(self):
        """关闭浏览器"""
        if self.context: self.context.close()
        if self.browser: self.browser.close()
        if self.playwright: self.playwright.stop()

    def load_subtitles(self) -> List[srt.Subtitle]:
        """加载 SRT 文件"""
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return list(srt.parse(content))
        except Exception as e:
            logger.error(f"读取字幕文件失败: {e}")
            sys.exit(1)

    def translate_text(self, text: str) -> str:
        """使用网页版翻译文本"""
        if not text.strip():
            return ""
            
        try:
            # 根据 t.html 分析，DeepL 使用 div[contenteditable] 作为输入输出框
            # 第一个是源语言输入框，第二个是目标语言输出框
            source_selector = "div[contenteditable] >> nth=0"
            target_selector = "div[contenteditable] >> nth=1"
            
            # 清空输入框 (聚焦 -> 全选 -> 删除)
            self.page.click(source_selector)
            self.page.keyboard.press("Meta+A") # Mac use Meta, Windows use Control
            self.page.keyboard.press("Backspace")
            
            # 填入新文本
            # 使用 fill 而不是 type，速度更快且稳定
            self.page.fill(source_selector, text)
            
            # 增加一个初始等待，确保DeepL开始处理
            time.sleep(2) 
            
            # 轮询检查结果是否稳定
            prev_text = ""
            stable_count = 0
            
            for i in range(60): # 最多等待 30秒
                # 尝试获取文本内容
                # 因为是 div[contenteditable]，必须用 inner_text，input_value 会报错
                try:
                    current_text = self.page.inner_text(target_selector)
                except Exception as e:
                    # 如果找不到目标元素，可能是页面结构变了或者还没加载出来
                    logger.debug(f"获取译文失败: {e}")
                    current_text = ""
                
                # 过滤无效状态
                if not current_text or "[...]" in current_text:
                    time.sleep(0.5)
                    continue
                
                if current_text != prev_text:
                    prev_text = current_text
                    stable_count = 0
                else:
                    stable_count += 1
                    # 连续稳定 1.5 秒 (3次 * 0.5s)
                    if stable_count >= 3:
                        # 再次确认不是空
                        if current_text.strip():
                            return current_text
                
                time.sleep(0.5)
            
            # 如果超时，返回最后获取到的内容
            return prev_text
            
        except Exception as e:
            logger.error(f"网页翻译失败: {e}")
            # 尝试刷新页面恢复
            try:
                self.page.reload()
                self.page.wait_for_selector("[data-testid='translator-source-input']", timeout=15000)
            except:
                pass
            return text # 失败返回原文

    def process(self):
        """执行翻译流程"""
        logger.info(f"正在读取字幕文件: {self.input_file}")
        subs = self.load_subtitles()
        
        self.start_browser()
        
        new_subs = []
        pbar = tqdm(total=len(subs))
        
        # 智能合并文本以减少页面跳转次数
        # DeepL 网页版每次跳转都需要加载，频繁跳转效率极低且容易被封
        # 我们将字幕合并成大段文本进行翻译，然后拆分
        
        buffer_subs = []
        buffer_len = 0
        
        translated_map = {}
        
        # 内部函数：处理缓冲区
        def process_buffer(subs_list):
            if not subs_list: return
            
            # 合并文本，使用特殊分隔符，DeepL 通常能保留换行，但为了保险，可以用一些特殊符号辅助
            # 这里直接用换行符，DeepL 对段落处理较好
            merged_text = "\n".join([s.content.replace('\n', ' ') for s in subs_list])
            
            trans_text = self.translate_text(merged_text)
            trans_lines = trans_text.split('\n')
            
            # 简单对齐
            # 如果行数不一致，尝试回退到逐行翻译 (比较慢)
            if len(trans_lines) != len(subs_list):
                logger.warning(f"行数不匹配 (原:{len(subs_list)}, 译:{len(trans_lines)})，切换单条模式...")
                for s in subs_list:
                    t = self.translate_text(s.content.replace('\n', ' '))
                    translated_map[s.index] = t
                    # 随机延时防封
                    time.sleep(random.uniform(1, 3))
            else:
                for idx, s in enumerate(subs_list):
                    translated_map[s.index] = trans_lines[idx]
            
            # 批次间延时
            time.sleep(random.uniform(2, 5))

        for sub in subs:
            # 简单的长度估算
            content_len = len(sub.content)
            
            if buffer_len + content_len > self.max_chars:
                process_buffer(buffer_subs)
                pbar.update(len(buffer_subs))
                buffer_subs = []
                buffer_len = 0
            
            buffer_subs.append(sub)
            buffer_len += content_len + 1 # +1 for newline
            
        # 处理剩余
        process_buffer(buffer_subs)
        pbar.update(len(buffer_subs))
        pbar.close()
        
        self.close_browser()
        
        # 重组字幕
        for sub in subs:
            trans = translated_map.get(sub.index, "")
            if not trans: trans = sub.content
            
            if self.bilingual:
                new_content = f"{trans}\n{sub.content}"
            else:
                new_content = trans
                
            new_subs.append(srt.Subtitle(
                index=sub.index,
                start=sub.start,
                end=sub.end,
                content=new_content
            ))
            
        # 保存
        output_path = self.output_file
        if not output_path:
            name, ext = os.path.splitext(self.input_file)
            output_path = f"{name}_chs_web{ext}"
            
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(srt.compose(new_subs))
            
        logger.info(f"翻译完成: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="DeepL 网页版字幕翻译工具 (Playwright)")
    parser.add_argument("input_file", help="输入 SRT 文件")
    parser.add_argument("--output_file", "-o", help="输出文件")
    parser.add_argument("--bilingual", action="store_true", help="输出双语字幕")
    parser.add_argument("--show_browser", action="store_true", help="显示浏览器窗口 (调试用)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"文件不存在: {args.input_file}")
        sys.exit(1)
        
    setup_logging()
    
    # 首次运行需要安装浏览器
    if not os.path.exists(os.path.expanduser("~/.cache/ms-playwright")) and not os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
         print("提示: 首次运行可能需要安装浏览器内核，请执行: playwright install chromium")
    
    translator = DeepLWebTranslator(args)
    translator.process()

if __name__ == "__main__":
    main()
