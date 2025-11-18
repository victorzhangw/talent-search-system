#!/usr/bin/env python3
"""
檢查 PDF 內容的腳本
"""
import PyPDF2
import sys

def check_pdf_content(pdf_path):
    """檢查 PDF 內容"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            print(f"PDF 檔案: {pdf_path}")
            print(f"總頁數: {len(pdf_reader.pages)}")
            print("=" * 50)
            
            for i, page in enumerate(pdf_reader.pages, 1):
                print(f"\n第 {i} 頁內容:")
                print("-" * 30)
                try:
                    text = page.extract_text()
                    if text.strip():
                        # 只顯示前300個字元
                        preview = text.strip()[:300]
                        print(preview)
                        if len(text.strip()) > 300:
                            print("...")
                    else:
                        print("[頁面主要為圖表或格式化內容]")
                except Exception as e:
                    print(f"無法提取文字: {e}")
                    
    except ImportError:
        print("需要安裝 PyPDF2: pip install PyPDF2")
    except Exception as e:
        print(f"錯誤: {e}")

if __name__ == "__main__":
    check_pdf_content("/tmp/test_report_5.pdf")