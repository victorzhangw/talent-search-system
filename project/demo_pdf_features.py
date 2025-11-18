#!/usr/bin/env python3
"""
展示 PDF 功能特點的腳本
"""
import os
import sys
import django

# 設定 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from utils.pdf_report_generator import PDFReportGenerator
from core.models import TestProjectResult

def demo_pdf_features():
    """展示 PDF 功能特點"""
    print("🎯 測驗結果 PDF 報告生成功能展示")
    print("=" * 60)
    
    # 檢查是否有測試數據
    test_results = TestProjectResult.objects.filter(crawl_status='completed')
    
    if not test_results.exists():
        print("❌ 沒有找到已完成的測驗結果")
        return
    
    test_result = test_results.first()
    
    print(f"📊 測試資料:")
    print(f"   • 受測者: {test_result.test_invitation.invitee.name}")
    print(f"   • 測驗項目: {test_result.test_project.name}")
    print(f"   • 狀態: {test_result.crawl_status}")
    print(f"   • 完成時間: {test_result.test_invitation.completed_at or '未知'}")
    print()
    
    print("🎨 PDF 報告特點:")
    print("   ✅ 專業封面頁設計")
    print("   ✅ 自訂頁首頁尾")
    print("   ✅ Logo 預留空間 (2cm)")
    print("   ✅ Traitty 專業職位測評品牌")
    print("   ✅ Perception Group 公司資訊")
    print("   ✅ 完整的測驗結果分析")
    print("   ✅ 分類和特質詳細報告")
    print()
    
    print("📄 頁面內容:")
    print("   第1頁: 封面頁 (標題 + 受測人基本資訊)")
    print("   第2頁: 基本資訊詳情")
    print("   第3頁: 測驗結果和分類分析")
    print("   第4頁: 特質分析和數據摘要")
    print()
    
    print("🎯 頁首內容:")
    print("   • [Logo 空間] + Traitty 專業職位測評")
    print("   • 生成日期")
    print()
    
    print("📝 頁尾內容:")
    print("   • Perception Group 公司描述")
    print("   • Copyright © Perception Group")
    print("   • 聯絡信箱與網站")
    print("   • 頁碼")
    print()
    
    try:
        # 生成 PDF
        generator = PDFReportGenerator()
        output_path = f"/tmp/demo_report_{test_result.id}.pdf"
        result_path = generator.generate_test_result_report(test_result, output_path)
        
        file_size = os.path.getsize(result_path)
        print(f"✅ PDF 報告已生成:")
        print(f"   • 檔案路徑: {result_path}")
        print(f"   • 檔案大小: {file_size} bytes")
        print(f"   • 可以使用 PDF 檢視器開啟查看")
        
    except Exception as e:
        print(f"❌ 生成失敗: {str(e)}")

if __name__ == "__main__":
    demo_pdf_features()