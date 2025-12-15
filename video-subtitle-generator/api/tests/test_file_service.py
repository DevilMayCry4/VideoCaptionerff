#!/usr/bin/env python3
"""
测试文件服务模块
"""

import unittest
import os
import tempfile
import shutil
from io import BytesIO
from werkzeug.datastructures import FileStorage

from src.services.file_service import FileService


class TestFileService(unittest.TestCase):
    """测试文件服务"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.file_service = FileService(upload_folder=os.path.join(self.temp_dir, 'uploads'))
    
    def tearDown(self):
        """测试后清理"""
        # 删除临时目录
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_save_uploaded_file(self):
        """测试保存上传文件"""
        # 创建测试文件
        test_content = b'Test video content'
        file_storage = FileStorage(
            stream=BytesIO(test_content),
            filename='test_video.mp4',
            content_type='video/mp4'
        )
        
        task_id = 'test-task-123'
        
        # 保存文件
        file_path = self.file_service.save_uploaded_file(file_storage, task_id)
        
        # 验证文件存在
        self.assertTrue(os.path.exists(file_path), "文件应该被保存")
        
        # 验证文件内容
        with open(file_path, 'rb') as f:
            saved_content = f.read()
        self.assertEqual(saved_content, test_content, "文件内容应该匹配")
        
        # 验证文件名包含任务ID
        self.assertIn(task_id, os.path.basename(file_path), "文件名应该包含任务ID")
    
    def test_save_uploaded_file_secure_filename(self):
        """测试保存上传文件时使用安全文件名"""
        # 创建包含危险字符的文件名
        dangerous_filename = '../../../etc/passwd.mp4'
        test_content = b'Test content'
        file_storage = FileStorage(
            stream=BytesIO(test_content),
            filename=dangerous_filename,
            content_type='video/mp4'
        )
        
        task_id = 'test-task-456'
        
        # 保存文件
        file_path = self.file_service.save_uploaded_file(file_storage, task_id)
        
        # 验证文件名被安全处理
        filename = os.path.basename(file_path)
        self.assertNotIn('..', filename, "文件名不应该包含路径穿越字符")
        self.assertNotIn('/', filename, "文件名不应该包含路径分隔符")
    
    def test_get_file_extension(self):
        """测试获取文件扩展名"""
        test_cases = [
            ('video.mp4', '.mp4'),
            ('movie.MOV', '.MOV'),
            ('clip.avi', '.avi'),
            ('show.wmv', '.wmv'),
            ('no_extension', ''),
            ('', ''),
            ('.hidden', ''),
            ('multiple.dots.mp4', '.mp4')
        ]
        
        for filename, expected_extension in test_cases:
            with self.subTest(filename=filename):
                extension = self.file_service.get_file_extension(filename)
                self.assertEqual(extension, expected_extension, 
                               f"文件 {filename} 的扩展名应该是 {expected_extension}")
    
    def test_ensure_directory_exists(self):
        """测试确保目录存在"""
        test_dir = os.path.join(self.temp_dir, 'test_subdir')
        
        # 验证目录不存在
        self.assertFalse(os.path.exists(test_dir), "测试目录应该不存在")
        
        # 确保目录存在
        self.file_service.ensure_directory_exists(test_dir)
        
        # 验证目录存在
        self.assertTrue(os.path.exists(test_dir), "目录应该被创建")
        self.assertTrue(os.path.isdir(test_dir), "路径应该是目录")
        
        # 再次调用不应该报错
        self.file_service.ensure_directory_exists(test_dir)
        self.assertTrue(os.path.exists(test_dir), "目录应该仍然存在")
    
    def test_delete_file(self):
        """测试删除文件"""
        # 创建测试文件
        test_file = os.path.join(self.temp_dir, 'test_delete.mp4')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        # 验证文件存在
        self.assertTrue(os.path.exists(test_file), "测试文件应该存在")
        
        # 删除文件
        success = self.file_service.delete_file(test_file)
        
        # 验证文件被删除
        self.assertTrue(success, "文件删除应该成功")
        self.assertFalse(os.path.exists(test_file), "文件应该被删除")
    
    def test_delete_nonexistent_file(self):
        """测试删除不存在的文件"""
        nonexistent_file = os.path.join(self.temp_dir, 'does_not_exist.mp4')
        
        # 删除不存在的文件不应该报错
        success = self.file_service.delete_file(nonexistent_file)
        self.assertTrue(success, "删除不存在的文件应该返回成功")


if __name__ == '__main__':
    unittest.main()