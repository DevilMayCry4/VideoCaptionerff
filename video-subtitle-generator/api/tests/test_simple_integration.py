import unittest
import json
import tempfile
import os
from unittest.mock import patch, Mock

from app import create_app, db
from src.models.process_record import ProcessRecord


class TestSimpleIntegration(unittest.TestCase):
    """简单集成测试 - 验证基本API功能"""
    
    def setUp(self):
        """设置测试环境"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
    
    def tearDown(self):
        """清理测试环境"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_health_check(self):
        """测试健康检查端点"""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['code'], 'SUCCESS')
        self.assertEqual(data['data']['status'], 'healthy')
    
    def test_upload_no_file(self):
        """测试上传接口 - 无文件"""
        response = self.client.post('/api/upload')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertEqual(data['code'], 'NO_FILE')
    
    def test_upload_invalid_file_type(self):
        """测试上传接口 - 无效文件类型"""
        # 创建一个临时文本文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test content")
            temp_file_path = f.name
        
        try:
            with open(temp_file_path, 'rb') as f:
                response = self.client.post('/api/upload', 
                                          data={'file': (f, 'test.txt')})
            
            self.assertEqual(response.status_code, 400)
            data = json.loads(response.data)
            self.assertEqual(data['code'], 'INVALID_FILE_TYPE')
            
        finally:
            os.unlink(temp_file_path)
    
    @patch('src.services.file_service.FileService.save_uploaded_file')
    def test_upload_success(self, mock_save_file):
        """测试上传接口 - 成功上传"""
        # Mock文件保存
        mock_save_file.return_value = '/tmp/test_video.mp4'
        
        # 创建一个临时MP4文件
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.mp4', delete=False) as f:
            f.write(b'dummy video content')
            temp_file_path = f.name
        
        try:
            with open(temp_file_path, 'rb') as f:
                response = self.client.post('/api/upload', 
                                          data={'file': (f, 'test_video.mp4')})
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(data['code'], 'SUCCESS')
            self.assertIn('task_id', data['data'])
            self.assertEqual(data['data']['filename'], 'test_video.mp4')
            self.assertEqual(data['data']['status'], 'pending')
            
        finally:
            os.unlink(temp_file_path)
    
    def test_status_no_task_id(self):
        """测试状态查询 - 无任务ID"""
        response = self.client.get('/api/status/')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertEqual(data['code'], 'NO_TASK_ID')
    
    def test_status_task_not_found(self):
        """测试状态查询 - 任务不存在"""
        response = self.client.get('/api/status/invalid-task-id')
        self.assertEqual(response.status_code, 404)
        
        data = json.loads(response.data)
        self.assertEqual(data['code'], 'TASK_NOT_FOUND')
    
    def test_status_success(self):
        """测试状态查询 - 成功查询"""
        # 创建一个测试记录
        from datetime import datetime
        with self.app.app_context():
            record = ProcessRecord(
                id='test-task-123',
                original_filename='test.mp4',
                file_path='/tmp/test.mp4',
                status='pending',
                progress=0,
                created_at=datetime.now()
            )
            db.session.add(record)
            db.session.commit()
        
        response = self.client.get('/api/status/test-task-123')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['code'], 'SUCCESS')
        self.assertEqual(data['data']['task_id'], 'test-task-123')
        self.assertEqual(data['data']['status'], 'pending')
        self.assertEqual(data['data']['progress'], 0)
    
    def test_extract_audio_no_data(self):
        """测试音频提取 - 无请求数据"""
        response = self.client.post('/api/extract-audio', 
                                  data=json.dumps({}),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertEqual(data['code'], 'INVALID_REQUEST')
    
    def test_extract_audio_no_task_id(self):
        """测试音频提取 - 无任务ID"""
        response = self.client.post('/api/extract-audio',
                                  data=json.dumps({'other_field': 'value'}),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertEqual(data['code'], 'INVALID_REQUEST')
    
    def test_generate_subtitle_no_data(self):
        """测试字幕生成 - 无请求数据"""
        response = self.client.post('/api/generate-subtitle',
                                  data=json.dumps({}),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertEqual(data['code'], 'INVALID_REQUEST')
    
    def test_generate_subtitle_no_task_id(self):
        """测试字幕生成 - 无任务ID"""
        response = self.client.post('/api/generate-subtitle',
                                  data=json.dumps({'other_field': 'value'}),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertEqual(data['code'], 'INVALID_REQUEST')
    
    def test_download_no_task_id(self):
        """测试文件下载 - 无任务ID"""
        response = self.client.get('/api/download')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertEqual(data['code'], 'NO_TASK_ID')
    
    def test_download_task_not_found(self):
        """测试文件下载 - 任务不存在"""
        response = self.client.get('/api/download/invalid-task-id')
        self.assertEqual(response.status_code, 404)
        
        data = json.loads(response.data)
        self.assertEqual(data['code'], 'TASK_NOT_FOUND')


if __name__ == '__main__':
    unittest.main()