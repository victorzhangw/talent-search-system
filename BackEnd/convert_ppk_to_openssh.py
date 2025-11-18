#!/usr/bin/env python3
"""
PPK 轉 OpenSSH 格式工具
將 PuTTY 的 PPK 格式私鑰轉換為 OpenSSH 格式
"""

import sys
import os

def convert_ppk_to_openssh():
    """轉換 PPK 到 OpenSSH 格式"""
    ppk_file = r'C:\Users\adrian\Desktop\性格分析\private-key-251017.ppk'
    output_file = 'private-key-openssh.pem'
    
    print("=" * 60)
    print("PPK 轉 OpenSSH 格式工具")
    print("=" * 60)
    print()
    print(f"來源檔案: {ppk_file}")
    print(f"輸出檔案: {output_file}")
    print()
    
    if not os.path.exists(ppk_file):
        print(f"錯誤: 找不到 PPK 檔案: {ppk_file}")
        return False
    
    print("請選擇轉換方式:")
    print()
    print("方式 1: 使用 PuTTYgen (推薦)")
    print("  1. 開啟 PuTTYgen")
    print("  2. 點選 'Load' 載入 PPK 檔案")
    print("  3. 點選 'Conversions' -> 'Export OpenSSH key'")
    print(f"  4. 儲存為: {os.path.abspath(output_file)}")
    print()
    print("方式 2: 使用命令列工具")
    print("  如果已安裝 PuTTY，可以使用以下命令:")
    print(f'  puttygen "{ppk_file}" -O private-openssh -o "{output_file}"')
    print()
    print("方式 3: 使用密碼認證")
    print("  修改 db_schema_analyzer.py 使用密碼而非私鑰")
    print()
    
    return True

if __name__ == '__main__':
    convert_ppk_to_openssh()
    input("\n按 Enter 鍵結束...")
