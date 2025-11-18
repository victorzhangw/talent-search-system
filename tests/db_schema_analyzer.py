#!/usr/bin/env python3
"""
資料庫 Schema 分析工具
透過 SSH 隧道連接 PostgreSQL 資料庫並生成詳細的 schema 文件
"""

import psycopg2
from sshtunnel import SSHTunnelForwarder
import paramiko
import json
from datetime import datetime
import os

# 資料庫連接配置
DB_CONFIG = {
    'ssh_host': '61.216.152.8',
    'ssh_port': 22,
    'ssh_username': 'victor_cheng',
    # 選項 1: 使用私鑰（需要先轉換 PPK 為 OpenSSH 格式）
    'ssh_private_key': 'private-key-openssh.pem',  # 使用轉換後的 OpenSSH 格式
    # 選項 2: 使用密碼（如果不使用私鑰，請註解上面一行並取消下面註解）
    # 'ssh_password': '',  # 填入 SSH 密碼
    'db_host': 'localhost',
    'db_port': 5432,
    'db_name': 'projectdb',
    'db_user': 'projectuser',
    'db_password': 'projectpass'  # 請填入資料庫密碼
}

def load_ssh_key(key_path):
    """載入 SSH 私鑰（支援 PPK 和 OpenSSH 格式）"""
    try:
        # 嘗試載入 PPK 格式
        if key_path.lower().endswith('.ppk'):
            print(f"偵測到 PPK 格式私鑰，正在載入...")
            return paramiko.RSAKey.from_private_key_file(key_path)
        else:
            # 嘗試載入 OpenSSH 格式
            print(f"正在載入 OpenSSH 格式私鑰...")
            return paramiko.RSAKey.from_private_key_file(key_path)
    except paramiko.ssh_exception.SSHException:
        # 如果 RSA 失敗，嘗試其他格式
        try:
            return paramiko.Ed25519Key.from_private_key_file(key_path)
        except:
            try:
                return paramiko.ECDSAKey.from_private_key_file(key_path)
            except:
                return paramiko.DSSKey.from_private_key_file(key_path)

def create_ssh_tunnel(config):
    """建立 SSH 隧道"""
    print(f"正在建立 SSH 隧道到 {config['ssh_host']}...")
    
    # 準備 SSH 認證參數
    ssh_params = {
        'ssh_address_or_host': (config['ssh_host'], config['ssh_port']),
        'ssh_username': config['ssh_username'],
        'remote_bind_address': (config['db_host'], config['db_port'])
    }
    
    # 使用私鑰或密碼
    if 'ssh_private_key' in config and config['ssh_private_key']:
        if os.path.exists(config['ssh_private_key']):
            print(f"使用私鑰認證: {config['ssh_private_key']}")
            ssh_key = load_ssh_key(config['ssh_private_key'])
            ssh_params['ssh_pkey'] = ssh_key
        else:
            print(f"警告: 找不到私鑰檔案: {config['ssh_private_key']}")
            print("請確認檔案路徑或使用密碼認證")
            raise FileNotFoundError(f"私鑰檔案不存在: {config['ssh_private_key']}")
    elif 'ssh_password' in config and config['ssh_password']:
        print("使用密碼認證")
        ssh_params['ssh_password'] = config['ssh_password']
    else:
        raise ValueError("請提供 SSH 私鑰或密碼")
    
    tunnel = SSHTunnelForwarder(**ssh_params)
    
    tunnel.start()
    print(f"SSH 隧道已建立，本地端口: {tunnel.local_bind_port}")
    return tunnel

def connect_database(tunnel, config):
    """連接資料庫"""
    print("正在連接資料庫...")
    
    conn = psycopg2.connect(
        host='localhost',
        port=tunnel.local_bind_port,
        database=config['db_name'],
        user=config['db_user'],
        password=config['db_password']
    )
    
    print("資料庫連接成功！")
    return conn

def get_all_tables(cursor):
    """取得所有資料表"""
    query = """
        SELECT 
            schemaname,
            tablename,
            tableowner
        FROM pg_tables
        WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
        ORDER BY schemaname, tablename;
    """
    cursor.execute(query)
    return cursor.fetchall()

def get_table_columns(cursor, schema, table):
    """取得資料表欄位資訊"""
    query = """
        SELECT 
            column_name,
            data_type,
            character_maximum_length,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position;
    """
    cursor.execute(query, (schema, table))
    return cursor.fetchall()

def get_table_constraints(cursor, schema, table):
    """取得資料表約束條件"""
    query = """
        SELECT
            tc.constraint_name,
            tc.constraint_type,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        LEFT JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        LEFT JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.table_schema = %s AND tc.table_name = %s
        ORDER BY tc.constraint_type, tc.constraint_name;
    """
    cursor.execute(query, (schema, table))
    return cursor.fetchall()

def get_table_indexes(cursor, schema, table):
    """取得資料表索引"""
    query = """
        SELECT
            indexname,
            indexdef
        FROM pg_indexes
        WHERE schemaname = %s AND tablename = %s
        ORDER BY indexname;
    """
    cursor.execute(query, (schema, table))
    return cursor.fetchall()

def get_table_row_count(cursor, schema, table):
    """取得資料表筆數"""
    try:
        query = f'SELECT COUNT(*) FROM "{schema}"."{table}";'
        cursor.execute(query)
        return cursor.fetchone()[0]
    except Exception as e:
        return f"無法取得 (錯誤: {str(e)})"

