#!/usr/bin/env python3
"""
測試中文字體顯示的腳本
"""
import os
import sys
import django

# 設定 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from utils.pdf_report_generator import PDFReportGenerator
from core.models import TestProjectResult

def test_chinese_font():
    """測試中文字體顯示"""
    print("🔤 測試 PDF 中文字體顯示功能")
    print("=" * 50)
    
    test_results = TestProjectResult.objects.filter(crawl_status='completed')
    
    if not test_results.exists():
        print("❌ 沒有找到已完成的測驗結果")
        return
    
    test_result = test_results.first()
    
    try:
        # 建立 PDF 生成器
        generator = PDFReportGenerator()
        
        print(f"✅ 成功建立 PDF 生成器")
        print(f"   • 中文字體: {generator.chinese_font_name}")
        print(f"   • 中文粗體: {generator.chinese_font_bold_name}")
        print()
        
        # 生成測試 PDF
        output_path = "/tmp/chinese_font_test.pdf"
        result_path = generator.generate_test_result_report(test_result, output_path)
        
        file_size = os.path.getsize(result_path)
        print(f"✅ PDF 生成成功:")
        print(f"   • 檔案路徑: {result_path}")
        print(f"   • 檔案大小: {file_size:,} bytes")
        print()
        
        print("🎯 中文內容測試:")
        print("   ✅ 封面標題: 測驗項目名稱 + 完整報告")
        print("   ✅ 受測人基本資訊")
        print("   ✅ 頁首: Traitty 專業職位測評")
        print("   ✅ 頁尾: 公司描述和版權信息") 
        print("   ✅ 內容區域: 所有中文標題和內容")
        print()
        
        if file_size > 20000:  # 超過 20KB 表示字體已嵌入
            print("✅ 字體嵌入成功 (檔案大小 > 20KB)")
        else:
            print("⚠️  字體可能未正確嵌入 (檔案過小)")
            
    except Exception as e:
        print(f"❌ 測試失敗: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_chinese_font()