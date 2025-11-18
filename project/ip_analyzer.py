#!/usr/bin/env python3
"""
簡化版IP分析腳本
專門分析Django security.log中的攻擊IP
"""

import re
import subprocess
from collections import defaultdict, Counter
from datetime import datetime
import os

def parse_security_log(log_file='security.log'):
    """解析security.log文件"""
    if not os.path.exists(log_file):
        print(f"❌ 日誌文件不存在: {log_file}")
        return {}
    
    ip_activities = defaultdict(list)
    
    # 匹配日誌中的IP地址
    ip_pattern = r'IP: ([\d\.]+)'
    
    print(f"🔍 正在分析 {log_file}...")
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                # 提取IP地址
                ip_match = re.search(ip_pattern, line)
                if ip_match:
                    ip = ip_match.group(1)
                    
                    # 分析攻擊類型
                    attack_info = {
                        'line_num': line_num,
                        'content': line.strip(),
                        'type': 'unknown'
                    }
                    
                    # 識別攻擊類型
                    if 'SUSPICIOUS_PATH' in line:
                        attack_info['type'] = '路徑掃描'
                    elif 'SUSPICIOUS_USER_AGENT' in line:
                        attack_info['type'] = '可疑工具'
                    elif 'SUSPICIOUS_404' in line:
                        attack_info['type'] = '404掃描'
                    elif 'SUSPICIOUS_GET_PARAM' in line:
                        attack_info['type'] = 'GET參數攻擊'
                    elif 'SUSPICIOUS_POST_PARAM' in line:
                        attack_info['type'] = 'POST參數攻擊'
                    elif 'HIGH_RISK_IP' in line:
                        attack_info['type'] = '高風險IP'
                    elif 'RATE_LIMIT_EXCEEDED' in line:
                        attack_info['type'] = '速率限制'
                    
                    ip_activities[ip].append(attack_info)
    
    except Exception as e:
        print(f"❌ 讀取日誌文件錯誤: {e}")
        return {}
    
    print(f"✅ 分析完成，發現 {len(ip_activities)} 個可疑IP")
    return ip_activities

def analyze_ips(ip_activities, threshold=5):
    """分析IP威脅等級"""
    if not ip_activities:
        print("📊 沒有發現可疑活動")
        return []
    
    dangerous_ips = []
    
    print(f"\n📊 IP威脅分析報告:")
    print("=" * 80)
    
    # 按活動次數排序
    sorted_ips = sorted(ip_activities.items(), key=lambda x: len(x[1]), reverse=True)
    
    for ip, activities in sorted_ips:
        count = len(activities)
        
        # 統計攻擊類型
        attack_types = Counter(activity['type'] for activity in activities)
        
        # 計算威脅等級
        threat_level = "低"
        if count >= threshold * 2:
            threat_level = "高"
        elif count >= threshold:
            threat_level = "中"
        
        print(f"\n🎯 IP地址: {ip}")
        print(f"   攻擊次數: {count}")
        print(f"   威脅等級: {threat_level}")
        print(f"   攻擊類型: {dict(attack_types)}")
        
        # 顯示最近幾次攻擊
        recent_attacks = activities[-3:]
        print(f"   最近攻擊:")
        for attack in recent_attacks:
            print(f"     - {attack['type']}: {attack['content'][:100]}...")
        
        # 判斷是否建議封鎖
        if count >= threshold:
            print(f"   🚨 建議: 立即封鎖")
            dangerous_ips.append({
                'ip': ip,
                'count': count,
                'threat_level': threat_level,
                'attack_types': dict(attack_types)
            })
        else:
            print(f"   ✅ 建議: 繼續監控")
        
        print("-" * 40)
    
    return dangerous_ips

def check_if_blocked(ip):
    """檢查IP是否已被封鎖"""
    try:
        result = subprocess.run(
            f"iptables -L INPUT -v -n | grep {ip}",
            shell=True, capture_output=True, text=True
        )
        return result.returncode == 0
    except:
        return False

def block_ip(ip):
    """封鎖IP"""
    if check_if_blocked(ip):
        print(f"⚠️  {ip} 已經被封鎖")
        return False
    
    try:
        subprocess.run(
            f"sudo iptables -A INPUT -s {ip} -j DROP",
            shell=True, check=True
        )
        
        # 記錄封鎖行為
        with open('blocked_ips.log', 'a') as f:
            f.write(f"{datetime.now().isoformat()} - Blocked: {ip}\n")
        
        print(f"✅ 成功封鎖: {ip}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 封鎖失敗 {ip}: {e}")
        print("💡 提示: 可能需要sudo權限")
        return False

def show_block_commands(dangerous_ips):
    """顯示封鎖命令"""
    if not dangerous_ips:
        return
    
    print(f"\n🛡️  建議執行的封鎖命令:")
    print("-" * 50)
    
    for ip_info in dangerous_ips:
        ip = ip_info['ip']
        count = ip_info['count']
        print(f"# 封鎖 {ip} (攻擊{count}次)")
        print(f"sudo iptables -A INPUT -s {ip} -j DROP")
        print()
    
    print("# 保存iptables規則 (Ubuntu/Debian)")
    print("sudo iptables-save > /etc/iptables/rules.v4")
    print()
    print("# 或者使用iptables-persistent")
    print("sudo apt install iptables-persistent")
    print("sudo netfilter-persistent save")

def main():
    print("🛡️  Django安全日誌分析工具")
    print("=" * 50)
    
    # 分析日誌
    ip_activities = parse_security_log('security.log')
    
    if not ip_activities:
        print("✅ 沒有發現可疑活動")
        return
    
    # 分析威脅
    threshold = 5  # 可以調整閾值
    dangerous_ips = analyze_ips(ip_activities, threshold)
    
    if not dangerous_ips:
        print("\n✅ 沒有發現需要封鎖的高威脅IP")
        return
    
    print(f"\n🚨 發現 {len(dangerous_ips)} 個建議封鎖的IP")
    
    # 詢問是否要自動封鎖
    choice = input("\n選擇操作:\n1. 顯示封鎖命令\n2. 手動確認封鎖\n3. 退出\n請選擇 (1-3): ")
    
    if choice == '1':
        show_block_commands(dangerous_ips)
    elif choice == '2':
        for ip_info in dangerous_ips:
            ip = ip_info['ip']
            count = ip_info['count']
            threat = ip_info['threat_level']
            
            response = input(f"\n是否封鎖 {ip}? (攻擊{count}次, 威脅等級:{threat}) [y/N]: ")
            if response.lower() in ['y', 'yes']:
                block_ip(ip)
    else:
        print("👋 退出")
    
    print(f"\n📋 建議:")
    print("1. 定期執行此腳本監控新攻擊")
    print("2. 檢查 blocked_ips.log 查看封鎖歷史")
    print("3. 考慮設定cron job自動化執行")

if __name__ == "__main__":
    main()