def analyze_database(conn):
    """分析資料庫結構"""
    cursor = conn.cursor()
    schema_data = {}
    
    # 取得所有資料表
    tables = get_all_tables(cursor)
    print(f"\n找到 {len(tables)} 個資料表")
    
    for schema, table, owner in tables:
        print(f"\n分析資料表: {schema}.{table}")
        
        if schema not in schema_data:
            schema_data[schema] = {}
        
        # 取得欄位資訊
        columns = get_table_columns(cursor, schema, table)
        
        # 取得約束條件
        constraints = get_table_constraints(cursor, schema, table)
        
        # 取得索引
        indexes = get_table_indexes(cursor, schema, table)
        
        # 取得資料筆數
        row_count = get_table_row_count(cursor, schema, table)
        
        schema_data[schema][table] = {
            'owner': owner,
            'row_count': row_count,
            'columns': [
                {
                    'name': col[0],
                    'type': col[1],
                    'max_length': col[2],
                    'nullable': col[3],
                    'default': col[4]
                }
                for col in columns
            ],
            'constraints': [
                {
                    'name': const[0],
                    'type': const[1],
                    'column': const[2],
                    'foreign_table': const[3],
                    'foreign_column': const[4]
                }
                for const in constraints
            ],
            'indexes': [
                {
                    'name': idx[0],
                    'definition': idx[1]
                }
                for idx in indexes
            ]
        }
    
    cursor.close()
    return schema_data

def generate_markdown_report(schema_data, output_file='database_schema.md'):
    """生成 Markdown 格式的 schema 報告"""
    print(f"\n正在生成 Markdown 報告: {output_file}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# 資料庫 Schema 文件\n\n")
        f.write(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        
        # 目錄
        f.write("## 目錄\n\n")
        for schema_name in sorted(schema_data.keys()):
            f.write(f"### Schema: {schema_name}\n")
            for table_name in sorted(schema_data[schema_name].keys()):
                f.write(f"- [{table_name}](#{schema_name}-{table_name})\n")
            f.write("\n")
        
        f.write("---\n\n")
        
        # 詳細內容
        for schema_name in sorted(schema_data.keys()):
            f.write(f"## Schema: {schema_name}\n\n")
            
            for table_name in sorted(schema_data[schema_name].keys()):
                table_data = schema_data[schema_name][table_name]
                
                f.write(f"### <a name='{schema_name}-{table_name}'></a>{table_name}\n\n")
                f.write(f"**擁有者**: {table_data['owner']}\n\n")
                f.write(f"**資料筆數**: {table_data['row_count']}\n\n")
                
                # 欄位資訊
                f.write("#### 欄位\n\n")
                f.write("| 欄位名稱 | 資料型別 | 長度 | 可為空 | 預設值 |\n")
                f.write("|---------|---------|------|--------|--------|\n")
                
                for col in table_data['columns']:
                    max_len = col['max_length'] if col['max_length'] else '-'
                    nullable = '是' if col['nullable'] == 'YES' else '否'
                    default = col['default'] if col['default'] else '-'
                    f.write(f"| {col['name']} | {col['type']} | {max_len} | {nullable} | {default} |\n")
                
                f.write("\n")
                
                # 約束條件
                if table_data['constraints']:
                    f.write("#### 約束條件\n\n")
                    f.write("| 約束名稱 | 類型 | 欄位 | 外鍵資料表 | 外鍵欄位 |\n")
                    f.write("|---------|------|------|-----------|----------|\n")
                    
                    for const in table_data['constraints']:
                        foreign_table = const['foreign_table'] if const['foreign_table'] else '-'
                        foreign_column = const['foreign_column'] if const['foreign_column'] else '-'
                        f.write(f"| {const['name']} | {const['type']} | {const['column']} | {foreign_table} | {foreign_column} |\n")
                    
                    f.write("\n")
                
                # 索引
                if table_data['indexes']:
                    f.write("#### 索引\n\n")
                    for idx in table_data['indexes']:
                        f.write(f"**{idx['name']}**\n")
                        f.write(f"```sql\n{idx['definition']}\n```\n\n")
                
                f.write("---\n\n")
    
    print(f"Markdown 報告已生成: {output_file}")

def generate_json_report(schema_data, output_file='database_schema.json'):
    """生成 JSON 格式的 schema 報告"""
    print(f"\n正在生成 JSON 報告: {output_file}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'generated_at': datetime.now().isoformat(),
            'schemas': schema_data
        }, f, ensure_ascii=False, indent=2)
    
    print(f"JSON 報告已生成: {output_file}")

def main():
    """主程式"""
    print("=" * 60)
    print("資料庫 Schema 分析工具")
    print("=" * 60)
    
    tunnel = None
    conn = None
    
    try:
        # 建立 SSH 隧道
        tunnel = create_ssh_tunnel(DB_CONFIG)
        
        # 連接資料庫
        conn = connect_database(tunnel, DB_CONFIG)
        
        # 分析資料庫
        schema_data = analyze_database(conn)
        
        # 生成報告
        generate_markdown_report(schema_data)
        generate_json_report(schema_data)
        
        print("\n" + "=" * 60)
        print("分析完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 關閉連接
        if conn:
            conn.close()
            print("\n資料庫連接已關閉")
        
        if tunnel:
            tunnel.stop()
            print("SSH 隧道已關閉")

if __name__ == '__main__':
    main()
