"""
Генератор PDF отчета по площадям разверток

Использует reportlab для создания красивого PDF
"""

import logging
from pathlib import Path
from typing import Dict
from datetime import datetime


class UnfoldingPDFGenerator:
    """Генерация PDF отчета по площадям разверток"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_report(self, project_name: str, area_data: Dict, output_path: str, order_number: str = None) -> Dict:
        """
        Генерация PDF отчета
        
        Args:
            project_name: Название проекта
            area_data: Данные о площадях (из UnfoldingAreaCalculator)
            output_path: Путь для сохранения PDF
        
        Returns:
            dict: {'success': bool, 'pdf_path': str, 'error': str}
        """
        result = {
            'success': False,
            'pdf_path': output_path,
            'error': None
        }
        
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_LEFT
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            
            # Регистрация шрифтов (для кириллицы)
            # КРИТИЧНО: Используем Arial из Windows!
            try:
                pdfmetrics.registerFont(TTFont('ArialUnicode', 'C:/Windows/Fonts/arial.ttf'))
                pdfmetrics.registerFont(TTFont('ArialUnicode-Bold', 'C:/Windows/Fonts/arialbd.ttf'))
                font_name = 'ArialUnicode'
                font_name_bold = 'ArialUnicode-Bold'
                self.logger.info("✓ Шрифт Arial загружен")
            except Exception as e:
                self.logger.warning(f"⚠ Ошибка загрузки Arial: {e}")
                # Пробуем Times
                try:
                    pdfmetrics.registerFont(TTFont('TimesUnicode', 'C:/Windows/Fonts/times.ttf'))
                    font_name = 'TimesUnicode'
                    font_name_bold = 'TimesUnicode'
                    self.logger.info("✓ Шрифт Times загружен")
                except:
                    font_name = 'Helvetica'
                    font_name_bold = 'Helvetica-Bold'
                    self.logger.warning("⚠ Используется Helvetica (без кириллицы!)")
            
            # Создаем PDF
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=20*mm,
                leftMargin=20*mm,
                topMargin=20*mm,
                bottomMargin=20*mm
            )
            
            # Стили
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontName=font_name_bold,
                fontSize=18,
                textColor=colors.HexColor('#1f4788'),
                spaceAfter=12,
                alignment=TA_CENTER
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontName=font_name_bold,
                fontSize=14,
                textColor=colors.HexColor('#2c5aa0'),
                spaceAfter=6,
                spaceBefore=12
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontName=font_name,
                fontSize=10,
                spaceAfter=6
            )
            
            # Контент
            story = []
            
            # Заголовок
            story.append(Paragraph(f"РАСЧЕТ ПЛОЩАДЕЙ РАЗВЕРТОК", title_style))
            story.append(Paragraph(f"Проект: {project_name}", heading_style))
            story.append(Paragraph(f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}", normal_style))
            
            # НОМЕР ЗАКАЗА (если указан)
            if order_number:
                order_style = ParagraphStyle(
                    'OrderStyle',
                    parent=styles['Normal'],
                    fontName=font_name_bold,
                    fontSize=12,
                    textColor=colors.HexColor('#d32f2f'),
                    spaceAfter=6
                )
                story.append(Paragraph(f"<b>Номер заказа: {order_number}</b>", order_style))
            
            story.append(Spacer(1, 12))
            
            # Таблица деталей
            if area_data.get('parts'):
                story.append(Paragraph("Детали:", heading_style))
                
                # Заголовок таблицы
                table_data = [[
                    'No',
                    'Наименование',
                    'Площадь (м²)',
                    'Площадь (мм²)',
                    'Габариты (мм)',
                    'Кол-во',
                    'Итого (м²)'
                ]]
                
                # Данные
                for i, part in enumerate(area_data['parts'], 1):
                    table_data.append([
                        str(i),
                        part['name'],
                        f"{part['area_m2']:.6f}",
                        f"{part['area_mm2']:.0f}",
                        f"{part['width_mm']:.1f} x {part['height_mm']:.1f}",
                        str(part['quantity']),
                        f"{part['total_area_m2']:.6f}"
                    ])
                
                # Итого
                table_data.append([
                    '',
                    'ИТОГО:',
                    '',
                    '',
                    '',
                    '',
                    f"{area_data['total_area_with_quantity']:.6f}"
                ])
                
                # Создаем таблицу
                table = Table(table_data, colWidths=[
                    15*mm,  # No
                    60*mm,  # Наименование
                    25*mm,  # Площадь м²
                    25*mm,  # Площадь мм²
                    30*mm,  # Габариты
                    15*mm,  # Кол-во
                    25*mm   # Итого
                ])
                
                # Стиль таблицы
                table.setStyle(TableStyle([
                    # Заголовок
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), font_name_bold),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    
                    # Данные
                    ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
                    ('TEXTCOLOR', (0, 1), (-1, -2), colors.black),
                    ('ALIGN', (0, 1), (0, -2), 'CENTER'),  # No
                    ('ALIGN', (2, 1), (-1, -2), 'RIGHT'),  # Числа
                    ('FONTNAME', (0, 1), (-1, -2), font_name),
                    ('FONTSIZE', (0, 1), (-1, -2), 9),
                    ('TOPPADDING', (0, 1), (-1, -2), 4),
                    ('BOTTOMPADDING', (0, 1), (-1, -2), 4),
                    
                    # Итого
                    ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0f0f0')),
                    ('TEXTCOLOR', (0, -1), (-1, -1), colors.black),
                    ('ALIGN', (0, -1), (-1, -1), 'RIGHT'),
                    ('FONTNAME', (0, -1), (-1, -1), font_name_bold),
                    ('FONTSIZE', (0, -1), (-1, -1), 11),
                    ('TOPPADDING', (0, -1), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, -1), (-1, -1), 8),
                    
                    # Сетка
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#2c5aa0')),
                    ('LINEABOVE', (0, -1), (-1, -1), 2, colors.grey),
                ]))
                
                story.append(table)
            
            # Ошибки (если есть)
            if area_data.get('errors'):
                story.append(Spacer(1, 12))
                story.append(Paragraph("Ошибки:", heading_style))
                for error in area_data['errors']:
                    story.append(Paragraph(f"• {error}", normal_style))
            
            # Генерируем PDF
            doc.build(story)
            
            result['success'] = True
            self.logger.info(f"✓ PDF отчет создан: {output_path}")
            
        except ImportError as e:
            result['error'] = f"Библиотека reportlab не установлена! Установите: pip install reportlab"
            self.logger.error(result['error'])
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Ошибка создания PDF: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
        
        return result


if __name__ == "__main__":
    # Тестирование
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    
    # Тестовые данные
    test_data = {
        'success': True,
        'total_area_m2': 0.5,
        'total_area_with_quantity': 1.5,
        'parts': [
            {
                'name': '001 - Корпус короба - Развертка',
                'area_m2': 0.3,
                'area_mm2': 300000,
                'width_mm': 500,
                'height_mm': 600,
                'quantity': 1,
                'total_area_m2': 0.3
            },
            {
                'name': '003 - Распорка - Развертка',
                'area_m2': 0.2,
                'area_mm2': 200000,
                'width_mm': 400,
                'height_mm': 500,
                'quantity': 3,
                'total_area_m2': 0.6
            }
        ],
        'errors': []
    }
    
    generator = UnfoldingPDFGenerator()
    result = generator.generate_report(
        "ZVD.LITE.90.260.1000",
        test_data,
        "test_report.pdf"
    )
    
    print(f"\nРезультат: {result}")

