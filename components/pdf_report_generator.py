#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор PDF отчетов с таблицей площадей разверток
"""

from pathlib import Path
from typing import Dict, List
from datetime import datetime
import logging

class PDFReportGenerator:
    """Генератор PDF отчетов"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_area_report(self, project_name: str, area_data: Dict, output_path: str) -> Dict:
        """
        Генерация PDF отчета с площадями разверток
        
        Args:
            project_name: Название проекта
            area_data: Данные о площадях из AreaCalculator
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
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            
            # Регистрируем русский шрифт
            try:
                pdfmetrics.registerFont(TTFont('DejaVu', 'DejaVuSans.ttf'))
                font_name = 'DejaVu'
            except:
                font_name = 'Helvetica'
            
            # Создаем PDF
            pdf = SimpleDocTemplate(
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
                fontName=font_name,
                fontSize=16,
                textColor=colors.HexColor('#1976D2'),
                spaceAfter=12,
                alignment=1  # Центр
            )
            
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Heading2'],
                fontName=font_name,
                fontSize=12,
                spaceAfter=6
            )
            
            # Элементы документа
            elements = []
            
            # Заголовок
            title = Paragraph(f"Расчет площадей разверток", title_style)
            elements.append(title)
            
            subtitle = Paragraph(f"Проект: {project_name}", subtitle_style)
            elements.append(subtitle)
            
            date_text = Paragraph(f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}", styles['Normal'])
            elements.append(date_text)
            
            elements.append(Spacer(1, 10*mm))
            
            # Таблица данных
            table_data = [
                ['№', 'Наименование детали', 'Ширина, мм', 'Высота, мм', 'Площадь, м²']
            ]
            
            unfoldings = area_data.get('unfoldings', [])
            
            for idx, unfolding in enumerate(unfoldings, 1):
                table_data.append([
                    str(idx),
                    unfolding['name'],
                    f"{unfolding['width']:.1f}",
                    f"{unfolding['height']:.1f}",
                    f"{unfolding['area_m2']:.4f}"
                ])
            
            # Итоговая строка
            total_area = area_data.get('total_area', 0)
            table_data.append([
                '',
                'ИТОГО:',
                '',
                '',
                f"{total_area:.4f}"
            ])
            
            # Создаем таблицу
            table = Table(table_data, colWidths=[15*mm, 80*mm, 30*mm, 30*mm, 30*mm])
            
            # Стиль таблицы
            table.setStyle(TableStyle([
                # Заголовок
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976D2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), font_name),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                
                # Данные
                ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -2), colors.black),
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Номер
                ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),  # Числа
                ('FONTNAME', (0, 1), (-1, -1), font_name),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
                
                # Итоговая строка
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#FFC107')),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.black),
                ('FONTNAME', (0, -1), (-1, -1), font_name),
                ('FONTSIZE', (0, -1), (-1, -1), 10),
                ('ALIGN', (1, -1), (1, -1), 'RIGHT'),
                ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
            ]))
            
            elements.append(table)
            
            # Дополнительная информация
            elements.append(Spacer(1, 10*mm))
            
            info_text = f"Всего деталей: {len(unfoldings)}<br/>"
            info_text += f"Общая площадь листового металла: {total_area:.4f} м²<br/>"
            info_text += f"Расчет выполнен автоматически системой автоматизации КОМПАС-3D"
            
            info = Paragraph(info_text, styles['Normal'])
            elements.append(info)
            
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
        
        return result
    
    def _get_dimensions_from_dxf(self, dxf_path: str) -> tuple:
        """Получение габаритов из DXF файла"""
        try:
            import ezdxf
            
            doc = ezdxf.readfile(dxf_path)
            msp = doc.modelspace()
            
            # Находим габариты
            min_x = min_y = float('inf')
            max_x = max_y = float('-inf')
            
            for entity in msp:
                try:
                    if hasattr(entity, 'dxf'):
                        if hasattr(entity.dxf, 'start') and hasattr(entity.dxf, 'end'):
                            min_x = min(min_x, entity.dxf.start.x, entity.dxf.end.x)
                            max_x = max(max_x, entity.dxf.start.x, entity.dxf.end.x)
                            min_y = min(min_y, entity.dxf.start.y, entity.dxf.end.y)
                            max_y = max(max_y, entity.dxf.start.y, entity.dxf.end.y)
                        elif hasattr(entity.dxf, 'center'):
                            center = entity.dxf.center
                            radius = getattr(entity.dxf, 'radius', 0)
                            min_x = min(min_x, center.x - radius)
                            max_x = max(max_x, center.x + radius)
                            min_y = min(min_y, center.y - radius)
                            max_y = max(max_y, center.y + radius)
                except:
                    pass
            
            if min_x != float('inf'):
                width = abs(max_x - min_x)
                height = abs(max_y - min_y)
                return (width, height)
            
            return (None, None)
            
        except:
            return (None, None)

