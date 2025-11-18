# core/test_pdf_views.py
"""
測試 PDF 生成的視圖
"""
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from utils.pdf_report_generator import generate_test_result_pdf
from .models import TestProjectResult
import logging

logger = logging.getLogger(__name__)

def test_pdf_generation_view(request, result_id):
    """測試 PDF 生成（不需要登入）"""
    try:
        # 取得測驗結果
        result = get_object_or_404(TestProjectResult, id=result_id)
        
        # 生成 PDF
        return generate_test_result_pdf(result)
        
    except ImportError:
        return HttpResponse('PDF 生成套件未安裝', status=500)
    except Exception as e:
        logger.error(f"PDF 生成失敗：{str(e)}")
        return HttpResponse(f'PDF 生成失敗：{str(e)}', status=500)