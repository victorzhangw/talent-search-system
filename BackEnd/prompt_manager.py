"""
Prompt 管理器
負責載入和管理所有 LLM Prompt 模板
"""

import json
import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class PromptManager:
    """Prompt 模板管理器"""
    
    def __init__(self, prompts_dir: str = "prompts"):
        """
        初始化 Prompt 管理器
        
        Args:
            prompts_dir: Prompt 配置文件目錄
        """
        self.prompts_dir = prompts_dir
        self.prompts = {}
        self._load_prompts()
    
    def _load_prompts(self):
        """載入所有 Prompt 配置文件"""
        try:
            # HR 諮詢 Prompts
            hr_prompts_path = os.path.join(self.prompts_dir, "hr_consultation_prompts.json")
            if os.path.exists(hr_prompts_path):
                with open(hr_prompts_path, 'r', encoding='utf-8') as f:
                    self.prompts['hr_consultation'] = json.load(f)
                logger.info(f"✅ 載入 HR 諮詢 Prompts: {hr_prompts_path}")
            else:
                logger.warning(f"⚠️ HR 諮詢 Prompts 文件不存在: {hr_prompts_path}")
                self.prompts['hr_consultation'] = self._get_default_hr_prompts()
        
        except Exception as e:
            logger.error(f"❌ 載入 Prompts 失敗: {e}")
            # 使用默認 Prompts
            self.prompts['hr_consultation'] = self._get_default_hr_prompts()
    
    def _get_default_hr_prompts(self) -> Dict:
        """獲取默認的 HR 諮詢 Prompts（作為後備）"""
        return {
            "candidate_specific": {
                "system_prompt_template": "你是一位資深的人力資源專家。",
                "user_prompt_template": "用戶問題：{query}"
            },
            "general": {
                "system_prompt_template": "你是一位資深的人力資源專家。",
                "user_prompt_template": "用戶問題：{query}"
            }
        }
    
    def get_hr_candidate_prompts(self, **kwargs) -> tuple[str, str]:
        """
        獲取候選人特定諮詢的 System 和 User Prompts
        
        Args:
            **kwargs: Prompt 模板變數
            
        Returns:
            (system_prompt, user_prompt)
        """
        try:
            templates = self.prompts['hr_consultation']['candidate_specific']
            system_prompt = templates['system_prompt_template'].format(**kwargs)
            user_prompt = templates['user_prompt_template'].format(**kwargs)
            return system_prompt, user_prompt
        except Exception as e:
            logger.error(f"❌ 生成候選人 Prompts 失敗: {e}")
            raise
    
    def get_hr_general_prompts(self, **kwargs) -> tuple[str, str]:
        """
        獲取通用 HR 諮詢的 System 和 User Prompts
        
        Args:
            **kwargs: Prompt 模板變數
            
        Returns:
            (system_prompt, user_prompt)
        """
        try:
            templates = self.prompts['hr_consultation']['general']
            system_prompt = templates['system_prompt_template'].format(**kwargs)
            user_prompt = templates['user_prompt_template'].format(**kwargs)
            return system_prompt, user_prompt
        except Exception as e:
            logger.error(f"❌ 生成通用 Prompts 失敗: {e}")
            raise
    
    def reload_prompts(self):
        """重新載入所有 Prompt 配置"""
        logger.info("🔄 重新載入 Prompts...")
        self.prompts = {}
        self._load_prompts()
        logger.info("✅ Prompts 重新載入完成")


# 全局 Prompt 管理器實例
_prompt_manager = None


def get_prompt_manager() -> PromptManager:
    """獲取全局 Prompt 管理器實例"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager
