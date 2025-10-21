"""
Компонент для оптимальной раскладки разверток на листы металла

Задача раскроя (Cutting Stock Problem)
Лист: 2500 × 1250 мм
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple
import math


class SheetNestingOptimizer:
    """Оптимизатор раскладки разверток на листы"""
    
    # Стандартный лист
    SHEET_WIDTH = 2500   # мм
    SHEET_HEIGHT = 1250  # мм
    SHEET_AREA = SHEET_WIDTH * SHEET_HEIGHT  # 3,125,000 мм²
    
    # Зазоры для резки
    CUT_GAP = 2.5  # мм - ПОЛОВИНА зазора (между деталями будет 2.5+2.5=5мм)
    EDGE_MARGIN = 10  # мм от края листа
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def optimize_layout(self, area_data: Dict) -> Dict:
        """
        Оптимизация раскладки разверток на листы
        
        Args:
            area_data: Данные о развертках (из UnfoldingAreaCalculator)
        
        Returns:
            dict: {
                'sheets_needed': int,
                'utilization_percent': float,
                'parts_layout': [...],
                'scraps': [...],
                'reusable_scraps': [...]
            }
        """
        result = {
            'success': False,
            'sheets_needed': 0,
            'total_parts_area_mm2': 0.0,
            'total_used_area_mm2': 0.0,
            'total_scrap_area_mm2': 0.0,
            'utilization_percent': 0.0,
            'sheets': [],
            'scraps': [],
            'reusable_scraps': [],
            'unusable_scraps': []
        }
        
        if not area_data.get('success') or not area_data.get('parts'):
            result['error'] = "Нет данных о развертках"
            return result
        
        # Подготавливаем список деталей с учетом количества
        parts_to_place = []
        
        for part in area_data['parts']:
            quantity = part.get('quantity', 1)
            
            for i in range(quantity):
                parts_to_place.append({
                    'name': part['name'],
                    'width': part['width_mm'],
                    'height': part['height_mm'],
                    'area': part['area_mm2'],
                    'instance': i + 1,
                    'total_quantity': quantity
                })
        
        result['total_parts_area_mm2'] = sum(p['area'] for p in parts_to_place)
        
        self.logger.info(f"\n{'='*70}")
        self.logger.info(f"ОПТИМИЗАЦИЯ РАСКРОЯ")
        self.logger.info(f"{'='*70}")
        self.logger.info(f"Лист: {self.SHEET_WIDTH} × {self.SHEET_HEIGHT} мм")
        self.logger.info(f"Площадь листа: {self.SHEET_AREA:,.0f} мм² ({self.SHEET_AREA/1_000_000:.3f} м²)")
        self.logger.info(f"Деталей для размещения: {len(parts_to_place)}")
        self.logger.info(f"Общая площадь деталей: {result['total_parts_area_mm2']:,.0f} мм²")
        
        # Сортируем детали по площади (большие сначала)
        parts_sorted = sorted(parts_to_place, key=lambda x: x['area'], reverse=True)
        
        # АЛГОРИТМ: First Fit Decreasing (FFD) с упрощенной упаковкой
        sheets = []
        current_sheet = {
            'number': 1,
            'parts': [],
            'used_area': 0,
            'remaining_area': self.SHEET_AREA,
            'current_x': self.EDGE_MARGIN,  # Текущая позиция X
            'current_y': self.EDGE_MARGIN,  # Текущая позиция Y
            'row_height': 0  # Высота текущего ряда
        }
        
        usable_width = self.SHEET_WIDTH - 2 * self.EDGE_MARGIN
        usable_height = self.SHEET_HEIGHT - 2 * self.EDGE_MARGIN
        
        for part in parts_sorted:
            part_width = part['width'] + self.CUT_GAP
            part_height = part['height'] + self.CUT_GAP
            part_area = part_width * part_height
            
            # Пытаемся разместить деталь на текущем листе
            placed = False
            
            # Проверяем, помещается ли справа в текущем ряду
            if (current_sheet['current_x'] + part_width <= usable_width + self.EDGE_MARGIN and
                current_sheet['current_y'] + part_height <= usable_height + self.EDGE_MARGIN):
                # Помещается в текущий ряд
                part['x'] = current_sheet['current_x']
                part['y'] = current_sheet['current_y']
                
                current_sheet['parts'].append(part)
                current_sheet['used_area'] += part_area
                current_sheet['remaining_area'] -= part_area
                
                # Обновляем позицию
                current_sheet['current_x'] += part_width
                current_sheet['row_height'] = max(current_sheet['row_height'], part_height)
                
                placed = True
            
            # Если не поместилась справа, пробуем новый ряд
            elif (self.EDGE_MARGIN + part_width <= usable_width + self.EDGE_MARGIN and
                  current_sheet['current_y'] + current_sheet['row_height'] + part_height <= usable_height + self.EDGE_MARGIN):
                # Переходим на новый ряд
                current_sheet['current_y'] += current_sheet['row_height']
                current_sheet['current_x'] = self.EDGE_MARGIN
                current_sheet['row_height'] = 0
                
                # Размещаем деталь
                part['x'] = current_sheet['current_x']
                part['y'] = current_sheet['current_y']
                
                current_sheet['parts'].append(part)
                current_sheet['used_area'] += part_area
                current_sheet['remaining_area'] -= part_area
                
                current_sheet['current_x'] += part_width
                current_sheet['row_height'] = part_height
                
                placed = True
            
            # Если не поместилась - новый лист
            if not placed:
                sheets.append(current_sheet)
                
                # Создаем новый лист
                current_sheet = {
                    'number': len(sheets) + 1,
                    'parts': [],
                    'used_area': 0,
                    'remaining_area': self.SHEET_AREA,
                    'current_x': self.EDGE_MARGIN,
                    'current_y': self.EDGE_MARGIN,
                    'row_height': 0
                }
                
                # Размещаем деталь на новом листе
                part['x'] = current_sheet['current_x']
                part['y'] = current_sheet['current_y']
                
                current_sheet['parts'].append(part)
                current_sheet['used_area'] += part_area
                current_sheet['remaining_area'] -= part_area
                
                current_sheet['current_x'] += part_width
                current_sheet['row_height'] = part_height
        
        # Добавляем последний лист
        if current_sheet['parts']:
            sheets.append(current_sheet)
        
        result['sheets'] = sheets
        result['sheets_needed'] = len(sheets)
        result['total_used_area_mm2'] = sum(s['used_area'] for s in sheets)
        result['total_scrap_area_mm2'] = (len(sheets) * self.SHEET_AREA) - result['total_used_area_mm2']
        result['utilization_percent'] = (result['total_used_area_mm2'] / (len(sheets) * self.SHEET_AREA)) * 100 if sheets else 0
        
        # Анализ обрезков
        for sheet in sheets:
            scrap_area = sheet['remaining_area']
            
            if scrap_area > 0:
                # Оцениваем размер обрезка (грубо, как квадрат)
                scrap_side = math.sqrt(scrap_area)
                
                scrap_info = {
                    'sheet_number': sheet['number'],
                    'area_mm2': scrap_area,
                    'area_m2': scrap_area / 1_000_000,
                    'approx_size': f"~{scrap_side:.0f} × {scrap_side:.0f} мм",
                    'reusable': scrap_area >= 100_000  # >= 0.1 м² считаем пригодным
                }
                
                result['scraps'].append(scrap_info)
                
                if scrap_info['reusable']:
                    result['reusable_scraps'].append(scrap_info)
                else:
                    result['unusable_scraps'].append(scrap_info)
        
        result['success'] = True
        
        # Логи
        self.logger.info(f"\n{'='*70}")
        self.logger.info(f"РЕЗУЛЬТАТ РАСКРОЯ:")
        self.logger.info(f"{'='*70}")
        self.logger.info(f"Листов требуется: {result['sheets_needed']}")
        self.logger.info(f"Использование материала: {result['utilization_percent']:.1f}%")
        self.logger.info(f"Обрезков: {len(result['scraps'])}")
        self.logger.info(f"  - Пригодных для переиспользования: {len(result['reusable_scraps'])}")
        self.logger.info(f"  - Непригодных (мелкие): {len(result['unusable_scraps'])}")
        
        for i, sheet in enumerate(sheets, 1):
            self.logger.info(f"\nЛИСТ №{i}:")
            self.logger.info(f"  Деталей: {len(sheet['parts'])}")
            self.logger.info(f"  Использовано: {sheet['used_area']/1_000_000:.4f} м² ({sheet['used_area']/self.SHEET_AREA*100:.1f}%)")
            self.logger.info(f"  Обрезок: {sheet['remaining_area']/1_000_000:.4f} м²")
            
            # Список деталей на листе
            for part in sheet['parts']:
                inst_str = f" [{part['instance']}/{part['total_quantity']}]" if part['total_quantity'] > 1 else ""
                self.logger.info(f"    • {part['name']}{inst_str}: {part['width']:.0f}×{part['height']:.0f} мм")
        
        return result
    
    def generate_nesting_pdf(self, project_name: str, area_data: Dict, nesting_data: Dict, 
                            output_path: str, order_number: str = None) -> Dict:
        """
        Генерация PDF с раскладкой на листы
        
        Args:
            project_name: Название проекта
            area_data: Данные о площадях
            nesting_data: Данные о раскладке
            output_path: Путь для PDF
            order_number: Номер заказа
        
        Returns:
            dict: {'success': bool, 'pdf_path': str}
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
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            
            # Шрифты (для кириллицы)
            try:
                # Попытка 1: Arial (есть в Windows)
                pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf'))
                pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:/Windows/Fonts/arialbd.ttf'))
                font_name = 'Arial'
                font_name_bold = 'Arial-Bold'
            except:
                try:
                    # Попытка 2: Times New Roman
                    pdfmetrics.registerFont(TTFont('TimesNewRoman', 'C:/Windows/Fonts/times.ttf'))
                    pdfmetrics.registerFont(TTFont('TimesNewRoman-Bold', 'C:/Windows/Fonts/timesbd.ttf'))
                    font_name = 'TimesNewRoman'
                    font_name_bold = 'TimesNewRoman-Bold'
                except:
                    # Fallback
                    font_name = 'Helvetica'
                    font_name_bold = 'Helvetica-Bold'
            
            doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm,
                                   topMargin=20*mm, bottomMargin=20*mm)
            
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontName=font_name_bold,
                                        fontSize=18, textColor=colors.HexColor('#1f4788'),
                                        spaceAfter=12, alignment=TA_CENTER)
            
            heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontName=font_name_bold,
                                          fontSize=14, textColor=colors.HexColor('#2c5aa0'),
                                          spaceAfter=6, spaceBefore=12)
            
            normal_style = ParagraphStyle('Normal', parent=styles['Normal'], fontName=font_name,
                                         fontSize=10, spaceAfter=6)
            
            story = []
            
            # === СТРАНИЦА 1: ОБЩАЯ ИНФОРМАЦИЯ ===
            story.append(Paragraph("РАСЧЕТ ПЛОЩАДЕЙ И РАСКРОЙ РАЗВЕРТОК", title_style))
            story.append(Paragraph(f"Проект: {project_name}", heading_style))
            
            from datetime import datetime
            story.append(Paragraph(f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}", normal_style))
            
            if order_number:
                order_style = ParagraphStyle('Order', parent=normal_style, fontName=font_name_bold,
                                            fontSize=12, textColor=colors.HexColor('#d32f2f'))
                story.append(Paragraph(f"<b>Номер заказа: {order_number}</b>", order_style))
            
            story.append(Spacer(1, 12))
            
            # Сводка
            story.append(Paragraph("Сводка:", heading_style))
            
            summary_data = [
                ['Параметр', 'Значение'],
                ['Листов требуется', f"{nesting_data['sheets_needed']} шт"],
                ['Размер листа', f"{self.SHEET_WIDTH} × {self.SHEET_HEIGHT} мм"],
                ['Площадь листа', f"{self.SHEET_AREA/1_000_000:.3f} м²"],
                ['Общая площадь деталей', f"{nesting_data['total_parts_area_mm2']/1_000_000:.4f} м²"],
                ['Использование материала', f"{nesting_data['utilization_percent']:.1f}%"],
                ['Обрезков всего', f"{len(nesting_data['scraps'])} шт"],
                ['Обрезков пригодных', f"{len(nesting_data['reusable_scraps'])} шт"],
            ]
            
            summary_table = Table(summary_data, colWidths=[80*mm, 80*mm])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), font_name_bold),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTNAME', (0, 1), (-1, -1), font_name),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
            ]))
            
            story.append(summary_table)
            story.append(PageBreak())
            
            # === СТРАНИЦА 2: РАСКЛАДКА ПО ЛИСТАМ ===
            story.append(Paragraph("РАСКЛАДКА ПО ЛИСТАМ", title_style))
            
            # Импортируем визуализатор
            try:
                from .nesting_visualizer import NestingVisualizer
                visualizer = NestingVisualizer()
                use_visualization = True
            except:
                use_visualization = False
                self.logger.warning("Визуализатор не доступен")
            
            for sheet in nesting_data['sheets']:
                story.append(Paragraph(f"Лист №{sheet['number']}", heading_style))
                
                # Добавляем визуализацию схемы листа
                if use_visualization:
                    try:
                        drawing = visualizer.create_advanced_visualization(
                            sheet,
                            sheet_width_mm=self.SHEET_WIDTH,
                            sheet_height_mm=self.SHEET_HEIGHT,
                            with_coordinates=True
                        )
                        story.append(Spacer(1, 5))
                        story.append(drawing)
                        story.append(Spacer(1, 10))
                    except Exception as e:
                        self.logger.warning(f"Ошибка создания визуализации: {e}")
                
                # Таблица деталей на листе
                parts_data = [[
                    Paragraph('№', ParagraphStyle('h', fontName=font_name_bold, fontSize=10)),
                    Paragraph('Деталь', ParagraphStyle('h', fontName=font_name_bold, fontSize=10)),
                    Paragraph('Размер (мм)', ParagraphStyle('h', fontName=font_name_bold, fontSize=10)),
                    Paragraph('Площадь (м²)', ParagraphStyle('h', fontName=font_name_bold, fontSize=10)),
                    Paragraph('Экз.', ParagraphStyle('h', fontName=font_name_bold, fontSize=10))
                ]]
                
                for i, part in enumerate(sheet['parts'], 1):
                    inst_str = f"{part['instance']}/{part['total_quantity']}" if part['total_quantity'] > 1 else "1/1"
                    parts_data.append([
                        Paragraph(str(i), ParagraphStyle('n', fontName=font_name, fontSize=9)),
                        Paragraph(part['name'], ParagraphStyle('n', fontName=font_name, fontSize=9)),
                        Paragraph(f"{part['width']:.0f} × {part['height']:.0f}", ParagraphStyle('n', fontName=font_name, fontSize=9)),
                        Paragraph(f"{part['area']/1_000_000:.4f}", ParagraphStyle('n', fontName=font_name, fontSize=9)),
                        Paragraph(inst_str, ParagraphStyle('n', fontName=font_name, fontSize=9))
                    ])
                
                # Итого по листу
                parts_data.append([
                    '',
                    Paragraph('ИТОГО:', ParagraphStyle('b', fontName=font_name_bold, fontSize=10)),
                    '',
                    Paragraph(f"{sheet['used_area']/1_000_000:.4f}", ParagraphStyle('b', fontName=font_name_bold, fontSize=10)),
                    ''
                ])
                
                parts_data.append([
                    '',
                    Paragraph('Обрезок:', ParagraphStyle('b', fontName=font_name_bold, fontSize=10)),
                    '',
                    Paragraph(f"{sheet['remaining_area']/1_000_000:.4f}", ParagraphStyle('b', fontName=font_name, fontSize=10)),
                    Paragraph(f"({sheet['remaining_area']/self.SHEET_AREA*100:.1f}%)", ParagraphStyle('b', fontName=font_name, fontSize=9))
                ])
                
                sheet_table = Table(parts_data, colWidths=[15*mm, 70*mm, 35*mm, 30*mm, 20*mm])
                sheet_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), font_name_bold),
                    ('BACKGROUND', (0, 1), (-1, -3), colors.lightgrey),
                    ('BACKGROUND', (0, -2), (-1, -2), colors.HexColor('#e0e0e0')),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fff9c4')),
                    ('FONTNAME', (0, -2), (-1, -1), font_name_bold),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                
                story.append(sheet_table)
                story.append(Spacer(1, 12))
            
            story.append(PageBreak())
            
            # === СТРАНИЦА 3: ОБРЕЗКИ ===
            story.append(Paragraph("АНАЛИЗ ОБРЕЗКОВ", title_style))
            
            # Пригодные обрезки
            if nesting_data['reusable_scraps']:
                story.append(Paragraph("Пригодные для переиспользования:", heading_style))
                
                reusable_data = [[
                    Paragraph('Лист №', ParagraphStyle('h', fontName=font_name_bold, fontSize=10)),
                    Paragraph('Площадь (м²)', ParagraphStyle('h', fontName=font_name_bold, fontSize=10)),
                    Paragraph('Примерный размер', ParagraphStyle('h', fontName=font_name_bold, fontSize=10)),
                    Paragraph('Рекомендация', ParagraphStyle('h', fontName=font_name_bold, fontSize=10))
                ]]
                
                for scrap in nesting_data['reusable_scraps']:
                    recommendation = ""
                    if scrap['area_m2'] >= 0.5:
                        recommendation = "Отлично! Можно кроить небольшие детали"
                    elif scrap['area_m2'] >= 0.2:
                        recommendation = "Хорошо! Для мелких деталей"
                    else:
                        recommendation = "Для заплаток"
                    
                    reusable_data.append([
                        Paragraph(str(scrap['sheet_number']), ParagraphStyle('n', fontName=font_name, fontSize=9)),
                        Paragraph(f"{scrap['area_m2']:.4f}", ParagraphStyle('n', fontName=font_name, fontSize=9)),
                        Paragraph(scrap['approx_size'], ParagraphStyle('n', fontName=font_name, fontSize=9)),
                        Paragraph(recommendation, ParagraphStyle('n', fontName=font_name, fontSize=9))
                    ])
                
                reusable_table = Table(reusable_data, colWidths=[20*mm, 30*mm, 40*mm, 80*mm])
                reusable_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('FONTNAME', (0, 0), (-1, 0), font_name_bold),
                ]))
                
                story.append(reusable_table)
                story.append(Spacer(1, 12))
            
            # Непригодные обрезки
            if nesting_data['unusable_scraps']:
                story.append(Paragraph("Непригодные обрезки (< 0.1 м²):", heading_style))
                
                unusable_data = [['Лист №', 'Площадь (м²)']]
                
                for scrap in nesting_data['unusable_scraps']:
                    unusable_data.append([
                        str(scrap['sheet_number']),
                        f"{scrap['area_m2']:.4f}"
                    ])
                
                unusable_table = Table(unusable_data, colWidths=[30*mm, 40*mm])
                unusable_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f44336')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('FONTNAME', (0, 0), (-1, 0), font_name_bold),
                ]))
                
                story.append(unusable_table)
            
            # Генерируем PDF
            doc.build(story)
            
            result['success'] = True
            self.logger.info(f"\n✓ PDF с раскроем создан: {output_path}")
            
        except ImportError:
            result['error'] = "Библиотека reportlab не установлена"
            self.logger.error(result['error'])
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Ошибка создания PDF: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
        
        return result


if __name__ == "__main__":
    # Тестирование
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    # Тестовые данные
    test_area_data = {
        'success': True,
        'parts': [
            {'name': '001 - Корпус', 'width_mm': 600, 'height_mm': 800, 'area_mm2': 480000, 'quantity': 1},
            {'name': '002 - Стенка', 'width_mm': 300, 'height_mm': 600, 'area_mm2': 180000, 'quantity': 2},
            {'name': '003 - Распорка', 'width_mm': 200, 'height_mm': 400, 'area_mm2': 80000, 'quantity': 3},
        ]
    }
    
    optimizer = SheetNestingOptimizer()
    nesting_result = optimizer.optimize_layout(test_area_data)
    
    print(f"\n\nРезультат: {nesting_result}")
    
    # Генерация PDF
    pdf_result = optimizer.generate_nesting_pdf(
        "ZVD.LITE.TEST",
        test_area_data,
        nesting_result,
        "test_nesting.pdf",
        "А-TEST-12345"
    )
    
    print(f"\nPDF: {pdf_result}")

