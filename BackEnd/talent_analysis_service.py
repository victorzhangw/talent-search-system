#!/usr/bin/env python3
"""
人才特質分析服務 - 使用 LLM 生成深度分析報告
"""

import httpx
import json
from typing import Dict, List, Any

class TalentAnalysisService:
    """人才特質分析服務"""
    
    def __init__(self, api_key: str, api_endpoint: str, model: str):
        self.api_key = api_key
        self.api_endpoint = api_endpoint
        self.model = model
    
    def get_analysis_prompt(self) -> str:
        """生成分析 Prompt"""
        return """你是一位資深的人力資源專家和心理學家，擅長分析人才特質並提供專業建議。

請根據候選人的測驗結果，提供以下分析：

1. **性格特徵** (3-5 個關鍵詞，用口語化描述)
2. **核心優勢** (列出 3-5 個主要優勢，每個用一句話說明)
3. **適合職位** (推薦 3-5 個具體職位，說明為什麼適合)
4. **工作風格** (描述這個人的工作方式和偏好)
5. **團隊角色** (在團隊中適合扮演什麼角色)
6. **發展建議** (給出 2-3 個具體的發展方向)
7. **面試重點** (建議面試時應該關注的 2-3 個方面)
8. **一句話總結** (用一句話概括這個人才)

**輸出格式要求**：
- 使用口語化、親切的語氣
- 避免過於學術化的用詞
- 具體、實用、有洞察力
- 以 JSON 格式輸出

JSON 結構：
{
  "personality_traits": ["特徵1", "特徵2", "特徵3"],
  "core_strengths": [
    {"strength": "優勢名稱", "description": "具體說明"},
    ...
  ],
  "suitable_positions": [
    {"position": "職位名稱", "reason": "適合原因"},
    ...
  ],
  "work_style": "工作風格描述（2-3 句話）",
  "team_role": "團隊角色描述（2-3 句話）",
  "development_suggestions": [
    {"area": "發展領域", "suggestion": "具體建議"},
    ...
  ],
  "interview_focus": ["重點1", "重點2", "重點3"],
  "summary": "一句話總結"
}"""
    
    async def analyze_candidate(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析候選人特質
        
        Args:
            candidate: 候選人資料，包含 trait_results
            
        Returns:
            分析結果字典
        """
        try:
            # 準備候選人資料
            trait_results = candidate.get('trait_results', {})
            
            if not trait_results:
                return {
                    'success': False,
                    'error': '候選人沒有測驗結果'
                }
            
            # 整理特質資料
            traits_summary = []
            high_traits = []  # 高分特質 (>= 75)
            medium_traits = []  # 中等特質 (60-74)
            low_traits = []  # 低分特質 (< 60)
            
            for trait_key, trait_data in trait_results.items():
                if isinstance(trait_data, dict):
                    score = trait_data.get('score', 0)
                    chinese_name = trait_data.get('chinese_name', trait_key)
                    description = trait_data.get('description', '')
                    
                    trait_info = f"{chinese_name}: {score:.0f}分"
                    if description:
                        trait_info += f" ({description[:50]}...)"
                    
                    traits_summary.append(trait_info)
                    
                    # 分類特質
                    if score >= 75:
                        high_traits.append(f"{chinese_name}({score:.0f}分)")
                    elif score >= 60:
                        medium_traits.append(f"{chinese_name}({score:.0f}分)")
                    else:
                        low_traits.append(f"{chinese_name}({score:.0f}分)")
            
            # 構建分析請求
            candidate_info = f"""
候選人資料：
- 姓名：{candidate.get('name', '未提供')}
- 職位：{candidate.get('position', '未提供')}
- 公司：{candidate.get('company', '未提供')}

測驗結果分析：
總共完成 {len(trait_results)} 項特質測評

高分特質（≥75分）：
{', '.join(high_traits) if high_traits else '無'}

中等特質（60-74分）：
{', '.join(medium_traits) if medium_traits else '無'}

待發展特質（<60分）：
{', '.join(low_traits) if low_traits else '無'}

詳細特質分數：
{chr(10).join(traits_summary[:15])}  # 只顯示前15個特質
"""
            
            # 調用 LLM API
            async with httpx.AsyncClient(timeout=60.0) as client:
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
                                'content': self.get_analysis_prompt()
                            },
                            {
                                'role': 'user',
                                'content': f'請分析以下候選人的特質：\n\n{candidate_info}'
                            }
                        ],
                        'temperature': 0.7,
                        'max_tokens': 2000,
                        'response_format': {'type': 'json_object'}
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    analysis = json.loads(content)
                    
                    print(f"\n✨ LLM 分析完成: {candidate.get('name')}")
                    print(f"   性格特徵: {', '.join(analysis.get('personality_traits', []))}")
                    print(f"   適合職位: {len(analysis.get('suitable_positions', []))} 個")
                    
                    return {
                        'success': True,
                        'analysis': analysis,
                        'raw_traits': {
                            'high': high_traits,
                            'medium': medium_traits,
                            'low': low_traits
                        }
                    }
                else:
                    print(f"❌ LLM API 錯誤: {response.status_code}")
                    return {
                        'success': False,
                        'error': f'LLM API 錯誤: {response.status_code}'
                    }
        
        except Exception as e:
            print(f"❌ 分析錯誤: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    async def batch_analyze_candidates(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量分析候選人
        
        Args:
            candidates: 候選人列表
            
        Returns:
            分析結果列表
        """
        results = []
        
        for candidate in candidates:
            analysis_result = await self.analyze_candidate(candidate)
            results.append({
                'candidate_id': candidate.get('id'),
                'candidate_name': candidate.get('name'),
                'analysis': analysis_result
            })
        
        return results
    
    def format_analysis_for_display(self, analysis: Dict[str, Any]) -> str:
        """
        格式化分析結果為易讀的文字
        
        Args:
            analysis: 分析結果
            
        Returns:
            格式化的文字
        """
        if not analysis.get('success'):
            return f"分析失敗: {analysis.get('error', '未知錯誤')}"
        
        data = analysis['analysis']
        
        output = []
        
        # 一句話總結
        if 'summary' in data:
            output.append(f"💡 {data['summary']}\n")
        
        # 性格特徵
        if 'personality_traits' in data:
            output.append("🎭 性格特徵：")
            output.append(f"   {' • '.join(data['personality_traits'])}\n")
        
        # 核心優勢
        if 'core_strengths' in data:
            output.append("💪 核心優勢：")
            for strength in data['core_strengths']:
                output.append(f"   • {strength['strength']}: {strength['description']}")
            output.append("")
        
        # 適合職位
        if 'suitable_positions' in data:
            output.append("🎯 適合職位：")
            for pos in data['suitable_positions']:
                output.append(f"   • {pos['position']}: {pos['reason']}")
            output.append("")
        
        # 工作風格
        if 'work_style' in data:
            output.append(f"🏢 工作風格：\n   {data['work_style']}\n")
        
        # 團隊角色
        if 'team_role' in data:
            output.append(f"👥 團隊角色：\n   {data['team_role']}\n")
        
        # 發展建議
        if 'development_suggestions' in data:
            output.append("📈 發展建議：")
            for suggestion in data['development_suggestions']:
                output.append(f"   • {suggestion['area']}: {suggestion['suggestion']}")
            output.append("")
        
        # 面試重點
        if 'interview_focus' in data:
            output.append("🔍 面試重點：")
            for focus in data['interview_focus']:
                output.append(f"   • {focus}")
        
        return '\n'.join(output)


# 使用範例
if __name__ == '__main__':
    """
    使用範例：
    
    import asyncio
    
    # 初始化服務
    service = TalentAnalysisService(
        api_key='your-api-key',
        api_endpoint='https://api.siliconflow.cn/v1/chat/completions',
        model='deepseek-ai/DeepSeek-V3'
    )
    
    # 準備候選人資料
    candidate = {
        'id': 1,
        'name': 'Stella',
        'position': '專案經理',
        'company': 'ABC公司',
        'trait_results': {
            'AI科技素養': {'score': 85, 'chinese_name': 'AI科技素養'},
            '人際溝通': {'score': 73, 'chinese_name': '人際溝通'},
            '創造性思考': {'score': 64, 'chinese_name': '創造性思考'},
            # ... 更多特質
        }
    }
    
    # 分析候選人
    result = asyncio.run(service.analyze_candidate(candidate))
    
    # 格式化輸出
    if result['success']:
        print(service.format_analysis_for_display(result))
    """
    print("人才特質分析服務")
    print("請參考程式碼中的使用範例")
