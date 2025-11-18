#!/usr/bin/env python
"""
測試覆蓋率腳本
"""
import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

def run_coverage():
    """運行測試覆蓋率分析"""
    try:
        import coverage
    except ImportError:
        print("請安裝 coverage 套件：pip install coverage")
        return
    
    # 啟動覆蓋率分析
    cov = coverage.Coverage()
    cov.start()
    
    # 設定 Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
    django.setup()
    
    # 運行測試
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["tests"])
    
    # 停止覆蓋率分析
    cov.stop()
    cov.save()
    
    # 生成報告
    print("\n" + "="*50)
    print("測試覆蓋率報告")
    print("="*50)
    
    cov.report()
    
    # 生成 HTML 報告
    print("\n生成 HTML 覆蓋率報告...")
    cov.html_report(directory='htmlcov')
    print("HTML 報告已生成至 htmlcov/ 目錄")
    
    return failures

if __name__ == "__main__":
    failures = run_coverage()
    sys.exit(1 if failures else 0)