"""
面試問題生成 API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import httpx
import json
import os
import asyncio
from datetime import datetime

router = APIRouter()

# 判斷運行環境
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
IS_PRODUCTION = ENVIRONMENT == 'production'

# LLM 配置 - 根據環境自動選擇
if IS_PRODUCTION:
    # 生產環境：使用 AkashML
    LLM_CONFIG = {
        'api_key': os.getenv('LLM_API_KEY', 'akml-RTl88SQKMDZFX2c43QslImWLO7DNUdee'),
        'api_host': os.getenv('LLM_API_HOST', 'https://api.akashml.com'),
        'model': os.getenv('LLM_MODEL', 'deepseek-ai/DeepSeek-V3.1'),
        'endpoint': os.getenv('LLM_API_HOST', 'https://api.akashml.com') + '/v1/chat/completions'
    }
    print("🌐 面試 API 使用 AkashML")
else:
    # 開發環境：從環境變數讀取 LLM 配置
    # 注意：不在模組載入時檢查，而是在使用時檢查
    llm_api_host = os.getenv('LLM_API_HOST', 'https://api.siliconflow.cn')
    LLM_CONFIG = {
        'api_key': os.getenv('LLM_API_KEY', ''),  # 空字串作為預設值
        'api_host': llm_api_host,
        'model': os.getenv('LLM_MODEL', 'deepseek-ai/DeepSeek-V3'),
        'endpoint': f"{llm_api_host}/v1/chat/completions"
    }
    print("🌐 面試 API 使用 SiliconFlow")

class InterviewRequest(BaseModel):
    candidates: List[Dict[str, Any]]
    conversation_history: Optional[List[Dict[str, str]]] = []

class InterviewResponse(BaseModel):
    questions: str
    conversation_id: str

@router.post("/api/generate-interview-questions", response_model=InterviewResponse)
async def generate_interview_questions(request: InterviewRequest):
    """生成面試問題"""
    try:
        # 診斷資訊
        print(f"\n{'='*60}")
        print(f"🔍 面試問題生成請求")
        print(f"{'='*60}")
        print(f"候選人數量: {len(request.candidates)}")
        print(f"LLM API 端點: {LLM_CONFIG['endpoint']}")
        print(f"LLM 模型: {LLM_CONFIG['model']}")
        print(f"API Key (前10字): {LLM_CONFIG['api_key'][:10]}...")
        print(f"{'='*60}\n")
        # 構建候選人信息摘要
        candidates_summary = []
        for candidate in request.candidates:
            trait_results = candidate.get('trait_results', {})
            
            # 提取高分特質
            high_traits = []
            for trait_key, trait_data in trait_results.items():
                if isinstance(trait_data, dict):
                    score = trait_data.get('score', 0)
                    chinese_name = trait_data.get('chinese_name', trait_key)
                    if score >= 70:
                        high_traits.append(f"{chinese_name}({score:.0f}分)")
            
            candidates_summary.append({
                'name': candidate.get('name', '未知'),
                'position': candidate.get('position', '未知'),
                'company': candidate.get('company', '未知'),
                'high_traits': high_traits[:5]  # 只取前5個
            })
        
        # 構建 prompt
        if not request.conversation_history:
            # 首次生成
            prompt = f"""你是一位專業的 HR 面試官。請根據以下候選人的特質測評結果，為每位候選人生成 3-5 個針對性的面試問題。

候選人信息：
"""
            for i, candidate in enumerate(candidates_summary, 1):
                prompt += f"\n{i}. {candidate['name']}"
                if candidate['position']:
                    prompt += f" - {candidate['position']}"
                if candidate['company']:
                    prompt += f" ({candidate['company']})"
                prompt += f"\n   優勢特質：{', '.join(candidate['high_traits'])}\n"
            
            prompt += """
請為每位候選人生成面試問題，要求：
1. 問題應該針對候選人的優勢特質設計
2. 問題應該是開放式的，能夠深入了解候選人的能力
3. 問題應該具體、實用，便於在面試中使用
4. 每個問題後面簡要說明考察目的

請以清晰的格式輸出，每位候選人的問題分開列出。

