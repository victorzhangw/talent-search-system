#!/usr/bin/env python
"""
測試運行腳本
"""
import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
    django.setup()
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    # 運行所有測試
    failures = test_runner.run_tests(["tests"])
    
    if failures:
        sys.exit(1)
    else:
        print("\n✅ 所有測試都通過了！")
        sys.exit(0)