#!/usr/bin/env python3
"""
测试验证器模块
"""

import unittest
from io import BytesIO
from werkzeug.datastructures import FileStorage

from src.utils.validators import validate_video_file, ALLOWED_EXTENSIONS, MAX_FILE_SIZE


class TestValidators(unittest.TestCase):
    """测试文件验证器"""
    
    def setUp(self):
        """测试前准备"""
        self.allowed_extensions = ALLOWED_EXTENSIONS
        self.max_file_size = MAX_FILE_SIZE
    
    def test_valid_video_extensions(self):
        """测试有效的视频文件扩展名"""
        valid_files = [
            'test.mp4',
            'video.mov',
            'movie.avi',
            'clip.wmv',
            'UPPER.MP4',
            'mixed.Mp4'
        ]
        
        for filename in valid_files:
            with self.subTest(filename=filename):
                # 创建模拟文件对象
                file_storage = FileStorage(
                    stream=BytesIO(b'dummy content'),
                    filename=filename,
                    content_type='video/mp4'
                )
                is_valid, error_msg = validate_video_file(file_storage)
                self.assertTrue(is_valid, f"文件 {filename} 应该被接受")
                self.assertEqual(error_msg, '', f"文件 {filename} 不应该有错误消息")
    
    def test_invalid_video_extensions(self):
        """测试无效的视频文件扩展名"""
        invalid_files = [
            'document.pdf',
            'image.jpg',
            'audio.mp3',
            'text.txt',
            'script.py',
            'no_extension'
        ]
        
        for filename in invalid_files:
            with self.subTest(filename=filename):
                file_storage = FileStorage(
                    stream=BytesIO(b'dummy content'),
                    filename=filename,
                    content_type='application/octet-stream'
                )
                is_valid, error_msg = validate_video_file(file_storage)
                self.assertFalse(is_valid, f"文件 {filename} 应该被拒绝")
                self.assertIn('不支持的视频格式', error_msg)
    
    def test_file_size_validation(self):
        """测试文件大小验证"""
        # 创建超过大小限制的文件 (500MB + 1字节)
        oversized_content = b'x' * (self.max_file_size + 1)
        file_storage = FileStorage(
            stream=BytesIO(oversized_content),
            filename='large_video.mp4',
            content_type='video/mp4'
        )
        
        is_valid, error_msg = validate_video_file(file_storage)
        self.assertFalse(is_valid, "超大文件应该被拒绝")
        self.assertIn('文件大小超过限制', error_msg)
    
    def test_empty_file(self):
        """测试空文件"""
        file_storage = FileStorage(
            stream=BytesIO(b''),
            filename='empty.mp4',
            content_type='video/mp4'
        )
        
        is_valid, error_msg = validate_video_file(file_storage)
        self.assertFalse(is_valid, "空文件应该被拒绝")
        self.assertIn('文件为空', error_msg)
    
    def test_none_file(self):
        """测试None文件"""
        is_valid, error_msg = validate_video_file(None)
        self.assertFalse(is_valid, "None文件应该被拒绝")
        self.assertIn('文件对象无效', error_msg)
    
    def test_valid_file_size(self):
        """测试有效的文件大小"""
        # 创建100MB的文件
        valid_content = b'x' * (100 * 1024 * 1024)
        file_storage = FileStorage(
            stream=BytesIO(valid_content),
            filename='valid_video.mp4',
            content_type='video/mp4'
        )
        
        is_valid, error_msg = validate_video_file(file_storage)
        self.assertTrue(is_valid, "有效大小的文件应该被接受")
        self.assertEqual(error_msg, '')


if __name__ == '__main__':
    unittest.main()