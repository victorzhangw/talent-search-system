# utils/pdf_report_generator.py
"""
PDF 報告生成器
提供測驗結果詳情的 PDF 報告生成功能
"""

import os
import io
from datetime import datetime
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.template import Template, Context

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
        self.left_margin = 2.5 * cm
        self.right_margin = 2.5 * cm
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
    
    def _register_chinese_fonts(self):
        """註冊中文字體"""
        try:
            # 嘗試註冊系統中文字體
            import platform
            system = platform.system()
            
            if system == "Darwin":  # macOS
                # 嘗試註冊 macOS 系統字體 - 使用微軟正黑體為優先
                chinese_fonts = [
                    "/Library/Fonts/Microsoft JhengHei.ttf",  # 微軟正黑體（優先）
                    "/System/Library/Fonts/PingFang.ttc",  # PingFang SC
                    "/System/Library/Fonts/STHeiti Light.ttc",  # 黑體
                    "/Library/Fonts/Arial Unicode MS.ttf",  # Arial Unicode MS
                    "/System/Library/Fonts/Helvetica.ttc",  # Helvetica (後備)
                ]
            elif system == "Windows":
                # Windows 系統字體 - 使用微軟正黑體為優先
                chinese_fonts = [
                    "C:/Windows/Fonts/msjh.ttc",  # 微軟正黑體（優先）
                    "C:/Windows/Fonts/msyh.ttc",  # 微軟雅黑
                    "C:/Windows/Fonts/simhei.ttf",  # 黑體
                    "C:/Windows/Fonts/simsun.ttc",  # 新宋體
                ]
            else:  # Linux
                chinese_fonts = [
                    "/usr/share/fonts/truetype/droid/DroidSansFallback.ttf",
                    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                ]
            
            # 嘗試註冊字體
            self.chinese_font_name = None
            self.chinese_font_bold_name = None
            
            for font_path in chinese_fonts:
                try:
                    if os.path.exists(font_path):
                        if self.chinese_font_name is None:
                            pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                            self.chinese_font_name = 'ChineseFont'
                            print(f"成功註冊中文字體: {font_path}")
                            
                            # 嘗試註冊粗體版本
                            try:
                                pdfmetrics.registerFont(TTFont('ChineseFontBold', font_path))
                                self.chinese_font_bold_name = 'ChineseFontBold'
                            except:
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
        # 標題樣式
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=HexColor('#34495D'),
            fontName=self.chinese_font_bold_name
        )
        
        # 副標題樣式
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            alignment=TA_LEFT,
            textColor=HexColor('#34495D'),
            fontName=self.chinese_font_bold_name
        )
        
        # 內容樣式
        self.content_style = ParagraphStyle(
            'CustomContent',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=8,
            alignment=TA_LEFT,
            textColor=black,  # 內容文字改為黑色
            leftIndent=0.5 * cm,
            fontName=self.chinese_font_name
        )
        
        # 頁首樣式
        self.header_style = ParagraphStyle(
            'CustomHeader',
            parent=self.styles['Normal'],
            fontSize=12,
            alignment=TA_CENTER,
            textColor=HexColor('#34495D'),
            fontName=self.chinese_font_name
        )
        
        # 頁尾樣式
        self.footer_style = ParagraphStyle(
            'CustomFooter',
            parent=self.styles['Normal'],
            fontSize=12,
            alignment=TA_CENTER,
            textColor=HexColor('#34495D'),
            fontName=self.chinese_font_name
        )
        
        # 封面標題樣式
        self.cover_title_style = ParagraphStyle(
            'CoverTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=HexColor('#34495D'),
            fontName=self.chinese_font_bold_name
        )
        
        # 封面副標題樣式
        self.cover_subtitle_style = ParagraphStyle(
            'CoverSubtitle',
            parent=self.styles['Normal'],
            fontSize=16,
            spaceAfter=40,
            alignment=TA_CENTER,
            textColor=HexColor('#34495D'),
            fontName=self.chinese_font_name
        )
        
        # 封面資訊樣式
        self.cover_info_style = ParagraphStyle(
            'CoverInfo',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=12,
            alignment=TA_LEFT,
            textColor=black,  # 封面資訊內容改為黑色
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
            invitee_name = test_result.test_invitation.invitee.name
            # 清理檔案名稱中的特殊字符，避免檔案系統問題
            safe_name = invitee_name.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
            
            # 使用英文檔名作為後備，避免編碼問題
            import re
            # 移除非ASCII字符，只保留英文、數字和基本符號
            ascii_name = re.sub(r'[^\x00-\x7F]+', '', safe_name).strip()
            # 將空格替換為底線，確保檔名安全
            ascii_name = ascii_name.replace(' ', '_')
            if not ascii_name:
                ascii_name = f"user_{test_result.id}"
            safe_filename = f"Traitty_Assessment_Report_{ascii_name}.pdf"
            display_filename = f"Traitty 評鑑結果_{safe_name}.pdf"
            
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
            fontSize=28,
            fontName=self.chinese_font_bold_name,
            textColor=HexColor('#34495D'),  # 標題使用#34495D顏色
            spaceAfter=15
        )
        story.append(Paragraph(f"<b>{main_title}</b>", main_title_style))
        
        
        # 固定文字
        fixed_text_style = ParagraphStyle(
            'FixedText',
            parent=self.cover_subtitle_style,
            fontSize=16,
            fontName=self.chinese_font_name,
            spaceAfter=30
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
        from django.utils import timezone
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
        
        # 創建帶行距的樣式
        content_with_spacing = ParagraphStyle(
            'ContentWithSpacing',
            parent=self.content_style,
            fontSize=12,
            spaceAfter=12,
            leading=18,  # 行距
            fontName=self.chinese_font_name
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
            intro_content = """這份心理特質評鑑專為企業設計，幫助您在招募時更快速、準確地找到真正適合的人才。
以心理學與行為科學兩者學理背景為基礎，結合台灣知名人力銀行、最大人才媒體平台的資料，調查
自25萬筆求職資料與4,000份企業問卷，加上PerceptionPredict十年來以AI模型協助企業辨識高績效
人才的實務經驗所開發，具備高度信效度與實用性。
整份測驗僅需15分鐘，能有效協助企業找出具備「穩定性」、「責任感」、「正向影響力」三大職場核心特
質的人才，是數位化招募流程的強力工具。"""
        
        story.append(Paragraph(intro_content, content_with_spacing))
        story.append(Spacer(1, 0.8 * cm))
        
        # 使用方式部分
        story.append(Paragraph("<b>使用方式 | 如何善用、發揮效果</b>", bold_title_style))
        
        # 從測驗項目獲取使用方式內容
        usage_content = ""
        if test_result.test_project.usage_guide:
            usage_content = self._clean_html_content(test_result.test_project.usage_guide)
        else:
            usage_content = """評鑑完成後，將取得預測值（按評鑑項目不同有所不同）、關鍵特質列表、特質分數，便於企業快速從
大量應徵者中篩選具潛力者。您可直接參考預測值進行初步識別，若需進一步分析，可深入閱讀報告
中的特質構面定義與分數解析，作為面談或內部評估的輔助資料。建議可將此評鑑納入現行招募流程
的初篩或第二關卡，以提升決策效率與人才命中率。

完成評鑑後，您會看到三個主要資訊：AI預測值（按評鑑項目不同）、關鍵特質列表，以及每個特質的分
數說明。
可直接依預測值進行初步篩選，快速找出具潛力的候選人，提升篩選效率與人才命中率；若需要進一
步判斷，也可參考特質的定義與分數細節，作為招募、團隊配置、辨別具發展潛力人才的參考依據。"""
        
        story.append(Paragraph(usage_content, content_with_spacing))
        story.append(Spacer(1, 0.8 * cm))
        
        # 注意事項部分
        story.append(Paragraph("<b>注意事項 | 正確運用心法</b>", bold_title_style))
        
        # 從測驗項目獲取注意事項內容
        notice_content = ""
        if test_result.test_project.precautions:
            notice_content = self._clean_html_content(test_result.test_project.precautions)
        else:
            notice_content = """此AI心理特質評鑑為輔助性人才識別工具，雖已具備高度準確性與預測力，但仍非100%判定結果。請
避免將報告分數作對受測者貼標籤或產生偏見。進行後續人才了解、培訓、資源提供時，應搭配其他
職位相關條件、資源進行後續行動依據。"""
        
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
                    # 使用適中的正方形尺寸，避免雷達圖變形和過大的空白區域
                    radar_size = 14 * cm  # 縮小到9cm的正方形，減少左右空白
                    radar_image = Image(radar_image_path, width=radar_size, height=radar_size)
                    story.append(radar_image)
                    story.append(Spacer(1, 0.5 * cm))
                except Exception as e:
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
        
        # 3. 各向度數值
        story.append(Spacer(1, 0.8 * cm))
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
        story.append(Spacer(1, 0.8 * cm))
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
        analysis_content_style = ParagraphStyle(
            'AnalysisContent',
            parent=self.content_style,
            fontSize=12,
            fontName=self.chinese_font_name,
            leading=16
        )
        advantage_content = self._get_category_advantage_analysis(max_category_name, test_result)
        # 將%改成分
        advantage_content = advantage_content.replace('%', ' 分')
        story.append(Paragraph(advantage_content, analysis_content_style))
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
        story.append(Spacer(1, 0.8 * cm))
        
        # 5. 發展建議
        story.append(Spacer(1, 0.8 * cm))
        story.append(Paragraph("<b>發展建議</b>", bold_title_style))
        story.append(Spacer(1, 0.4 * cm))  # 標題與內容間距
        
        # 獲取最高分分類的發展建議參數內容
        max_category_obj = test_result.test_project.categories.filter(name=max_category_name).first()
        if max_category_obj and max_category_obj.development_parameter_content:
            development_content = self._clean_html_content(max_category_obj.development_parameter_content)
            story.append(Paragraph(development_content, analysis_content_style))
        else:
            # 如果沒有設定，顯示預設內容
            default_content = f"根據您在{max_category_name}方面的優秀表現，建議您在職場中發揮相關專長，承擔對應的角色與責任。"
            story.append(Paragraph(default_content, analysis_content_style))
        
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
            trait_data = [['關鍵特質', '特質描述', '分數']]
            
            for trait in unique_traits:
                # 限制描述長度
                description = trait['description']
                if len(description) > 120:
                    description = description[:120] + "..."
                
                # 將描述包裝為Paragraph以支援自動換行
                desc_paragraph = Paragraph(description, ParagraphStyle(
                    'DescriptionStyle',
                    parent=self.content_style,
                    fontSize=12,
                    fontName=self.chinese_font_name,
                    leading=16,
                    leftIndent=0,
                    rightIndent=0,
                    wordWrap='LTR',
                    textColor=black,  # 設定文字顏色為黑色
                    alignment=0  # 0=LEFT 靠左對齊
                ))
                
                # 根據 headsupflag 設定分數文字顏色
                score_color = HexColor('#FF0000') if trait.get('headsupflag') == 1 else black
                score_paragraph = Paragraph(str(trait['score']), ParagraphStyle(
                    'ScoreStyle',
                    fontSize=14,  # 與表格字體大小一致
                    fontName=self.chinese_font_name,
                    textColor=score_color,
                    alignment=1,  # 1=CENTER 置中對齊
                    leading=14,   # 行距設定
                    spaceAfter=0,  # 段落後間距
                    spaceBefore=0  # 段落前間距
                ))
                
                trait_data.append([
                    trait['name'],
                    desc_paragraph,
                    score_paragraph  # 使用帶顏色的分數段落
                ])
            
            # 建立表格，調整欄位寬度讓表頭更好置中
            table = Table(trait_data, colWidths=[3*cm, 11*cm, 1.5*cm], repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#152233')),  # 表頭背景
                ('TEXTCOLOR', (0, 0), (-1, 0), white),               # 表頭文字白色
                ('TEXTCOLOR', (0, 1), (-1, -1), black),              # 內容文字黑色
                ('FONTNAME', (0, 0), (-1, 0), self.chinese_font_bold_name),
                ('FONTNAME', (0, 1), (-1, -1), self.chinese_font_name),
                ('FONTSIZE', (0, 0), (-1, 0), 14),                  # 表頭字體大小14
                ('FONTSIZE', (0, 1), (0, -1), 14),                  # 關鍵特質欄字體大小14
                ('FONTSIZE', (1, 1), (1, -1), 12),                  # 特質描述欄字體大小12
                ('FONTSIZE', (2, 1), (2, -1), 14),                  # 分數欄字體大小14
                ('BOTTOMPADDING', (0, 0), (-1, 0), 17),            # 表頭底部padding
                ('TOPPADDING', (0, 0), (-1, 0), 11),               # 表頭頂部padding
                # 分別設定各欄位的上下間距（可個別調整）
                ('BOTTOMPADDING', (0, 1), (0, -1), 15),            # 第0欄（關鍵特質）底部padding
                ('TOPPADDING', (0, 1), (0, -1), 9),               # 第0欄（關鍵特質）頂部padding
                ('BOTTOMPADDING', (1, 1), (1, -1), 12),            # 第1欄（特質描述）底部padding
                ('TOPPADDING', (1, 1), (1, -1), 12),               # 第1欄（特質描述）頂部padding  
                ('BOTTOMPADDING', (2, 1), (2, -1), 15),            # 第2欄（分數）底部padding
                ('TOPPADDING', (2, 1), (2, -1), 9),               # 第2欄（分數）頂部padding
                ('LEFTPADDING', (0, 0), (-1, -1), 10),             # 增加左內距
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),            # 增加右內距
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
                    
                    # 清理HTML內容
                    description = self._clean_html_content(description)
                    
                    # 限制描述長度
                    if len(description) > 150:
                        description = description[:150] + "..."
                    
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
            
            # 嘗試找到並設定中文字體 - 使用微軟正黑體為優先
            chinese_font_path = None
            possible_fonts = [
                # Windows 路徑
                'C:/Windows/Fonts/msjh.ttc',           # 微軟正黑體（Windows）
                'C:/Windows/Fonts/msyh.ttc',           # 微軟雅黑（Windows）
                # macOS 路徑
                '/Library/Fonts/Microsoft JhengHei.ttf',  # 微軟正黑體（macOS）
                '/System/Library/Fonts/PingFang.ttc',     # PingFang SC
                '/System/Library/Fonts/STHeiti Light.ttc', # 黑體
                '/Library/Fonts/Arial Unicode MS.ttf'     # Arial Unicode MS
            ]
            
            for font_path in possible_fonts:
                if os.path.exists(font_path):
                    chinese_font_path = font_path
                    break
            
            if chinese_font_path:
                # 註冊中文字體
                font_prop = fm.FontProperties(fname=chinese_font_path)
                plt.rcParams['font.family'] = [font_prop.get_name(), 'sans-serif']
            else:
                # 設定中文字體回退 - 使用微軟正黑體為優先
                plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'PingFang SC', 'STHeiti Light', 'SimHei', 'Arial Unicode MS']
            
            plt.rcParams['axes.unicode_minus'] = False
            
            # 準備數據 - 使用與網頁版相同的標籤格式
            categories = list(category_scores.keys())
            values = list(category_scores.values())
            
            # 數據驗證
            if not categories or not values:
                return None
            
            # 創建顯示標籤，包含分類名稱和分數
            display_categories = []
            for cat, value in zip(categories, values):
                # 在分類名稱後面添加括號內的四捨五入分數
                display_categories.append(f"{cat}({self._django_round(value)})")
            
            # 創建圓形雷達圖
            N = len(categories)
            angles = [n / float(N) * 2 * np.pi for n in range(N)]
            angles += angles[:1]  # 完成圓形
            
            # 創建極座標圖，使用正方形尺寸並設定適當的邊距
            fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
            
            # 調整圖表在圖片中的位置，確保標籤不被裁切
            plt.tight_layout(pad=2.0)
            
            # 繪製數據
            values_plot = values + values[:1]  # 完成圓形
            ax.plot(angles, values_plot, 'o-', linewidth=2, color='#4285f4', markersize=8)
            ax.fill(angles, values_plot, alpha=0.25, color='#4285f4')
            
            # 設定角度標籤（包含分數），調整字體大小
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(display_categories, fontsize=12, fontweight='bold')
            
            # 設定數值範圍和標籤
            ax.set_ylim(0, 100)
            ax.set_yticks([20, 40, 60, 80, 100])
            ax.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=12)
            ax.grid(True)
            
            # 設定樣式
            ax.set_theta_offset(np.pi / 2)  # 從頂部開始
            ax.set_theta_direction(-1)  # 順時針方向
            
            
            # 保存圖表到臨時檔案
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            temp_file.close()  # 關閉檔案句柄，讓 matplotlib 可以寫入
            
            # 使用標準邊界保持正方形比例，避免自動裁剪變形
            plt.savefig(temp_file.name, dpi=150, bbox_inches=None, 
                       facecolor='white', edgecolor='none')
            plt.close()
            
            # 檢查檔案是否真的被創建
            if os.path.exists(temp_file.name) and os.path.getsize(temp_file.name) > 0:
                return temp_file.name
            else:
                return None
            
        except Exception as e:
            # 靜默處理錯誤，避免影響PDF生成
            try:
                plt.close()
            except:
                pass
            return None
    
    def _calculate_category_scores(self, test_result):
        """計算分類平均分數"""
        if not test_result.raw_data or not test_result.test_project:
            return {}
        
        categories = test_result.test_project.categories.prefetch_related('traits').all()
        category_scores = {}
        
        for category in categories:
            traits = category.traits.all()
            if traits:
                trait_scores = []
                for trait in traits:
                    trait_score = None
                    
                    # 建立中文名稱映射表 (用於處理不一致的中文翻譯)
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
                        '社交智商': ['社會智能', 'Social Intelligence']
                    }
                    
                    # 方法1: 從 trait_scores 中查找（新的爬蟲數據結構）
                    if test_result.raw_data.get('trait_scores'):
                        trait_scores_data = test_result.raw_data['trait_scores']
                        for key, value in trait_scores_data.items():
                            if isinstance(value, dict) and 'chinese_name' in value:
                                # 直接匹配
                                if (value.get('chinese_name') == trait.chinese_name or 
                                    key == trait.system_name or
                                    key == trait.chinese_name or
                                    key.lower().replace(' ', '_') == trait.system_name.lower().replace(' ', '_')):
                                    trait_score = value.get('score', 0)
                                    break
                                # 使用映射表匹配
                                alternative_names = chinese_name_mapping.get(trait.chinese_name, [])
                                if key in alternative_names or value.get('chinese_name') in alternative_names:
                                    trait_score = value.get('score', 0)
                                    break
                            elif key == trait.system_name or key == trait.chinese_name:
                                trait_score = value if isinstance(value, (int, float)) else 0
                                break
                            # 檢查映射表
                            elif key in chinese_name_mapping.get(trait.chinese_name, []):
                                trait_score = value if isinstance(value, (int, float)) else value.get('score', 0)
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
                    category_scores[category.name] = avg_score
        
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
        """清理HTML內容，保留基本列表結構並轉換為ReportLab格式"""
        import re
        
        if not content:
            return ""
        
        # 先處理混合的有序列表和無序列表結構
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
                    clean_item = re.sub(r'<[^>]+>', '', item_content)
                    clean_item = clean_item.strip()
                    if clean_item:
                        new_content += f"{i}. {clean_item}<br/><br/>"
            
            elif list_block.startswith('<ul'):
                # 無序列表 - 使用項目符號
                li_pattern = r'<li[^>]*>(.*?)</li>'
                li_items = re.findall(li_pattern, list_block, re.DOTALL)
                for item_content in li_items:
                    clean_item = re.sub(r'<[^>]+>', '', item_content)
                    clean_item = clean_item.strip()
                    if clean_item:
                        new_content += f"• {clean_item}<br/><br/>"
        
        # 如果有混合內容，則使用處理後的內容
        if new_content:
            content = new_content
        else:
            # 沒有列表結構，直接移除HTML標籤
            content = re.sub(r'<[^>]+>', '', content)
        
        # 解碼HTML實體
        content = content.replace('&mdash;', '—')
        content = content.replace('&nbsp;', ' ')
        content = content.replace('&amp;', '&')
        content = content.replace('&lt;', '<')
        content = content.replace('&gt;', '>')
        content = content.replace('&quot;', '"')
        
        # 移除多餘的空白字符，但保留段落分隔
        content = re.sub(r' +', ' ', content)  # 合併多個空格
        content = re.sub(r'\n +', '\n', content)  # 移除行首空格
        content = re.sub(r' +\n', '\n', content)  # 移除行尾空格
        content = re.sub(r'\n{3,}', '\n\n', content)  # 最多保留兩個換行
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
        story.append(Paragraph(f"<b>報告版本:</b> v1.0", self.content_style))
        
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