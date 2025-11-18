# utils/pdf_report_generator.py
"""
PDF 報告生成器
提供測驗結果詳情的 PDF 報告生成功能
"""

import os
import io
from typing import Dict
from decimal import Decimal, InvalidOperation
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.utils.text import slugify
from django.template import Template, Context

from .radar_calculations import compute_role_based_scores

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
    from reportlab.lib.colors import HexColor, black, white, gray
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    import matplotlib
    # 在導入時就設定 backend，避免後續問題
    matplotlib.use('Agg', force=True)
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
    print("matplotlib imported successfully")
except ImportError as e:
    MATPLOTLIB_AVAILABLE = False
    print(f"matplotlib import failed: {e}")


class PDFReportGenerator:
    """PDF 報告生成器"""
    
    def __init__(self):
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab 套件未安裝，請先安裝: pip install reportlab")
        if not MATPLOTLIB_AVAILABLE:
            print("⚠️  matplotlib 套件未安裝，雷達圖將使用文字說明替代")
        
        # 註冊中文字體
        self._register_chinese_fonts()
        
        # 設定頁面大小
        self.page_size = A4
        self.page_width, self.page_height = self.page_size
        
        # 設定邊距
        self.left_margin = 1.5 * cm
        self.right_margin = 1.5 * cm
        self.top_margin = 3.5 * cm
        self.bottom_margin = 3 * cm
        
        # 計算內容區域
        self.content_width = self.page_width - self.left_margin - self.right_margin
        self.content_height = self.page_height - self.top_margin - self.bottom_margin
        
        # 設定樣式
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
        # 設定公司資訊
        self.company_info = {
            'name': 'Traitty 專業職位測評',
            'name_en': 'Traitty Professional Position Assessment',
            'company': 'Perception Group',
            'description': 'Perception Group is pioneering solutions that help businesses improve the accuracy and effectiveness of how they select and promote the right people for the right roles.',
            'copyright': 'Copyright © Perception Group',
            'website': 'www.perception-group.com',
            'email': 'info@perception-group.com'
        }
        self._latest_role_based_metrics = None
    
    def _register_chinese_fonts(self):
        """註冊中文字體"""
        try:
            # 收集可能的字體來源，優先專案自帶字體
            possible_fonts: list[str] = []

            try:
                static_dirs = list(getattr(settings, 'STATICFILES_DIRS', []))
                static_root = getattr(settings, 'STATIC_ROOT', None)
                if static_root:
                    static_dirs.append(static_root)

                for static_dir in static_dirs:
                    fonts_dir = os.path.join(static_dir, 'fonts')
                    if not os.path.isdir(fonts_dir):
                        continue
                    for filename in sorted(os.listdir(fonts_dir)):
                        if filename.lower().endswith((".ttf", ".otf", ".ttc")):
                            possible_fonts.append(os.path.join(fonts_dir, filename))
            except Exception as static_font_exc:
                print(f"⚠️  載入專案字體資料夾失敗: {static_font_exc}")

            # 系統字體路徑（依不同平台補齊）
            import platform
            system = platform.system()

            if system == "Darwin":
                possible_fonts.extend([
                    "/Library/Fonts/Microsoft JhengHei.ttf",
                    "/System/Library/Fonts/PingFang.ttc",
                    "/System/Library/Fonts/STHeiti Light.ttc",
                    "/Library/Fonts/Arial Unicode MS.ttf",
                ])
            elif system == "Windows":
                possible_fonts.extend([
                    "C:/Windows/Fonts/msjh.ttc",
                    "C:/Windows/Fonts/msyh.ttc",
                    "C:/Windows/Fonts/simhei.ttf",
                    "C:/Windows/Fonts/simsun.ttc",
                ])
            else:  # Linux / Docker
                possible_fonts.extend([
                    "/usr/local/share/fonts/NotoSansTC-Regular.otf",
                    "/usr/local/share/fonts/NotoSansCJK-Regular.ttc",
                    "/usr/share/fonts/opentype/noto/NotoSansTC-Regular.otf",
                    "/usr/share/fonts/opentype/noto/NotoSansCJKtc-Regular.otf",
                    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
                    "/usr/share/fonts/truetype/droid/DroidSansFallback.ttf",
                ])

            self.chinese_font_name = None
            self.chinese_font_bold_name = None

            for font_path in possible_fonts:
                if not os.path.exists(font_path):
                    continue
                try:
                    pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                    self.chinese_font_name = 'ChineseFont'
                    print(f"成功註冊中文字體: {font_path}")

                    try:
                        pdfmetrics.registerFont(TTFont('ChineseFontBold', font_path))
                        self.chinese_font_bold_name = 'ChineseFontBold'
                    except Exception as bold_exc:
                        print(f"⚠️  粗體註冊失敗，改用普通體: {bold_exc}")
                        self.chinese_font_bold_name = 'ChineseFont'
                    break
                except Exception as e:
                    print(f"無法註冊字體 {font_path}: {e}")
                    continue
            
            # 如果無法找到系統字體，使用 ReportLab 內建字體
            if self.chinese_font_name is None:
                print("警告: 無法找到合適的中文字體，將使用英文字體")
                self.chinese_font_name = 'Helvetica'
                self.chinese_font_bold_name = 'Helvetica-Bold'
                
        except Exception as e:
            print(f"字體註冊過程中發生錯誤: {e}")
            # 使用後備字體
            self.chinese_font_name = 'Helvetica'
            self.chinese_font_bold_name = 'Helvetica-Bold'
    
    def _django_round(self, value):
        """模擬Django floatformat:0的四捨五入行為"""
        template_str = '{{ value|floatformat:0 }}'
        template = Template(template_str)
        context = Context({'value': value})
        return int(template.render(context))
    
    def _setup_custom_styles(self):
        """設定自訂樣式"""
        # 標題樣式：16 → 14
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=14,
            spaceAfter=16,
            alignment=TA_CENTER,
            textColor=HexColor('#34495D'),
            fontName=self.chinese_font_bold_name
        )

        # 副標題：16 → 14
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=10,
            alignment=TA_LEFT,
            textColor=HexColor('#34495D'),
            fontName=self.chinese_font_bold_name
        )

        # 內容：12 → 11
        self.content_style = ParagraphStyle(
            'CustomContent',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=6,
            alignment=TA_LEFT,
            textColor=black,
            leftIndent=0.5 * cm,
            fontName=self.chinese_font_name
        )

        # 頁首/頁尾：12 → 11
        self.header_style = ParagraphStyle(
            'CustomHeader',
            parent=self.styles['Normal'],
            fontSize=11,
            alignment=TA_CENTER,
            textColor=HexColor('#34495D'),
            fontName=self.chinese_font_name
        )

        self.footer_style = ParagraphStyle(
            'CustomFooter',
            parent=self.styles['Normal'],
            fontSize=11,
            alignment=TA_CENTER,
            textColor=HexColor('#34495D'),
            fontName=self.chinese_font_name
        )

        # 封面大標：24 → 22
        self.cover_title_style = ParagraphStyle(
            'CoverTitle',
            parent=self.styles['Heading1'],
            fontSize=22,
            spaceAfter=24,
            alignment=TA_CENTER,
            textColor=HexColor('#34495D'),
            fontName=self.chinese_font_bold_name
        )

        # 封面副標：16 → 14
        self.cover_subtitle_style = ParagraphStyle(
            'CoverSubtitle',
            parent=self.styles['Normal'],
            fontSize=14,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=HexColor('#34495D'),
            fontName=self.chinese_font_name
        )

        # 封面資訊：12 → 11
        self.cover_info_style = ParagraphStyle(
            'CoverInfo',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=10,
            alignment=TA_LEFT,
            textColor=black,
            leftIndent=1 * cm,
            fontName=self.chinese_font_name
        )
    
    def _draw_header_footer(self, canvas, doc):
        """繪製頁首和頁尾"""
        canvas.saveState()
        
        page_num = canvas.getPageNumber()
        # 移除舊的total_pages邏輯
        
        # 第一頁（封面）不繪製頁首頁尾
        if page_num == 1:
            canvas.restoreState()
            return
            
        # 頁首 - Header_img.png（完全滿版，無任何留白）
        try:
            header_img_path = os.path.join(settings.STATICFILES_DIRS[0], 'img', 'Header_img.png')
            if os.path.exists(header_img_path):
                # 設定圖片為滿版寬度，從頁面最頂部開始
                img_width = self.page_width  # 滿版寬度
                img_height = 2.8 * cm  # 圖片高度
                # 圖片位置：稍微超出頁面頂部以消除留白
                canvas.drawImage(header_img_path, 0, self.page_height - img_height + 0.1 * cm, 
                               width=img_width, height=img_height, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print(f"無法載入頁首圖片: {e}")
            # 如果圖片載入失敗，顯示文字
            canvas.setFont(self.chinese_font_bold_name, 10)
            canvas.setFillColor(HexColor('#2c3e50'))
            canvas.drawString(self.left_margin, header_y, "WePredict/Traitty")
        
        # 頁尾
        footer_y = 2.5 * cm
        
        # 動態判斷最後一頁 - 使用實際的總頁數
        is_last_page = page_num == self.total_pages_count
        
        print(f"[DEBUG] 當前頁: {page_num}, 總頁數: {self.total_pages_count}, 是最後一頁: {is_last_page}")
        
        if is_last_page:
            # 最後一頁 - Footer_img.png
            try:
                footer_img_path = os.path.join(settings.STATICFILES_DIRS[0], 'img', 'Footer_img.png')
                if os.path.exists(footer_img_path):
                    # 設定圖片為滿版寬度，貼到頁面絕對底部
                    img_width = self.page_width  # 滿版寬度
                    img_height = 4 * cm  # 恢復適當高度
                    # 圖片強制填滿底部區域，不保持比例以消除留白
                    canvas.drawImage(footer_img_path, 0, 0, 
                                   width=img_width, height=img_height, preserveAspectRatio=False, mask='auto')
                else:
                    # 如果圖片不存在，顯示版權文字
                    canvas.setFont(self.chinese_font_name, 10)
                    canvas.setFillColor(HexColor('#7f8c8d'))
                    canvas.drawCentredString(self.page_width / 2, footer_y, "© Copyright WePredict/Traitty")
            except Exception as e:
                print(f"無法載入頁尾圖片: {e}")
                # 如果圖片載入失敗，顯示文字
                canvas.setFont(self.chinese_font_name, 10)
                canvas.setFillColor(HexColor('#7f8c8d'))
                canvas.drawCentredString(self.page_width / 2, footer_y, "© Copyright WePredict/Traitty")
        else:
            # 非最後一頁 - 顯示版權文字，更接近底部
            canvas.setFont(self.chinese_font_name, 10)
            canvas.setFillColor(HexColor('#7f8c8d'))
            # 調整版權文字位置，更接近頁面底部
            canvas.drawCentredString(self.page_width / 2, 1.5 * cm, "© Copyright WePredict/Traitty")
        
        canvas.restoreState()
    
    def _draw_cover_page_header_footer(self, canvas, doc):
        """繪製封面頁的頁首和頁尾"""
        canvas.saveState()
        
        # 封面頁首 - Header_img.png（完全滿版，無留白）
        try:
            header_img_path = os.path.join(settings.STATICFILES_DIRS[0], 'img', 'Header_img.png')
            if os.path.exists(header_img_path):
                # 設定圖片為滿版寬度，稍微超出頁面頂部以消除留白
                img_width = self.page_width  # 滿版寬度
                img_height = 2.8 * cm  # 圖片高度
                # 與其他頁面一致的設定，稍微超出頁面頂部
                canvas.drawImage(header_img_path, 0, self.page_height - img_height + 0.1 * cm, 
                               width=img_width, height=img_height, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print(f"無法載入封面頁首圖片: {e}")
            # 如果圖片載入失敗，顯示文字
            canvas.setFont(self.chinese_font_bold_name, 12)
            canvas.setFillColor(HexColor('#2c3e50'))
            canvas.drawString(self.left_margin, self.page_height - 1 * cm, "WePredict/Traitty")
        
        # 封面頁尾 - 顯示版權文字
        footer_y = 2.5 * cm
        canvas.setFont(self.chinese_font_name, 10)
        canvas.setFillColor(HexColor('#7f8c8d'))
        canvas.drawCentredString(self.page_width / 2, footer_y, "© Copyright WePredict/Traitty")
        
        canvas.restoreState()
    
    def _draw_header_footer_dynamic(self, canvas, doc):
        """繪製頁首和頁尾 - 動態判斷最後一頁"""
        canvas.saveState()
        
        page_num = canvas.getPageNumber()
        
        # 檢查這是否是文檔的最後一頁
        # ReportLab會在最後一頁調用時設置_pageNumber，我們可以檢查是否還有更多頁面
        try:
            # 嘗試訪問文檔對象的頁面信息
            is_last_page = not hasattr(doc, '_template') or getattr(canvas, '_pageCallbacks', None) is None
        except:
            is_last_page = False
        
        print(f"[DEBUG] 頁數: {page_num}, 是否為最後一頁: {is_last_page}")
        
        # 第一頁（封面）不繪製頁首頁尾
        if page_num == 1:
            canvas.restoreState()
            return
            
        # 頁首 - Header_img.png（完全滿版，無任何留白）
        try:
            header_img_path = os.path.join(settings.STATICFILES_DIRS[0], 'img', 'Header_img.png')
            if os.path.exists(header_img_path):
                # 設定圖片為滿版寬度，從頁面最頂部開始
                img_width = self.page_width  # 滿版寬度
                img_height = 2.8 * cm  # 圖片高度
                # 圖片位置：稍微超出頁面頂部以消除留白
                canvas.drawImage(header_img_path, 0, self.page_height - img_height + 0.1 * cm, 
                               width=img_width, height=img_height, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print(f"無法載入頁首圖片: {e}")
            # 如果圖片載入失敗，顯示文字
            canvas.setFont(self.chinese_font_bold_name, 10)
            canvas.setFillColor(HexColor('#2c3e50'))
            canvas.drawString(self.left_margin, header_y, "WePredict/Traitty")
        
        # 頁尾
        footer_y = 2.5 * cm
        
        # 動態判斷最後一頁 - 使用實際的總頁數
        is_last_page = page_num == self.total_pages_count
        
        print(f"[DEBUG] 當前頁: {page_num}, 總頁數: {self.total_pages_count}, 是最後一頁: {is_last_page}")
        
        if is_last_page:
            # 可能是最後一頁 - Footer_img.png
            try:
                footer_img_path = os.path.join(settings.STATICFILES_DIRS[0], 'img', 'Footer_img.png')
                if os.path.exists(footer_img_path):
                    # 設定圖片為滿版寬度，貼到頁面絕對底部
                    img_width = self.page_width  # 滿版寬度
                    img_height = 4 * cm  # 恢復適當高度
                    # 圖片強制填滿底部區域，不保持比例以消除留白
                    canvas.drawImage(footer_img_path, 0, 0, 
                                   width=img_width, height=img_height, preserveAspectRatio=False, mask='auto')
                else:
                    # 如果圖片不存在，顯示版權文字
                    canvas.setFont(self.chinese_font_name, 10)
                    canvas.setFillColor(HexColor('#7f8c8d'))
                    canvas.drawCentredString(self.page_width / 2, footer_y, "© Copyright WePredict/Traitty")
            except Exception as e:
                print(f"無法載入頁尾圖片: {e}")
                # 如果圖片載入失敗，顯示文字
                canvas.setFont(self.chinese_font_name, 10)
                canvas.setFillColor(HexColor('#7f8c8d'))
                canvas.drawCentredString(self.page_width / 2, footer_y, "© Copyright WePredict/Traitty")
        else:
            # 非最後一頁 - 顯示版權文字，更接近底部
            canvas.setFont(self.chinese_font_name, 10)
            canvas.setFillColor(HexColor('#7f8c8d'))
            # 調整版權文字位置，更接近頁面底部
            canvas.drawCentredString(self.page_width / 2, 1.5 * cm, "© Copyright WePredict/Traitty")
        
        canvas.restoreState()
    
    def generate_test_result_report(self, test_result, output_path=None):
        """
        生成測驗結果報告
        
        Args:
            test_result: TestProjectResult 物件
            output_path: 輸出路徑，如果為 None 則返回 HttpResponse
        
        Returns:
            HttpResponse 或 檔案路徑
        """
        # 建立 PDF 文件
        buffer = io.BytesIO()
        
        # 初始化標記
        self.has_development_suggestions = False
        
        # 創建story生成函數
        def create_story():
            story = []
            
            # 添加封面頁
            story.extend(self._create_cover_page(test_result))
            
            # 添加分頁
            story.append(PageBreak())
            
            # 添加報告使用指南（第二頁固定內容）
            story.extend(self._create_report_guide_section(test_result))
            
            # 添加分頁
            story.append(PageBreak())
            
            # 添加關鍵特質分析頁（第三頁，移除基本資訊頁）
            story.extend(self._create_key_analysis_section(test_result))
            
            return story
        
        # 移除舊的總頁數設定
        
        # 建立文檔
        doc = SimpleDocTemplate(
            buffer,
            pagesize=self.page_size,
            leftMargin=self.left_margin,
            rightMargin=self.right_margin,
            topMargin=self.top_margin,
            bottomMargin=self.bottom_margin
        )
        
        # 使用兩階段生成：先計算總頁數，再生成正確的PDF
        # 第一階段：計算總頁數
        temp_buffer = io.BytesIO()
        temp_doc = SimpleDocTemplate(
            temp_buffer,
            pagesize=self.page_size,
            leftMargin=self.left_margin,
            rightMargin=self.right_margin,
            topMargin=self.top_margin,
            bottomMargin=self.bottom_margin
        )
        self.total_pages_count = 0
        
        def count_pages_only(canvas, doc):
            self.total_pages_count = max(self.total_pages_count, canvas.getPageNumber())
        
        # 先建立一次來計算總頁數
        temp_doc.build(create_story(), onFirstPage=count_pages_only, onLaterPages=count_pages_only)
        
        print(f"[DEBUG] 計算得出總頁數: {self.total_pages_count}")
        
        # 第二階段：使用正確的總頁數生成最終PDF
        doc.build(create_story(), onFirstPage=self._draw_cover_page_header_footer, onLaterPages=self._draw_header_footer)
        
        # 處理輸出
        if output_path:
            # 儲存到檔案
            with open(output_path, 'wb') as f:
                f.write(buffer.getvalue())
            buffer.close()
            return output_path
        else:
            # 返回 HTTP 響應
            buffer.seek(0)
            # 獲取受測者姓名
            invitee_name = test_result.test_invitation.invitee.name or ''
            project_abbreviation = (test_result.test_project.name_abbreviation or '').strip()
            if not project_abbreviation:
                project_abbreviation = test_result.test_project.name or ''

            # 清理檔案名稱中的特殊字符，避免檔案系統問題
            import re

            def sanitize_component(value: str) -> str:
                cleaned = re.sub(r'[\\/:*?"<>|]', '_', value or '')
                return cleaned.strip().strip('_')

            display_invitee_name = sanitize_component(invitee_name) or f"受測者{test_result.id}"
            display_project_abbr = sanitize_component(project_abbreviation) or sanitize_component(test_result.test_project.name) or "測驗"

            # ASCII 後備檔名，避免特殊字元導致下載失敗
            ascii_invitee = slugify(display_invitee_name) or f"user_{test_result.id}"
            ascii_project = slugify(display_project_abbr) or "project"
            safe_filename = f"traitty_result_report_{ascii_project}_{ascii_invitee}.pdf"
            display_filename = f"Traitty結果報告＿{display_project_abbr}＿{display_invitee_name}.pdf"
            
            response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
            # 使用標準的檔名編碼方式
            import urllib.parse
            encoded_display_name = urllib.parse.quote(display_filename.encode('utf-8'))
            response['Content-Disposition'] = f'attachment; filename="{safe_filename}"; filename*=UTF-8\'\'{encoded_display_name}'
            buffer.close()
            return response
    
    def _create_cover_page(self, test_result):
        """建立封面頁"""
        story = []
        
        # 添加空白以將內容置中
        story.append(Spacer(1, 3 * cm))
        
        # 主標題 - 使用測驗項目的標題名稱，加粗加黑
        main_title = test_result.test_project.title_name or test_result.test_project.name
        main_title_style = ParagraphStyle(
            'MainTitle',
            parent=self.cover_title_style,
            fontSize=24,
            fontName=self.chinese_font_bold_name,
            textColor=HexColor('#34495D'),  # 標題使用#34495D顏色
            spaceAfter=12
        )
        story.append(Paragraph(f"<b>{main_title}</b>", main_title_style))
        
        
        # 固定文字
        fixed_text_style = ParagraphStyle(
            'FixedText',
            parent=self.cover_subtitle_style,
            fontSize=14,
            fontName=self.chinese_font_name,
            spaceAfter=24
        )
        story.append(Paragraph("特質分析與多向度洞察報告", fixed_text_style))
        
        # 添加空白分隔
        story.append(Spacer(1, 1.5 * cm))
        
        # 受測人員基本資訊 - 採用兩欄無框架布局
        
        # 準備資料
        invitee_name = test_result.test_invitation.invitee.name
        invitee_email = test_result.test_invitation.invitee.email
        position = test_result.test_invitation.invitee.position or "專案經理"
        status_display = test_result.test_invitation.invitee.get_status_display() if hasattr(test_result.test_invitation.invitee, 'get_status_display') else "求職者"
        
        # 測驗項目（值帶入標題名稱＋標題名稱英文）
        project_title = main_title
        if test_result.test_project.title_name_english:
            project_title += f" {test_result.test_project.title_name_english}"
        
        # 時間資料 - 轉換為台灣時區顯示
        import pytz
        
        taiwan_tz = pytz.timezone('Asia/Taipei')
        
        # 邀請時間
        if test_result.test_invitation.invited_at:
            invited_time_tw = test_result.test_invitation.invited_at.astimezone(taiwan_tz)
            invited_time = invited_time_tw.strftime('%Y年%m月%d日 %H:%M')
        else:
            invited_time = "N/A"
        
        # 結果取得時間（爬蟲完成時間）
        if test_result.crawled_at:
            crawled_time_tw = test_result.crawled_at.astimezone(taiwan_tz)
            completed_time = crawled_time_tw.strftime('%Y年%m月%d日 %H:%M')
        else:
            completed_time = "N/A"
        
        # 創建兩欄式表格資料
        basic_info_data = [
            ['受測者姓名', invitee_name],
            ['電子信箱', invitee_email],
            ['職務角色', position],
            ['身份別', status_display],
            ['測驗項目', project_title],
            ['邀請時間', invited_time],
            ['結果取得時間', completed_time]
        ]
        
        # 添加上方水平線
        from reportlab.graphics.shapes import Line, Drawing
        
        # 創建上方線條
        top_line = Drawing(self.content_width, 0.2*cm)
        top_line.add(Line(0, 0.1*cm, self.content_width, 0.1*cm, strokeColor=HexColor('#34495D'), strokeWidth=1))
        story.append(top_line)
        story.append(Spacer(1, 0.3*cm))
        
        # 建立簡潔的兩欄表格，無框線無底色
        info_table = Table(basic_info_data, colWidths=[4*cm, 9*cm])
        info_table.setStyle(TableStyle([
            ('TEXTCOLOR', (0, 0), (-1, -1), black),  # 統一文字顏色改為黑色
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # 全部左對齊
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # 垂直對齊頂部
            ('FONTNAME', (0, 0), (-1, -1), self.chinese_font_name),  # 統一字體
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            # 不設定任何背景色或格線
        ]))
        
        story.append(info_table)
        
        # 添加下方水平線
        story.append(Spacer(1, 0.3*cm))
        bottom_line = Drawing(self.content_width, 0.2*cm)
        bottom_line.add(Line(0, 0.1*cm, self.content_width, 0.1*cm, strokeColor=HexColor('#34495D'), strokeWidth=1))
        story.append(bottom_line)
        
        # 添加空白填充底部
        story.append(Spacer(1, 2 * cm))
        
        return story
    
    def _create_report_guide_section(self, test_result):
        """建立報告使用指南（第二頁固定內容）"""
        story = []
        
        # 創建帶行距的樣式，支援自動換行和HTML標籤，優化中英混合文字處理
        content_with_spacing = ParagraphStyle(
            'ContentWithSpacing',
            parent=self.content_style,
            fontSize=12,
            spaceAfter=12,
            leading=16,  # 行距
            fontName=self.chinese_font_name,
            wordWrap='CJK',  # 使用CJK換行模式，適合中日韓文字
            alignment=TA_JUSTIFY,  # 使用兩端對齊，改善排版
            leftIndent=0,
            rightIndent=0,
            allowWidows=1,   # 允許孤行
            allowOrphans=1,  # 允許孤字
            splitLongWords=1,  # 允許長單詞分割
            breakLongWords=1   # 在必要時分割長單詞
        )
        
        # 粗體標題樣式
        bold_title_style = ParagraphStyle(
            'BoldTitleStyle',
            parent=self.subtitle_style,
            fontSize=16,
            fontName=self.chinese_font_bold_name,
            spaceAfter=15
        )
        
        # 簡介部分 - 添加頂部間距與其他標題保持一致
        story.append(Spacer(1, 0.8 * cm))
        story.append(Paragraph("<b>簡介 | 快速掌握價值</b>", bold_title_style))
        
        # 從測驗項目獲取簡介內容
        intro_content = ""
        if test_result.test_project.introduction:
            intro_content = self._clean_html_content(test_result.test_project.introduction)
        else:
            # 預設內容優化排版，手動控制換行位置避免英文單詞被切斷
            intro_content = """WePredict 運用伯思 AI (PerceptionPredict) 的識才預測技術，<br/>打造了這份 AI 時代人才潛能評鑑 (AI Nexus Insight Assessment)，<br/>讓人們能先一步掌握優勢並規劃未來發展方向。<br/><br/>以心理學、行為科學等科學方法為基礎，結合結合世界經濟組織 WEF《2025 Future of Jobs 未來就業報告》以及全球產、官、學界等 10 數篇 2023-2025 年發布之重點報告，其中包含了 25 萬筆求職資料、4,000 份企業問卷、涵蓋至少 22 個產業、55 個經濟體，加上 PerceptionPredict 十年協助企業建置精準識才 AI 模型、辨識高績效人才的實務經驗所開發，具備高度實用性與未來效益。"""
        
        story.append(Paragraph(intro_content, content_with_spacing))
        story.append(Spacer(1, 0.8 * cm))
        
        # 使用方式部分
        story.append(Paragraph("<b>使用方式 | 如何善用、發揮效果</b>", bold_title_style))
        
        # 從測驗項目獲取使用方式內容
        usage_content = ""
        if test_result.test_project.usage_guide:
            usage_content = self._clean_html_content(test_result.test_project.usage_guide)
        else:
            # 預設內容使用換行格式，提升可讀性
            usage_content = """評鑑完成後，將取得預測值（按評鑑項目不同有所不同）、關鍵特質列表、特質分數，便於企業快速從大量應徵者中篩選具潛力者。您可直接參考預測值進行初步識別，若需進一步分析，可深入閱讀報告中的特質構面定義與分數解析，作為面談或內部評估的輔助資料。建議可將此評鑑納入現行招募流程的初篩或第二關卡，以提升決策效率與人才命中率。<br/><br/>完成評鑑後，您會看到三個主要資訊：AI預測值（按評鑑項目不同）、關鍵特質列表，以及每個特質的分數說明。<br/><br/>可直接依預測值進行初步篩選，快速找出具潛力的候選人，提升篩選效率與人才命中率；若需要進一步判斷，也可參考特質的定義與分數細節，作為招募、團隊配置、辨別具發展潛力人才的參考依據。"""
        
        story.append(Paragraph(usage_content, content_with_spacing))
        story.append(Spacer(1, 0.8 * cm))
        
        # 注意事項部分
        story.append(Paragraph("<b>注意事項 | 正確運用心法</b>", bold_title_style))
        
        # 從測驗項目獲取注意事項內容
        notice_content = ""
        if test_result.test_project.precautions:
            notice_content = self._clean_html_content(test_result.test_project.precautions)
        else:
            # 預設內容使用換行格式，提升可讀性
            notice_content = """此AI心理特質評鑑為輔助性人才識別工具，雖已具備高度準確性與預測力，但仍非100%判定結果。<br/><br/>請避免將報告分數作對受測者貼標籤或產生偏見。進行後續人才了解、培訓、資源提供時，應搭配其他職位相關條件、資源進行後續行動依據。"""
        
        story.append(Paragraph(notice_content, content_with_spacing))
        story.append(Spacer(1, 1 * cm))
        
        return story
    
    def _create_key_analysis_section(self, test_result):
        """建立關鍵特質分析區塊（第三頁）"""
        story = []
        
        if not test_result.raw_data or not test_result.test_project:
            return story
        
        # 計算分類分數
        category_scores = self._calculate_category_scores(test_result)
        
        if not category_scores:
            return story
        
        # 粗體標題樣式
        bold_title_style = ParagraphStyle(
            'BoldTitleStyle',
            parent=self.subtitle_style,
            fontSize=16,
            fontName=self.chinese_font_bold_name,
            spaceAfter=15
        )
        
        # 第三頁開始的標題間距 - 增加到與標題到表格間距相等
        story.append(Spacer(1, 0.6 * cm))  # 增加頁首到標題間距
        
        # 1. 關鍵特質分數表（合併所有分類的特質）
        story.append(Paragraph("<b>關鍵特質分數</b>", bold_title_style))
        story.append(Spacer(1, 0.8 * cm))  # 標題與表格間距
        story.extend(self._create_merged_trait_scores_section(test_result))
        story.append(Spacer(1, 0.8 * cm))
        
        # 添加分頁
        story.append(PageBreak())
        
        # 2. 特質向度雷達圖
        story.append(Spacer(1, 0.8 * cm))  # 頁首到標題間距
        story.append(Paragraph("<b>特質向度雷達圖</b>", bold_title_style))
        story.append(Spacer(1, 0.8 * cm))  # 標題與內容間距
        
        # 生成並嵌入雷達圖
        if MATPLOTLIB_AVAILABLE:
            radar_image_path = self._generate_radar_chart(category_scores)
            if radar_image_path and os.path.exists(radar_image_path):
                try:
                    from reportlab.lib.utils import ImageReader 
                    ir = ImageReader(radar_image_path)
                    iw, ih = ir.getSize()  # 原始像素寬高

                    # 你希望的最大邊長（別超過內容寬度）
                    target_max_side = min(14 * cm, self.content_width)  # 可調：想更大就改數值

                    # 依最大邊長做等比縮放，保持正圓
                    scale = target_max_side / max(iw, ih)
                    scaled_w = iw * scale
                    scaled_h = ih * scale

                    radar_image = Image(radar_image_path, width=scaled_w, height=scaled_h)
                    story.append(radar_image)
                    story.append(Spacer(1, 0.5 * cm))
                except Exception:
                    # 如果雷達圖嵌入失敗，使用文字說明
                    radar_text = """雷達圖顯示您在各個特質分類的綜合表現。圖表中的每個頂點代表一個特質分類，數值越高表示該分類的表現越好。此圖有助於快速了解您的特質分佈與優勢領域。"""
                    story.append(Paragraph(radar_text, self.content_style))
                    story.append(Spacer(1, 0.8 * cm))
                
                # 延遲清理臨時檔案
                def cleanup_temp_file():
                    try:
                        if os.path.exists(radar_image_path):
                            os.remove(radar_image_path)
                    except:
                        pass
                # 延遲清理
                import threading
                timer = threading.Timer(5.0, cleanup_temp_file)
                timer.start()
            else:
                # 如果雷達圖生成失敗，使用文字說明
                radar_text = """雷達圖顯示您在各個特質分類的綜合表現。圖表中的每個頂點代表一個特質分類，數值越高表示該分類的表現越好。此圖有助於快速了解您的特質分佈與優勢領域。"""
                story.append(Paragraph(radar_text, self.content_style))
                story.append(Spacer(1, 0.8 * cm))
        else:
            # matplotlib 不可用時使用文字說明
            radar_text = """雷達圖顯示您在各個特質分類的綜合表現。圖表中的每個頂點代表一個特質分類，數值越高表示該分類的表現越好。此圖有助於快速了解您的特質分佈與優勢領域。"""
            story.append(Paragraph(radar_text, self.content_style))
            story.append(Spacer(1, 0.8 * cm))
        
        # 混合型人才區塊
        mixed_role_categories = []
        mixed_role_sentence = None
        if self._latest_role_based_metrics:
            mixed_roles = self._latest_role_based_metrics.get("mixed_roles") or []
            for role_name in mixed_roles:
                category = test_result.test_project.categories.filter(name=role_name).first()
                if category:
                    mixed_role_categories.append(category)
            if mixed_role_categories:
                quoted_names = [f'”{category.name}”' for category in mixed_role_categories]
                names_text = '、'.join(quoted_names)
                mixed_role_sentence = f'兼具{names_text}的特點，具備不同角色發展適性，亦可做為跨角色溝通橋樑'

        analysis_content_style = ParagraphStyle(
            'AnalysisContent',
            parent=self.content_style,
            fontSize=12,
            fontName=self.chinese_font_name,
            leading=16
        )

        if mixed_role_sentence:
            story.append(Spacer(1, 0.8 * cm))
            story.append(Paragraph("<b>混合型人才</b>", bold_title_style))
            story.append(Spacer(1, 0.4 * cm))
            story.append(Paragraph(mixed_role_sentence, analysis_content_style))
            story.append(Spacer(1, 0.8 * cm))
        else:
            story.append(Spacer(1, 0.8 * cm))

        # 3. 各向度數值
        story.append(Paragraph("<b>各向度數值</b>", bold_title_style))
        story.append(Spacer(1, 0.8 * cm))  # 標題與內容間距
        
        # 使用 ListFlowable 建立編號列表
        from reportlab.platypus import ListFlowable, ListItem
        
        # 準備列表項目
        list_items = []
        sorted_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
        
        for category_name, score in sorted_categories:
            # 獲取分類物件以取得英文名稱和說明
            category = test_result.test_project.categories.filter(name=category_name).first()
            english_name = ""
            if category and hasattr(category, 'english_name') and category.english_name.strip():
                english_name = f" ({category.english_name.strip()})"
            
            # 建立主要項目內容
            main_text = f"<b>{category_name}{english_name}：{self._django_round(score)} 分</b>"
            
            # 如果有說明，加入說明文字，增加行距
            if category and category.description:
                description_text = self._clean_html_content(category.description)
                main_text += f"<br/><br/>說明：{description_text}"
            
            # 建立段落樣式
            item_style = ParagraphStyle(
                'ListItemStyle',
                parent=self.content_style,
                fontSize=12,
                fontName=self.chinese_font_name,
                spaceAfter=16,  # 增加每個項目後的間距
                leading=16,
                textColor=black  # 設定文字顏色為黑色
            )
            
            # 加入列表項目
            list_items.append(ListItem(Paragraph(main_text, item_style), leftIndent=0))
        
        # 建立有序列表
        ordered_list = ListFlowable(
            list_items,
            bulletType='1',  # 數字項目符號 (1. 2. 3.)
            bulletFormat='%s.',  # 確保顯示點號 (1. 2. 3.)
            bulletFontName=self.chinese_font_name,  # 使用中文字體
            bulletFontSize=12,  # 字體大小與內容一致
            bulletColor=black,  # 項目符號顏色改為黑色
            leftIndent=0,  # 與標題起始位置一致
            bulletOffsetY=0,
            spaceBefore=0,
            spaceAfter=8
        )
        
        story.append(ordered_list)
        
        story.append(Spacer(1, 0.8 * cm))
        
        # 4. 綜合分析
        story.append(Paragraph("<b>綜合分析</b>", bold_title_style))
        story.append(Spacer(1, 0.4 * cm))  # 標題與內容間距
        
        # 優勢分析：最高分分類
        max_category = max(category_scores.items(), key=lambda x: x[1])
        max_category_name, max_score = max_category
        
        advantage_subtitle_style = ParagraphStyle(
            'AdvantageSubtitle',
            parent=self.subtitle_style,
            fontSize=14,
            fontName=self.chinese_font_bold_name,
            spaceAfter=10
        )
        
        story.append(Paragraph(f"<b>優勢面向：{max_category_name} ({self._django_round(max_score)} 分)</b>", advantage_subtitle_style))
        
        # 獲取優勢分析內容
        advantage_content = self._get_category_advantage_analysis(max_category_name, test_result)
        # 將%改成分
        advantage_content = advantage_content.replace('%', ' 分')
        story.append(Paragraph(advantage_content, analysis_content_style))
        story.append(Spacer(1, 0.5 * cm))

        if mixed_role_categories:
            for category in mixed_role_categories:
                if category.name == max_category_name:
                    continue
                extra_score = category_scores.get(category.name)
                if extra_score is not None:
                    story.append(Paragraph(
                        f"<b>優勢面向：{category.name} ({self._django_round(extra_score)} 分)</b>",
                        advantage_subtitle_style
                    ))
                else:
                    story.append(Paragraph(f"<b>優勢面向：{category.name}</b>", advantage_subtitle_style))
                extra_advantage = self._get_category_advantage_analysis(category.name, test_result)
                extra_advantage = extra_advantage.replace('%', ' 分')
                story.append(Paragraph(extra_advantage, analysis_content_style))
                story.append(Spacer(1, 0.5 * cm))
        
        # 劣勢分析：最低分分類
        min_category = min(category_scores.items(), key=lambda x: x[1])
        min_category_name, min_score = min_category
        
        story.append(Paragraph(f"<b>劣勢面向：{min_category_name} ({self._django_round(min_score)} 分)</b>", advantage_subtitle_style))
        
        # 獲取劣勢分析內容
        disadvantage_content = self._get_category_disadvantage_analysis(min_category_name, test_result)
        # 將%改成分
        disadvantage_content = disadvantage_content.replace('%', ' 分')
        story.append(Paragraph(disadvantage_content, analysis_content_style))
        story.append(Spacer(1, 0.5 * cm))

        story.append(Spacer(1, 0.8 * cm))
        
        # 5. 發展建議 - 必須參數名稱和內容都有值才顯示
        max_category_obj = test_result.test_project.categories.filter(name=max_category_name).first()
        has_development_name = max_category_obj and max_category_obj.development_parameter_name.strip()
        has_development_content = max_category_obj and max_category_obj.development_parameter_content.strip()
        
        # 只有當參數名稱和內容都有設定時才顯示發展建議區塊
        if has_development_name and has_development_content:
            story.append(Spacer(1, 0.8 * cm))
            # 使用參數名稱作為標題
            development_title = max_category_obj.development_parameter_name.strip()
            story.append(Paragraph(f"<b>{development_title}</b>", bold_title_style))
            story.append(Spacer(1, 0.4 * cm))  # 標題與內容間距
            
            # 顯示參數內容
            development_content = self._clean_html_content(max_category_obj.development_parameter_content)
            story.append(Paragraph(development_content, analysis_content_style))
            
            story.append(Spacer(1, 1 * cm))
            
            # 在發展建議區塊的最後設置標記
            self.has_development_suggestions = True
        
        return story
    
    def _create_merged_trait_scores_section(self, test_result):
        """建立合併的關鍵特質分數表（使用與網頁版相同的邏輯）"""
        story = []
        
        if not test_result.raw_data or not test_result.test_project:
            return story
        
        # 使用與網頁版 test_result_views.py 相同的邏輯
        category_traits = {}
        
        # 建立中文名稱映射表
        chinese_name_mapping = {
            '準確嚴謹度': ['注重細節', 'Attention to Detail'],
            '認知彈性': ['認知靈活性', 'Cognitive Flexibility'],
            '適應敏捷力': ['變化敏捷性', 'Change Agility'],
            '卓越驅動力': ['成就動機', 'Achievement Motivation'],
            '自主領導力': ['自我領導力', 'Self-Leadership'],
            '創造性思考': ['創意思考', 'Creative Thinking'],
            '分析性思考': ['分析思考能力', 'Analytical Thinking'],
            '系統性思考': ['系統性思維', 'Systems Thinking'],
            '高效決策力': ['決策能力', 'Decision-Making'],
            '溝通協調力': ['人際溝通', 'Interpersonal Communication'],
            '協商談判力': ['談判技巧', 'Negotiation Skills'],
            '社交智商': ['社會智能', 'Social Intelligence'],
            'AI素養': ['AI Literacy'],
            '自我意識': ['Self-Awareness'],
            '自我批評': ['Self-Criticism'],
            '自我反思': ['Self-Reflection'],
            '社會期望反應': ['Social Desirability'],
            '反饋尋求': ['Feedback Seeking'],
            '洞察力': ['Insight'],
            '差異察覺': ['Difference Awareness']
        }
        
        # 獲取所有分類
        categories = test_result.test_project.categories.prefetch_related('traits').all()
        
        for category in categories:
            traits = category.traits.all()
            category_trait_list = []
            
            for trait in traits:
                # 跳過包含[社會期望值]的特質
                trait_chinese_name = trait.chinese_name or trait.name or ''
                if '[社會期望值]' in trait_chinese_name:
                    continue
                
                trait_score = None
                headsupflag = None
                
                # 方法1: 從 trait_scores 中查找（新爬蟲數據）
                if test_result.raw_data.get('trait_scores'):
                    trait_scores = test_result.raw_data['trait_scores']
                    # 嘗試用各種方式匹配特質名稱
                    for key, value in trait_scores.items():
                        # 如果是字典格式，提取分數
                        if isinstance(value, dict) and 'chinese_name' in value:
                            # 直接匹配
                            if (value.get('chinese_name') == trait.chinese_name or 
                                key == trait.system_name or
                                key == trait.chinese_name or
                                key.lower().replace(' ', '_') == trait.system_name.lower().replace(' ', '_')):
                                trait_score = value.get('score', 0)
                                headsupflag = value.get('headsupflag', 0)
                                break
                            # 使用映射表匹配
                            alternative_names = chinese_name_mapping.get(trait.chinese_name, [])
                            if key in alternative_names or value.get('chinese_name') in alternative_names:
                                trait_score = value.get('score', 0)
                                headsupflag = value.get('headsupflag', 0)
                                break
                        elif key == trait.system_name or key == trait.chinese_name:
                            trait_score = value if isinstance(value, (int, float)) else 0
                            headsupflag = 0
                            break
                        # 檢查映射表
                        elif key in chinese_name_mapping.get(trait.chinese_name, []):
                            trait_score = value if isinstance(value, (int, float)) else value.get('score', 0)
                            headsupflag = value.get('headsupflag', 0) if isinstance(value, dict) else 0
                            break
                
                # 方法2: 從原始數據根目錄查找（舊數據格式）
                if trait_score is None:
                    trait_score = test_result.raw_data.get(trait.system_name, None)
                    if trait_score is None:
                        # 轉換為小寫底線格式
                        system_name_underscore = trait.system_name.lower().replace(' ', '_')
                        trait_score = test_result.raw_data.get(system_name_underscore, 0)
                    headsupflag = 0  # 舊格式預設為 0
                
                if isinstance(trait_score, (int, float)) and trait_score > 0:
                    category_trait_list.append({
                        'name': trait.chinese_name,
                        'score': trait_score,
                        'system_name': trait.system_name,
                        'headsupflag': headsupflag,
                        'description': trait.description if hasattr(trait, 'description') and trait.description else '無特質描述'
                    })
            
            # 計算分類平均分數
            if category_trait_list:
                category_traits[category.name] = category_trait_list
        
        # 使用與網頁版相同的 get_unique_traits 邏輯
        unique_traits = []
        seen_system_names = set()
        
        # 遍歷所有分類的特質
        for category_name, traits in category_traits.items():
            for trait in traits:
                # 使用系統名稱作為唯一識別
                system_name = trait.get('system_name', '')
                if system_name and system_name not in seen_system_names:
                    seen_system_names.add(system_name)
                    
                    # 獲取特質描述並清理HTML
                    description = trait['description']
                    description = self._clean_html_content(description)
                    
                    unique_traits.append({
                        'name': trait['name'],
                        'score': int(trait['score']),  # 不需要小數點
                        'description': description,
                        'headsupflag': trait['headsupflag'],
                        'system_name': trait['system_name']
                    })
        
        # 依照中文名稱排序（字母順序）
        try:
            unique_traits.sort(key=lambda x: x['name'])
        except (ValueError, TypeError):
            pass
        
        if unique_traits:
            # 建立特質表格，包含特質名稱、特質描述、分數
            trait_data = [['關鍵特質', '分數', '特質描述']]  
            
            for trait in unique_traits:
                # ★ 不再截斷描述，完整顯示；改用 CJK 換行，支援自動分行
                description = trait['description']

                desc_paragraph = Paragraph(
                    description,
                    ParagraphStyle(
                        'DescriptionStyle',
                        parent=self.content_style,
                        fontSize=11,                        # 比原先小一階  CHANGED
                        fontName=self.chinese_font_name,
                        leading=15,                         # 行距加大，利於閱讀  CHANGED
                        leftIndent=0,
                        rightIndent=0,
                        wordWrap='CJK',                     # 關鍵：CJK 自動換行  CHANGED
                        splitLongWords=1,                   # 允許切分長字  CHANGED
                        allowWidows=1,
                        allowOrphans=1,
                        alignment=TA_LEFT
                    )
                )

                score_color = HexColor('#FF0000') if trait.get('headsupflag') == 1 else black
                score_paragraph = Paragraph(
                    str(trait['score']),
                    ParagraphStyle(
                        'ScoreStyle',
                        fontSize=12,                        # 原 14 → 12  CHANGED
                        fontName=self.chinese_font_name,
                        textColor=score_color,
                        alignment=TA_CENTER,
                        leading=12,
                        spaceAfter=0,
                        spaceBefore=0
                    )
                )

                # CHANGED: 資料順序也調整為「名稱 | 分數 | 描述」
                trait_data.append([
                    trait['name'],
                    score_paragraph,
                    desc_paragraph
                ])

            # 欄寬：給分數較窄、描述較寬（左右留白已縮小，這裡也讓描述更佔寬）
            table = Table(trait_data, colWidths=[3*cm, 2*cm, self.content_width - (3*cm + 2*cm)], repeatRows=1)  # CHANGED

            table.setStyle(TableStyle([
                # 表頭
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#152233')),  # 表頭背景
                ('TEXTCOLOR', (0, 0), (-1, 0), white),               # 表頭文字白色
                ('TEXTCOLOR', (0, 1), (-1, -1), black),              # 內容文字黑色
                ('FONTNAME', (0, 0), (-1, 0), self.chinese_font_bold_name),
                ('FONTNAME', (0, 1), (-1, -1), self.chinese_font_name),
                ('FONTSIZE', (0, 0), (-1, 0), 12),                  # 表頭字體大小14
                ('FONTSIZE', (0, 1), (0, -1), 12),                  # 關鍵特質欄字體大小14
                ('FONTSIZE', (1, 1), (1, -1), 10),                  # 特質描述欄字體大小12
                ('FONTSIZE', (2, 1), (2, -1), 12),                  # 分數欄字體大小14
                ('BOTTOMPADDING', (0, 0), (-1, 0), 14),            # 表頭底部padding
                ('TOPPADDING', (0, 0), (-1, 0), 10),               # 表頭頂部padding
                # 分別設定各欄位的上下間距（可個別調整）
                ('BOTTOMPADDING', (0, 1), (0, -1), 15),            # 第0欄（關鍵特質）底部padding
                ('TOPPADDING', (0, 1), (0, -1), 9),               # 第0欄（關鍵特質）頂部padding
                ('BOTTOMPADDING', (1, 1), (1, -1), 12),            # 第1欄（特質描述）底部padding
                ('TOPPADDING', (1, 1), (1, -1), 12),               # 第1欄（特質描述）頂部padding  
                ('BOTTOMPADDING', (2, 1), (2, -1), 10),            # 第2欄（分數）底部padding
                ('TOPPADDING', (2, 1), (2, -1), 8),               # 第2欄（分數）頂部padding
                ('LEFTPADDING', (0, 0), (-1, -1), 8),             # 增加左內距
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),            # 增加右內距
                ('GRID', (0, 0), (-1, -1), 1, HexColor('#bdc3c7')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#f8f9fa')]),
                # 分別設定對齊方式，確保表頭也能正確置中
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),               # 表頭水平置中
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),               # 關鍵特質欄置中
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),                 # 特質描述欄左對齊
                ('ALIGN', (2, 1), (2, -1), 'CENTER'),               # 分數欄位置中
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),              # 表頭垂直置中
                ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),             # 內容垂直置中
            ]))
            
            story.append(table)
        
        return story
    
    def _create_detailed_trait_scores_section(self, test_result, category_scores):
        """建立特質詳細分數表區塊（合併所有特質，不分分類）"""
        story = []
        
        if not test_result.raw_data or not test_result.test_project:
            return story
        
        # 定義較大的標題樣式
        larger_subtitle_style = ParagraphStyle(
            'LargerSubtitle',
            parent=self.subtitle_style,
            fontSize=16,
            fontName=self.chinese_font_bold_name
        )
        
        story.append(Paragraph("特質詳細分析", larger_subtitle_style))
        story.append(Spacer(1, 0.5 * cm))
        
        # 收集所有特質資料
        all_traits_data = []
        
        # 獲取所有分類
        categories = test_result.test_project.categories.all()
        
        for category in categories:
            # 取得該分類的特質
            traits = category.traits.all()
            for trait in traits:
                trait_score = None
                
                # 方法1: 從 trait_scores 中查找（新的爬蟲數據結構）
                if test_result.raw_data.get('trait_scores'):
                    trait_scores_data = test_result.raw_data['trait_scores']
                    for key, value in trait_scores_data.items():
                        if isinstance(value, dict) and 'chinese_name' in value:
                            if (value.get('chinese_name') == trait.chinese_name or 
                                key == trait.system_name or
                                key.lower().replace(' ', '_') == trait.system_name.lower().replace(' ', '_')):
                                trait_score = value.get('score', 0)
                                break
                        elif key == trait.system_name:
                            trait_score = value if isinstance(value, (int, float)) else 0
                            break
                
                # 方法2: 從原始數據根目錄查找（原始方式）
                if trait_score is None:
                    trait_score = test_result.raw_data.get(trait.system_name, None)
                    if trait_score is None:
                        system_name_underscore = trait.system_name.lower().replace(' ', '_')
                        trait_score = test_result.raw_data.get(system_name_underscore, 0)
                
                if isinstance(trait_score, (int, float)) and trait_score > 0:
                    # 獲取特質描述並清理HTML
                    description = trait.description if hasattr(trait, 'description') and trait.description else '無特質描述'
                    
                    # 清理HTML內容並保持換行格式
                    description = self._clean_html_content(description)
                    
                    # 智能截斷：考慮換行標籤，避免破壞格式
                    if len(description) > 250:  # 增加長度限制以容納更多內容
                        import re
                        # 尋找合適的截斷點（在換行標籤附近）
                        br_positions = [m.start() for m in re.finditer(r'<br/?>', description)]
                        suitable_cutoff = None
                        
                        for pos in br_positions:
                            if pos <= 220:  # 在合理範圍內的換行位置
                                suitable_cutoff = pos
                        
                        if suitable_cutoff:
                            description = description[:suitable_cutoff] + "..."
                        else:
                            # 如果沒有合適的換行位置，按字符截斷
                            description = description[:220] + "..."
                    
                    all_traits_data.append({
                        'name': trait.chinese_name or trait.name,
                        'score': trait_score,
                        'description': description
                    })
        
        # 按分數排序（由高到低）
        all_traits_data.sort(key=lambda x: x['score'], reverse=True)
        
        if all_traits_data:
            # 建立合併的特質表格，包含特質名稱、分數和描述
            trait_data = [['特質名稱', '分數', '特質描述']]
            
            for trait in all_traits_data:
                # 將描述包裝為Paragraph以支援自動換行
                desc_paragraph = Paragraph(trait['description'], ParagraphStyle(
                    'DescriptionStyle',
                    parent=self.content_style,
                    fontSize=10,  # 增大字體
                    fontName=self.chinese_font_name,
                    leading=14,   # 增大行距
                    leftIndent=0,
                    rightIndent=0,
                    wordWrap='LTR',
                    alignment=0  # 0=LEFT 靠左對齊
                ))
                
                trait_data.append([
                    trait['name'],
                    f"{trait['score']:.1f}",
                    desc_paragraph
                ])
            
            # 建立表格，調整欄寬：特質名稱縮小，特質描述放大
            table = Table(trait_data, colWidths=[3*cm, 1.5*cm, 9*cm], repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#152233')),  # 表頭背景
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),   # 表頭標題置中對齊
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),     # 特質名稱左對齊
                ('ALIGN', (1, 1), (1, -1), 'CENTER'),   # 分數置中對齊
                ('ALIGN', (2, 1), (2, -1), 'LEFT'),   # 描述置中對齊
                ('FONTNAME', (0, 0), (-1, 0), self.chinese_font_bold_name),
                ('FONTNAME', (0, 1), (-1, -1), self.chinese_font_name),  # 所有內容都使用中文字體
                ('FONTSIZE', (0, 0), (-1, 0), 14),      # 表頭字體大小14
                ('FONTSIZE', (0, 1), (-1, -1), 10),     # 增大內容字體
                ('BOTTOMPADDING', (0, 0), (-1, 0), 14), # 表頭底部padding
                ('TOPPADDING', (0, 0), (-1, 0), 14),    # 表頭頂部padding
                ('BOTTOMPADDING', (0, 1), (-1, -1), 10), # 內容底部padding
                ('TOPPADDING', (0, 1), (-1, -1), 10),    # 內容頂部padding
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, HexColor('#bdc3c7')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#f8f9fa')]),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),  # 表頭垂直置中
                ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'), # 內容垂直置中
            ]))
            
            story.append(table)
            story.append(Spacer(1, 0.5 * cm))
        
        return story
    
    def _generate_radar_chart(self, category_scores):
        """生成雷達圖並返回檔案路徑"""
        if not MATPLOTLIB_AVAILABLE or not category_scores:
            return None
        
        try:
            # 確保使用 Agg backend
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import matplotlib.font_manager as fm
            
            import tempfile
            import numpy as np
            import os

            # 嘗試找到並設定中文字體
            chinese_font_path = None
            possible_fonts: list[str] = []

            # 專案內自帶字體（static/fonts）
            try:
                static_dirs = list(getattr(settings, 'STATICFILES_DIRS', []))
                static_root = getattr(settings, 'STATIC_ROOT', None)
                if static_root:
                    static_dirs.append(static_root)

                for static_dir in static_dirs:
                    fonts_dir = os.path.join(static_dir, 'fonts')
                    if not os.path.isdir(fonts_dir):
                        continue
                    for filename in sorted(os.listdir(fonts_dir)):
                        if filename.lower().endswith((".ttf", ".otf", ".ttc")):
                            possible_fonts.append(os.path.join(fonts_dir, filename))
            except Exception as static_font_exc:
                print(f"⚠️  載入專案字體失敗: {static_font_exc}")

            # 系統常見字體路徑（依優先順序）
            possible_fonts.extend([
                # Debian/Ubuntu + fonts-noto-cjk
                "/usr/share/fonts/opentype/noto/NotoSansTC-Regular.otf",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJKtc-Regular.otf",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                # WenQuanYi（fonts-wqy-microhei）
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
                # Windows
                "C:/Windows/Fonts/msjh.ttc",
                "C:/Windows/Fonts/msyh.ttc",
                # macOS
                "/Library/Fonts/Microsoft JhengHei.ttf",
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/STHeiti Light.ttc",
                "/Library/Fonts/Arial Unicode MS.ttf",
            ])

            for font_path in possible_fonts:
                if os.path.exists(font_path):
                    chinese_font_path = font_path
                    try:
                        fm.fontManager.addfont(font_path)
                    except Exception as add_font_exc:
                        print(f"⚠️  無法預先註冊字體 {font_path}: {add_font_exc}")
                    break

            fallback_families = [
                'Noto Sans CJK TC', 'Noto Sans TC', 'Noto Sans CJK',
                'WenQuanYi Micro Hei', 'WenQuanYi Zen Hei',
                'Microsoft JhengHei', 'PingFang SC', 'STHeiti Light',
                'SimHei', 'Arial Unicode MS'
            ]

            if chinese_font_path:
                font_prop = fm.FontProperties(fname=chinese_font_path)
                font_name = font_prop.get_name() or 'Noto Sans CJK TC'
                plt.rcParams['font.family'] = [font_name]
                plt.rcParams['font.sans-serif'] = [font_name, *fallback_families]
            else:
                plt.rcParams['font.family'] = ['sans-serif']
                plt.rcParams['font.sans-serif'] = fallback_families

            plt.rcParams['axes.unicode_minus'] = False
                                                  
            # 準備數據 - 使用與網頁版相同的標籤格式
            categories = list(category_scores.keys())
            values = list(category_scores.values())

            if not categories or not values:
                return None

            # 顯示標籤：分類名稱 + (四捨五入分數)
            display_categories = [f"{cat}({self._django_round(val)})" for cat, val in zip(categories, values)]

            # 雷達圖
            N = len(categories)
            angles = [n / float(N) * 2 * np.pi for n in range(N)]
            angles += angles[:1]  # 完成圓形
            
            # 創建極座標圖，使用正方形尺寸並設定適當的邊距
            fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
            ax.set_aspect('equal', 'box')  # 關鍵：正圓

            # REMOVED: 會影響外圈文字被裁切
            # plt.tight_layout(pad=2.0)

            # 曲線
            values_plot = values + values[:1]
            ax.plot(angles, values_plot, 'o-', linewidth=2, color='#4285f4', markersize=8)
            ax.fill(angles, values_plot, alpha=0.25, color='#4285f4')

            # CHANGED: 不直接用 set_xticklabels，避免被裁切
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels([])  # NEW: 先清空，改用手動文字

            # 軸範圍與刻度
            ax.set_ylim(0, 100)
            ax.set_yticks([20, 40, 60, 80, 100])
            ax.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=11)
            ax.grid(True)
            
            # 設定樣式
            ax.set_theta_offset(np.pi / 2)  # 從頂部開始
            ax.set_theta_direction(-1)  # 順時針方向
            
            # NEW: 手動繪製外圈標籤，字體更大且不被裁切
            label_fontsize = 20   # 需求：更大
            r_label = 106         # 放在半徑 100 外，避免被扇形/邊界吃到

            for ang, label in zip(angles[:-1], display_categories):
                # 根據角度決定水平對齊，避免右括弧/分數被切掉
                a = (ang + 2*np.pi) % (2*np.pi)
                if 0 < a < np.pi:          # 右半邊
                    ha = 'left'
                elif np.pi < a < 2*np.pi:  # 左半邊
                    ha = 'right'
                else:
                    ha = 'center'

                ax.text(
                    ang, r_label, label,
                    ha=ha, va='center',
                    fontsize=label_fontsize, fontweight='bold',
                    clip_on=False  # 關鍵：不要讓文字被軸範圍裁切
                )

            # NEW: 給外圈文字留更寬鬆的邊界
            fig.subplots_adjust(left=0.08, right=0.92, top=0.92, bottom=0.10)

            # 存檔
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            temp_file.close()

            # CHANGED: 使用 tight + padding，確保外圈標籤不被圖檔邊界裁掉
            plt.savefig(
                temp_file.name,
                dpi=150,
                bbox_inches='tight',
                pad_inches=0.5,
                facecolor='white',
                edgecolor='none'
            )
            plt.close()
            
            # 檢查檔案是否真的被創建
            if os.path.exists(temp_file.name) and os.path.getsize(temp_file.name) > 0:
                return temp_file.name
            else:
                return None

        except Exception:
            # 靜默處理錯誤，避免影響PDF生成
            try:
                plt.close()
            except:
                pass
            return None

    
    def _calculate_category_scores(self, test_result):
        """計算分類分數與角色指標"""
        if not test_result.raw_data or not test_result.test_project:
            return {}
        
        project = test_result.test_project
        use_weighted = getattr(project, 'radar_mode', 'role') == 'score'
        show_mixed_role = getattr(project, 'show_mixed_role', False)

        categories = project.categories.prefetch_related('traits', 'category_traits__trait').all()
        category_scores = {}
        self._latest_role_based_metrics = None

        # 中文名稱映射表 (用於處理不一致的中文翻譯)
        chinese_name_mapping = {
            '準確嚴謹度': ['注重細節', 'Attention to Detail'],
            '認知彈性': ['認知靈活性', 'Cognitive Flexibility'],
            '適應敏捷力': ['變化敏捷性', 'Change Agility'],
            '卓越驅動力': ['成就動機', 'Achievement Motivation'],
            '自主領導力': ['自我領導力', 'Self-Leadership'],
            '創造性思考': ['創意思考', 'Creative Thinking'],
            '分析性思考': ['分析思考能力', 'Analytical Thinking'],
            '系統性思考': ['系統性思維', 'Systems Thinking'],
            '高效決策力': ['決策能力', 'Decision-Making'],
            '溝通協調力': ['人際溝通', 'Interpersonal Communication'],
            '協商談判力': ['談判技巧', 'Negotiation Skills'],
            '社交智商': ['社會智能', 'Social Intelligence'],
        }

        trait_scores_cache: Dict[int, float] = {}

        def get_trait_score(trait):
            cache_key = trait.id
            if cache_key in trait_scores_cache:
                return trait_scores_cache[cache_key]

            trait_score = None

            # 方法1: 從 trait_scores 中查找（新的爬蟲數據結構）
            trait_scores_data = test_result.raw_data.get('trait_scores') if isinstance(test_result.raw_data, dict) else None
            if isinstance(trait_scores_data, dict):
                for key, value in trait_scores_data.items():
                    value_dict = value if isinstance(value, dict) else None
                    candidate = (
                        value_dict.get('score') if value_dict and isinstance(value_dict.get('score'), (int, float))
                        else value if isinstance(value, (int, float)) else None
                    )
                    if candidate is None:
                        continue

                    key_normalized = key.lower().replace(' ', '_')
                    alternatives = chinese_name_mapping.get(trait.chinese_name or '', [])
                    chinese_value = value_dict.get('chinese_name') if value_dict else None

                    if (
                        key == trait.system_name
                        or key == trait.chinese_name
                        or key_normalized == (trait.system_name or '').lower().replace(' ', '_')
                        or chinese_value == trait.chinese_name
                        or key in alternatives
                        or (chinese_value and chinese_value in alternatives)
                    ):
                        trait_score = float(candidate)
                        break

            # 方法2: 從原始數據根目錄查找（原始方式）
            if trait_score is None and isinstance(test_result.raw_data, dict):
                direct_keys = [
                    trait.system_name,
                    trait.chinese_name,
                    (trait.system_name or '').lower().replace(' ', '_'),
                ]
                for alias in chinese_name_mapping.get(trait.chinese_name or '', []):
                    direct_keys.append(alias)

                for key in direct_keys:
                    if not key:
                        continue
                    value = test_result.raw_data.get(key)
                    if isinstance(value, (int, float)):
                        trait_score = float(value)
                        break
                    if isinstance(value, dict) and isinstance(value.get('score'), (int, float)):
                        trait_score = float(value['score'])
                        break

            if trait_score is not None:
                trait_scores_cache[cache_key] = trait_score
            return trait_score

        role_inputs: Dict[str, Dict[str, float]] = {}

        for category in categories:
            trait_score_map: Dict[int, float] = {}
            for trait in category.traits.all():
                score = get_trait_score(trait)
                if score is not None:
                    trait_score_map[trait.id] = score

            if not trait_score_map:
                continue

            raw_score = Decimal('0')
            weight_sum = Decimal('0')
            for relation in category.category_traits.select_related('trait').all():
                trait = relation.trait
                if not trait or trait.id not in trait_score_map:
                    continue
                try:
                    weight = Decimal(str(relation.weight))
                except (InvalidOperation, TypeError, ValueError):
                    continue
                score_value = Decimal(str(trait_score_map[trait.id]))
                raw_score += score_value * weight
                weight_sum += weight

            max_score = weight_sum * Decimal('100')
            role_index = Decimal('0')
            if max_score != 0:
                role_index = (raw_score / max_score) * Decimal('100')

            role_inputs[category.name] = {
                'raw_score': float(raw_score),
                'max_score': float(max_score),
                'role_index': float(role_index),
                'weight_sum': float(weight_sum),
            }

        if use_weighted:
            category_scores = {
                name: max(0.0, min(100.0, data.get('role_index', 0.0)))
                for name, data in role_inputs.items()
            }
            self._latest_role_based_metrics = None
        else:
            role_based_metrics = compute_role_based_scores(
                role_inputs,
                show_mixed_role=show_mixed_role,
            )
            category_scores = role_based_metrics["contrast_index"]
            self._latest_role_based_metrics = role_based_metrics

        return category_scores
    
    def _get_category_advantage_analysis(self, category_name, test_result):
        """從資料庫獲取分類優勢分析內容"""
        try:
            category = test_result.test_project.categories.filter(name=category_name).first()
            if category and category.advantage_analysis:
                # 清理HTML標籤和特殊字符
                content = category.advantage_analysis
                content = self._clean_html_content(content)
                return content
        except Exception as e:
            print(f"獲取優勢分析時發生錯誤: {e}")
        
        # 如果資料庫中沒有內容，使用預設內容
        return f'在{category_name}方面表現優秀，具備相關領域的突出能力和特質。'
    
    def _get_category_disadvantage_analysis(self, category_name, test_result):
        """從資料庫獲取分類劣勢分析內容"""
        try:
            category = test_result.test_project.categories.filter(name=category_name).first()
            if category and category.disadvantage_analysis:
                # 清理HTML標籤和特殊字符
                content = category.disadvantage_analysis
                content = self._clean_html_content(content)
                return content
        except Exception as e:
            print(f"獲取劣勢分析時發生錯誤: {e}")
        
        # 如果資料庫中沒有內容，使用預設內容
        return f'在{category_name}方面有改善空間，建議加強相關技能的培養和發展。'
    
    def _clean_html_content(self, content):
        """清理HTML內容，保留基本列表結構和換行符號並轉換為ReportLab格式"""
        import re
        
        if not content:
            return ""
        
        # 先處理換行標籤 - 轉換為ReportLab的換行格式
        content = re.sub(r'<br\s*/?>', '<br/>', content, flags=re.IGNORECASE)
        content = re.sub(r'<p\s*>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'</p>', '<br/>', content, flags=re.IGNORECASE)
        content = re.sub(r'<div\s*>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'</div>', '<br/>', content, flags=re.IGNORECASE)
        
        # 處理混合的有序列表和無序列表結構
        # 按照原始順序處理所有列表元素
        
        # 先找到所有列表區塊（有序和無序）的位置
        list_pattern = r'(<ol[^>]*>.*?</ol>|<ul[^>]*>.*?</ul>)'
        list_matches = re.findall(list_pattern, content, re.DOTALL)
        
        new_content = ""
        
        for list_block in list_matches:
            if list_block.startswith('<ol'):
                # 有序列表 - 使用編號
                li_pattern = r'<li[^>]*>(.*?)</li>'
                li_items = re.findall(li_pattern, list_block, re.DOTALL)
                for i, item_content in enumerate(li_items, 1):
                    # 清理項目內容，但保留換行
                    clean_item = re.sub(r'<(?!br/?>)[^>]+>', '', item_content)
                    clean_item = clean_item.strip()
                    if clean_item:
                        new_content += f"{i}. {clean_item}<br/><br/>"
            
            elif list_block.startswith('<ul'):
                # 無序列表 - 使用項目符號
                li_pattern = r'<li[^>]*>(.*?)</li>'
                li_items = re.findall(li_pattern, list_block, re.DOTALL)
                for item_content in li_items:
                    # 清理項目內容，但保留換行
                    clean_item = re.sub(r'<(?!br/?>)[^>]+>', '', item_content)
                    clean_item = clean_item.strip()
                    if clean_item:
                        new_content += f"• {clean_item}<br/><br/>"
        
        # 如果有混合內容，則使用處理後的內容
        if new_content:
            content = new_content
        else:
            # 沒有列表結構，清理其他HTML標籤但保留<br/>
            content = re.sub(r'<(?!br/?>)[^>]+>', '', content)
        
        # 解碼HTML實體
        content = content.replace('&mdash;', '—')
        content = content.replace('&nbsp;', ' ')
        content = content.replace('&amp;', '&')
        content = content.replace('&lt;', '<')
        content = content.replace('&gt;', '>')
        content = content.replace('&quot;', '"')
        
        # 處理普通的換行符號 - 轉換為<br/>標籤
        content = re.sub(r'\r?\n', '<br/>', content)
        
        # 優化中英文混合文字的換行 - 在合適的位置插入空格幫助換行
        # 在中英文切換點加入適當的空格，幫助ReportLab更好地處理換行
        content = re.sub(r'([一-龯])([A-Za-z])', r'\1 \2', content)  # 中文後接英文時加空格
        content = re.sub(r'([A-Za-z])([一-龯])', r'\1 \2', content)  # 英文後接中文時加空格
        # 只在句號和分號後加空格，避免逗號造成不必要的換行
        content = re.sub(r'([。；])([A-Za-z一-龯])', r'\1 \2', content)  # 只在句號、分號後加空格
        
        # 清理多餘的<br/>標籤，但保留合理的間距
        content = re.sub(r'(<br/>\s*){3,}', '<br/><br/>', content)  # 最多保留兩個換行
        content = re.sub(r'^\s*<br/>', '', content)  # 移除開頭的換行
        content = re.sub(r'<br/>\s*$', '', content)  # 移除結尾的換行
        
        # 移除多餘的空白字符
        content = re.sub(r' +', ' ', content)  # 合併多個空格
        content = content.strip()
        
        return content
    
    def _create_basic_info_section(self, test_result):
        """建立基本資訊區塊"""
        story = []
        
        story.append(Paragraph("基本資訊", self.subtitle_style))
        
        # 建立基本資訊表格
        basic_data = [
            ['受測者姓名', test_result.test_invitation.invitee.name],
            ['電子信箱', test_result.test_invitation.invitee.email],
            ['測驗項目', test_result.test_project.name],
            ['邀請時間', test_result.test_invitation.invited_at.strftime('%Y-%m-%d %H:%M') if test_result.test_invitation.invited_at else 'N/A'],
            ['開始時間', test_result.test_invitation.started_at.strftime('%Y-%m-%d %H:%M') if test_result.test_invitation.started_at else 'N/A'],
            ['完成時間', test_result.test_invitation.completed_at.strftime('%Y-%m-%d %H:%M') if test_result.test_invitation.completed_at else 'N/A'],
            ['結果取得時間', test_result.crawled_at.strftime('%Y-%m-%d %H:%M') if test_result.crawled_at else 'N/A'],
            ['測驗狀態', self._get_status_display(test_result.crawl_status)],
        ]
        
        # 添加公司和職位資訊（如果有）
        if hasattr(test_result.test_invitation.invitee, 'company') and test_result.test_invitation.invitee.company:
            basic_data.append(['公司', test_result.test_invitation.invitee.company])
        
        if hasattr(test_result.test_invitation.invitee, 'position') and test_result.test_invitation.invitee.position:
            basic_data.append(['職位', test_result.test_invitation.invitee.position])
        
        # 建立表格
        table = Table(basic_data, colWidths=[4*cm, 10*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), HexColor('#152233')),  # 表頭背景
            ('TEXTCOLOR', (0, 0), (0, -1), white),  # 白色文字
            ('TEXTCOLOR', (1, 0), (1, -1), black),  # 內容文字顏色改為黑色
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), self.chinese_font_bold_name),  # 使用中文粗體字體
            ('FONTNAME', (1, 0), (1, -1), self.chinese_font_name),  # 使用中文字體
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#bdc3c7')),
            ('ROWBACKGROUNDS', (1, 0), (1, -1), [white, HexColor('#f8f9fa')]),  # 交替行背景
        ]))
        
        story.append(table)
        story.append(Spacer(1, 20))
        
        return story
    
    def _create_test_results_section(self, test_result):
        """建立測驗結果區塊"""
        story = []
        
        story.append(Paragraph("測驗結果", self.subtitle_style))
        
        # 評分結果
        if test_result.score_value:
            score_text = f"<b>{test_result.test_project.score_field_chinese or '評分結果'}:</b> {test_result.score_value}"
            if test_result.test_project.score_unit:
                score_text += f" {test_result.test_project.score_unit}"
            story.append(Paragraph(score_text, self.content_style))
        
        # 預測結果
        if test_result.prediction_value:
            prediction_text = f"<b>{test_result.test_project.prediction_field_chinese or '預測結果'}:</b> {test_result.prediction_value}"
            story.append(Paragraph(prediction_text, self.content_style))
        
        # 主要指標
        if test_result.raw_data and test_result.raw_data.get('vehicles'):
            vehicles_text = f"<b>Vehicles:</b> {test_result.raw_data['vehicles']}"
            if test_result.raw_data.get('vehicles_percentage'):
                vehicles_text += f" ({test_result.raw_data['vehicles_percentage']}%)"
            story.append(Paragraph(vehicles_text, self.content_style))
        
        if test_result.raw_data and test_result.raw_data.get('composite_index'):
            composite_text = f"<b>Composite Index:</b> {test_result.raw_data['composite_index']}"
            story.append(Paragraph(composite_text, self.content_style))
        
        story.append(Spacer(1, 15))
        
        return story
    
    def _create_category_analysis_section(self, test_result):
        """建立分類分析區塊"""
        story = []
        
        if not test_result.raw_data or not test_result.test_project:
            return story
        
        story.append(Paragraph("分類分析", self.subtitle_style))
        
        # 取得分類資料
        categories = test_result.test_project.categories.prefetch_related('traits').all()
        
        if categories:
            category_data = [['分類名稱', '平均分數', '等級']]
            
            for category in categories:
                traits = category.traits.all()
                if traits:
                    trait_scores = []
                    for trait in traits:
                        trait_score = None
                        
                        # 方法1: 從 trait_scores 中查找（新的爬蟲數據結構）
                        if test_result.raw_data.get('trait_scores'):
                            trait_scores_data = test_result.raw_data['trait_scores']
                            for key, value in trait_scores_data.items():
                                if isinstance(value, dict) and 'chinese_name' in value:
                                    if (value.get('chinese_name') == trait.chinese_name or 
                                        key == trait.system_name or
                                        key.lower().replace(' ', '_') == trait.system_name.lower().replace(' ', '_')):
                                        trait_score = value.get('score', 0)
                                        break
                                elif key == trait.system_name:
                                    trait_score = value if isinstance(value, (int, float)) else 0
                                    break
                        
                        # 方法2: 從原始數據根目錄查找（原始方式）
                        if trait_score is None:
                            trait_score = test_result.raw_data.get(trait.system_name, None)
                            if trait_score is None:
                                system_name_underscore = trait.system_name.lower().replace(' ', '_')
                                trait_score = test_result.raw_data.get(system_name_underscore, 0)
                        
                        if isinstance(trait_score, (int, float)) and trait_score > 0:
                            trait_scores.append(trait_score)
                    
                    if trait_scores:
                        avg_score = sum(trait_scores) / len(trait_scores)
                        level = self._get_performance_level(avg_score)
                        category_data.append([
                            category.name,
                            f"{avg_score:.1f}",
                            level
                        ])
            
            if len(category_data) > 1:  # 有資料才建立表格
                table = Table(category_data, colWidths=[6*cm, 3*cm, 3*cm])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), HexColor('#152233')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), white),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),   # 表頭置中
                    ('ALIGN', (0, 1), (-1, -1), 'CENTER'), # 內容置中
                    ('FONTNAME', (0, 0), (-1, 0), self.chinese_font_bold_name),
                    ('FONTNAME', (0, 1), (-1, -1), self.chinese_font_name),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),     # 表頭字體大小14
                    ('FONTSIZE', (0, 1), (-1, -1), 10),    # 內容字體大小10
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 1, HexColor('#bdc3c7')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#f8f9fa')]),
                ]))
                
                story.append(table)
        
        story.append(Spacer(1, 15))
        
        return story
    
    def _create_trait_analysis_section(self, test_result):
        """建立特質分析區塊"""
        story = []
        
        if not test_result.raw_data or not test_result.test_project:
            return story
        
        story.append(Paragraph("特質分析", self.subtitle_style))
        
        # 取得特質資料
        categories = test_result.test_project.categories.prefetch_related('traits').all()
        
        for category in categories:
            traits = category.traits.all()
            if traits:
                story.append(Paragraph(f"<b>{category.name}</b>", self.content_style))
                
                trait_data = [['特質名稱', '分數', '等級']]
                
                for trait in traits:
                    trait_score = None
                    
                    # 方法1: 從 trait_scores 中查找（新的爬蟲數據結構）
                    if test_result.raw_data.get('trait_scores'):
                        trait_scores_data = test_result.raw_data['trait_scores']
                        for key, value in trait_scores_data.items():
                            if isinstance(value, dict) and 'chinese_name' in value:
                                if (value.get('chinese_name') == trait.chinese_name or 
                                    key == trait.system_name or
                                    key.lower().replace(' ', '_') == trait.system_name.lower().replace(' ', '_')):
                                    trait_score = value.get('score', 0)
                                    break
                            elif key == trait.system_name:
                                trait_score = value if isinstance(value, (int, float)) else 0
                                break
                    
                    # 方法2: 從原始數據根目錄查找（原始方式）
                    if trait_score is None:
                        trait_score = test_result.raw_data.get(trait.system_name, None)
                        if trait_score is None:
                            system_name_underscore = trait.system_name.lower().replace(' ', '_')
                            trait_score = test_result.raw_data.get(system_name_underscore, 0)
                    
                    if isinstance(trait_score, (int, float)) and trait_score > 0:
                        level = self._get_performance_level(trait_score)
                        trait_data.append([
                            trait.chinese_name,
                            f"{trait_score:.1f}",
                            level
                        ])
                
                if len(trait_data) > 1:  # 有資料才建立表格
                    table = Table(trait_data, colWidths=[6*cm, 3*cm, 3*cm])
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#152233')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), white),
                        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),   # 表頭置中
                        ('ALIGN', (0, 1), (-1, -1), 'CENTER'), # 內容置中
                        ('FONTNAME', (0, 0), (-1, 0), self.chinese_font_bold_name),
                        ('FONTNAME', (0, 1), (-1, -1), self.chinese_font_name),
                        ('FONTSIZE', (0, 0), (-1, 0), 14),     # 表頭字體大小14
                        ('FONTSIZE', (0, 1), (-1, -1), 9),     # 內容字體大小9
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                        ('TOPPADDING', (0, 0), (-1, -1), 6),
                        ('GRID', (0, 0), (-1, -1), 1, HexColor('#bdc3c7')),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#f8f9fa')]),
                    ]))
                    
                    story.append(table)
                    story.append(Spacer(1, 10))
        
        story.append(Spacer(1, 15))
        
        return story
    
    def _create_data_summary_section(self, test_result):
        """建立數據摘要區塊"""
        story = []
        
        story.append(Paragraph("數據摘要", self.subtitle_style))
        
        # 測驗時間統計
        if test_result.test_invitation.started_at and test_result.test_invitation.completed_at:
            duration = test_result.test_invitation.completed_at - test_result.test_invitation.started_at
            duration_text = f"<b>測驗耗時:</b> {duration}"
            story.append(Paragraph(duration_text, self.content_style))
        
        # 數據項目統計
        if test_result.raw_data:
            data_count = len([v for v in test_result.raw_data.values() if isinstance(v, (int, float))])
            story.append(Paragraph(f"<b>數據項目數量:</b> {data_count}", self.content_style))
        
        # 品質指標
        if test_result.raw_data and test_result.raw_data.get('vehicles_percentage'):
            quality_text = f"<b>結果品質:</b> {test_result.raw_data['vehicles_percentage']}%"
            story.append(Paragraph(quality_text, self.content_style))
        
        # 生成資訊
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"<b>報告生成時間:</b> {timezone.now().strftime('%Y年%m月%d日 %H:%M:%S')}", self.content_style))
        story.append(Paragraph("<b>報告版本:</b> v1.0", self.content_style))
        
        return story
    
    def _get_status_display(self, status):
        """取得狀態顯示文字"""
        status_map = {
            'pending': '待處理',
            'crawling': '處理中',
            'completed': '已完成',
            'failed': '失敗'
        }
        return status_map.get(status, status)
    
    def _get_performance_level(self, score):
        """根據分數取得表現等級"""
        if score >= 90:
            return '優秀'
        elif score >= 80:
            return '良好'
        elif score >= 70:
            return '一般'
        elif score >= 60:
            return '待改善'
        else:
            return '需加強'


# 便利函數
def generate_test_result_pdf(test_result, output_path=None):
    """
    生成測驗結果 PDF 報告的便利函數
    
    Args:
        test_result: TestProjectResult 物件
        output_path: 輸出路徑，如果為 None 則返回 HttpResponse
    
    Returns:
        HttpResponse 或 檔案路徑
    """
    generator = PDFReportGenerator()
    return generator.generate_test_result_report(test_result, output_path)
