#!/usr/bin/env python3
"""
测试响应工具模块
"""

import unittest
import json

from src.utils.response import success_response, error_response


class TestResponse(unittest.TestCase):
    """测试响应工具函数"""
    
    def test_success_response_with_data(self):
        """测试成功响应（包含数据）"""
        data = {
            'task_id': 'test-123',
            'status': 'processing',
            'progress': 50
        }
        
        response, status_code = success_response(data)
        
        # 验证状态码
        self.assertEqual(status_code, 200, "成功响应的状态码应该是200")
        
        # 验证响应数据
        response_data = json.loads(response.data)
        self.assertEqual(response_data['code'], 0, "成功响应的code应该是0")
        self.assertEqual(response_data['message'], 'success', "成功响应的message应该是success")
        self.assertEqual(response_data['data'], data, "响应数据应该匹配输入数据")
    
    def test_success_response_empty_data(self):
        """测试成功响应（空数据）"""
        response, status_code = success_response({})
        
        self.assertEqual(status_code, 200, "成功响应的状态码应该是200")
        
        response_data = json.loads(response.data)
        self.assertEqual(response_data['code'], 0, "成功响应的code应该是0")
        self.assertEqual(response_data['data'], {}, "空数据应该返回空对象")
    
    def test_success_response_none_data(self):
        """测试成功响应（None数据）"""
        response, status_code = success_response(None)
        
        self.assertEqual(status_code, 200, "成功响应的状态码应该是200")
        
        response_data = json.loads(response.data)
        self.assertEqual(response_data['code'], 0, "成功响应的code应该是0")
        self.assertIsNone(response_data['data'], "None数据应该返回null")
    
    def test_error_response_with_message(self):
        """测试错误响应（包含错误消息）"""
        error_code = 'INVALID_FILE'
        error_message = '不支持的视频格式'
        
        response, status_code = error_response(error_code, error_message)
        
        # 验证状态码
        self.assertEqual(status_code, 400, "错误响应的状态码应该是400")
        
        # 验证响应数据
        response_data = json.loads(response.data)
        self.assertEqual(response_data['code'], error_code, "错误响应的code应该匹配输入错误码")
        self.assertEqual(response_data['message'], error_message, "错误响应的message应该匹配输入错误消息")
        self.assertIsNone(response_data['data'], "错误响应的data应该是null")
    
    def test_error_response_empty_message(self):
        """测试错误响应（空错误消息）"""
        error_code = 'UNKNOWN_ERROR'
        
        response, status_code = error_response(error_code, '')
        
        self.assertEqual(status_code, 400, "错误响应的状态码应该是400")
        
        response_data = json.loads(response.data)
        self.assertEqual(response_data['code'], error_code, "错误响应的code应该匹配输入错误码")
        self.assertEqual(response_data['message'], '', "空错误消息应该返回空字符串")
    
    def test_error_response_none_message(self):
        """测试错误响应（None错误消息）"""
        error_code = 'SYSTEM_ERROR'
        
        response, status_code = error_response(error_code, None)
        
        self.assertEqual(status_code, 400, "错误响应的状态码应该是400")
        
        response_data = json.loads(response.data)
        self.assertEqual(response_data['code'], error_code, "错误响应的code应该匹配输入错误码")
        self.assertEqual(response_data['message'], '操作失败', "None错误消息应该返回默认消息")
    
    def test_response_structure_consistency(self):
        """测试响应结构的一致性"""
        # 测试成功响应结构
        success_resp, _ = success_response({'test': 'data'})
        success_data = json.loads(success_resp.data)
        
        # 验证成功响应包含必要字段
        self.assertIn('code', success_data, "成功响应应该包含code字段")
        self.assertIn('message', success_data, "成功响应应该包含message字段")
        self.assertIn('data', success_data, "成功响应应该包含data字段")
        
        # 测试错误响应结构
        error_resp, _ = error_response('TEST_ERROR', 'Test error message')
        error_data = json.loads(error_resp.data)
        
        # 验证错误响应包含必要字段
        self.assertIn('code', error_data, "错误响应应该包含code字段")
        self.assertIn('message', error_data, "错误响应应该包含message字段")
        self.assertIn('data', error_data, "错误响应应该包含data字段")
    
    def test_response_content_type(self):
        """测试响应内容类型"""
        response, _ = success_response({'test': 'data'})
        
        # 验证响应头
        self.assertEqual(response.content_type, 'application/json', 
                        "响应内容类型应该是application/json")
        self.assertEqual(response.mimetype, 'application/json',
                        "响应MIME类型应该是application/json")


if __name__ == '__main__':
    unittest.main()