#!/usr/bin/env python3
"""
偵錯字體問題
"""
import os
import sys
import django

# 設定 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from utils.pdf_report_generator import PDFReportGenerator
from core.models import TestProjectResult

def debug_font_issue():
    """偵錯字體問題"""
    print("🔍 偵錯字體問題")
    print("=" * 50)
    
    try:
        # 建立 PDF 生成器
        generator = PDFReportGenerator()
        
        print(f"✅ PDF 生成器建立成功")
        print(f"   • 中文字體名稱: {generator.chinese_font_name}")
        print(f"   • 中文粗體名稱: {generator.chinese_font_bold_name}")
        print()
        
        # 檢查字體檔案是否存在
        import platform
        system = platform.system()
        print(f"🖥️  作業系統: {system}")
        
        if system == "Darwin":  # macOS
            font_paths = [
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/Helvetica.ttc", 
                "/Library/Fonts/Arial Unicode MS.ttf",
                "/System/Library/Fonts/STHeiti Light.ttc"
            ]
            
            print("📁 檢查 macOS 字體檔案:")
            for path in font_paths:
                exists = os.path.exists(path)
                status = "✅" if exists else "❌"
                print(f"   {status} {path}")
        
        print()
        
        # 測試字體註冊
        try:
            from reportlab.pdfbase import pdfmetrics
            registered_fonts = pdfmetrics.getRegisteredFontNames()
            print(f"📝 已註冊的字體: {len(registered_fonts)} 個")
            
            chinese_fonts = [name for name in registered_fonts if 'Chinese' in name or 'Font' in name]
            if chinese_fonts:
                print(f"   中文相關字體: {chinese_fonts}")
            else:
                print("   ⚠️  找不到中文相關字體")
        except Exception as e:
            print(f"   ❌ 無法檢查字體註冊: {e}")
        
        print()
        
        # 取得測試數據並生成 PDF
        test_results = TestProjectResult.objects.filter(crawl_status='completed')
        if test_results.exists():
            test_result = test_results.first()
            print(f"📄 生成測試 PDF...")
            
            output_path = "/tmp/debug_font_test.pdf"
            result_path = generator.generate_test_result_report(test_result, output_path)
            
            file_size = os.path.getsize(result_path)
            print(f"   • 檔案路徑: {result_path}")
            print(f"   • 檔案大小: {file_size:,} bytes")
            
            # 檢查檔案內容
            with open(result_path, 'rb') as f:
                content = f.read(100)  # 讀取前 100 bytes
                if b'ChineseFont' in content or b'PingFang' in content:
                    print(f"   ✅ PDF 包含中文字體資訊")
                else:
                    print(f"   ⚠️  PDF 可能未包含中文字體")
                    
            print()
            print("🎯 建議的解決方案:")
            print("   1. 清除瀏覽器快取並重新整理頁面")
            print("   2. 使用無痕模式重新下載 PDF")
            print("   3. 檢查 PDF 檢視器是否支援嵌入字體")
            
        else:
            print("❌ 找不到測試數據")
            
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_font_issue()