**重要：請務必使用繁體中文回覆，不要使用簡體中文。**"""
        else:
            # 多輪對話
            prompt = request.conversation_history[-1]['content']
        
        # 調用 LLM
        messages = [
            {
                'role': 'system',
                'content': '你是一位專業的 HR 面試官，擅長根據候選人的特質設計針對性的面試問題。請務必使用繁體中文回覆。'
            }
        ]
        
        # 添加對話歷史
        if request.conversation_history:
            for msg in request.conversation_history:
                messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })
        else:
            messages.append({
                'role': 'user',
                'content': prompt
            })
        
        # 重試機制
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # 記錄 LLM API 調用開始（面試問題生成）
                print("=" * 80)
                print(f"🚀 開始調用 LLM API（面試問題生成 - 第 {attempt + 1}/{max_retries} 次）")
                print(f"📍 API 端點: {LLM_CONFIG['endpoint']}")
                print(f"🤖 模型: {LLM_CONFIG['model']}")
                print(f"⏰ 請求時間: {datetime.now().isoformat()}")
                
                import time
                start_time = time.time()
                
                async with httpx.AsyncClient(timeout=60.0) as client:
                    request_data = {
                        'model': LLM_CONFIG['model'],
                        'messages': messages,
                        'temperature': 0.7,
                        'max_tokens': 2000
                    }
                    
                    print(f"🌡️ Temperature: 0.7")
                    print(f"📊 Max Tokens: 2000")
                    print(f"💬 消息數量: {len(messages)}")
                    print(f"📝 請求資料大小: {len(str(request_data))} 字元")
                    
                    # 記錄消息內容摘要
                    for i, msg in enumerate(messages):
                        role = msg.get('role', 'unknown')
                        content_len = len(msg.get('content', ''))
                        print(f"   消息 {i+1}: {role} ({content_len} 字符)")
                    
                    response = await client.post(
                        LLM_CONFIG['endpoint'],
                        headers={
                            'Content-Type': 'application/json',
                            'Authorization': f'Bearer {LLM_CONFIG["api_key"]}'
                        },
                        json=request_data
                    )
                    
                    elapsed_time = time.time() - start_time
                    
                    # 記錄響應狀態
                    print(f"⏱️ API 響應時間: {elapsed_time:.2f} 秒")
                    print(f"📡 HTTP 狀態碼: {response.status_code}")
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # 記錄 Token 使用統計
                        if 'usage' in result:
                            usage = result['usage']
                            print(f"📊 Token 使用統計:")
                            print(f"   - Prompt Tokens: {usage.get('prompt_tokens', 'N/A')}")
                            print(f"   - Completion Tokens: {usage.get('completion_tokens', 'N/A')}")
                            print(f"   - Total Tokens: {usage.get('total_tokens', 'N/A')}")
                        
                        questions = result['choices'][0]['message']['content']
                        print(f"💬 生成的問題長度: {len(questions)} 字符")
                        print(f"✅ 面試問題生成成功")
                        print("=" * 80)
                        
                        return InterviewResponse(
                            questions=questions,
                            conversation_id=str(hash(questions))
                        )
                    elif response.status_code == 503 and attempt < max_retries - 1:
                        # 503 錯誤且還有重試機會，等待後重試
                        print(f"⚠️ LLM API 503 錯誤，{retry_delay} 秒後重試 (嘗試 {attempt + 1}/{max_retries})")
                        print("=" * 80)
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # 指數退避
                        continue
                    else:
                        error_detail = f"LLM API 錯誤: {response.status_code}"
                        try:
                            error_body = response.json()
                            error_detail += f" - {error_body}"
                            print(f"❌ API 錯誤詳情: {error_body}")
                        except:
                            try:
                                error_text = response.text
                                print(f"❌ API 錯誤文本: {error_text[:500]}")
                                error_detail += f" - {error_text[:200]}"
                            except:
                                pass
                        print("=" * 80)
                        raise HTTPException(status_code=500, detail=error_detail)
            except httpx.TimeoutException:
                print(f"❌ LLM API 超時異常")
                if attempt < max_retries - 1:
                    print(f"⚠️ {retry_delay} 秒後重試 (嘗試 {attempt + 1}/{max_retries})")
                    print("=" * 80)
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    print("=" * 80)
                    raise HTTPException(status_code=504, detail="LLM API 請求超時")
            except httpx.RequestError as e:
                print(f"❌ LLM API 連線錯誤: {e}")
                if attempt < max_retries - 1:
                    print(f"⚠️ {retry_delay} 秒後重試")
                    print("=" * 80)
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    raise HTTPException(status_code=503, detail=f"LLM API 連線失敗: {str(e)}")
    
    except Exception as e:
        print(f"生成面試問題錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
