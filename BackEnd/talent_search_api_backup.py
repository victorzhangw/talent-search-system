#!/usr/bin/env python3
"""
人才聊天搜索 API
整合資料庫與 AI 對話，提供智能人才匹配服務
支援本地開發和雲端部署
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import psycopg2
from sshtunnel import SSHTunnelForwarder
import json
from datetime import datetime
import os
import sys
import tempfile
import uvicorn
import httpx
import asyncio

# 確保可以導入本地模塊
sys.path.insert(0, os.path.dirname(__file__))

# 導入面試 API router
try:
    from interview_api import router as interview_router
    INTERVIEW_API_AVAILABLE = True
    print("✅ 面試 API 模組已載入")
except ImportError as e:
    INTERVIEW_API_AVAILABLE = False
    print(f"⚠️ 面試 API 模組未找到: {e}")

# ============================================
# 環境配置
# ============================================

# 判斷運行環境
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
IS_PRODUCTION = ENVIRONMENT == 'production'

print(f"\n{'='*60}")
print(f"🚀 運行環境: {ENVIRONMENT.upper()}")
print(f"{'='*60}\n")

# 資料庫連接配置 - 從環境變數讀取
DB_CONFIG = {
    'ssh_host': os.getenv('DB_SSH_HOST', '54.199.255.239'),
    'ssh_port': int(os.getenv('DB_SSH_PORT', '22')),
    'ssh_username': os.getenv('DB_SSH_USERNAME', 'victor_cheng'),
    'ssh_private_key': os.getenv('DB_SSH_PRIVATE_KEY'),  # 生產環境：key 內容
    'ssh_private_key_file': os.getenv('DB_SSH_PRIVATE_KEY_FILE', 'private-key-openssh.pem'),  # 本地：檔案路徑
    'db_host': os.getenv('DB_HOST', 'localhost'),
    'db_port': int(os.getenv('DB_PORT', '5432')),
    'db_name': os.getenv('DB_NAME', 'projectdb'),
    'db_user': os.getenv('DB_USER', 'projectuser'),
    'db_password': os.getenv('DB_PASSWORD', 'projectpass')
}

# LLM API 配置 - 根據環境自動選擇
if IS_PRODUCTION:
    # 生產環境：使用 AkashML
    LLM_CONFIG = {
        'api_key': os.getenv('LLM_API_KEY', 'akml-RTl88SQKMDZFX2c43QslImWLO7DNUdee'),
        'api_host': os.getenv('LLM_API_HOST', 'https://api.akashml.com'),
        'model': os.getenv('LLM_MODEL', 'deepseek-ai/DeepSeek-V3.1'),
        'endpoint': os.getenv('LLM_API_HOST', 'https://api.akashml.com') + '/v1/chat/completions'
    }
    print("🌐 使用 AkashML API")
else:
    # 開發環境：使用 SiliconFlow
    LLM_CONFIG = {
        'api_key': os.getenv('LLM_API_KEY', 'sk-xmwxrtsxgsjwuyeceydoyuopezzlqresdjyvlzrbbjeejiff'),
        'api_host': os.getenv('LLM_API_HOST', 'https://api.siliconflow.cn'),
        'model': os.getenv('LLM_MODEL', 'deepseek-ai/DeepSeek-V3'),
        'endpoint': os.getenv('LLM_API_HOST', 'https://api.siliconflow.cn') + '/v1/chat/completions'
    }
    print("🌐 使用 SiliconFlow API")

# FastAPI 應用
app = FastAPI(
    title="人才聊天搜索 API",
    version="2.0.0",
    description="完整版 - 支援本地開發和雲端部署"
)

# CORS 設定 - 根據環境調整
if IS_PRODUCTION:
    # 生產環境：指定允許的來源
    allowed_origins = [
        os.getenv('FRONTEND_URL', 'https://talent-search-frontend-68e7.onrender.com'),
        "https://talent-search-frontend.vercel.app",
        "https://talent-search-frontend.netlify.app",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    # 支持通配符匹配 (Render/Vercel/Netlify 的預覽部署)
    allow_origin_regex = r"https://.*\.(onrender\.com|vercel\.app|netlify\.app)$"
else:
    # 開發環境：允許所有來源
    allowed_origins = ["*"]
    allow_origin_regex = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=allow_origin_regex if IS_PRODUCTION else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含面試 API router
if INTERVIEW_API_AVAILABLE:
    app.include_router(interview_router)
    print("✅ 面試 API 端點已註冊")

# 全域變數
tunnel = None
db_conn = None

# 資料模型
class SearchQuery(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None

class Candidate(BaseModel):
    id: int
    name: str
    email: str
    test_results: List[Dict[str, Any]]
    match_score: float
    match_reason: str

class SearchResponse(BaseModel):
    candidates: List[Candidate]
    total: int
    query_understanding: str
    suggestions: List[str]

# 資料庫連接管理
def get_db_connection(max_retries=3):
    """取得資料庫連接 - 支援本地和雲端環境，帶錯誤處理和重試機制"""
    global tunnel, db_conn
    
    for attempt in range(max_retries):
        try:
            if db_conn is None or db_conn.closed:
                if tunnel is None or not tunnel.is_active:
                    print(f"🔌 正在建立 SSH 隧道... (嘗試 {attempt + 1}/{max_retries})")
                    print(f"   SSH 主機: {DB_CONFIG['ssh_host']}:{DB_CONFIG['ssh_port']}")
                    print(f"   SSH 用戶: {DB_CONFIG['ssh_username']}")
                    
                    # 處理 SSH private key
                    ssh_key = DB_CONFIG['ssh_private_key']
                    
                    if ssh_key:
                        # 生產環境：從環境變數讀取 key 內容
                        print("✅ 使用環境變數中的 SSH key")
                        # 檢查 key 格式
                        if not ssh_key.startswith('-----BEGIN'):
                            print("⚠️ SSH key 格式可能不正確")
                        temp_key_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem')
                        temp_key_file.write(ssh_key)
                        temp_key_file.close()
                        ssh_pkey = temp_key_file.name
                        print(f"   臨時 key 檔案: {ssh_pkey}")
                    else:
                        # 開發環境：使用本地檔案
                        ssh_key_file = DB_CONFIG['ssh_private_key_file']
                        if os.path.isfile(ssh_key_file):
                            print(f"✅ 使用本地 SSH key 檔案: {ssh_key_file}")
                            ssh_pkey = ssh_key_file
                        else:
                            raise ValueError(f"❌ 找不到 SSH key 檔案: {ssh_key_file}")
                    
                    # 建立 SSH 隧道，增加超時設定
                    print("   正在連接 SSH...")
                    tunnel = SSHTunnelForwarder(
                        (DB_CONFIG['ssh_host'], DB_CONFIG['ssh_port']),
                        ssh_username=DB_CONFIG['ssh_username'],
                        ssh_pkey=ssh_pkey,
                        remote_bind_address=(DB_CONFIG['db_host'], DB_CONFIG['db_port']),
                        set_keepalive=10.0,  # 保持連接活躍
                        compression=True
                    )
                    tunnel.start()
                    print(f"✅ SSH 隧道已建立，本地端口: {tunnel.local_bind_port}")
                
                print(f"🔌 正在連接資料庫... (嘗試 {attempt + 1}/{max_retries})")
                print(f"   資料庫: {DB_CONFIG['db_name']}")
                print(f"   用戶: {DB_CONFIG['db_user']}")
                db_conn = psycopg2.connect(
                    host='localhost',
                    port=tunnel.local_bind_port,
                    database=DB_CONFIG['db_name'],
                    user=DB_CONFIG['db_user'],
                    password=DB_CONFIG['db_password'],
                    connect_timeout=30  # 30 秒超時
                )
                print("✅ 資料庫連接成功")
            
            return db_conn
        
        except Exception as e:
            print(f"❌ 連接失敗 (嘗試 {attempt + 1}/{max_retries}): {str(e)}")
            print(f"   錯誤類型: {type(e).__name__}")
            
            # 清理失敗的連接
            if tunnel and tunnel.is_active:
                try:
                    tunnel.stop()
                    print("   已清理 SSH 隧道")
                except Exception as cleanup_error:
                    print(f"   清理隧道時出錯: {cleanup_error}")
            tunnel = None
            db_conn = None
            
            # 如果還有重試機會，等待後重試
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2  # 遞增等待時間
                print(f"   等待 {wait_time} 秒後重試...")
                import time
                time.sleep(wait_time)
            else:
                # 最後一次嘗試失敗，拋出異常
                print("❌ 所有連接嘗試均失敗")
                raise HTTPException(
                    status_code=503,
                    detail=f"資料庫連接失敗（已重試 {max_retries} 次）: {str(e)}"
                )

# LLM 服務類
class LLMService:
    """LLM 服務 - 使用 DeepSeek API"""
    
    def __init__(self, db_conn):
        self.api_key = LLM_CONFIG['api_key']
        self.api_endpoint = LLM_CONFIG['endpoint']
        self.model = LLM_CONFIG['model']
        self.db_conn = db_conn
        self.available_traits = self._load_traits_from_db()
        
        # 載入意圖定義
        self.intent_config = self._load_intent_definitions()
        self.INTENT_DEFINITIONS = self.intent_config.get('intents', {})
        self.ENTITY_DEFINITIONS = self.intent_config.get('entities', {})
        self.SETTINGS = self.intent_config.get('settings', {})
        
        print(f"✅ 載入 {len(self.INTENT_DEFINITIONS)} 個意圖定義")
        enabled_intents = [
            intent_code for intent_code, intent_info in self.INTENT_DEFINITIONS.items()
            if intent_info.get('enabled', True)
        ]
        print(f"✅ 啟用的意圖: {', '.join(enabled_intents)}")
    
    def _load_intent_definitions(self) -> Dict:
        """從 JSON 文件載入意圖定義"""
        import os
        
        possible_paths = [
            'intent_definitions.json',
            'BackEnd/intent_definitions.json',
            os.path.join(os.path.dirname(__file__), 'intent_definitions.json')
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    print(f"✅ 從 {path} 載入意圖定義")
                    return config
                except Exception as e:
                    print(f"❌ 載入意圖定義失敗: {str(e)}")
        
        print("⚠️ 找不到 intent_definitions.json，使用預設定義")
        return {
            'intents': {
                'search': {
                    'name': '搜索人才',
                    'description': '根據特質要求搜索符合條件的候選人',
                    'examples': ['找一個善於溝通的人'],
                    'entities': ['traits'],
                    'enabled': True
                }
            },
            'entities': {},
            'settings': {
                'llm_temperature': 0.3,
                'llm_max_tokens': 500,
                'default_intent': 'search',
                'min_confidence': 0.5
            }
        }
    
    def _clean_json_response(self, content: str) -> str:
        """清理 LLM 返回的 JSON 內容，確保格式正確"""
        import re
        
        # 1. 移除 markdown 代碼塊標記
        if '```' in content:
            # 提取代碼塊中的內容
            match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', content, re.DOTALL)
            if match:
                content = match.group(1)
        
        # 2. 移除開頭和結尾的空白字符
        content = content.strip()
        
        # 3. 移除可能的前導文字（如 "這是 JSON："）
        # 找到第一個 { 或 [
        json_start = -1
        for i, char in enumerate(content):
            if char in ['{', '[']:
                json_start = i
                break
        
        if json_start > 0:
            content = content[json_start:]
        
        # 4. 找到最後一個 } 或 ]，移除後面的文字
        json_end = -1
        for i in range(len(content) - 1, -1, -1):
            if content[i] in ['}', ']']:
                json_end = i + 1
                break
        
        if json_end > 0:
            content = content[:json_end]
        
        # 5. 替換單引號為雙引號（但要小心字串內容中的單引號）
        # 這是一個簡化版本，只處理屬性名稱的單引號
        content = re.sub(r"'([^']*?)'(\s*:)", r'"\1"\2', content)
        
        # 6. 移除 JSON 中的註釋（// 和 /* */）
        content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        # 7. 移除多餘的逗號（在 } 或 ] 前面的逗號）
        content = re.sub(r',(\s*[}\]])', r'\1', content)
        
        return content.strip()
    
    def _load_traits_from_db(self) -> List[Dict]:
        """從資料庫載入所有可用的特質"""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT id, chinese_name, system_name, description
            FROM trait
            ORDER BY id;
        """)
        
        traits = []
        for row in cursor.fetchall():
            traits.append({
                'id': row[0],
                'chinese_name': row[1],
                'system_name': row[2],
                'description': row[3]
            })
        
        cursor.close()
        return traits
    
    def get_system_prompt(self, available_traits: List[Dict]) -> str:
        """系統 Prompt - 使用資料庫中的實際特質，改進版確保 JSON 格式正確"""
        
        # 將資料庫特質格式化為 Prompt
        traits_list = []
        for trait in available_traits:
            traits_list.append(f"- {trait['chinese_name']} ({trait['system_name']}): {trait['description'][:50]}...")
        
        traits_text = "\n".join(traits_list[:30])  # 限制數量避免 Prompt 過長
        
        return f"""你是一個專業的人才搜索助手，專門幫助 HR 和招聘人員理解和分析人才需求。你必須嚴格按照 JSON 格式回覆。

**你的任務**：
1. 理解用戶用自然語言描述的人才需求
2. 從資料庫的特質列表中，選擇最匹配的特質
3. 生成 SQL WHERE 條件來查詢符合條件的候選人

**資料庫中可用的特質列表**：
{traits_text}

**JSON 輸出格式規範**：
1. 必須是有效的 JSON 格式
2. 所有字串必須使用雙引號 "
3. 不要使用單引號 '
4. 不要包含註釋或說明文字
5. 不要包含 markdown 代碼塊標記
6. 數字類型不要加引號

**輸出範例**：
{{
  "matched_traits": [
    {{
      "chinese_name": "協調溝通",
      "system_name": "communication",
      "min_score": 70
    }}
  ],
  "sql_conditions": [
    "jsonb_extract_path_text(trait_results, '協調溝通', 'score')::int >= 70"
  ],
  "summary": "搜索協調溝通能力強的銷售人員",
  "clarification": null
}}

**必須遵守的規則**：
1. 只輸出純 JSON，不要有任何其他文字
2. 只能使用上述特質列表中的特質
3. sql_conditions 必須是有效的 PostgreSQL JSONB 查詢語法
4. min_score 範圍是 0-100 的整數
5. 如果用戶需求模糊，在 clarification 中提出問題（字串或 null）
6. 如果用戶只是要找特定候選人（如「找到 Howard」），sql_conditions 返回空陣列 []
7. sql_conditions 只用於查詢特質分數，不要包含候選人姓名、email 等個人資訊
8. 確保所有 JSON 屬性名稱使用雙引號

現在請分析用戶需求並輸出 JSON。"""
    
    def _get_intent_detection_prompt(self) -> str:
        """生成意圖識別的 Prompt - 改進版，確保 JSON 格式正確"""
        
        # 只包含啟用的意圖
        intent_list = []
        for intent_code, intent_info in self.INTENT_DEFINITIONS.items():
            if not intent_info.get('enabled', True):
                continue
            
            examples = '\n   '.join([f'- {ex}' for ex in intent_info['examples'][:3]])
            intent_list.append(f"""
{intent_code} - {intent_info['name']}
   描述: {intent_info['description']}
   範例:
   {examples}""")
        
        intents_text = '\n'.join(intent_list)
        
        # 構建實體說明
        entity_list = []
        for entity_code, entity_info in self.ENTITY_DEFINITIONS.items():
            examples = ', '.join([str(ex) for ex in entity_info.get('examples', [])[:2]])
            entity_list.append(f"   {entity_code}: {entity_info['description']} (例: {examples})")
        
        entities_text = '\n'.join(entity_list) if entity_list else '   (無特定實體)'
        
        return f"""你是一個人才管理系統的意圖識別助手。你必須嚴格按照 JSON 格式回覆。

請分析用戶查詢，識別其意圖並提取關鍵資訊。

**支援的意圖類型**:
{intents_text}

**可提取的實體**:
{entities_text}

**JSON 輸出格式規範**:
1. 必須是有效的 JSON 格式
2. 所有字串必須使用雙引號 "
3. 不要使用單引號 '
4. 不要包含註釋
5. 不要包含 markdown 代碼塊標記
6. 數字類型的 confidence 不要加引號

**輸出範例**:
{{
  "intent": "search",
  "entities": {{
    "traits": ["溝通", "領導力"]
  }},
  "confidence": 0.95,
  "reasoning": "用戶明確要求搜索具有特定特質的人才"
}}

**必須遵守的規則**:
1. 只輸出純 JSON，不要有任何其他文字
2. 不要在 JSON 前後添加說明文字
3. 確保所有屬性名稱使用雙引號
4. entities 中沒有的欄位可以省略或設為 null
5. confidence 必須是 0.0 到 1.0 之間的數字

現在請分析用戶查詢並輸出 JSON。"""
    
    async def _detect_query_intent_with_llm(self, query: str) -> tuple[str, dict, float]:
        """使用 LLM 檢測查詢意圖"""
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_endpoint,
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {self.api_key}'
                    },
                    json={
                        'model': self.model,
                        'messages': [
                            {
                                'role': 'system',
                                'content': self._get_intent_detection_prompt()
                            },
                            {
                                'role': 'user',
                                'content': f'請分析以下查詢的意圖：\n\n{query}'
                            }
                        ],
                        'temperature': self.SETTINGS.get('llm_temperature', 0.3),
                        'max_tokens': self.SETTINGS.get('llm_max_tokens', 500)
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content'].strip()
                    
                    # 清理 JSON 內容
                    content = self._clean_json_response(content)
                    
                    # 解析 JSON
                    try:
                        intent_result = json.loads(content)
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON 解析失敗: {str(e)}")
                        print(f"   原始內容: {content[:200]}")
                        # 降級到預設意圖
                        return 'search', {}, 0.0
                    
                    intent = intent_result.get('intent', 'search')
                    entities = intent_result.get('entities', {})
                    confidence = intent_result.get('confidence', 0.5)
                    reasoning = intent_result.get('reasoning', '')
                    
                    print(f"\n🤖 LLM 意圖識別:")
                    print(f"   意圖: {intent}")
                    print(f"   信心度: {confidence:.2%}")
                    print(f"   實體: {entities}")
                    print(f"   理由: {reasoning}")
                    
                    # 驗證意圖是否有效且啟用
                    if intent not in self.INTENT_DEFINITIONS:
                        print(f"   ⚠️ 未知意圖 '{intent}'，使用預設意圖")
                        intent = self.SETTINGS.get('default_intent', 'search')
                    elif not self.INTENT_DEFINITIONS[intent].get('enabled', True):
                        print(f"   ⚠️ 意圖 '{intent}' 已停用，使用預設意圖")
                        intent = self.SETTINGS.get('default_intent', 'search')
                    
                    # 檢查信心度
                    min_confidence = self.SETTINGS.get('min_confidence', 0.5)
                    if confidence < min_confidence:
                        print(f"   ⚠️ 信心度過低 ({confidence:.2%} < {min_confidence:.2%})，使用預設意圖")
                        intent = self.SETTINGS.get('default_intent', 'search')
                    
                    return intent, entities, confidence
                else:
                    print(f"❌ LLM API 錯誤: {response.status_code}")
                    return 'search', {}, 0.0
        
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析錯誤: {str(e)}")
            print(f"   內容: {content[:200]}")
            return 'search', {}, 0.0
        
        except Exception as e:
            print(f"❌ 意圖識別錯誤: {str(e)}")
            return 'search', {}, 0.0
    
    async def analyze_query(self, query: str) -> Dict[str, Any]:
        """使用 LLM 分析查詢 - 識別意圖並處理"""
        
        # 使用 LLM 檢測查詢意圖
        intent, entities, confidence = await self._detect_query_intent_with_llm(query)
        
        # 如果是列表查詢，直接返回不需要條件
        if intent == 'list_all':
            return {
                'success': True,
                'analysis': {
                    'intent': 'list_all',
                    'entities': entities,
                    'confidence': confidence,
                    'matched_traits': [],
                    'sql_conditions': [],
                    'summary': '列出所有候選人'
                }
            }
        
        if intent == 'list_traits':
            return {
                'success': True,
                'analysis': {
                    'intent': 'list_traits',
                    'entities': entities,
                    'confidence': confidence,
                    'matched_traits': [],
                    'sql_conditions': [],
                    'summary': '列出所有特質',
                    'traits': [
                        {'chinese_name': t['chinese_name'], 'system_name': t['system_name']}
                        for t in self.available_traits[:20]  # 只顯示前 20 個
                    ]
                }
            }
        
        if intent == 'interview':
            return {
                'success': True,
                'analysis': {
                    'intent': 'interview',
                    'entities': entities,
                    'confidence': confidence,
                    'matched_traits': [],
                    'sql_conditions': [],
                    'summary': '生成面試綱要'
                }
            }
        
        if intent == 'statistics':
            return {
                'success': True,
                'analysis': {
                    'intent': 'statistics',
                    'entities': entities,
                    'confidence': confidence,
                    'matched_traits': [],
                    'sql_conditions': [],
                    'summary': '統計分析'
                }
            }
        
        if intent == 'compare':
            return {
                'success': True,
                'analysis': {
                    'intent': 'compare',
                    'entities': entities,
                    'confidence': confidence,
                    'matched_traits': [],
                    'sql_conditions': [],
                    'summary': '比較候選人'
                }
            }
        
        if intent == 'advice':
            return {
                'success': True,
                'analysis': {
                    'intent': 'advice',
                    'entities': entities,
                    'confidence': confidence,
                    'matched_traits': [],
                    'sql_conditions': [],
                    'summary': '建議諮詢'
                }
            }
        
        # 搜索查詢 - 調用 LLM
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_endpoint,
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {self.api_key}'
                    },
                    json={
                        'model': self.model,
                        'messages': [
                            {
                                'role': 'system',
                                'content': self.get_system_prompt(self.available_traits)
                            },
                            {
                                'role': 'user',
                                'content': f'請分析以下人才需求並生成 SQL 查詢條件：\n\n{query}'
                            }
                        ],
                        'temperature': 0.3,
                        'max_tokens': 1500,
                        'response_format': {'type': 'json_object'}
                    }
                )
                
                if response.status_code != 200:
                    raise Exception(f'LLM API 錯誤: {response.status_code}')
                
                data = response.json()
                content = data['choices'][0]['message']['content']
                
                # 清理 JSON 內容
                content = self._clean_json_response(content)
                
                # 解析 JSON，帶錯誤處理
                try:
                    analysis = json.loads(content)
                except json.JSONDecodeError as e:
                    print(f"❌ 搜索分析 JSON 解析失敗: {str(e)}")
                    print(f"   原始內容: {content[:300]}")
                    # 返回降級結果
                    return {
                        'success': False,
                        'error': f'JSON 解析失敗: {str(e)}',
                        'fallback': True
                    }
                
                # 驗證必要欄位
                if 'matched_traits' not in analysis:
                    analysis['matched_traits'] = []
                if 'sql_conditions' not in analysis:
                    analysis['sql_conditions'] = []
                if 'summary' not in analysis:
                    analysis['summary'] = f'搜索：{query}'
                
                analysis['intent'] = 'search'
                analysis['entities'] = entities  # 添加意圖識別提取的實體
                analysis['confidence'] = confidence  # 添加信心度
                
                print(f"\n✅ 搜索分析成功:")
                print(f"   匹配特質: {len(analysis['matched_traits'])} 個")
                print(f"   SQL 條件: {len(analysis['sql_conditions'])} 個")
                
                return {
                    'success': True,
                    'analysis': analysis
                }
        
        except json.JSONDecodeError as e:
            print(f"❌ LLM 返回的 JSON 格式錯誤: {str(e)}")
            return {
                'success': False,
                'error': f'JSON 格式錯誤: {str(e)}',
                'fallback': True
            }
        except Exception as e:
            print(f"❌ LLM 分析錯誤: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'fallback': True
            }
    
    async def generate_match_reason(self, candidate: Dict, query: str, score: float) -> str:
        """生成匹配理由"""
        try:
            # 提取候選人的測評結果
            test_info = ""
            if candidate.get('test_results'):
                test_count = len([t for t in candidate['test_results'] if t])
                test_info = f"已完成 {test_count} 項測評"
            
            prompt = f"""作為人才推薦顧問，請為以下候選人生成簡短的推薦理由。

用戶需求：{query}

候選人資訊：
- 姓名：{candidate.get('name', '未知')}
- {test_info}
- 匹配度：{score:.0f}%

請用一句話（30字內）說明為什麼推薦這位候選人。直接輸出理由，不要包含其他內容。"""

            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    self.api_endpoint,
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {self.api_key}'
                    },
                    json={
                        'model': self.model,
                        'messages': [
                            {
                                'role': 'user',
                                'content': prompt
                            }
                        ],
                        'temperature': 0.7,
                        'max_tokens': 100
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    reason = data['choices'][0]['message']['content'].strip()
                    return reason
                else:
                    return self._generate_simple_reason(candidate, score, test_info)
        
        except Exception as e:
            print(f"生成理由錯誤: {str(e)}")
            return self._generate_simple_reason(candidate, score, test_info)
    
    def _generate_simple_reason(self, candidate: Dict, score: float, test_info: str) -> str:
        """簡單的理由生成（降級方案）"""
        reasons = []
        
        if test_info:
            reasons.append(test_info)
        
        if score > 0.8:
            reasons.append("高度符合您的需求")
        elif score > 0.6:
            reasons.append("基本符合您的需求")
        else:
            reasons.append("部分符合您的需求")
        
        return "；".join(reasons) if reasons else "具備相關能力"

# 人才搜索核心功能
class TalentSearchEngine:
    """人才搜索引擎"""
    
    def __init__(self):
        self.conn = get_db_connection()
        self.llm_service = LLMService(self.conn)
    
    async def parse_query(self, query: str) -> Dict[str, Any]:
        """解析自然語言查詢 - 使用 LLM"""
        # 嘗試使用 LLM 分析
        llm_result = await self.llm_service.analyze_query(query)
        
        if llm_result['success']:
            return llm_result['analysis']
        
        # LLM 失敗，降級到關鍵字匹配
        return self._parse_query_simple(query)
    
    def _search_all_candidates(self) -> List[Dict]:
        """降級方案：返回所有候選人"""
        cursor = self.conn.cursor()
        
        sql = """
            SELECT 
                cu.id,
                cu.username as name,
                cu.email,
                (SELECT phone FROM individual_profile WHERE user_id = cu.id LIMIT 1) as phone,
                cu.date_joined as created_at,
                itr.trait_results,
                json_agg(
                    json_build_object(
                        'test_id', itr.id,
                        'test_completion_date', itr.test_completion_date,
                        'trait_results', itr.trait_results
                    )
                ) as test_results
            FROM core_user cu
            LEFT JOIN individual_test_result itr ON cu.id = itr.user_id
            WHERE cu.username IS NOT NULL
            GROUP BY cu.id, cu.username, cu.email, cu.date_joined, itr.trait_results
            LIMIT 50;
        """
        
        cursor.execute(sql)
        results = cursor.fetchall()
        
        candidates = []
        for row in results:
            candidate = {
                'id': row[0],
                'name': row[1],
                'email': row[2],
                'phone': row[3],
                'created_at': row[4].isoformat() if row[4] else None,
                'trait_results': row[5] if row[5] else {},
                'test_results': row[6] if row[6] else []
            }
            candidates.append(candidate)
        
        cursor.close()
        return candidates
    
    def _parse_query_simple(self, query: str) -> Dict[str, Any]:
        """簡單的關鍵字匹配（降級方案）"""
        return {
            'matched_traits': [],
            'sql_conditions': [],
            'summary': f'搜索：{query}',
            'fallback': True
        }
    
    def search_candidates(self, parsed_query: Dict, filters: Optional[Dict] = None) -> List[Dict]:
        """使用 LLM 生成的 SQL 條件搜索候選人"""
        cursor = self.conn.cursor()
        
        # 使用 DISTINCT ON 避免重複，每個用戶只取最新的測評結果
        base_sql = """
            SELECT DISTINCT ON (cu.id)
                cu.id,
                cu.username as name,
                cu.email,
                (SELECT phone FROM individual_profile WHERE user_id = cu.id LIMIT 1) as phone,
                cu.date_joined as created_at,
                itr.trait_results
            FROM core_user cu
            JOIN individual_test_result itr ON cu.id = itr.user_id
            WHERE cu.username IS NOT NULL
              AND itr.trait_results IS NOT NULL
        """
        
        # 添加 LLM 生成的 SQL 條件
        sql_conditions = parsed_query.get('sql_conditions', [])
        has_conditions = sql_conditions and len(sql_conditions) > 0
        
        if has_conditions:
            where_clause = " AND (" + " OR ".join(sql_conditions) + ")"
            base_sql += where_clause
        
        base_sql += """
            ORDER BY cu.id, itr.test_completion_date DESC NULLS LAST
            LIMIT 50;
        """
        
        # 降級查詢 SQL（如果主查詢失敗或返回空結果）
        fallback_sql = """
            SELECT DISTINCT ON (cu.id)
                cu.id,
                cu.username as name,
                cu.email,
                (SELECT phone FROM individual_profile WHERE user_id = cu.id LIMIT 1) as phone,
                cu.date_joined as created_at,
                itr.trait_results
            FROM core_user cu
            JOIN individual_test_result itr ON cu.id = itr.user_id
            WHERE cu.username IS NOT NULL
              AND itr.trait_results IS NOT NULL
            ORDER BY cu.id, itr.test_completion_date DESC NULLS LAST
            LIMIT 50;
        """
        
        print(f"\n執行 SQL:\n{base_sql}\n")
        
        try:
            cursor.execute(base_sql)
            results = cursor.fetchall()
            
            # 如果有條件但返回空結果，嘗試降級查詢
            if len(results) == 0 and has_conditions:
                print("⚠️ 主查詢返回空結果，使用降級查詢（移除條件）...")
                cursor.execute(fallback_sql)
                results = cursor.fetchall()
                print(f"降級查詢找到 {len(results)} 筆結果")
            
            candidates = []
            for row in results:
                candidate = {
                    'id': row[0],
                    'name': row[1],
                    'email': row[2],
                    'phone': row[3],
                    'created_at': row[4].isoformat() if row[4] else None,
                    'trait_results': row[5] if row[5] else {},
                    'test_results': []  # 簡化版不包含完整測評歷史
                }
                candidates.append(candidate)
            
            cursor.close()
            return candidates
        
        except Exception as e:
            print(f"❌ SQL 執行錯誤: {str(e)}")
            print("使用降級查詢...")
            try:
                cursor.execute(fallback_sql)
                results = cursor.fetchall()
                print(f"✅ 降級查詢找到 {len(results)} 筆結果")
                
                candidates = []
                for row in results:
                    candidate = {
                        'id': row[0],
                        'name': row[1],
                        'email': row[2],
                        'phone': row[3],
                        'created_at': row[4].isoformat() if row[4] else None,
                        'trait_results': row[5] if row[5] else {},
                        'test_results': []
                    }
                    candidates.append(candidate)
                
                cursor.close()
                return candidates
            except Exception as e2:
                print(f"❌ 降級查詢也失敗: {str(e2)}")
                cursor.close()
                return []
    
    def _find_trait_score(self, trait_name: str, trait_results: Dict) -> Optional[float]:
        """在 trait_results 中查找特質分數，支援多種名稱格式"""
        if not trait_results:
            return None
        
        # 嘗試直接匹配
        if trait_name in trait_results:
            trait_data = trait_results[trait_name]
            if isinstance(trait_data, dict):
                return trait_data.get('score', 0)
            return trait_data
        
        # 嘗試部分匹配（模糊搜索）
        for key in trait_results.keys():
            if trait_name in key or key in trait_name:
                trait_data = trait_results[key]
                if isinstance(trait_data, dict):
                    return trait_data.get('score', 0)
                return trait_data
        
        return None
    
    def calculate_match_score(self, candidate: Dict, parsed_query: Dict) -> float:
        """綜合評分算法 - 混合搜索策略"""
        matched_traits = parsed_query.get('matched_traits', [])
        trait_results = candidate.get('trait_results', {})
        
        # 沒有測評結果
        if not trait_results:
            return 0.1
        
        # 沒有特定要求，給予基礎分數
        if not matched_traits:
            return 0.5
        
        total_score = 0
        total_weight = 0
        matched_count = 0
        
        for trait in matched_traits:
            # 獲取特質名稱（嘗試多個可能的名稱）
            possible_names = [
                trait.get('system_name'),
                trait.get('chinese_name')
            ]
            
            weight = trait.get('weight', 1.0)
            min_score = trait.get('min_score', 0)
            
            # 嘗試找到特質分數
            actual_score = None
            for name in possible_names:
                if name:
                    actual_score = self._find_trait_score(name, trait_results)
                    if actual_score is not None:
                        break
            
            if actual_score is not None:
                # 計算加權分數
                if actual_score >= min_score:
                    # 達標：全分
                    total_score += actual_score * weight
                else:
                    # 未達標：給予部分分數（50%）
                    total_score += actual_score * weight * 0.5
                
                total_weight += 100 * weight
                matched_count += 1
        
        # 計算基礎分數
        if total_weight > 0:
            base_score = total_score / total_weight
            
            # 覆蓋率獎勵：匹配的特質越多，分數越高
            coverage_ratio = matched_count / len(matched_traits)
            coverage_bonus = coverage_ratio * 0.1
            
            final_score = min(base_score + coverage_bonus, 1.0)
            return final_score
        
        # 沒有匹配任何特質，但有測評結果
        return 0.3
    
    async def generate_match_reason(self, candidate: Dict, query: str, score: float, parsed_query: Dict) -> str:
        """生成匹配理由 - 使用 LLM"""
        # 使用 LLM 生成個性化理由
        reason = await self.llm_service.generate_match_reason(candidate, query, score)
        return reason
    
    def get_all_candidates(self, limit: int = 50) -> List[Dict]:
        """獲取所有候選人"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = """
            SELECT DISTINCT ON (cu.id)
                cu.id,
                cu.username as name,
                cu.email,
                (SELECT phone FROM individual_profile WHERE user_id = cu.id LIMIT 1) as phone,
                cu.date_joined as created_at,
                itr.trait_results
            FROM core_user cu
            LEFT JOIN individual_test_result itr ON cu.id = itr.user_id
            WHERE cu.username IS NOT NULL
            ORDER BY cu.id, itr.test_completion_date DESC NULLS LAST
            LIMIT %s;
        """
        
        print(f"\n🔍 執行查詢: get_all_candidates (limit={limit})")
        cursor.execute(sql, (limit,))
        results = cursor.fetchall()
        print(f"✓ 查詢返回 {len(results)} 筆記錄")
        
        candidates = []
        with_traits_count = 0
        
        for row in results:
            trait_results = row[5] if row[5] else {}
            
            # 調試輸出
            if trait_results:
                with_traits_count += 1
                print(f"  候選人 {row[1]}: {len(trait_results)} 個特質")
            else:
                print(f"  候選人 {row[1]}: 無特質數據")
            
            candidate = {
                'id': row[0],
                'name': row[1],
                'email': row[2],
                'phone': row[3],
                'created_at': row[4].isoformat() if row[4] else None,
                'trait_results': trait_results,
                'test_results': []
            }
            candidates.append(candidate)
        
        print(f"✓ 有特質數據的候選人: {with_traits_count}/{len(results)}")
        
        cursor.close()
        return candidates
    
    def find_candidate_by_name(self, name: str) -> Optional[Dict]:
        """根據姓名查找候選人"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = """
            SELECT DISTINCT ON (cu.id)
                cu.id,
                cu.username as name,
                cu.email,
                (SELECT phone FROM individual_profile WHERE user_id = cu.id LIMIT 1) as phone,
                cu.date_joined as created_at,
                itr.trait_results
            FROM core_user cu
            LEFT JOIN individual_test_result itr ON cu.id = itr.user_id
            WHERE cu.username = %s
            ORDER BY cu.id, itr.test_completion_date DESC NULLS LAST
            LIMIT 1;
        """
        
        cursor.execute(sql, (name,))
        row = cursor.fetchone()
        cursor.close()
        
        if not row:
            return None
        
        return {
            'id': row[0],
            'name': row[1],
            'email': row[2],
            'phone': row[3],
            'created_at': row[4].isoformat() if row[4] else None,
            'trait_results': row[5] if row[5] else {},
            'test_results': []
        }
    
    async def generate_interview_guide(self, candidate: Dict, query: str) -> str:
        """使用 LLM 生成面試綱要"""
        
        trait_results = candidate.get('trait_results', {})
        
        # 提取優勢和劣勢
        strengths = []
        weaknesses = []
        neutral = []
        
        for trait_name, trait_data in trait_results.items():
            if isinstance(trait_data, dict):
                score = trait_data.get('score', 0)
            else:
                continue
            
            if score >= 75:
                strengths.append(f"{trait_name} ({score}分)")
            elif score < 50:
                weaknesses.append(f"{trait_name} ({score}分)")
            else:
                neutral.append(f"{trait_name} ({score}分)")
        
        prompt = f"""
請為以下候選人設計一份面試綱要：

**候選人**: {candidate.get('name')}
**Email**: {candidate.get('email')}

**優勢特質** (≥75分):
{chr(10).join(f'• {s}' for s in strengths[:5]) if strengths else '• 無明顯優勢'}

**中等特質** (50-75分):
{chr(10).join(f'• {n}' for n in neutral[:3]) if neutral else '• 無'}

**待發展特質** (<50分):
{chr(10).join(f'• {w}' for w in weaknesses[:3]) if weaknesses else '• 無明顯劣勢'}

請生成：

## 📋 面試綱要

### 1. 面試重點 (3-5 個)
基於候選人的特質，列出面試時應該重點關注的方面。

### 2. 建議的面試問題 (5-8 個)
針對候選人的優勢和劣勢，設計具體的面試問題。

### 3. 評估標準
如何評估候選人的回答？

### 4. 注意事項
面試時需要特別注意什麼？

請用繁體中文，格式清晰，具體實用。
"""
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.llm_service.api_endpoint,
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {self.llm_service.api_key}'
                    },
                    json={
                        'model': self.llm_service.model,
                        'messages': [
                            {
                                'role': 'system',
                                'content': '你是一位專業的人力資源顧問，擅長設計面試流程和評估候選人。'
                            },
                            {
                                'role': 'user',
                                'content': prompt
                            }
                        ],
                        'temperature': 0.7,
                        'max_tokens': 1500
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    return content
                else:
                    return f"無法生成面試綱要（API 錯誤: {response.status_code}）"
        
        except Exception as e:
            print(f"生成面試綱要錯誤: {str(e)}")
            return f"無法生成面試綱要（錯誤: {str(e)}）"
    
    async def generate_comparison(self, candidates: List[Dict], query: str) -> str:
        """使用 LLM 生成候選人比較分析"""
        
        # 構建候選人資訊
        candidates_info = []
        for candidate in candidates:
            trait_results = candidate.get('trait_results', {})
            
            # 提取優勢特質
            strengths = []
            for trait_name, trait_data in trait_results.items():
                if isinstance(trait_data, dict):
                    score = trait_data.get('score', 0)
                    if score >= 75:
                        strengths.append(f"{trait_name} ({score}分)")
            
            candidates_info.append(f"""
**{candidate.get('name')}**
- Email: {candidate.get('email')}
- 優勢特質: {', '.join(strengths[:5]) if strengths else '無明顯優勢'}
- 測評項目數: {len(trait_results)}
""")
        
        candidates_text = '\n'.join(candidates_info)
        
        prompt = f"""
請比較以下候選人，提供詳細的分析：

{candidates_text}

請生成：

## 🔍 候選人比較分析

### 1. 整體評估
對每位候選人的整體印象和定位。

### 2. 優勢對比
各候選人的優勢特質對比。

### 3. 適合職位
根據特質分析，各候選人適合的職位類型。

### 4. 選擇建議
如果要選擇一位，建議選擇誰？為什麼？

### 5. 注意事項
選擇時需要考慮的其他因素。

請用繁體中文，格式清晰，客觀公正。
"""
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.llm_service.api_endpoint,
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {self.llm_service.api_key}'
                    },
                    json={
                        'model': self.llm_service.model,
                        'messages': [
                            {
                                'role': 'system',
                                'content': '你是一位專業的人力資源顧問，擅長評估和比較候選人。'
                            },
                            {
                                'role': 'user',
                                'content': prompt
                            }
                        ],
                        'temperature': 0.7,
                        'max_tokens': 2000
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    return content
                else:
                    return f"無法生成比較分析（API 錯誤: {response.status_code}）"
        
        except Exception as e:
            print(f"生成比較分析錯誤: {str(e)}")
            return f"無法生成比較分析（錯誤: {str(e)}）"
    
    async def generate_advice(self, topic: str, query: str) -> str:
        """使用 LLM 生成建議諮詢"""
        
        prompt = f"""
用戶諮詢: {query}

請提供專業的人才管理建議：

## 💡 專業建議

### 1. 問題分析
分析用戶的需求和關注點。

### 2. 建議方案
提供 3-5 個具體的建議或方案。

### 3. 實施步驟
如何實施這些建議？

### 4. 注意事項
需要注意的風險和挑戰。

### 5. 延伸思考
相關的其他建議或資源。

請用繁體中文，格式清晰，實用可行。
"""
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.llm_service.api_endpoint,
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {self.llm_service.api_key}'
                    },
                    json={
                        'model': self.llm_service.model,
                        'messages': [
                            {
                                'role': 'system',
                                'content': '你是一位資深的人力資源專家，擅長提供人才管理和團隊建設的建議。'
                            },
                            {
                                'role': 'user',
                                'content': prompt
                            }
                        ],
                        'temperature': 0.7,
                        'max_tokens': 2000
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    return content
                else:
                    return f"無法生成建議（API 錯誤: {response.status_code}）"
        
        except Exception as e:
            print(f"生成建議錯誤: {str(e)}")
            return f"無法生成建議（錯誤: {str(e)}）"

# API 端點
@app.on_event("startup")
async def startup_event():
    """應用啟動事件 - 不在此建立資料庫連接，改為延遲連接"""
    print("✅ 應用程式已啟動")
    print("📌 資料庫連接將在首次請求時建立（延遲連接策略）")

@app.on_event("shutdown")
async def shutdown_event():
    """應用關閉時清理資源"""
    global tunnel, db_conn
    try:
        if db_conn and not db_conn.closed:
            db_conn.close()
            print("✅ 資料庫連接已關閉")
        if tunnel and tunnel.is_active:
            tunnel.stop()
            print("✅ SSH 隧道已關閉")
    except Exception as e:
        print(f"⚠️ 清理資源時發生錯誤: {str(e)}")
    print("✅ 資源清理完成")

@app.get("/")
async def root():
    """根路徑"""
    return {
        "message": "人才聊天搜索 API",
        "version": "2.0.0",
        "status": "running",
        "environment": ENVIRONMENT,
        "endpoints": {
            "search": "/api/search",
            "candidates": "/api/candidates",
            "websocket": "/ws",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """健康檢查端點 - 用於 Render 監控"""
    global db_conn, tunnel
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "environment": ENVIRONMENT,
        "checks": {
            "api": "ok"
        }
    }
    
    # 檢查資料庫連接（不強制建立）
    if db_conn and not db_conn.closed:
        health_status["checks"]["database"] = "connected"
    else:
        health_status["checks"]["database"] = "not_connected"
    
    # 檢查 SSH 隧道
    if tunnel and tunnel.is_active:
        health_status["checks"]["ssh_tunnel"] = "active"
    else:
        health_status["checks"]["ssh_tunnel"] = "inactive"
    
    return health_status

@app.post("/api/search", response_model=SearchResponse)
async def search_talents(query: SearchQuery):
    """統一查詢入口 - 支援多種意圖"""
    try:
        engine = TalentSearchEngine()
        
        # 使用 LLM 解析查詢（識別意圖）
        parsed_query = await engine.parse_query(query.query)
        
        # 檢查查詢意圖
        intent = parsed_query.get('intent', 'search')
        entities = parsed_query.get('entities', {})
        
        # ===== 處理「列出所有人」=====
        if intent == 'list_all':
            print("\n📋 處理意圖: 列出所有候選人")
            
            candidates_data = engine.get_all_candidates(limit=100)
            
            # 統計資訊
            total = len(candidates_data)
            with_traits = len([c for c in candidates_data if c.get('trait_results')])
            
            # 轉換為 Candidate 物件
            candidates = []
            for c in candidates_data[:20]:  # 只返回前 20 個
                # 計算平均分數
                trait_results = c.get('trait_results', {})
                if trait_results:
                    scores = [t.get('score', 0) for t in trait_results.values() if isinstance(t, dict)]
                    avg_score = sum(scores) / len(scores) if scores else 0
                else:
                    avg_score = 0
                
                candidates.append(Candidate(
                    id=c['id'],
                    name=c['name'],
                    email=c['email'] or '',
                    test_results=[],
                    match_score=avg_score / 100,  # 轉換為 0-1
                    match_reason=f"已完成 {len(trait_results)} 項特質測評" if trait_results else "尚未完成測評"
                ))
            
            summary = f"""📊 資料庫中共有 {total} 位候選人
✅ 其中 {with_traits} 位已完成測評

您可以：
• 搜索特定特質：「找一個善於溝通的人」
• 查看特質列表：「有哪些特質可以搜索？」
• 準備面試：「為 [姓名] 設計面試綱要」"""
            
            return SearchResponse(
                candidates=candidates,
                total=total,
                query_understanding=summary,
                suggestions=[
                    "搜索特定特質的人才",
                    "查看候選人詳細資料",
                    "為候選人準備面試問題"
                ]
            )
        
        # ===== 處理「列出特質」=====
        if intent == 'list_traits':
            print("\n📋 處理意圖: 列出特質")
            
            traits_list = parsed_query.get('traits', [])
            trait_text = '\n'.join([
                f"• {t['chinese_name']} ({t['system_name']})"
                for t in traits_list
            ])
            
            return SearchResponse(
                candidates=[],
                total=0,
                query_understanding=f"系統中有 {len(engine.llm_service.available_traits)} 個特質，以下是部分列表：\n{trait_text}",
                suggestions=[
                    "嘗試搜索：「找一個協調溝通能力強的人」",
                    "嘗試搜索：「需要創造性思考的設計師」",
                    "列出所有候選人"
                ]
            )
        
        # ===== 處理「面試綱要」=====
        if intent == 'interview':
            print("\n📋 處理意圖: 生成面試綱要")
            
            candidate_name = entities.get('candidate_name')
            
            if not candidate_name:
                return SearchResponse(
                    candidates=[],
                    total=0,
                    query_understanding="請指定候選人姓名，例如：「為張三設計面試綱要」",
                    suggestions=[
                        "先列出所有候選人",
                        "搜索符合條件的人才",
                        "查看候選人列表"
                    ]
                )
            
            # 查找候選人
            candidate_data = engine.find_candidate_by_name(candidate_name)
            
            if not candidate_data:
                return SearchResponse(
                    candidates=[],
                    total=0,
                    query_understanding=f"❌ 找不到候選人：{candidate_name}\n\n請檢查姓名是否正確，或先列出所有候選人。",
                    suggestions=[
                        "列出所有候選人",
                        "檢查姓名拼寫",
                        "搜索類似的候選人"
                    ]
                )
            
            # 生成面試綱要
            print(f"為候選人 {candidate_name} 生成面試綱要...")
            interview_guide = await engine.generate_interview_guide(candidate_data, query.query)
            
            # 轉換為 Candidate 物件
            trait_results = candidate_data.get('trait_results', {})
            if trait_results:
                scores = [t.get('score', 0) for t in trait_results.values() if isinstance(t, dict)]
                avg_score = sum(scores) / len(scores) if scores else 0
            else:
                avg_score = 0
            
            candidate = Candidate(
                id=candidate_data['id'],
                name=candidate_data['name'],
                email=candidate_data['email'] or '',
                test_results=[],
                match_score=avg_score / 100,
                match_reason=f"已完成 {len(trait_results)} 項特質測評"
            )
            
            return SearchResponse(
                candidates=[candidate],
                total=1,
                query_understanding=interview_guide,
                suggestions=[
                    "查看候選人完整測評報告",
                    "搜索類似特質的人才",
                    "比較其他候選人"
                ]
            )
        
        # ===== 處理「統計分析」=====
        if intent == 'statistics':
            print("\n📋 處理意圖: 統計分析")
            
            candidates_data = engine.get_all_candidates(limit=1000)
            
            total = len(candidates_data)
            with_traits = len([c for c in candidates_data if c.get('trait_results')])
            
            # 簡單統計
            summary = f"""📊 統計分析

總候選人數: {total}
已測評人數: {with_traits}
測評完成率: {(with_traits/total*100):.1f}%

您可以：
• 搜索特定特質的人才
• 查看所有候選人
• 為候選人準備面試"""
            
            return SearchResponse(
                candidates=[],
                total=0,
                query_understanding=summary,
                suggestions=[
                    "搜索高分候選人",
                    "列出所有候選人",
                    "查看特質列表"
                ]
            )
        
        # ===== 處理「比較候選人」=====
        if intent == 'compare':
            print("\n📋 處理意圖: 比較候選人")
            
            candidate_names = entities.get('candidate_names', [])
            
            if len(candidate_names) < 2:
                return SearchResponse(
                    candidates=[],
                    total=0,
                    query_understanding="請指定至少兩位候選人進行比較，例如：「比較張三和李四」",
                    suggestions=[
                        "先列出所有候選人",
                        "搜索符合條件的人才",
                        "查看候選人列表"
                    ]
                )
            
            # 查找候選人
            candidates_data = []
            for name in candidate_names[:3]:  # 最多比較 3 個
                candidate = engine.find_candidate_by_name(name)
                if candidate:
                    candidates_data.append(candidate)
            
            if len(candidates_data) < 2:
                return SearchResponse(
                    candidates=[],
                    total=0,
                    query_understanding=f"❌ 找不到足夠的候選人進行比較\n\n請檢查姓名是否正確，或先列出所有候選人。",
                    suggestions=[
                        "列出所有候選人",
                        "檢查姓名拼寫",
                        "搜索類似的候選人"
                    ]
                )
            
            # 使用 LLM 生成比較分析
            comparison = await engine.generate_comparison(candidates_data, query.query)
            
            # 轉換為 Candidate 物件
            candidates = []
            for c in candidates_data:
                trait_results = c.get('trait_results', {})
                if trait_results:
                    scores = [t.get('score', 0) for t in trait_results.values() if isinstance(t, dict)]
                    avg_score = sum(scores) / len(scores) if scores else 0
                else:
                    avg_score = 0
                
                candidates.append(Candidate(
                    id=c['id'],
                    name=c['name'],
                    email=c['email'] or '',
                    test_results=[],
                    match_score=avg_score / 100,
                    match_reason=f"已完成 {len(trait_results)} 項特質測評"
                ))
            
            return SearchResponse(
                candidates=candidates,
                total=len(candidates),
                query_understanding=comparison,
                suggestions=[
                    "查看候選人詳細資料",
                    "為候選人準備面試",
                    "搜索更多候選人"
                ]
            )
        
        # ===== 處理「建議諮詢」=====
        if intent == 'advice':
            print("\n📋 處理意圖: 建議諮詢")
            
            topic = entities.get('topic', query.query)
            
            # 使用 LLM 生成建議
            advice = await engine.generate_advice(topic, query.query)
            
            return SearchResponse(
                candidates=[],
                total=0,
                query_understanding=advice,
                suggestions=[
                    "搜索符合條件的人才",
                    "列出所有候選人",
                    "查看特質列表"
                ]
            )
        
        # 檢查是否是搜索特定候選人
        entities = parsed_query.get('entities', {})
        candidate_name = entities.get('candidate_name')
        
        if candidate_name:
            # 搜索特定候選人
            print(f"\n🔍 搜索特定候選人: {candidate_name}")
            candidate_data = engine.find_candidate_by_name(candidate_name)
            
            if candidate_data:
                # 找到候選人，返回結果
                trait_results = candidate_data.get('trait_results', {})
                if trait_results:
                    scores = [t.get('score', 0) for t in trait_results.values() if isinstance(t, dict)]
                    avg_score = sum(scores) / len(scores) if scores else 0
                else:
                    avg_score = 0
                
                candidate = Candidate(
                    id=candidate_data['id'],
                    name=candidate_data['name'],
                    email=candidate_data['email'] or '',
                    test_results=[],
                    match_score=avg_score / 100,
                    match_reason=f"找到候選人 {candidate_name}，已完成 {len(trait_results)} 項特質測評"
                )
                
                return SearchResponse(
                    candidates=[candidate],
                    total=1,
                    query_understanding=f"✅ 找到候選人：{candidate_name}",
                    suggestions=[
                        f"為 {candidate_name} 設計面試綱要",
                        "查看其他候選人",
                        "搜索類似特質的人才"
                    ]
                )
            else:
                # 找不到候選人
                return SearchResponse(
                    candidates=[],
                    total=0,
                    query_understanding=f"❌ 找不到候選人：{candidate_name}",
                    suggestions=[
                        "列出所有候選人",
                        "檢查姓名拼寫",
                        "搜索特定特質的人才"
                    ]
                )
        
        # 使用 LLM 生成的 SQL 條件搜索候選人（按特質搜索）
        raw_candidates = engine.search_candidates(parsed_query, query.filters)
        
        # 計算匹配分數和生成理由（並行處理以提升速度）
        candidates = []
        for candidate in raw_candidates[:20]:  # 限制處理數量
            score = engine.calculate_match_score(candidate, parsed_query)
            
            # 使用 LLM 生成個性化理由
            reason = await engine.generate_match_reason(candidate, query.query, score, parsed_query)
            
            candidates.append(Candidate(
                id=candidate['id'],
                name=candidate['name'],
                email=candidate['email'] or '',
                test_results=candidate['test_results'],
                match_score=score,
                match_reason=reason
            ))
        
        # 按分數排序
        candidates.sort(key=lambda x: x.match_score, reverse=True)
        
        # 生成查詢理解和建議
        if parsed_query.get('summary'):
            query_understanding = parsed_query['summary']
        else:
            traits = parsed_query.get('traits', [])
            if traits:
                query_understanding = f"您正在尋找：{', '.join(traits)}"
            else:
                query_understanding = "正在為您搜索合適的候選人"
        
        suggestions = [
            "嘗試添加更多具體要求",
            "指定職位類型或經驗水平",
            "描述理想候選人的特質"
        ]
        
        # 如果 LLM 提供了澄清問題
        if parsed_query.get('clarification'):
            suggestions.insert(0, parsed_query['clarification'])
        
        return SearchResponse(
            candidates=candidates[:10],  # 只返回前 10 個
            total=len(candidates),
            query_understanding=query_understanding,
            suggestions=suggestions
        )
    
    except Exception as e:
        print(f"搜索錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/traits")
async def get_all_traits():
    """取得所有可用的特質列表"""
    try:
        engine = TalentSearchEngine()
        traits = engine.llm_service.available_traits
        
        # 按分類組織特質
        traits_by_category = {}
        for trait in traits:
            # 這裡可以從資料庫查詢分類，暫時返回所有特質
            category = "所有特質"
            if category not in traits_by_category:
                traits_by_category[category] = []
            
            traits_by_category[category].append({
                'id': trait['id'],
                'chinese_name': trait['chinese_name'],
                'system_name': trait['system_name'],
                'description': trait['description'][:100] + '...' if len(trait['description']) > 100 else trait['description']
            })
        
        return {
            'total': len(traits),
            'traits': traits,
            'traits_by_category': traits_by_category
        }
    
    except Exception as e:
        print(f"❌ 獲取特質定義錯誤: {str(e)}")
        # 返回預設列表，不讓前端崩潰
        default_traits = [
            {"id": 1, "name": "communication", "chinese_name": "溝通能力", "system_name": "communication", "description": "與他人有效交流的能力"},
            {"id": 2, "name": "leadership", "chinese_name": "領導力", "system_name": "leadership", "description": "引導和激勵團隊的能力"},
            {"id": 3, "name": "creativity", "chinese_name": "創造力", "system_name": "creativity", "description": "產生新想法和解決方案的能力"},
            {"id": 4, "name": "analytical", "chinese_name": "分析能力", "system_name": "analytical", "description": "邏輯思考和數據分析的能力"},
            {"id": 5, "name": "teamwork", "chinese_name": "團隊合作", "system_name": "teamwork", "description": "與他人協作完成目標的能力"},
        ]
        return {
            "total": len(default_traits),
            "traits": default_traits,
            "traits_by_category": {"所有特質": default_traits}
        }

@app.get("/api/candidates/{candidate_id}")
async def get_candidate_detail(candidate_id: int):
    """取得候選人詳細資訊"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = """
            SELECT 
                ip.id,
                ip.name,
                ip.email,
                ip.phone,
                ip.created_at,
                json_agg(
                    json_build_object(
                        'test_id', itr.id,
                        'test_date', itr.test_date,
                        'result', itr.result_data,
                        'project_id', itr.project_id
                    )
                ) as test_results
            FROM individual_profile ip
            LEFT JOIN individual_test_result itr ON ip.id = itr.individual_id
            WHERE ip.id = %s
            GROUP BY ip.id, ip.name, ip.email, ip.phone, ip.created_at;
        """
        
        cursor.execute(sql, (candidate_id,))
        result = cursor.fetchone()
        cursor.close()
        
        if not result:
            raise HTTPException(status_code=404, detail="候選人不存在")
        
        return {
            'id': result[0],
            'name': result[1],
            'email': result[2],
            'phone': result[3],
            'created_at': result[4].isoformat() if result[4] else None,
            'test_results': result[5] if result[5] else []
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端點用於即時聊天 - 使用 LLM"""
    await websocket.accept()
    
    try:
        while True:
            # 接收訊息
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 處理搜索請求
            if message.get('type') == 'search':
                query = message.get('query', '')
                
                # 執行搜索
                engine = TalentSearchEngine()
                parsed_query = await engine.parse_query(query)
                raw_candidates = engine.search_candidates(query)
                
                # 計算匹配分數和生成理由
                candidates = []
                for candidate in raw_candidates[:5]:  # WebSocket 只返回前 5 個
                    score = engine.calculate_match_score(candidate, parsed_query)
                    reason = await engine.generate_match_reason(candidate, query, score, parsed_query)
                    
                    candidates.append({
                        'id': candidate['id'],
                        'name': candidate['name'],
                        'email': candidate['email'],
                        'match_score': score,
                        'match_reason': reason
                    })
                
                # 發送結果
                understanding = parsed_query.get('summary', f"找到 {len(candidates)} 位候選人")
                await websocket.send_json({
                    'type': 'search_results',
                    'candidates': candidates,
                    'query_understanding': understanding
                })
            
            # 回應 ping
            elif message.get('type') == 'ping':
                await websocket.send_json({'type': 'pong'})
    
    except WebSocketDisconnect:
        print("WebSocket 連接已斷開")
    except Exception as e:
        print(f"WebSocket 錯誤: {str(e)}")
        await websocket.close()

if __name__ == '__main__':
    print("=" * 60)
    print("人才聊天搜索 API 服務")
    print("=" * 60)
    print("啟動服務...")
    print("API 文檔: http://localhost:8000/docs")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
