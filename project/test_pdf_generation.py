#!/usr/bin/env python3
"""
測試 PDF 生成功能的腳本
"""
import os
import sys
import django

# 設定 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from utils.pdf_report_generator import PDFReportGenerator
from core.models import TestProjectResult

def test_pdf_generation():
    """測試 PDF 生成功能"""
    print("開始測試 PDF 生成功能...")
    
    # 檢查是否有測試數據
    test_results = TestProjectResult.objects.filter(crawl_status='completed')
    
    if not test_results.exists():
        print("沒有找到已完成的測驗結果，建立模擬數據...")
        create_mock_data()
        return
    
    # 使用第一個測試結果
    test_result = test_results.first()
    print(f"使用測試結果 ID: {test_result.id}")
    print(f"受測者: {test_result.test_invitation.invitee.name}")
    print(f"測驗項目: {test_result.test_project.name}")
    
    try:
        # 建立 PDF 生成器
        generator = PDFReportGenerator()
        
        # 生成 PDF 到檔案
        output_path = f"/tmp/test_report_{test_result.id}.pdf"
        result_path = generator.generate_test_result_report(test_result, output_path)
        
        print(f"PDF 報告已生成: {result_path}")
        print(f"檔案大小: {os.path.getsize(result_path)} bytes")
        
        # 驗證檔案是否存在
        if os.path.exists(result_path):
            print("✅ PDF 生成成功！")
            print(f"您可以在此路徑查看報告: {result_path}")
        else:
            print("❌ PDF 檔案未找到")
            
    except Exception as e:
        print(f"❌ PDF 生成失敗: {str(e)}")
        import traceback
        traceback.print_exc()

def create_mock_data():
    """建立模擬數據用於測試"""
    print("建立模擬數據功能需要實際的數據模型...")
    print("請確保您有已完成的測驗結果數據來進行測試")

if __name__ == "__main__":
    test_pdf_generation()