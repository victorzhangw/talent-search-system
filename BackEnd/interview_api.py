"""
面試問題生成 API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import httpx
import json

router = APIRouter()

# LLM 配置
LLM_CONFIG = {
    'api_key': 'sk-xmwxrtsxgsjwuyeceydoyuopezzlqresdjyvlzrbbjeejiff',
    'api_host': 'https://api.siliconflow.cn',
    'model': 'deepseek-ai/DeepSeek-V3',
    'endpoint': 'https://api.siliconflow.cn/v1/chat/completions'
}

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
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                LLM_CONFIG['endpoint'],
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {LLM_CONFIG["api_key"]}'
                },
                json={
                    'model': LLM_CONFIG['model'],
                    'messages': messages,
                    'temperature': 0.7,
                    'max_tokens': 2000
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                questions = result['choices'][0]['message']['content']
                
                return InterviewResponse(
                    questions=questions,
                    conversation_id=str(hash(questions))
                )
            else:
                raise HTTPException(status_code=500, detail=f"LLM API 錯誤: {response.status_code}")
    
    except Exception as e:
        print(f"生成面試問題錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
