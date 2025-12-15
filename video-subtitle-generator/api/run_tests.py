#!/usr/bin/env python3
"""
测试运行器
运行所有测试并生成测试报告
"""

import unittest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_all_tests():
    """运行所有测试"""
    # 创建测试加载器
    loader = unittest.TestLoader()
    
    # 创建测试运行器，使用详细输出
    runner = unittest.TextTestRunner(verbosity=2)
    
    # 发现测试用例
    start_dir = 'tests'
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # 运行测试
    print("=" * 60)
    print("开始运行视频字幕生成器后端测试")
    print("=" * 60)
    
    result = runner.run(suite)
    
    # 打印测试统计
    print("\n" + "=" * 60)
    print("测试完成统计:")
    print(f"运行测试数量: {result.testsRun}")
    print(f"成功测试: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败测试: {len(result.failures)}")
    print(f"错误测试: {len(result.errors)}")
    print("=" * 60)
    
    return result.wasSuccessful()

def run_specific_test(test_name):
    """运行特定测试"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(f'tests.{test_name}')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='运行视频字幕生成器后端测试')
    parser.add_argument('--test', type=str, help='指定要运行的测试名称')
    parser.add_argument('--coverage', action='store_true', help='生成覆盖率报告')
    
    args = parser.parse_args()
    
    if args.coverage:
        try:
            import coverage
            cov = coverage.Coverage()
            cov.start()
            
            if args.test:
                success = run_specific_test(args.test)
            else:
                success = run_all_tests()
            
            cov.stop()
            cov.save()
            
            print("\n" + "=" * 60)
            print("生成测试覆盖率报告:")
            cov.report()
            cov.html_report(directory='htmlcov')
            print("覆盖率HTML报告已生成到 htmlcov/ 目录")
            print("=" * 60)
            
        except ImportError:
            print("警告: coverage 模块未安装，无法生成覆盖率报告")
            if args.test:
                success = run_specific_test(args.test)
            else:
                success = run_all_tests()
    else:
        if args.test:
            success = run_specific_test(args.test)
        else:
            success = run_all_tests()
    
    # 根据测试结果退出
    sys.exit(0 if success else 1)