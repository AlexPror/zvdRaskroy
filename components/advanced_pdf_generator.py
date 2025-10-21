#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Продвинутый генератор PDF отчетов с учетом количества деталей
"""

from pathlib import Path
from typing import Dict, List
from datetime import datetime
import logging

class AdvancedPDFGenerator:
    """Генератор PDF отчетов с количеством деталей"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_detailed_report(self, project_name: str, area_data: Dict, output_path: str) -> Dict:
        """
        Генерация подробного PDF отчета с количеством деталей
        
        Args:
            project_name: Название проекта
            area_data: Данные о площадях из AdvancedAreaCalculator
            output_path: Путь для сохранения PDF
            
        Returns:
            Dict с результатами
        """
        result = {'success': False, 'pdf_path': None, 'error': None}
        
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm
            from reportlab.lib.enums import TA_LEFT
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            
            # Регистрируем русский шрифт
            try:
                pdfmetrics.registerFont(TTFont('DejaVu', 'DejaVuSans.ttf'))
                font_name = 'DejaVu'
            except:
                try:
                    # Пробуем найти шрифт в системе Windows
                    import os
                    font_path = r"C:\Windows\Fonts\arial.ttf"
                    if os.path.exists(font_path):
                        pdfmetrics.registerFont(TTFont('Arial', font_path))
                        font_name = 'Arial'
                    else:
                        font_name = 'Helvetica'
                except:
                    font_name = 'Helvetica'
            
            # Создаем PDF
            pdf = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=15*mm,
                leftMargin=15*mm,
                topMargin=15*mm,
                bottomMargin=15*mm
            )
            
            # Стили
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontName=font_name,
                fontSize=18,
                textColor=colors.HexColor('#1976D2'),
                spaceAfter=12,
                alignment=1  # Центр
            )
            
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Heading2'],
                fontName=font_name,
                fontSize=14,
                textColor=colors.HexColor('#424242'),
                spaceAfter=8,
                alignment=1
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontName=font_name,
                fontSize=10,
                alignment=1
            )
            
            # Элементы документа
            elements = []
            
            # Заголовок
            title = Paragraph("Расчет площадей разверток листового металла", title_style)
            elements.append(title)
            
            subtitle = Paragraph(f"Проект: {project_name}", subtitle_style)
            elements.append(subtitle)
            
            date_text = Paragraph(
                f"Дата расчета: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                normal_style
            )
            elements.append(date_text)
            
            elements.append(Spacer(1, 10*mm))
            
            # Таблица данных
            table_data = [
                ['№', 'Наименование детали', 'Ширина,\nмм', 'Высота,\nмм', 
                 'Площадь\n1 шт, м²', 'Кол-во,\nшт', 'Итого, м²']
            ]
            
            unfoldings = area_data.get('unfoldings', [])
            
            for idx, unfolding in enumerate(unfoldings, 1):
                # Разбиваем длинное название для переноса строки
                name = unfolding['name']
                # Если есть номер заказа в скобках, переносим его на новую строку
                if '(' in name and ')' in name:
                    # Разделяем на основное имя и номер заказа
                    base_name = name.rsplit('(', 1)[0].strip()
                    order_num = '(' + name.rsplit('(', 1)[1]
                    display_name = Paragraph(f"{base_name}<br/>{order_num}", 
                                            ParagraphStyle('cell', parent=styles['Normal'], 
                                                         fontName=font_name, fontSize=8))
                else:
                    display_name = Paragraph(name, 
                                           ParagraphStyle('cell', parent=styles['Normal'],
                                                        fontName=font_name, fontSize=8))
                
                table_data.append([
                    str(idx),
                    display_name,
                    f"{unfolding['width']:.1f}",
                    f"{unfolding['height']:.1f}",
                    f"{unfolding['area_m2']:.4f}",
                    str(unfolding.get('quantity', 1)),
                    f"{unfolding.get('total_area_m2', unfolding['area_m2']):.4f}"
                ])
            
            # Итоговая строка - чистая площадь
            total_area = area_data.get('total_area_with_quantity', area_data.get('total_area', 0))
            table_data.append([
                '',
                'ИТОГО (площадь деталей):',
                '',
                '',
                '',
                '',
                f"{total_area:.4f}"
            ])
            
            # Площадь с зазорами (для заказа листов)
            # Добавляем 5 мм зазора между деталями и 10 мм от краев
            CUT_GAP = 5  # мм между деталями
            EDGE_MARGIN = 10  # мм от края
            
            total_area_with_gaps = 0
            for unfolding in unfoldings:
                width_with_gap = unfolding['width'] + CUT_GAP
                height_with_gap = unfolding['height'] + CUT_GAP
                area_with_gap = (width_with_gap * height_with_gap) / 1_000_000  # мм² → м²
                quantity = unfolding.get('quantity', 1)
                total_area_with_gaps += area_with_gap * quantity
            
            # Добавляем отступы от краев (грубая оценка)
            margin_area = (2 * EDGE_MARGIN) / 1000 * total_area  # примерная добавка
            total_area_with_gaps += margin_area
            
            table_data.append([
                '',
                'С зазорами (для листов):',
                '',
                '',
                '',
                '',
                f"{total_area_with_gaps:.4f}"
            ])
            
            # Создаем таблицу
            # Увеличена ширина колонки "Наименование" для длинных названий с номером заказа
            table = Table(
                table_data,
                colWidths=[8*mm, 75*mm, 20*mm, 20*mm, 20*mm, 15*mm, 20*mm]
            )
            
            # Стиль таблицы
            table.setStyle(TableStyle([
                # Заголовок
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976D2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), font_name),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TOPPADDING', (0, 0), (-1, 0), 6),
                
                # Данные
                ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -2), colors.black),
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Номер
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),  # Наименование - по левому краю
                ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),  # Числа - по правому краю
                ('FONTNAME', (0, 1), (-1, -1), font_name),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
                ('VALIGN', (0, 1), (-1, -2), 'TOP'),  # Верхнее выравнивание для переноса
                ('TOPPADDING', (0, 1), (-1, -2), 4),  # Увеличенные отступы
                ('BOTTOMPADDING', (0, 1), (-1, -2), 4),
                
                # Итоговые строки
                ('BACKGROUND', (0, -2), (-1, -2), colors.HexColor('#FFC107')),
                ('TEXTCOLOR', (0, -2), (-1, -2), colors.black),
                ('FONTNAME', (0, -2), (-1, -2), font_name),
                ('FONTSIZE', (0, -2), (-1, -2), 10),
                ('ALIGN', (1, -2), (1, -2), 'RIGHT'),
                ('LINEABOVE', (0, -2), (-1, -2), 2, colors.black),
                ('TOPPADDING', (0, -2), (-1, -2), 6),
                ('BOTTOMPADDING', (0, -2), (-1, -2), 6),
                
                # Строка с зазорами
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#FFE082')),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.black),
                ('FONTNAME', (0, -1), (-1, -1), font_name),
                ('FONTSIZE', (0, -1), (-1, -1), 9),
                ('ALIGN', (1, -1), (1, -1), 'RIGHT'),
                ('TOPPADDING', (0, -1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, -1), (-1, -1), 6),
            ]))
            
            elements.append(table)
            
            # Дополнительная информация
            elements.append(Spacer(1, 10*mm))
            
            summary_style = ParagraphStyle(
                'Summary',
                parent=styles['Normal'],
                fontName=font_name,
                fontSize=11,
                spaceAfter=4
            )
            
            info_lines = [
                f"<b>Уникальных деталей:</b> {len(unfoldings)}",
                f"<b>Площадь деталей (чистая):</b> {total_area:.4f} м²",
                f"<b>Площадь с зазорами резки:</b> {total_area_with_gaps:.4f} м² (+{((total_area_with_gaps/total_area - 1)*100):.1f}%)",
                f"<b>Зазоры:</b> {CUT_GAP} мм между деталями, {EDGE_MARGIN} мм от краев",
                f"<b>Расчет выполнен:</b> Система автоматизации КОМПАС-3D",
            ]
            
            for line in info_lines:
                elements.append(Paragraph(line, summary_style))
            
            # Генерируем PDF
            pdf.build(elements)
            
            result['success'] = True
            result['pdf_path'] = output_path
            
            self.logger.info(f"\n✓ PDF отчет создан: {output_path}")
            
        except ImportError as e:
            error_msg = "Библиотека reportlab не установлена. Установите: pip install reportlab"
            result['error'] = error_msg
            self.logger.error(error_msg)
        except Exception as e:
            error_msg = f"Ошибка генерации PDF: {e}"
            result['error'] = error_msg
            self.logger.error(error_msg)
            import traceback
            self.logger.error(traceback.format_exc())
        
        return result








