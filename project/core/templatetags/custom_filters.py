from django import template
from django.core.exceptions import ObjectDoesNotExist

register = template.Library()

@register.filter
def get_item(obj, key):
    """從字典或對象中獲取屬性或鍵值"""
    if isinstance(obj, dict):
        return obj.get(key, '')
    try:
        return getattr(obj, key, '')
    except:
        return ''

@register.filter
def get_highest_score_category(category_scores):
    """獲取分數最高的分類"""
    if not category_scores:
        return None
    
    # 如果是字典，找出分數最高的分類
    if isinstance(category_scores, dict):
        try:
            highest_score = max(category_scores.values())
            highest_category_name = [name for name, score in category_scores.items() if score == highest_score][0]
            
            # 透過分類名稱獲取分類物件
            from core.models import TestProjectCategory
            try:
                return TestProjectCategory.objects.filter(name=highest_category_name).first()
            except ObjectDoesNotExist:
                return None
        except (ValueError, IndexError):
            return None
    
    return None

@register.filter  
def get_lowest_score_category(category_scores):
    """獲取分數最低的分類"""
    if not category_scores:
        return None
    
    # 如果是字典，找出分數最低的分類
    if isinstance(category_scores, dict):
        try:
            lowest_score = min(category_scores.values())
            lowest_category_name = [name for name, score in category_scores.items() if score == lowest_score][0]
            
            # 透過分類名稱獲取分類物件
            from core.models import TestProjectCategory
            try:
                return TestProjectCategory.objects.filter(name=lowest_category_name).first()
            except ObjectDoesNotExist:
                return None
        except (ValueError, IndexError):
            return None
    
    return None

@register.filter
def split(value, delimiter):
    """將字串以指定的分隔符分割成列表"""
    if not value:
        return []
    return str(value).split(delimiter)

@register.filter
def trim(value):
    """去除字串前後空白"""
    if not value:
        return ''
    return str(value).strip()

@register.filter
def get_trait_score(trait_data):
    """從特質數據中提取分數值"""
    if isinstance(trait_data, dict):
        return trait_data.get('score', 0)
    elif isinstance(trait_data, (int, float)):
        return trait_data
    else:
        return 0

@register.filter
def get_trait_name(trait_data, key):
    """從特質數據中提取中文名稱"""
    if isinstance(trait_data, dict):
        return trait_data.get('chinese_name', key)
    else:
        return key

@register.filter
def get_unique_traits(category_traits):
    """取得去重後的特質列表（依據系統對應名稱去重）"""
    if not category_traits:
        return []
    
    unique_traits = []
    seen_system_names = set()
    
    # 遍歷所有分類的特質
    for category_name, traits in category_traits.items():
        for trait in traits:
            # 使用系統名稱作為唯一識別
            system_name = trait.get('system_name', '')
            if system_name and system_name not in seen_system_names:
                seen_system_names.add(system_name)
                unique_traits.append(trait)
    
    # 依照中文名稱排序（字母順序）
    try:
        unique_traits.sort(key=lambda x: x.get('name', ''))
    except (ValueError, TypeError):
        pass
    
    return unique_traits

@register.filter
def get_headsupflag(raw_data, trait_name):
    """從原始數據中獲取特質的headsupflag值"""
    if not raw_data or not trait_name:
        return 0
    
    # 從trait_scores中查找headsupflag
    trait_scores = raw_data.get('trait_scores', {})
    if not trait_scores:
        return 0
    
    # 方法1: 直接匹配 trait_name
    if trait_name in trait_scores:
        trait_data = trait_scores[trait_name]
        if isinstance(trait_data, dict):
            return trait_data.get('headsupflag', 0)
    
    # 方法2: 嘗試通過中文名稱映射匹配
    chinese_name_mapping = {
        'Analytical Thinking': ['分析思考能力', '分析性思考'],
        'Curiosity': ['好奇心'],
        'Lifelong Learning': ['終身學習'],
        'Systems Thinking': ['系統性思維', '系統性思考'],
        'Attention to Detail': ['注重細節', '準確嚴謹度'],
        'Critical Thinking': ['批判性思考'],
        'Cognitive Flexibility': ['認知靈活性', '認知彈性'],
        'Change Agility': ['變化敏捷性', '適應敏捷力'],
        'Self-Leadership': ['自我領導力', '自主領導力'],
        'Creative Thinking': ['創意思考', '創造性思考'],
        'Empathy': ['同理心'],
        'Social Influence': ['社會影響力'],
        'Achievement Motivation': ['成就動機', '卓越驅動力'],
        'Decision-Making': ['決策能力', '高效決策力'],
        'Resilience': ['韌性'],
        'Active Listening': ['積極傾聽'],
        'Interpersonal Communication': ['人際溝通', '溝通協調力'],
        'Negotiation Skills': ['談判技巧', '協商談判力'],
        'Social Intelligence': ['社會智能', '社交智商'],
        'Dependability': ['可靠性'],
        'AI Literacy': ['AI素養'],
        'Self-Awareness': ['自我意識'],
        'Self-Criticism': ['自我批評'],
        'Self-Reflection': ['自我反思'],
        'Social Desirability': ['社會期望反應'],
        'Feedback Seeking': ['反饋尋求'],
        'Insight': ['洞察力'],
        'Difference Awareness': ['差異察覺']
    }
    
    # 如果 trait_name 是英文（system_name），尋找對應的中文名稱
    if trait_name in chinese_name_mapping:
        alternative_names = chinese_name_mapping[trait_name]
        for alt_name in alternative_names:
            if alt_name in trait_scores:
                trait_data = trait_scores[alt_name]
                if isinstance(trait_data, dict):
                    return trait_data.get('headsupflag', 0)
    
    # 方法3: 反向查找，如果 trait_name 是中文，查找是否有英文對應
    for english_name, chinese_alternatives in chinese_name_mapping.items():
        if trait_name in chinese_alternatives:
            # 嘗試用英文名稱查找
            if english_name in trait_scores:
                trait_data = trait_scores[english_name]
                if isinstance(trait_data, dict):
                    return trait_data.get('headsupflag', 0)
            # 嘗試用其他中文別名查找
            for alt_name in chinese_alternatives:
                if alt_name in trait_scores:
                    trait_data = trait_scores[alt_name]
                    if isinstance(trait_data, dict):
                        return trait_data.get('headsupflag', 0)
    
    return 0

@register.filter
def get_category_by_name(test_project, category_name):
    """根據分類名稱獲取分類對象"""
    if not test_project or not category_name:
        return None
    
    try:
        return test_project.categories.filter(name=category_name).first()
    except:
        return None