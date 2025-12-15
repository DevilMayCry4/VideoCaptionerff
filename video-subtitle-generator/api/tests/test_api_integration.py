#!/usr/bin/env python3
"""
API集成测试
"""

import unittest
import json
import tempfile
import os
from io import BytesIO
from unittest.mock import patch, MagicMock

from werkzeug.datastructures import FileStorage
from app import create_app, db
from src.models.process_record import ProcessRecord


class TestAPIIntegration(unittest.TestCase):
    """API集成测试"""
    
    def setUp(self):
        """测试前准备"""
        # 创建测试应用
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.app.config['UPLOAD_FOLDER'] = os.path.join(self.temp_dir, 'uploads')
        self.app.config['AUDIO_FOLDER'] = os.path.join(self.temp_dir, 'audio')
        self.app.config['SUBTITLE_FOLDER'] = os.path.join(self.temp_dir, 'subtitles')
        
        # 创建必要的目录
        os.makedirs(self.app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(self.app.config['AUDIO_FOLDER'], exist_ok=True)
        os.makedirs(self.app.config['SUBTITLE_FOLDER'], exist_ok=True)
        
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
    
    def tearDown(self):
        """测试后清理"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        
        # 清理临时目录
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_health_check(self):
        """测试健康检查接口"""
        response = self.client.get('/health')
        
        self.assertEqual(response.status_code, 200, "健康检查应该返回200")
        
        data = json.loads(response.data)
        self.assertEqual(data['code'], 0, "响应code应该是0")
        self.assertEqual(data['data']['status'], 'healthy', "状态应该是healthy")
        self.assertIn('timestamp', data['data'], "响应应该包含时间戳")
        self.assertIn('version', data['data'], "响应应该包含版本号")
    
    def test_upload_file_success(self):
        """测试文件上传成功"""
        # 创建测试文件
        test_content = b'Test video content for upload'
        file_storage = FileStorage(
            stream=BytesIO(test_content),
            filename='test_video.mp4',
            content_type='video/mp4'
        )
        
        # 上传文件
        response = self.client.post('/api/upload', data={
            'file': file_storage
        })
        
        self.assertEqual(response.status_code, 200, "文件上传应该成功")
        
        data = json.loads(response.data)
        self.assertEqual(data['code'], 0, "响应code应该是0")
        self.assertIn('task_id', data['data'], "响应应该包含任务ID")
        self.assertEqual(data['data']['status'], 'pending', "初始状态应该是pending")
        self.assertIn('message', data['data'], "响应应该包含消息")
    
    def test_upload_file_no_file(self):
        """测试没有上传文件"""
        response = self.client.post('/api/upload', data={})
        
        self.assertEqual(response.status_code, 400, "没有文件应该返回400")
        
        data = json.loads(response.data)
        self.assertEqual(data['code'], 'INVALID_FILE', "错误码应该是INVALID_FILE")
        self.assertIn('没有上传文件', data['message'], "错误消息应该提示没有上传文件")
    
    def test_upload_file_empty_filename(self):
        """测试空文件名"""
        file_storage = FileStorage(
            stream=BytesIO(b'test content'),
            filename='',
            content_type='video/mp4'
        )
        
        response = self.client.post('/api/upload', data={
            'file': file_storage
        })
        
        self.assertEqual(response.status_code, 400, "空文件名应该返回400")
        
        data = json.loads(response.data)
        self.assertEqual(data['code'], 'INVALID_FILE', "错误码应该是INVALID_FILE")
        self.assertIn('文件名为空', data['message'], "错误消息应该提示文件名为空")
    
    def test_upload_file_invalid_format(self):
        """测试无效的文件格式"""
        file_storage = FileStorage(
            stream=BytesIO(b'test content'),
            filename='test.txt',
            content_type='text/plain'
        )
        
        response = self.client.post('/api/upload', data={
            'file': file_storage
        })
        
        self.assertEqual(response.status_code, 400, "无效格式应该返回400")
        
        data = json.loads(response.data)
        self.assertEqual(data['code'], 'INVALID_FILE', "错误码应该是INVALID_FILE")
        self.assertIn('不支持的视频格式', data['message'], "错误消息应该提示不支持的格式")
    
    def test_get_status_task_not_found(self):
        """测试查询不存在的任务状态"""
        response = self.client.get('/api/status/nonexistent-task-id')
        
        self.assertEqual(response.status_code, 400, "不存在的任务应该返回400")
        
        data = json.loads(response.data)
        self.assertEqual(data['code'], 'TASK_NOT_FOUND', "错误码应该是TASK_NOT_FOUND")
        self.assertIn('任务不存在', data['message'], "错误消息应该提示任务不存在")
    
    def test_get_status_existing_task(self):
        """测试查询存在的任务状态"""
        # 首先上传文件
        test_content = b'Test video content'
        file_storage = FileStorage(
            stream=BytesIO(test_content),
            filename='test_video.mp4',
            content_type='video/mp4'
        )
        
        upload_response = self.client.post('/api/upload', data={
            'file': file_storage
        })
        
        upload_data = json.loads(upload_response.data)
        task_id = upload_data['data']['task_id']
        
        # 查询任务状态
        response = self.client.get(f'/api/status/{task_id}')
        
        self.assertEqual(response.status_code, 200, "查询状态应该成功")
        
        data = json.loads(response.data)
        self.assertEqual(data['code'], 0, "响应code应该是0")
        self.assertEqual(data['data']['task_id'], task_id, "任务ID应该匹配")
        self.assertEqual(data['data']['status'], 'pending', "状态应该是pending")
        self.assertEqual(data['data']['progress'], 0, "进度应该是0")
        self.assertIn('filename', data['data'], "响应应该包含文件名")
        self.assertIn('created_at', data['data'], "响应应该包含创建时间")
    
    @patch('src.services.audio_service.AudioService.extract_audio')
    def test_extract_audio_success(self, mock_extract_audio):
        """测试音频提取成功"""
        # 首先上传文件
        test_content = b'Test video content'
        file_storage = FileStorage(
            stream=BytesIO(test_content),
            filename='test_video.mp4',
            content_type='video/mp4'
        )
        
        upload_response = self.client.post('/api/upload', data={
            'file': file_storage
        })
        
        upload_data = json.loads(upload_response.data)
        task_id = upload_data['data']['task_id']
        
        # 模拟音频提取成功
        mock_extract_audio.return_value = '/path/to/audio.wav'
        
        # 提取音频
        response = self.client.post('/api/extract-audio', 
                                  data=json.dumps({'task_id': task_id}),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200, "音频提取应该成功")
        
        data = json.loads(response.data)
        self.assertEqual(data['code'], 0, "响应code应该是0")
        self.assertEqual(data['data']['task_id'], task_id, "任务ID应该匹配")
        self.assertEqual(data['data']['status'], 'transcribing', "状态应该是transcribing")
        self.assertEqual(data['data']['progress'], 60, "进度应该是60")
        self.assertIn('音频提取成功', data['data']['message'], "消息应该提示音频提取成功")
    
    def test_extract_audio_no_task_id(self):
        """测试音频提取缺少任务ID"""
        response = self.client.post('/api/extract-audio',
                                  data=json.dumps({}),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400, "缺少任务ID应该返回400")
        
        data = json.loads(response.data)
        self.assertEqual(data['code'], 'INVALID_REQUEST', "错误码应该是INVALID_REQUEST")
        self.assertIn('缺少任务ID', data['message'], "错误消息应该提示缺少任务ID")
    
    def test_extract_audio_task_not_found(self):
        """测试音频提取任务不存在"""
        response = self.client.post('/api/extract-audio',
                                  data=json.dumps({'task_id': 'nonexistent'}),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400, "不存在的任务应该返回400")
        
        data = json.loads(response.data)
        self.assertEqual(data['code'], 'TASK_NOT_FOUND', "错误码应该是TASK_NOT_FOUND")
        self.assertIn('任务不存在', data['message'], "错误消息应该提示任务不存在")
    
    @patch('src.services.subtitle_service.SubtitleService.generate_subtitle')
    def test_generate_subtitle_success(self, mock_generate_subtitle):
        """测试字幕生成成功"""
        # 首先创建处理记录
        with self.app.app_context():
            record = ProcessRecord(
                id='test-task-123',
                original_filename='test_video.mp4',
                stored_filename='test-task-123_test_video.mp4',
                file_path='/path/to/video.mp4',
                audio_path='/path/to/audio.wav',
                status='transcribing',
                progress=60
            )
            db.session.add(record)
            db.session.commit()
        
        # 模拟字幕生成成功
        mock_generate_subtitle.return_value = {
            'subtitle_path': '/path/to/subtitle.srt',
            'content': '1\n00:00:00,000 --> 00:00:05,000\nTest subtitle content'
        }
        
        # 生成字幕
        response = self.client.post('/api/generate-subtitle',
                                  data=json.dumps({'task_id': 'test-task-123'}),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200, "字幕生成应该成功")
        
        data = json.loads(response.data)
        self.assertEqual(data['code'], 0, "响应code应该是0")
        self.assertEqual(data['data']['task_id'], 'test-task-123', "任务ID应该匹配")
        self.assertEqual(data['data']['status'], 'completed', "状态应该是completed")
        self.assertEqual(data['data']['progress'], 100, "进度应该是100")
        self.assertIn('subtitle_path', data['data'], "响应应该包含字幕文件路径")
        self.assertIn('content', data['data'], "响应应该包含字幕内容")
    
    def test_download_subtitle_task_not_found(self):
        """测试下载字幕任务不存在"""
        response = self.client.get('/api/download/nonexistent-task-id')
        
        self.assertEqual(response.status_code, 400, "不存在的任务应该返回400")
        
        data = json.loads(response.data)
        self.assertEqual(data['code'], 'TASK_NOT_FOUND', "错误码应该是TASK_NOT_FOUND")
        self.assertIn('任务不存在', data['message'], "错误消息应该提示任务不存在")
    
    def test_download_subtitle_not_found(self):
        """测试下载字幕文件不存在"""
        # 首先创建处理记录
        with self.app.app_context():
            record = ProcessRecord(
                id='test-task-123',
                original_filename='test_video.mp4',
                stored_filename='test-task-123_test_video.mp4',
                file_path='/path/to/video.mp4',
                status='completed',
                progress=100
            )
            db.session.add(record)
            db.session.commit()
        
        response = self.client.get('/api/download/test-task-123')
        
        self.assertEqual(response.status_code, 400, "不存在的字幕文件应该返回400")
        
        data = json.loads(response.data)
        self.assertEqual(data['code'], 'SUBTITLE_NOT_FOUND', "错误码应该是SUBTITLE_NOT_FOUND")
        self.assertIn('字幕文件不存在', data['message'], "错误消息应该提示字幕文件不存在")


if __name__ == '__main__':
    unittest.main()