#!/usr/bin/env python3
"""
資料庫結構探索腳本
逆向工程：從現有資料庫中提取完整的表結構和關係
"""

import psycopg2
from sshtunnel import SSHTunnelForwarder
import json
from collections import defaultdict

# 資料庫連接配置
import os

# 獲取腳本所在目錄
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PRIVATE_KEY_PATH = os.path.join(SCRIPT_DIR, 'private-key-openssh.pem')

DB_CONFIG = {
    'ssh_host': '54.199.255.239',
    'ssh_port': 22,
    'ssh_username': 'victor_cheng',
    'ssh_private_key': PRIVATE_KEY_PATH,
    'db_host': 'localhost',
    'db_port': 5432,
    'db_name': 'projectdb',
    'db_user': 'projectuser',
    'db_password': 'projectpass'
}

def explore_database():
    """探索資料庫結構"""
    
    print("=" * 80)
    print("資料庫結構探索工具 - 逆向工程")
    print("=" * 80)
    print()
    
    # 建立 SSH 隧道
    print("[步驟 1/7] 建立 SSH 隧道...")
    tunnel = SSHTunnelForwarder(
        (DB_CONFIG['ssh_host'], DB_CONFIG['ssh_port']),
        ssh_username=DB_CONFIG['ssh_username'],
        ssh_pkey=DB_CONFIG['ssh_private_key'],
        remote_bind_address=(DB_CONFIG['db_host'], DB_CONFIG['db_port'])
    )
    tunnel.start()
    print(f"✓ SSH 隧道已建立 (本地端口: {tunnel.local_bind_port})")
    print()
    
    # 連接資料庫
    print("[步驟 2/7] 連接資料庫...")
    conn = psycopg2.connect(
        host='localhost',
        port=tunnel.local_bind_port,
        database=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_password']
    )
    print("✓ 資料庫連接成功")
    print()
    
    cursor = conn.cursor()
    
    # ========== 步驟 3: 列出所有表 ==========
    print("[步驟 3/7] 列出所有表...")
    print("-" * 80)
    
    cursor.execute("""
        SELECT 
            table_schema,
            table_name,
            table_type
        FROM information_schema.tables
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY table_schema, table_name;
    """)
    
    tables = cursor.fetchall()
    print(f"✓ 找到 {len(tables)} 個表\n")
    
    table_list = []
    for schema, table_name, table_type in tables:
        print(f"  • {schema}.{table_name} ({table_type})")
        table_list.append((schema, table_name))
    
    print()
    
    # ========== 步驟 4: 分析每個表的結構 ==========
    print("[步驟 4/7] 分析表結構...")
    print("-" * 80)
    
    table_structures = {}
    
    for schema, table_name in table_list:
        full_table_name = f"{schema}.{table_name}"
        
        # 獲取欄位信息
        cursor.execute("""
            SELECT 
                column_name,
                data_type,
                character_maximum_length,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position;
        """, (schema, table_name))
        
        columns = cursor.fetchall()
        
        # 獲取主鍵
        cursor.execute("""
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = %s::regclass AND i.indisprimary;
        """, (full_table_name,))
        
        primary_keys = [row[0] for row in cursor.fetchall()]
        
        # 獲取外鍵
        cursor.execute("""
            SELECT
                kcu.column_name,
                ccu.table_schema AS foreign_table_schema,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = %s
                AND tc.table_name = %s;
        """, (schema, table_name))
        
        foreign_keys = cursor.fetchall()
        
        # 獲取索引
        cursor.execute("""
            SELECT
                i.relname AS index_name,
                a.attname AS column_name,
                ix.indisunique AS is_unique
            FROM pg_class t
            JOIN pg_index ix ON t.oid = ix.indrelid
            JOIN pg_class i ON i.oid = ix.indexrelid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
            WHERE t.relname = %s
                AND t.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = %s)
                AND NOT ix.indisprimary
            ORDER BY i.relname, a.attname;
        """, (table_name, schema))
        
        indexes = cursor.fetchall()
        
        # 獲取記錄數
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {full_table_name};")
            row_count = cursor.fetchone()[0]
        except:
            row_count = 0
        
        table_structures[full_table_name] = {
            'schema': schema,
            'table_name': table_name,
            'columns': columns,
            'primary_keys': primary_keys,
            'foreign_keys': foreign_keys,
            'indexes': indexes,
            'row_count': row_count
        }
        
        print(f"\n📋 {full_table_name}")
        print(f"   記錄數: {row_count:,}")
        print(f"   主鍵: {', '.join(primary_keys) if primary_keys else '(無)'}")
        print(f"   欄位數: {len(columns)}")
        if foreign_keys:
            print(f"   外鍵數: {len(foreign_keys)}")
    
    print()
    
    # ========== 步驟 5: 分析表之間的關係 ==========
    print("[步驟 5/7] 分析表關係...")
    print("-" * 80)
    
    relationships = []
    
    # 5.1 顯式外鍵關係
    print("\n📌 顯式外鍵關係:")
    for full_table_name, info in table_structures.items():
        for fk in info['foreign_keys']:
            column_name, fk_schema, fk_table, fk_column = fk
            relationships.append({
                'type': 'explicit_fk',
                'from_table': full_table_name,
                'from_column': column_name,
                'to_table': f"{fk_schema}.{fk_table}",
                'to_column': fk_column,
                'confidence': 'high'
            })
            print(f"  ✓ {full_table_name}.{column_name} → {fk_schema}.{fk_table}.{fk_column}")
    
    if not relationships:
        print("  ⚠️ 沒有找到顯式外鍵約束")
    
    # 5.2 推斷隱含關係（基於欄位名稱）
    print("\n🔍 推斷隱含關係（基於欄位命名）:")
    
    implicit_relationships = []
    
    # 常見的外鍵命名模式
    fk_patterns = [
        ('user_id', 'user', 'id'),
        ('candidate_id', 'candidate', 'id'),
        ('individual_id', 'individual', 'id'),
        ('test_id', 'test', 'id'),
        ('project_id', 'project', 'id'),
        ('trait_id', 'trait', 'id'),
        ('assessment_id', 'assessment', 'id'),
        ('profile_id', 'profile', 'id'),
    ]
    
    for full_table_name, info in table_structures.items():
        column_names = [col[0] for col in info['columns']]
        
        for col_name in column_names:
            # 檢查是否匹配外鍵模式
            for pattern, target_table_hint, target_col in fk_patterns:
                if col_name.lower() == pattern.lower():
                    # 查找可能的目標表
                    for target_full_name, target_info in table_structures.items():
                        target_table = target_info['table_name'].lower()
                        
                        # 檢查目標表名是否包含提示詞
                        if target_table_hint in target_table:
                            # 檢查目標表是否有對應的主鍵
                            if target_col in target_info['primary_keys']:
                                implicit_relationships.append({
                                    'type': 'implicit_fk',
                                    'from_table': full_table_name,
                                    'from_column': col_name,
                                    'to_table': target_full_name,
                                    'to_column': target_col,
                                    'confidence': 'medium',
                                    'reason': f'欄位名稱 {col_name} 匹配模式 {pattern}'
                                })
                                print(f"  ? {full_table_name}.{col_name} → {target_full_name}.{target_col} (推斷)")
    
    relationships.extend(implicit_relationships)
    
    # 5.3 分析數據重複（同一數據在不同表出現）
    print("\n🔎 分析數據重複模式:")
    
    data_overlap = []
    
    # 比較不同表的欄位名稱，找出可能的重複數據
    table_columns = {}
    for full_table_name, info in table_structures.items():
        table_columns[full_table_name] = set([col[0].lower() for col in info['columns']])
    
    # 找出共同欄位
    for table1, cols1 in table_columns.items():
        for table2, cols2 in table_columns.items():
            if table1 >= table2:  # 避免重複比較
                continue
            
            common_cols = cols1 & cols2
            
            # 排除常見的系統欄位
            system_cols = {'id', 'created_at', 'updated_at', 'created_by', 'updated_by'}
            meaningful_common = common_cols - system_cols
            
            if len(meaningful_common) >= 2:  # 至少有 2 個共同欄位
                data_overlap.append({
                    'table1': table1,
                    'table2': table2,
                    'common_columns': list(meaningful_common),
                    'overlap_count': len(meaningful_common)
                })
                print(f"  ⚠️ {table1} ↔ {table2}")
                print(f"     共同欄位: {', '.join(list(meaningful_common)[:5])}")
    
    if not data_overlap:
        print("  ✓ 沒有發現明顯的數據重複")
    
    print(f"\n✓ 找到 {len([r for r in relationships if r['type'] == 'explicit_fk'])} 個顯式外鍵")
    print(f"✓ 推斷 {len([r for r in relationships if r['type'] == 'implicit_fk'])} 個隱含關係")
    print(f"✓ 發現 {len(data_overlap)} 組可能的數據重複")
    print()
    
    # ========== 步驟 6: 分析數據樣本 ==========
    print("[步驟 6/7] 分析數據樣本與數據重複...")
    print("-" * 80)
    
    data_samples = {}
    value_overlaps = []
    
    for full_table_name, info in table_structures.items():
        if info['row_count'] > 0:
            try:
                # 獲取前 3 筆記錄
                cursor.execute(f"SELECT * FROM {full_table_name} LIMIT 3;")
                samples = cursor.fetchall()
                
                # 獲取欄位名稱
                column_names = [desc[0] for desc in cursor.description]
                
                data_samples[full_table_name] = {
                    'columns': column_names,
                    'samples': samples
                }
                
                print(f"\n📊 {full_table_name} (前 3 筆)")
                print(f"   欄位: {', '.join(column_names[:5])}{'...' if len(column_names) > 5 else ''}")
                
            except Exception as e:
                print(f"\n⚠️ {full_table_name}: 無法讀取數據 ({str(e)})")
    
    # 6.2 檢測實際數據重複
    print("\n🔍 檢測實際數據重複...")
    
    # 對於有共同欄位的表，檢查實際數據是否重複
    for overlap in data_overlap:
        table1 = overlap['table1']
        table2 = overlap['table2']
        common_cols = overlap['common_columns']
        
        # 只檢查前幾個共同欄位
        check_cols = common_cols[:3]
        
        try:
            # 構建查詢來檢查數據重複
            col_list = ', '.join([f't1.{col}' for col in check_cols])
            join_conditions = ' AND '.join([f't1.{col} = t2.{col}' for col in check_cols])
            
            query = f"""
                SELECT COUNT(*) 
                FROM {table1} t1
                INNER JOIN {table2} t2 ON {join_conditions}
                LIMIT 1;
            """
            
            cursor.execute(query)
            match_count = cursor.fetchone()[0]
            
            if match_count > 0:
                value_overlaps.append({
                    'table1': table1,
                    'table2': table2,
                    'matching_columns': check_cols,
                    'match_count': match_count
                })
                print(f"  ⚠️ 發現數據重複: {table1} ↔ {table2}")
                print(f"     匹配欄位: {', '.join(check_cols)}")
                print(f"     重複記錄數: {match_count}")
        
        except Exception as e:
            # 查詢失敗，可能是數據類型不匹配
            pass
    
    if not value_overlaps:
        print("  ✓ 沒有發現明顯的數據值重複")
    
    print()
    
    # ========== 步驟 7: 生成報告 ==========
    print("[步驟 7/7] 生成詳細報告...")
    print("-" * 80)
    
    report = {
        'database': DB_CONFIG['db_name'],
        'total_tables': len(tables),
        'total_relationships': len(relationships),
        'explicit_fk_count': len([r for r in relationships if r['type'] == 'explicit_fk']),
        'implicit_fk_count': len([r for r in relationships if r['type'] == 'implicit_fk']),
        'data_overlap_count': len(data_overlap),
        'value_overlap_count': len(value_overlaps),
        'tables': table_structures,
        'relationships': relationships,
        'data_overlaps': data_overlap,
        'value_overlaps': value_overlaps,
        'data_samples': data_samples
    }
    
    # 保存為 JSON
    with open('database_schema_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    
    print("✓ 詳細報告已保存到: database_schema_report.json")
    
    # 生成 Markdown 報告
    generate_markdown_report(report)
    print("✓ Markdown 報告已保存到: database_schema_report.md")
    
    print()
    print("=" * 80)
    print("探索完成！")
    print("=" * 80)
    
    # 清理
    cursor.close()
    conn.close()
    tunnel.stop()
    
    return report

def generate_markdown_report(report):
    """生成 Markdown 格式的報告"""
    
    md = []
    md.append("# 資料庫結構分析報告\n")
    md.append(f"**資料庫**: {report['database']}\n")
    md.append(f"**總表數**: {report['total_tables']}\n")
    md.append(f"**總關係數**: {report['total_relationships']}\n")
    md.append(f"**生成時間**: {json.dumps(None, default=str)}\n")
    md.append("\n---\n\n")
    
    # 表摘要
    md.append("## 📋 表摘要\n\n")
    md.append("| 表名 | 記錄數 | 欄位數 | 主鍵 | 外鍵數 |\n")
    md.append("|------|--------|--------|------|--------|\n")
    
    for table_name, info in sorted(report['tables'].items()):
        pk = ', '.join(info['primary_keys']) if info['primary_keys'] else '-'
        fk_count = len(info['foreign_keys'])
        md.append(f"| {table_name} | {info['row_count']:,} | {len(info['columns'])} | {pk} | {fk_count} |\n")
    
    md.append("\n---\n\n")
    
    # 表關係
    md.append("## 🔗 表關係分析\n\n")
    
    # 顯式外鍵
    md.append("### 顯式外鍵約束\n\n")
    explicit_fks = [r for r in report['relationships'] if r['type'] == 'explicit_fk']
    
    if explicit_fks:
        md.append("```\n")
        for rel in explicit_fks:
            md.append(f"{rel['from_table']}.{rel['from_column']} → {rel['to_table']}.{rel['to_column']}\n")
        md.append("```\n")
    else:
        md.append("⚠️ **沒有找到顯式外鍵約束**\n\n")
        md.append("這意味著資料庫設計時沒有定義外鍵關係，需要通過其他方式推斷表之間的關聯。\n")
    
    md.append("\n")
    
    # 隱含關係
    md.append("### 推斷的隱含關係\n\n")
    implicit_fks = [r for r in report['relationships'] if r['type'] == 'implicit_fk']
    
    if implicit_fks:
        md.append("基於欄位命名模式推斷的關係：\n\n")
        md.append("| 來源表 | 來源欄位 | 目標表 | 目標欄位 | 信心度 |\n")
        md.append("|--------|----------|--------|----------|--------|\n")
        for rel in implicit_fks:
            md.append(f"| {rel['from_table']} | {rel['from_column']} | {rel['to_table']} | {rel['to_column']} | {rel['confidence']} |\n")
        md.append("\n")
    else:
        md.append("沒有發現明顯的隱含關係。\n\n")
    
    # 數據重複
    md.append("### 數據重複分析\n\n")
    
    if report.get('data_overlaps'):
        md.append("⚠️ **發現以下表之間有共同欄位，可能存在數據重複**：\n\n")
        for overlap in report['data_overlaps']:
            md.append(f"**{overlap['table1']} ↔ {overlap['table2']}**\n")
            md.append(f"- 共同欄位數: {overlap['overlap_count']}\n")
            md.append(f"- 共同欄位: {', '.join(overlap['common_columns'][:10])}\n")
            md.append("\n")
    
    if report.get('value_overlaps'):
        md.append("🔴 **發現實際數據重複**：\n\n")
        for overlap in report['value_overlaps']:
            md.append(f"**{overlap['table1']} ↔ {overlap['table2']}**\n")
            md.append(f"- 匹配欄位: {', '.join(overlap['matching_columns'])}\n")
            md.append(f"- 重複記錄數: {overlap['match_count']}\n")
            md.append("\n")
        
        md.append("**建議**:\n")
        md.append("1. 確認這些表之間的關係\n")
        md.append("2. 考慮是否需要建立外鍵約束\n")
        md.append("3. 或者使用其中一個表作為主表，其他表引用它\n")
        md.append("\n")
    
    if not report.get('data_overlaps') and not report.get('value_overlaps'):
        md.append("✓ 沒有發現明顯的數據重複。\n\n")
    
    md.append("\n---\n\n")
    
    # 詳細表結構
    md.append("## 📊 詳細表結構\n\n")
    
    for table_name, info in sorted(report['tables'].items()):
        md.append(f"### {table_name}\n\n")
        md.append(f"**記錄數**: {info['row_count']:,}\n\n")
        
        # 欄位
        md.append("**欄位**:\n\n")
        md.append("| 欄位名 | 類型 | 可空 | 預設值 |\n")
        md.append("|--------|------|------|--------|\n")
        
        for col in info['columns']:
            col_name, data_type, max_len, nullable, default = col
            type_str = f"{data_type}({max_len})" if max_len else data_type
            nullable_str = "✓" if nullable == "YES" else "✗"
            default_str = str(default)[:30] if default else "-"
            
            # 標記主鍵
            if col_name in info['primary_keys']:
                col_name = f"**{col_name}** 🔑"
            
            md.append(f"| {col_name} | {type_str} | {nullable_str} | {default_str} |\n")
        
        md.append("\n")
        
        # 外鍵
        if info['foreign_keys']:
            md.append("**外鍵**:\n\n")
            for fk in info['foreign_keys']:
                col, fk_schema, fk_table, fk_col = fk
                md.append(f"- `{col}` → `{fk_schema}.{fk_table}.{fk_col}`\n")
            md.append("\n")
        
        # 索引
        if info['indexes']:
            md.append("**索引**:\n\n")
            current_index = None
            for idx_name, col_name, is_unique in info['indexes']:
                if idx_name != current_index:
                    unique_str = " (UNIQUE)" if is_unique else ""
                    md.append(f"- `{idx_name}`{unique_str}: {col_name}")
                    current_index = idx_name
                else:
                    md.append(f", {col_name}")
            md.append("\n\n")
        
        md.append("---\n\n")
    
    # 保存
    with open('database_schema_report.md', 'w', encoding='utf-8') as f:
        f.writelines(md)

if __name__ == '__main__':
    try:
        report = explore_database()
        
        print("\n📁 生成的文件:")
        print("  • database_schema_report.json - 完整的 JSON 報告")
        print("  • database_schema_report.md   - Markdown 格式報告")
        print("\n下一步:")
        print("  1. 查看報告文件")
        print("  2. 分析表關係")
        print("  3. 建立 ER Model")
        
    except Exception as e:
        print(f"\n❌ 錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
