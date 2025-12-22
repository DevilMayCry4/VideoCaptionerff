#!/usr/bin/env python3
"""
DeepL Web 翻译脚本 (无 Key 版本)
功能：读取 SRT 文件 -> 识别日语 -> 使用 Playwright 模拟浏览器调用 DeepL 网页版翻译 -> 生成双语/中文 SRT
注意：仅供学习研究，DeepL 网页版有严格的反爬策略和字符限制。
"""

import asyncio
import os
import sys
import argparse
import logging
import time
import random
import srt
from tqdm import tqdm
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from typing import List
import re

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
        self.input_file = None # 初始化时不指定文件
        self.output_file = None
        self.batch_size = 1 # 网页版建议每次只翻少量文本，或者合并成一段不超过限制的文本
        self.bilingual = args.bilingual
        self.headless = not args.show_browser
        self.max_chars = 1500 # 用户要求控制在1500字以内
        self.single_mode = args.single_mode # 是否强制使用单行模式
        
        # 浏览器实例
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def __aenter__(self):
        await self.start_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_browser()

    async def start_browser(self):
        """启动浏览器"""
        logger.info("正在启动浏览器...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.page = await self.context.new_page()
        
        # 预加载 DeepL 页面，设置语言方向
        try:
            # 根据 t.html 中的 SEO 早期文本 (seoEarlyTexts)，日语是 'ja'，中文是 'zh'
            # 构造 URL: https://www.deepl.com/zh/translator#ja/zh/
            # #ja/zh/ 表示源语言日语，目标语言中文
            await self.page.goto("https://www.deepl.com/zh")
            # 等待输入框加载 (DeepL 网页版输入框通常是 div[contenteditable])
            await self.page.wait_for_selector("div[contenteditable]", timeout=15000)
            logger.info("DeepL 网页加载成功")
        except Exception as e:
            logger.error(f"无法访问 DeepL: {e}")
            # await self.close_browser()
            sys.exit(1)

    async def close_browser(self):
        """关闭浏览器"""
        if self.context: await self.context.close()
        if self.browser: await self.browser.close()
        if self.playwright: await self.playwright.stop()

    def load_subtitles(self) -> List[srt.Subtitle]:
        """加载 SRT 文件"""
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return list(srt.parse(content))
        except Exception as e:
            logger.error(f"读取字幕文件失败: {e}")
            sys.exit(1)

    async def translate_text(self, text: str) -> str:
        """使用网页版翻译文本"""
        if not text.strip():
            return ""
            
        try:
            # 根据 t.html 分析，DeepL 使用 div[contenteditable] 作为输入输出框
            # 第一个是源语言输入框，第二个是目标语言输出框
            source_selector = "div[contenteditable] >> nth=0"
            target_selector = "div[contenteditable] >> nth=1"
            
            # 清空输入框 (聚焦 -> 全选 -> 删除)
            await self.page.click(source_selector)
            await self.page.keyboard.press("Meta+A") # Mac use Meta, Windows use Control
            await self.page.keyboard.press("Backspace")
            
            # 填入新文本
            # 使用 fill 而不是 type，速度更快且稳定
            await self.page.fill(source_selector, text)
            
            # 增加一个初始等待，确保DeepL开始处理
            await asyncio.sleep(2) 
            
            # 轮询检查结果是否稳定
            prev_text = ""
            stable_count = 0
            
            for i in range(60): # 最多等待 30秒
                # 尝试获取文本内容
                # 因为是 div[contenteditable]，必须用 inner_text，input_value 会报错
                try:
                    current_text = await self.page.inner_text(target_selector)
                except Exception as e:
                    # 如果找不到目标元素，可能是页面结构变了或者还没加载出来
                    logger.debug(f"获取译文失败: {e}")
                    current_text = ""
                
                # 过滤无效状态
                if not current_text or "[...]" in current_text:
                    await asyncio.sleep(0.5)
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
                
                await asyncio.sleep(0.5)
            
            # 如果超时，返回最后获取到的内容
            return prev_text
            
        except Exception as e:
            logger.error(f"网页翻译失败: {e}")
            # 尝试刷新页面恢复
            try:
                await self.page.reload()
                await self.page.wait_for_selector("[data-testid='translator-source-input']", timeout=15000)
            except:
                pass
            return text # 失败返回原文

    async def process_file(self, input_path: str, output_path: str = None):
        """处理单个文件"""
        self.input_file = input_path
        self.output_file = output_path
        await self.process()

    def is_sentence_end(self, text: str) -> bool:
        """判断是否为句子结束"""
        # 常见句末标点 (中英文)
        endings = ('.', '?', '!', ';', '。', '？', '！', '；', '…', '"', '”', '…')
        return text.strip().endswith(endings)

    async def process(self):
        """执行翻译流程 (内部方法)"""
        if not self.input_file:
            return

        logger.info(f"正在读取字幕文件: {self.input_file}")
        subs = self.load_subtitles()
        
        # 浏览器在外部启动
        # self.start_browser()
        
        new_subs = []
        pbar = tqdm(total=len(subs))
        
        buffer_subs = []
        buffer_len = 0
        
        translated_map = {}
        
        # 内部函数：处理缓冲区
        # subs_with_idx: List of (global_index, subtitle_object)
        async def process_buffer(subs_with_idx):
            if not subs_with_idx: return
            
            # 如果开启了单行模式，直接在这里分发
            if self.single_mode:
                for global_idx, s in subs_with_idx:
                    t = await self.translate_text(s.content)
                    translated_map[global_idx] = t
                    await asyncio.sleep(random.uniform(1, 2))
                return

            # 解包
            subs_list = [item[1] for item in subs_with_idx]
            
            # 1. 构建带锚点标记的垂直文本列表
            # 格式: <1>原文\n<2>原文
            # 这种格式利用了 DeepL 对列表和 XML 标签的处理能力，极大降低合并风险
            formatted_lines = []
            for i, s in enumerate(subs_list):
                # 序号从1开始
                seq_num = i + 1
                # 预处理：去除换行，替换可能干扰 XML 解析的符号
                content = s.content.strip().replace(chr(10), ' ').replace('<', '&lt;').replace('>', '&gt;')
                formatted_lines.append(f"<{seq_num}>{content}")
                
            # 使用换行符连接，形成清晰的列表结构
            merged_text = "\n".join(formatted_lines)
            
            logger.info(f"正在翻译批次，包含 {len(subs_list)} 条字幕，共 {len(merged_text)} 字符")
            
            # 2. 发送翻译
            trans_text = await self.translate_text(merged_text)
            
            # 3. 解析结果
            # 匹配行首的 <数字>标记
            # DeepL 有时会在标签后加空格，或者改变标签内的数字格式（较少见）
            # 正则：匹配 <数字> 及其后的内容，直到行尾或下一个标签前
            matches = re.findall(r'<(\d+)>(.*?)(?=\n<|\Z)', trans_text, re.DOTALL)
            
            # 转换匹配结果为字典: {序号: 译文}
            batch_trans_map = {}
            for seq_str, content in matches:
                try:
                    seq = int(seq_str)
                    # 清理译文中的潜在 HTML 转义字符和首尾空白
                    clean_content = content.strip().replace('&lt;', '<').replace('&gt;', '>')
                    batch_trans_map[seq] = clean_content
                except ValueError:
                    continue

            # 4. 结果对齐与填充
            # 检查是否所有序号都找到了
            missing_indices = [] # 这里存储的是 batch 内的相对索引 (0, 1, 2...)
            for i in range(len(subs_list)):
                seq_num = i + 1
                global_idx = subs_with_idx[i][0] # 获取全局索引
                
                if seq_num in batch_trans_map:
                    # 找到了，存入全局 map，使用全局索引作为key
                    translated_map[global_idx] = batch_trans_map[seq_num]
                else:
                    missing_indices.append(i)
            
            # 如果有缺失，对缺失的部分进行降级处理 (逐条翻译)
            if missing_indices:
                logger.warning(f"批次中有 {len(missing_indices)}/{len(subs_list)} 条字幕未匹配到序号，切换单行模式补翻...")
                logger.debug(f"原文片段: {merged_text[:200]}...")
                logger.debug(f"译文片段: {trans_text[:200]}...")
                
                for idx, i in enumerate(missing_indices):
                    # 获取原始信息
                    global_idx, sub = subs_with_idx[i]
                    
                    logger.info(f"  > 正在补翻 [{idx+1}/{len(missing_indices)}]: {sub.content[:20]}...")
                    
                    # 单行翻译
                    # 注意：单行翻译不需要加序号标签，直接翻内容效果最好
                    t = await self.translate_text(sub.content)
                    
                    # 存入结果
                    translated_map[global_idx] = t
                    
                    # 随机延时
                    await asyncio.sleep(random.uniform(1, 2))
            await asyncio.sleep(random.uniform(2, 5))

        # Main loop with smart batching
        for i, sub in enumerate(subs):
            content = sub.content.strip().replace('\n', ' ')
            # content length + separator length (" | ") -> 3 chars
            content_len = len(content) + 3 
            
            # Check if adding this subtitle exceeds max_chars
            if buffer_len + content_len > self.max_chars:
                # Batch is full. Try to optimize split point.
                # Look backwards for a sentence ending to split at.
                split_idx = -1
                
                # Find last sentence end in buffer
                # buffer_subs is list of (global_idx, sub)
                for j in range(len(buffer_subs) - 1, -1, -1):
                    _, s_sub = buffer_subs[j]
                    if self.is_sentence_end(s_sub.content):
                        split_idx = j
                        break
                
                if split_idx != -1 and split_idx < len(buffer_subs) - 1:
                    # Found a better split point (not at the very end, which is trivial)
                    # Send up to split point
                    to_send = buffer_subs[:split_idx+1]
                    remaining = buffer_subs[split_idx+1:]
                    
                    await process_buffer(to_send)
                    pbar.update(len(to_send))
                    
                    # Start new buffer with remaining items + current item
                    buffer_subs = remaining
                    # Recalculate length for remaining items
                    buffer_len = sum(len(s[1].content.strip().replace('\n',' '))+3 for s in buffer_subs)
                else:
                    # No better split point found, just send current buffer
                    await process_buffer(buffer_subs)
                    pbar.update(len(buffer_subs))
                    buffer_subs = []
                    buffer_len = 0
            
            # Add current subtitle to buffer
            buffer_subs.append((i, sub))
            buffer_len += content_len
            
        # 处理剩余
        await process_buffer(buffer_subs)
        pbar.update(len(buffer_subs))
        pbar.close()
        
        # 重组字幕
        for i, sub in enumerate(subs):
            # 使用全局索引获取译文，确保顺序绝对一致
            # 无论 SRT 序号如何乱序，这里使用的是读取时的列表索引，保证一一对应
            trans = translated_map.get(i, "")
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
            
        # 安全检查：确保输出数量与输入一致
        if len(new_subs) != len(subs):
            logger.error(f"严重错误: 输出字幕数量 ({len(new_subs)}) 与输入 ({len(subs)}) 不一致!")
        
        # 保存
        output_path = self.output_file
        if not output_path:
            name, ext = os.path.splitext(self.input_file)
            output_path = f"{name}_chs_web{ext}"
            
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(srt.compose(new_subs))
            
        logger.info(f"翻译完成: {output_path}")

async def process_batch(args):
    """批量处理"""
    input_path = args.input_path
    
    # 获取待处理文件列表
    files_to_process = []
    if os.path.isfile(input_path):
        files_to_process.append(input_path)
    elif os.path.isdir(input_path):
        for root, _, files in os.walk(input_path):
            for file in files:
                if file.lower().endswith('.srt') and not file.endswith('_chs_web.srt'):
                    files_to_process.append(os.path.join(root, file))
    
    if not files_to_process:
        logger.error(f"未找到 SRT 文件: {input_path}")
        return

    logger.info(f"共找到 {len(files_to_process)} 个文件待处理")
    
    # 使用上下文管理器复用浏览器
    async with DeepLWebTranslator(args) as translator:
        for i, file_path in enumerate(files_to_process):
            logger.info(f"[{i+1}/{len(files_to_process)}] 处理: {file_path}")
            try:
                # 如果指定了输出文件且输入是单个文件，则使用指定的输出路径
                # 如果是目录，则自动生成输出路径
                output_file = args.output_file if (len(files_to_process) == 1 and args.output_file) else None
                await translator.process_file(file_path, output_file)
            except Exception as e:
                logger.error(f"处理文件失败 {file_path}: {e}")
                # 出错后尝试重启浏览器上下文，防止页面崩溃影响下一个
                try:
                    await translator.page.reload()
                except:
                    pass

def main():
    parser = argparse.ArgumentParser(description="DeepL 网页版字幕翻译工具 (Playwright)")
    parser.add_argument("input_path", help="输入 SRT 文件或目录路径")
    parser.add_argument("--output_file", "-o", help="输出文件 (仅处理单个文件时有效)")
    parser.add_argument("--bilingual", action="store_true", help="输出双语字幕")
    parser.add_argument("--single-mode", action="store_true", help="强制使用逐行翻译模式 (速度较慢但最稳定)")
    parser.add_argument("--show_browser", action="store_true", help="显示浏览器窗口 (调试用)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_path):
        print(f"路径不存在: {args.input_path}")
        sys.exit(1)
        
    setup_logging()
    
    # 首次运行需要安装浏览器
    if not os.path.exists(os.path.expanduser("~/.cache/ms-playwright")) and not os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
         print("提示: 首次运行可能需要安装浏览器内核，请执行: playwright install chromium")
    
    asyncio.run(process_batch(args))

if __name__ == "__main__":
    main()
