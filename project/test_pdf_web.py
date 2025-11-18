#!/usr/bin/env python3
"""
透過網頁測試 PDF 生成功能
"""
import requests
import os

def test_pdf_via_web():
    """透過網頁測試 PDF 生成"""
    print("🌐 測試網頁 PDF 生成功能")
    print("=" * 40)
    
    # 測試伺服器狀態
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        print(f"✅ Django 服務器狀態: {response.status_code}")
    except Exception as e:
        print(f"❌ 無法連接到 Django 服務器: {e}")
        return
    
    # 假設我們有一個測試用的 result_id
    test_result_id = 5  # 使用我們之前測試過的 ID
    
    # 測試 PDF 生成 URL
    pdf_url = f"http://localhost:8000/enterprise/test-results/{test_result_id}/pdf/"
    
    print(f"📄 測試 PDF URL: {pdf_url}")
    
    try:
        # 嘗試訪問 PDF 生成 URL
        response = requests.get(pdf_url, timeout=30)
        
        if response.status_code == 200:
            # 儲存 PDF 檔案
            output_path = "/tmp/web_generated_report.pdf"
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            file_size = len(response.content)
            print(f"✅ PDF 生成成功!")
            print(f"   • 狀態碼: {response.status_code}")
            print(f"   • 檔案大小: {file_size:,} bytes")
            print(f"   • 儲存路徑: {output_path}")
            
            # 檢查檔案類型
            import subprocess
            try:
                result = subprocess.run(['file', output_path], capture_output=True, text=True)
                print(f"   • 檔案類型: {result.stdout.strip()}")
            except:
                pass
                
            if file_size > 20000:
                print("✅ 字體應已嵌入 (檔案大小 > 20KB)")
            else:
                print("⚠️  字體可能未嵌入 (檔案較小)")
                
        elif response.status_code == 302:
            print(f"🔄 重新導向到: {response.headers.get('Location', 'Unknown')}")
            print("   可能需要登入才能訪問")
        else:
            print(f"❌ PDF 生成失敗")
            print(f"   • 狀態碼: {response.status_code}")
            print(f"   • 回應內容: {response.text[:200]}...")
            
    except Exception as e:
        print(f"❌ 請求失敗: {e}")

if __name__ == "__main__":
    test_pdf_via_web()