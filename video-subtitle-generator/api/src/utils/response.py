"""
响应工具函数
"""

import json
from typing import Any, Optional, Tuple
from flask import Response

def success_response(data: Any = None) -> Tuple[Response, int]:
    """
    生成成功响应
    
    Args:
        data: 响应数据
        
    Returns:
        (Flask响应对象, HTTP状态码)
    """
    response = {
        'code': 0,
        'message': 'success',
        'data': data
    }
    
    # 使用标准的json库来避免Flask上下文问题
    return Response(
        json.dumps(response, ensure_ascii=False),
        status=200,
        mimetype='application/json'
    ), 200

def error_response(error_code: str, message: Optional[str] = None) -> Tuple[Response, int]:
    """
    生成错误响应
    
    Args:
        error_code: 错误代码
        message: 错误消息
        
    Returns:
        (Flask响应对象, HTTP状态码)
    """
    # 如果message是空字符串，保持空字符串；如果是None，使用默认值
    if message is None:
        message = '操作失败'
    
    response = {
        'code': error_code,
        'message': message,
        'data': None
    }
    
    # 使用标准的json库来避免Flask上下文问题
    return Response(
        json.dumps(response, ensure_ascii=False),
        status=400,
        mimetype='application/json'
    ), 400