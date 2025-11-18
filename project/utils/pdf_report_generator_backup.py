# utils/pdf_report_generator_backup.py
"""
PDF 報告生成器 - 備份版本
提供測驗結果詳情的 PDF 報告生成功能
"""

import os
import io
from datetime import datetime
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone

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
    print("✅ matplotlib 已成功載入")
except ImportError as e:
    MATPLOTLIB_AVAILABLE = False
    print(f"❌ matplotlib 載入失敗: {e}")


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
        self.top_margin = 3 * cm
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
    
    def _setup_custom_styles(self):
        """設定自訂樣式"""
        # 標題樣式
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=HexColor('#2c3e50'),
            fontName=self.chinese_font_bold_name
        )
        
        # 副標題樣式
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            alignment=TA_LEFT,
            textColor=HexColor('#34495e'),
            fontName=self.chinese_font_bold_name
        )
        
        # 內容樣式
        self.content_style = ParagraphStyle(
            'CustomContent',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=8,
            alignment=TA_LEFT,
            textColor=black,
            leftIndent=0.5 * cm,
            fontName=self.chinese_font_name
        )
        
        # 頁首樣式
        self.header_style = ParagraphStyle(
            'CustomHeader',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER,
            textColor=HexColor('#7f8c8d'),
            fontName=self.chinese_font_name
        )
        
        # 頁尾樣式
        self.footer_style = ParagraphStyle(
            'CustomFooter',
            parent=self.styles['Normal'],
            fontSize=9,
            alignment=TA_CENTER,
            textColor=HexColor('#7f8c8d'),
            fontName=self.chinese_font_name
        )
        
        # 封面標題樣式
        self.cover_title_style = ParagraphStyle(
            'CoverTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=HexColor('#2c3e50'),
            fontName=self.chinese_font_bold_name
        )
        
        # 封面副標題樣式
        self.cover_subtitle_style = ParagraphStyle(
            'CoverSubtitle',
            parent=self.styles['Normal'],
            fontSize=16,
            spaceAfter=40,
            alignment=TA_CENTER,
            textColor=HexColor('#34495e'),
            fontName=self.chinese_font_name
        )
        
        # 封面資訊樣式
        self.cover_info_style = ParagraphStyle(
            'CoverInfo',
            parent=self.styles['Normal'],
            fontSize=14,
            spaceAfter=12,
            alignment=TA_LEFT,
            textColor=HexColor('#2c3e50'),
            leftIndent=1 * cm,
            fontName=self.chinese_font_name
        )
    
    def _draw_header_footer(self, canvas, doc):
        """繪製頁首和頁尾"""
        canvas.saveState()
        
        page_num = canvas.getPageNumber()
        
        # 第一頁（封面）不繪製頁首頁尾
        if page_num == 1:
            canvas.restoreState()
            return
            
        # 頁首
        header_y = self.page_height - 1.5 * cm
        
        # 頁首左側 - Logo預留空間 + 公司名稱
        canvas.setFont(self.chinese_font_bold_name, 10)
        canvas.setFillColor(HexColor('#2c3e50'))
        # 預留 Logo 空間 (2cm 寬)
        logo_space = 2 * cm
        canvas.drawString(self.left_margin + logo_space, header_y, self.company_info['name'])
        
        # 頁首右側 - 生成日期
        canvas.setFont(self.chinese_font_name, 9)
        canvas.setFillColor(HexColor('#7f8c8d'))
        date_str = timezone.now().strftime('%Y年%m月%d日')
        canvas.drawRightString(self.page_width - self.right_margin, header_y, f"生成日期: {date_str}")
        
        # 頁首分隔線
        canvas.setStrokeColor(HexColor('#bdc3c7'))
        canvas.setLineWidth(0.5)
        canvas.line(self.left_margin, header_y - 0.3 * cm, 
                   self.page_width - self.right_margin, header_y - 0.3 * cm)
        
        # 頁尾
        footer_y = 2 * cm
        
        # 頁尾分隔線
        canvas.setStrokeColor(HexColor('#bdc3c7'))
        canvas.setLineWidth(0.5)
        canvas.line(self.left_margin, footer_y + 1.2 * cm, 
                   self.page_width - self.right_margin, footer_y + 1.2 * cm)
        
        # 頁尾主要內容 - Perception Group 描述
        canvas.setFont(self.chinese_font_name, 8)
        canvas.setFillColor(HexColor('#7f8c8d'))
        description_lines = [
            "Perception Group is pioneering solutions that help businesses improve the accuracy and",
            "effectiveness of how they select and promote the right people for the right roles."
        ]
        for i, line in enumerate(description_lines):
            canvas.drawString(self.left_margin, footer_y + 0.8 * cm - i * 0.3 * cm, line)
        
        # 頁尾版權信息
        canvas.setFont(self.chinese_font_name, 8)
        canvas.setFillColor(HexColor('#7f8c8d'))
        canvas.drawString(self.left_margin, footer_y + 0.1 * cm, self.company_info['copyright'])
        
        # 頁尾聯絡資訊
        contact_info = f"{self.company_info['email']} | {self.company_info['website']}"
        canvas.drawString(self.left_margin, footer_y - 0.2 * cm, contact_info)
        
        # 頁尾右側 - 頁碼
        canvas.setFont(self.chinese_font_name, 9)
        canvas.setFillColor(HexColor('#7f8c8d'))
        canvas.drawRightString(self.page_width - self.right_margin, footer_y + 0.4 * cm, 
                              f"第 {page_num} 頁")
        
        canvas.restoreState()
    
    def _draw_cover_page_header_footer(self, canvas, doc):
        """繪製封面頁的頁首和頁尾"""
        canvas.saveState()
        
        # 封面頁首
        header_y = self.page_height - 1.5 * cm
        
        # 頁首左側 - Logo預留空間 + 公司名稱
        canvas.setFont(self.chinese_font_bold_name, 12)
        canvas.setFillColor(HexColor('#2c3e50'))
        # 預留 Logo 空間 (2cm 寬)
        logo_space = 2 * cm
        canvas.drawString(self.left_margin + logo_space, header_y, self.company_info['name'])
        
        # 頁首分隔線
        canvas.setStrokeColor(HexColor('#bdc3c7'))
        canvas.setLineWidth(0.5)
        canvas.line(self.left_margin, header_y - 0.3 * cm, 
                   self.page_width - self.right_margin, header_y - 0.3 * cm)
        
        # 封面頁尾
        footer_y = 2 * cm
        
        # 頁尾分隔線
        canvas.setStrokeColor(HexColor('#bdc3c7'))
        canvas.setLineWidth(0.5)
        canvas.line(self.left_margin, footer_y + 1.2 * cm, 
                   self.page_width - self.right_margin, footer_y + 1.2 * cm)
        
        # 頁尾主要內容 - Perception Group 描述
        canvas.setFont(self.chinese_font_name, 8)
        canvas.setFillColor(HexColor('#7f8c8d'))
        description_lines = [
            "Perception Group is pioneering solutions that help businesses improve the accuracy and",
            "effectiveness of how they select and promote the right people for the right roles."
        ]
        for i, line in enumerate(description_lines):
            canvas.drawString(self.left_margin, footer_y + 0.8 * cm - i * 0.3 * cm, line)
        
        # 頁尾版權信息
        canvas.setFont(self.chinese_font_name, 8)
        canvas.setFillColor(HexColor('#7f8c8d'))
        canvas.drawString(self.left_margin, footer_y + 0.1 * cm, self.company_info['copyright'])
        
        # 頁尾聯絡資訊
        contact_info = f"{self.company_info['email']} | {self.company_info['website']}"
        canvas.drawString(self.left_margin, footer_y - 0.2 * cm, contact_info)
        
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
        
        # 建立文件
        doc = SimpleDocTemplate(
            buffer,
            pagesize=self.page_size,
            leftMargin=self.left_margin,
            rightMargin=self.right_margin,
            topMargin=self.top_margin,
            bottomMargin=self.bottom_margin
        )
        
        # 準備內容
        story = []
        
        # 添加封面頁
        story.extend(self._create_cover_page(test_result))
        
        # 添加分頁
        story.append(PageBreak())
        
        # 添加報告使用指南（第二頁固定內容）
        story.extend(self._create_report_guide_section())
        
        # 添加分頁
        story.append(PageBreak())
        
        # 添加關鍵特質分析頁（第三頁，移除基本資訊頁）
        story.extend(self._create_key_analysis_section(test_result))
        
        # 建立 PDF
        doc.build(story, onFirstPage=self._draw_cover_page_header_footer, onLaterPages=self._draw_header_footer)
        
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
            filename = f"test_result_{test_result.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            buffer.close()
            return response
    
    def _create_cover_page(self, test_result):
        """建立封面頁"""
        story = []
        
        # 添加一些空白以將內容置中
        story.append(Spacer(1, 4 * cm))
        
        # 主標題 - 測驗項目名稱 + 完整報告
        title_text = f"{test_result.test_project.name} 完整報告"
        story.append(Paragraph(title_text, self.cover_title_style))
        
        # 副標題
        story.append(Paragraph("測驗結果詳情報告", self.cover_subtitle_style))
        
        # 添加空白分隔
        story.append(Spacer(1, 2 * cm))
        
        # 受測人基本資訊
        story.append(Paragraph("<b>受測人基本資訊</b>", self.subtitle_style))
        story.append(Spacer(1, 0.5 * cm))
        
        # 基本資訊內容
        basic_info_data = []
        
        # 姓名
        basic_info_data.append(f"<b>姓名：</b> {test_result.test_invitation.invitee.name}")
        
        # 狀態：求職者
        basic_info_data.append(f"<b>狀態：</b> 求職者")
        
        # 職位
        position = "N/A"
        if hasattr(test_result.test_invitation.invitee, 'position') and test_result.test_invitation.invitee.position:
            position = test_result.test_invitation.invitee.position
        basic_info_data.append(f"<b>職位：</b> {position}")
        
        # 測驗日期
        test_date = "N/A"
        if test_result.test_invitation.completed_at:
            test_date = test_result.test_invitation.completed_at.strftime('%Y年%m月%d日')
        elif test_result.test_invitation.started_at:
            test_date = test_result.test_invitation.started_at.strftime('%Y年%m月%d日')
        basic_info_data.append(f"<b>測驗日期：</b> {test_date}")
        
        # 添加基本資訊到故事
        for info in basic_info_data:
            story.append(Paragraph(info, self.cover_info_style))
        
        # 添加空白填充底部
        story.append(Spacer(1, 3 * cm))
        
        return story
        
    # [其他方法的備份代碼繼續...]

# 便利函數
def generate_test_result_pdf_backup(test_result, output_path=None):
    """
    生成測驗結果 PDF 報告的便利函數 - 備份版本
    
    Args:
        test_result: TestProjectResult 物件
        output_path: 輸出路徑，如果為 None 則返回 HttpResponse
    
    Returns:
        HttpResponse 或 檔案路徑
    """
    generator = PDFReportGenerator()
    return generator.generate_test_result_report(test_result, output_path)