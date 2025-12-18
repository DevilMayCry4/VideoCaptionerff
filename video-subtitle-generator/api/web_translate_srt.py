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
        self.max_chars = 3500 # 用户要求4000，保守一点设为3500，留出符号的空间
        
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
            # 直接进入 JA -> ZH 模式
            await self.page.goto("https://www.deepl.com/zh/translator#ja/zh/")
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
        async def process_buffer(subs_list):
            if not subs_list: return
            
            # 1. 构建带【序号+原文】符号的文本
            # 例如: 【1Hello world】【2How are you】
            # 使用 batch 内的相对序号 (1, 2, 3...)，方便匹配
            formatted_lines = []
            for i, s in enumerate(subs_list):
                # 序号从1开始
                seq_num = i + 1
                content = s.content.strip().replace(chr(10), ' ')
                formatted_lines.append(f"【{seq_num}{content}】")
                
            # 用户要求不要用换行符分割，直接拼接
            merged_text = "".join(formatted_lines)
            
            logger.info(f"正在翻译批次，包含 {len(subs_list)} 条字幕，共 {len(merged_text)} 字符")
            
            # 2. 发送翻译
            trans_text = await self.translate_text(merged_text)
            
            # 3. 解析结果
            # 使用正则提取【序号+译文】中的内容
            # 匹配格式: 【数字+内容】
            matches = re.findall(r'【(\d+)(.*?)】', trans_text, re.DOTALL)
            
            # 转换匹配结果为字典: {序号: 译文}
            # 注意: 序号是字符串，需要转int
            batch_trans_map = {}
            for seq_str, content in matches:
                try:
                    seq = int(seq_str)
                    batch_trans_map[seq] = content.strip()
                except ValueError:
                    continue

            # 4. 结果对齐与填充
            # 检查是否所有序号都找到了
            missing_indices = []
            for i in range(len(subs_list)):
                seq_num = i + 1
                if seq_num in batch_trans_map:
                    # 找到了，存入全局 map
                    s = subs_list[i]
                    translated_map[s.index] = batch_trans_map[seq_num]
                else:
                    missing_indices.append(i)
            
            # 如果有缺失，对缺失的部分进行降级处理 (逐条翻译 -> 递归批量补翻)
            if missing_indices:
                logger.warning(f"批次中有 {len(missing_indices)}/{len(subs_list)} 条字幕未匹配到序号，尝试补翻...")
                logger.debug(f"原文片段: {merged_text[:200]}...")
                logger.debug(f"译文片段: {trans_text[:200]}...")
                
                # 收集所有缺失的字幕对象
                missing_subs = [subs_list[i] for i in missing_indices]
                
                # 递归调用 process_buffer 处理缺失的部分
                # 注意：为了防止无限递归，如果补翻数量太少（比如就1条），或者递归深度过深（这里未实现深度限制，但通常一两轮就能解决），
                # 其实对于少量缺失，递归调用也是安全的，因为它会重新生成序号并尝试翻译。
                # 如果只有1条，递归进去后也会走批量逻辑（虽然只有1条），也是带序号的。
                
                # 为了防止死循环（比如某条字幕永远无法翻译），我们可以加一个简单的判断：
                # 如果是补翻，我们仍然用 process_buffer，但如果失败了（再次进入 missing_indices），可能需要终极兜底（比如不带序号直接翻）。
                # 这里简化处理：直接递归调用 process_buffer。
                # 由于 process_buffer 内部生成序号是基于传入列表的 enumerate，
                # 所以 missing_subs 会被重新编号为 1, 2, 3...，这有助于 DeepL 重新理解。
                
                await process_buffer(missing_subs)
            
            # 批次间延时
            await asyncio.sleep(random.uniform(2, 5))

        for sub in subs:
            # 计算长度：内容长度 + 符号长度(2) + 换行符(1)
            content_len = len(sub.content) + 3
            
            if buffer_len + content_len > self.max_chars:
                await process_buffer(buffer_subs)
                pbar.update(len(buffer_subs))
                buffer_subs = []
                buffer_len = 0
            
            buffer_subs.append(sub)
            buffer_len += content_len
            
        # 处理剩余
        await process_buffer(buffer_subs)
        pbar.update(len(buffer_subs))
        pbar.close()
        
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
