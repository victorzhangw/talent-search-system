#!/usr/bin/env python3
"""
測驗結果報告生成器 - 示範如何從資料庫取得並合併資料
"""

class TestReportGenerator:
    """測驗結果報告生成器"""
    
    def __init__(self, db_connection):
        """
        初始化報告生成器
        
        Args:
            db_connection: 資料庫連接物件
        """
        self.conn = db_connection
        self.cursor = db_connection.cursor()
    
    def get_user_by_email(self, email):
        """
        步驟 1: 透過 email 取得使用者資訊
        
        Args:
            email: 使用者 email
            
        Returns:
            dict: 使用者資訊
        """
        query = """
            SELECT id, email, first_name, last_name, user_type
            FROM core_user
            WHERE email = %s;
        """
        self.cursor.execute(query, (email,))
        row = self.cursor.fetchone()
        
        if not row:
            return None
            
        return {
            'user_id': row[0],
            'email': row[1],
            'first_name': row[2],
            'last_name': row[3],
            'user_type': row[4]
        }
    
    def get_latest_test_result(self, user_id):
        """
        步驟 2: 取得使用者最新的測驗結果
        
        Args:
            user_id: 使用者 ID
            
        Returns:
            dict: 測驗結果資訊
        """
        query = """
            SELECT id, test_project_id, status, completed_at, created_at
            FROM test_result
            WHERE user_id = %s AND status = 'completed'
            ORDER BY completed_at DESC
            LIMIT 1;
        """
        self.cursor.execute(query, (user_id,))
        row = self.cursor.fetchone()
        
        if not row:
            return None
            
        return {
            'test_result_id': row[0],
            'test_project_id': row[1],
            'status': row[2],
            'completed_at': row[3],
            'created_at': row[4]
        }
    
    def get_trait_scores(self, test_result_id):
        """
        步驟 3: 取得特質評分
        
        Args:
            test_result_id: 測驗結果 ID
            
        Returns:
            list: 特質評分列表
        """
        query = """
            SELECT 
                trt.id,
                trt.trait_id,
                t.chinese_name,
                t.system_name,
                t.description,
                trt.score,
                trt.percentile
            FROM test_result_trait trt
            JOIN trait t ON trt.trait_id = t.id
            WHERE trt.test_result_id = %s
            ORDER BY trt.score DESC;
        """
        self.cursor.execute(query, (test_result_id,))
        rows = self.cursor.fetchall()
        
        traits = []
        for row in rows:
            traits.append({
                'id': row[0],
                'trait_id': row[1],
                'chinese_name': row[2],
                'system_name': row[3],
                'description': row[4],
                'score': row[5],
                'percentile': row[6]
            })
        
        return traits
    
    def get_project_info(self, test_project_id):
        """
        步驟 4: 取得測驗專案資訊
        
        Args:
            test_project_id: 測驗專案 ID
            
        Returns:
            dict: 專案資訊
        """
        query = """
            SELECT 
                tp.id,
                tp.name,
                tp.description,
                tpc.id as category_id,
                tpc.name as category_name,
                tpc.description as category_description
            FROM test_project tp
            LEFT JOIN test_project_category tpc ON tp.category_id = tpc.id
            WHERE tp.id = %s;
        """
        self.cursor.execute(query, (test_project_id,))
        row = self.cursor.fetchone()
        
        if not row:
            return None
            
        return {
            'project_id': row[0],
            'project_name': row[1],
            'project_description': row[2],
            'category_id': row[3],
            'category_name': row[4],
            'category_description': row[5]
        }
    
    def get_traits_by_category(self, test_result_id):
        """
        步驟 5: 按分類組織特質
        
        Args:
            test_result_id: 測驗結果 ID
            
        Returns:
            dict: 按分類組織的特質字典
        """
        query = """
            SELECT 
                tpc.id as category_id,
                tpc.name as category_name,
                t.id as trait_id,
                t.chinese_name as trait_name,
                trt.score,
                trt.percentile
            FROM test_result_trait trt
            JOIN trait t ON trt.trait_id = t.id
            LEFT JOIN test_project_category_trait tpct ON t.id = tpct.trait_id
            LEFT JOIN test_project_category tpc ON tpct.category_id = tpc.id
            WHERE trt.test_result_id = %s
            ORDER BY tpc.name, trt.score DESC;
        """
        self.cursor.execute(query, (test_result_id,))
        rows = self.cursor.fetchall()
        
        categories = {}
        for row in rows:
            category_id = row[0]
            category_name = row[1] or '未分類'
            
            if category_name not in categories:
                categories[category_name] = {
                    'category_id': category_id,
                    'traits': []
                }
            
            categories[category_name]['traits'].append({
                'trait_id': row[2],
                'trait_name': row[3],
                'score': row[4],
                'percentile': row[5]
            })
        
        return categories
    
    def generate_report(self, email):
        """
        完整報告生成流程
        
        Args:
            email: 使用者 email
            
        Returns:
            dict: 完整報告資料
        """
        # 步驟 1: 取得使用者資訊
        user = self.get_user_by_email(email)
        if not user:
            return {'error': f'找不到使用者: {email}'}
        
        # 步驟 2: 取得最新測驗結果
        test_result = self.get_latest_test_result(user['user_id'])
        if not test_result:
            return {'error': f'找不到測驗結果: {email}'}
        
        # 步驟 3: 取得特質評分
        traits = self.get_trait_scores(test_result['test_result_id'])
        
        # 步驟 4: 取得專案資訊
        project = self.get_project_info(test_result['test_project_id'])
        
        # 步驟 5: 按分類組織特質
        categories = self.get_traits_by_category(test_result['test_result_id'])
        
        # 步驟 6: 組合完整報告
        report = {
            'user': user,
            'test_result': test_result,
            'project': project,
            'traits': traits,
            'categories': categories,
            'statistics': {
                'total_traits': len(traits),
                'average_score': sum(t['score'] for t in traits if t['score']) / len(traits) if traits else 0,
                'highest_score': max((t['score'] for t in traits if t['score']), default=0),
                'lowest_score': min((t['score'] for t in traits if t['score']), default=0)
            }
        }
        
        return report
    
    def generate_report_single_query(self, email):
        """
        使用單一查詢取得所有資料（效能優化版本）
        
        Args:
            email: 使用者 email
            
        Returns:
            dict: 完整報告資料
        """
        query = """
            WITH user_info AS (
                SELECT id, email, first_name, last_name, user_type
                FROM core_user
                WHERE email = %s
            ),
            latest_test AS (
                SELECT tr.id, tr.test_project_id, tr.completed_at, tr.status
                FROM test_result tr
                JOIN user_info u ON tr.user_id = u.id
                WHERE tr.status = 'completed'
                ORDER BY tr.completed_at DESC
                LIMIT 1
            )
            SELECT 
                -- 使用者資訊
                u.id as user_id,
                u.email,
                u.first_name,
                u.last_name,
                u.user_type,
                
                -- 測驗資訊
                lt.id as test_result_id,
                lt.completed_at,
                lt.status,
                
                -- 專案資訊
                tp.id as project_id,
                tp.name as project_name,
                tp.description as project_description,
                
                -- 分類資訊
                tpc.id as category_id,
                tpc.name as category_name,
                tpc.description as category_description,
                
                -- 特質資訊
                t.id as trait_id,
                t.chinese_name as trait_name,
                t.system_name as trait_system_name,
                t.description as trait_description,
                
                -- 評分資訊
                trt.score,
                trt.percentile
                
            FROM user_info u
            CROSS JOIN latest_test lt
            JOIN test_project tp ON lt.test_project_id = tp.id
            LEFT JOIN test_project_category tpc ON tp.category_id = tpc.id
            JOIN test_result_trait trt ON lt.id = trt.test_result_id
            JOIN trait t ON trt.trait_id = t.id
            ORDER BY trt.score DESC;
        """
        
        self.cursor.execute(query, (email,))
        rows = self.cursor.fetchall()
        
        if not rows:
            return {'error': f'找不到資料: {email}'}
        
        # 解析第一行取得基本資訊
        first_row = rows[0]
        report = {
            'user': {
                'user_id': first_row[0],
                'email': first_row[1],
                'first_name': first_row[2],
                'last_name': first_row[3],
                'user_type': first_row[4]
            },
            'test_result': {
                'test_result_id': first_row[5],
                'completed_at': first_row[6],
                'status': first_row[7]
            },
            'project': {
                'project_id': first_row[8],
                'project_name': first_row[9],
                'project_description': first_row[10],
                'category_id': first_row[11],
                'category_name': first_row[12],
                'category_description': first_row[13]
            },
            'traits': [],
            'categories': {}
        }
        
        # 解析所有特質資料
        for row in rows:
            trait = {
                'trait_id': row[14],
                'chinese_name': row[15],
                'system_name': row[16],
                'description': row[17],
                'score': row[18],
                'percentile': row[19]
            }
            report['traits'].append(trait)
            
            # 按分類組織
            category_name = row[12] or '未分類'
            if category_name not in report['categories']:
                report['categories'][category_name] = {
                    'category_id': row[11],
                    'traits': []
                }
            report['categories'][category_name]['traits'].append(trait)
        
        # 計算統計資訊
        scores = [t['score'] for t in report['traits'] if t['score'] is not None]
        report['statistics'] = {
            'total_traits': len(report['traits']),
            'average_score': sum(scores) / len(scores) if scores else 0,
            'highest_score': max(scores) if scores else 0,
            'lowest_score': min(scores) if scores else 0
        }
        
        return report
    
    def print_report(self, report):
        """
        列印報告（格式化輸出）
        
        Args:
            report: 報告資料字典
        """
        if 'error' in report:
            print(f"錯誤: {report['error']}")
            return
        
        print("=" * 100)
        print("測驗結果報告")
        print("=" * 100)
        
        # 使用者資訊
        user = report['user']
        print(f"\n【受測者資訊】")
        print(f"姓名: {user['first_name']} {user['last_name']}")
        print(f"Email: {user['email']}")
        print(f"類型: {user['user_type']}")
        
        # 測驗資訊
        test = report['test_result']
        project = report['project']
        print(f"\n【測驗資訊】")
        print(f"測驗專案: {project['project_name']}")
        print(f"分類: {project['category_name']}")
        print(f"完成時間: {test['completed_at']}")
        print(f"狀態: {test['status']}")
        
        # 統計資訊
        stats = report['statistics']
        print(f"\n【統計資訊】")
        print(f"特質總數: {stats['total_traits']}")
        print(f"平均分數: {stats['average_score']:.2f}")
        print(f"最高分數: {stats['highest_score']}")
        print(f"最低分數: {stats['lowest_score']}")
        
        # 特質評分
        print(f"\n【特質評分】(前 10 名)")
        print(f"{'特質名稱':<20} | {'分數':<6} | {'百分位':<8} | {'描述':<40}")
        print("-" * 100)
        for trait in report['traits'][:10]:
            name = trait['chinese_name'] or ''
            score = trait['score'] if trait['score'] is not None else 'N/A'
            percentile = trait['percentile'] if trait['percentile'] is not None else 'N/A'
            desc = (trait['description'] or '')[:40]
            print(f"{name:<20} | {str(score):<6} | {str(percentile):<8} | {desc:<40}")
        
        # 按分類顯示
        print(f"\n【按分類統計】")
        for category_name, category_data in report['categories'].items():
            traits = category_data['traits']
            avg_score = sum(t['score'] for t in traits if t['score']) / len(traits) if traits else 0
            print(f"\n{category_name} (平均分數: {avg_score:.2f})")
            for trait in traits[:5]:  # 每個分類只顯示前5個
                print(f"  - {trait['chinese_name']}: {trait['score']}")


# 使用範例
if __name__ == '__main__':
    """
    使用範例：
    
    # 1. 建立資料庫連接
    import psycopg2
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='projectdb',
        user='projectuser',
        password='projectpass'
    )
    
    # 2. 建立報告生成器
    generator = TestReportGenerator(conn)
    
    # 3. 生成報告（多次查詢版本）
    report = generator.generate_report('stella24168@gmail.com')
    generator.print_report(report)
    
    # 4. 生成報告（單次查詢版本 - 效能更好）
    report = generator.generate_report_single_query('stella24168@gmail.com')
    generator.print_report(report)
    
    # 5. 關閉連接
    conn.close()
    """
    print("測驗結果報告生成器")
    print("請參考程式碼中的使用範例")
