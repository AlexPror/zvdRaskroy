#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Визуализатор раскроя с правильным масштабом
Для PDF и для GUI (tkinter Canvas)
"""

import logging
from typing import Dict, List, Tuple
from datetime import datetime
from pathlib import Path

# Для PDF
try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Для GUI
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Рендерер реальных контуров DXF
try:
    from components.dxf_contour_renderer import DXFContourRenderer
    HAS_CONTOUR_RENDERER = True
except ImportError:
    HAS_CONTOUR_RENDERER = False


class NestingVisualizer:
    """
    Визуализация раскроя с правильным масштабом
    """
    
    SHEET_WIDTH = 2500  # мм
    SHEET_HEIGHT = 1250  # мм
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Рендерер реальных контуров DXF
        if HAS_CONTOUR_RENDERER:
            self.contour_renderer = DXFContourRenderer()
        else:
            self.contour_renderer = None
    
        # Цвета для деталей
        self.part_colors_hex = [
            '#90CAF9',  # Светло-голубой
            '#A5D6A7',  # Светло-зеленый
            '#FFF59D',  # Светло-желтый
            '#F48FB1',  # Светло-розовый
            '#CE93D8',  # Светло-фиолетовый
            '#80DEEA',  # Светло-бирюзовый
        ]
        
        self.part_colors_rgb = [
            (144, 202, 249),
            (165, 214, 167),
            (255, 245, 157),
            (244, 143, 177),
            (206, 147, 216),
            (128, 222, 234),
        ]
    
    def create_pdf_visualization(self,
                                nesting_result: Dict,
                                waste_pieces: List[Dict],
                                project_name: str,
                                order_number: str = None,
                                output_file: str = None,
                                cipher: str = None) -> str:
        """
        Создание PDF с визуализацией в ПРАВИЛЬНОМ МАСШТАБЕ
        """
        
        if not REPORTLAB_AVAILABLE:
            self.logger.warning("ReportLab недоступен")
            return None
        
        if not output_file:
            output_file = f"Раскрой_{project_name}_{order_number or 'проект'}.pdf"
        
        try:
            # Регистрируем шрифт
            try:
                pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf'))
                pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:/Windows/Fonts/arialbd.ttf'))
                font_name = 'Arial'
                font_bold = 'Arial-Bold'
            except:
                font_name = 'Helvetica'
                font_bold = 'Helvetica-Bold'
            
            # Используем альбомную ориентацию для горизонтального листа
            c = canvas.Canvas(output_file, pagesize=landscape(A4))
            page_width, page_height = landscape(A4)
            
            # Заголовок
            c.setFont(font_bold, 16)
            c.drawString(30, page_height - 30, "Раскладка деталей")
            
            # Шифр конвектора
            if cipher:
                c.setFont(font_bold, 12)
                c.drawString(30, page_height - 50, f"Конвектор: {cipher}")
            
            # Номер заказа
            if order_number:
                c.setFont(font_name, 11)
                y_pos = page_height - 70 if cipher else page_height - 50
                c.drawString(30, y_pos, f"Заказ: {order_number}")
            
            # Дата
            c.setFont(font_name, 9)
            y_pos = page_height - 85 if (cipher and order_number) else (page_height - 65 if (cipher or order_number) else page_height - 45)
            c.drawString(30, y_pos, f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
            
            # Сводка справа
            c.setFont(font_bold, 11)
            c.drawString(page_width - 250, page_height - 30, "СВОДКА:")
            
            c.setFont(font_name, 9)
            c.drawString(page_width - 250, page_height - 45, f"Листов: {nesting_result['sheets_needed']}")
            c.drawString(page_width - 250, page_height - 58, f"Использование: {nesting_result['utilization_percent']:.1f}%")
            c.drawString(page_width - 250, page_height - 71, f"Обрезки: {nesting_result['overall_waste_percent']:.1f}%")
            
            # Рисуем каждый лист
            y_start = page_height - 100
            MIN_BOTTOM_MARGIN = 50  # Минимальный отступ снизу
            
            for sheet in nesting_result['sheets']:
                # Проверяем, хватит ли места для листа (~300-400 единиц высоты)
                if y_start < 350:  # Новая страница если места мало
                    c.showPage()
                    y_start = page_height - 50
                    
                    # Повторяем заголовки на новой странице
                    c.setFont(font_bold, 16)
                    c.drawString(30, page_height - 30, "Раскладка деталей")
                    if cipher:
                        c.setFont(font_bold, 12)
                        c.drawString(30, page_height - 50, f"Конвектор: {cipher}")
                    y_start = page_height - 80
                
                # Заголовок листа
                c.setFont(font_bold, 12)
                c.drawString(30, y_start, f"ЛИСТ №{sheet['number']} (2500×1250 мм)")
                
                c.setFont(font_name, 9)
                # Вычисляем утилизацию на месте
                sheet_area = self.SHEET_WIDTH * self.SHEET_HEIGHT  # мм²
                parts_area = sum(p['width'] * p['height'] for p in sheet['parts'])
                utilization = (parts_area / sheet_area) * 100 if sheet_area > 0 else 0
                waste = 100 - utilization
                
                info_text = (f"Деталей: {len(sheet['parts'])} | " +
                           f"Использование: {utilization:.1f}% | " +
                           f"Обрезки: {waste:.1f}%")
                c.drawString(30, y_start - 15, info_text)
                
                y_start -= 35
                
                # ПРАВИЛЬНЫЙ МАСШТАБ для листа 2500×1250
                # Доступная ширина для рисования: ~750 мм (page_width - отступы)
                available_width = page_width - 60  # мм в PDF points
                available_height = 800  # Увеличиваем высоту для лучшего масштаба
                
                # Масштаб рассчитываем по ширине листа
                # Лист 2500 мм должен поместиться в available_width
                scale_w = available_width / self.SHEET_WIDTH  # 2500 мм
                scale_h = available_height / self.SHEET_HEIGHT  # 1250 мм
                
                # Берем минимальный масштаб, чтобы поместился
                scale = min(scale_w, scale_h)
                
                # Размеры листа в PDF
                sheet_w = self.SHEET_WIDTH * scale
                sheet_h = self.SHEET_HEIGHT * scale
                
                # Позиция листа
                sheet_x = 30
                sheet_y = y_start - sheet_h
                
                # Проверка места
                if sheet_y < 50:
                    c.showPage()
                    y_start = page_height - 50
                    sheet_y = y_start - sheet_h
                
                # Рисуем контур листа
                c.setStrokeColor(colors.black)
                c.setLineWidth(2)
                c.setFillColor(colors.lightgrey)
                c.rect(sheet_x, sheet_y, sheet_w, sheet_h, fill=1, stroke=1)
                
                # Подпись размера листа
                c.setFont(font_name, 8)
                c.setFillColor(colors.black)
                c.drawString(sheet_x, sheet_y - 12, "2500 мм")
                c.drawRightString(sheet_x + sheet_w, sheet_y + sheet_h + 10, "1250 мм")
                
                # Рисуем детали В МАСШТАБЕ
                HALF_GAP = 2.5  # мм - половина зазора между деталями
                FULL_GAP = 5.0  # мм - полный зазор между деталями
                
                for idx, part in enumerate(sheet['parts']):
                    # Координаты и размеры из rectpack УЖЕ ВКЛЮЧАЮТ зазор 2.5мм со всех сторон
                    x_mm_with_gap = part['x']
                    y_mm_with_gap = part['y']
                    w_mm_with_gap = part['width']
                    h_mm_with_gap = part['height']
                    
                    # Вычисляем РЕАЛЬНЫЕ координаты и размеры детали (без зазора)
                    x_mm_real = x_mm_with_gap + HALF_GAP
                    y_mm_real = y_mm_with_gap + HALF_GAP
                    w_mm_real = w_mm_with_gap - 2 * HALF_GAP  # Убираем зазор с обеих сторон
                    h_mm_real = h_mm_with_gap - 2 * HALF_GAP
                    
                    # Переводим в координаты PDF с учетом масштаба
                    x_pdf = sheet_x + x_mm_real * scale
                    y_pdf = sheet_y + y_mm_real * scale
                    w_pdf = w_mm_real * scale
                    h_pdf = h_mm_real * scale
                    
                    # Цвет детали
                    color_hex = self.part_colors_hex[idx % len(self.part_colors_hex)]
                    color = colors.HexColor(color_hex)
                    rgb_color = self.part_colors_rgb[idx % len(self.part_colors_rgb)]
                    rgb_normalized = (rgb_color[0]/255, rgb_color[1]/255, rgb_color[2]/255)
                    
                    # Пытаемся отрисовать реальный контур из DXF
                    real_contour_drawn = False
                    if self.contour_renderer and part.get('filepath'):
                        try:
                            contour = self.contour_renderer.get_contour_polyline(part['filepath'])
                            if contour:
                                # Рисуем реальный контур детали (БЕЗ зазора)
                                self.contour_renderer.draw_contour_on_pdf(
                                    c, contour, x_pdf, y_pdf, scale, rgb_normalized
                                )
                                real_contour_drawn = True
                        except Exception as e:
                            self.logger.debug(f"Не удалось отрисовать контур {part['name']}: {e}")
                    
                    # Fallback: если контур не получилось нарисовать - рисуем прямоугольник БЕЗ зазора
                    if not real_contour_drawn:
                        c.setFillColor(color)
                        c.setStrokeColor(colors.black)
                        c.setLineWidth(0.8)
                        c.rect(x_pdf, y_pdf, w_pdf, h_pdf, fill=1, stroke=1)
            
            # Подпись детали
                    c.setFillColor(colors.black)
                    c.setFont(font_name, 7)
                    
                    # Имя (сокращенное, если нужно)
                    name = part['name']
                    if len(name) > 30:
                        name = name[:27] + "..."
            
            # Размеры детали (РЕАЛЬНЫЕ, без зазора)
                    size_text = f"{w_mm_real:.0f}x{h_mm_real:.0f}"
                    
                    # Центрируем текст в детали
                    text_x = x_pdf + w_pdf / 2
                    text_y = y_pdf + h_pdf / 2
                    
                    # Если деталь достаточно большая, пишем текст
                    if w_pdf > 30 and h_pdf > 20:
                        c.drawCentredString(text_x, text_y + 5, name)
                        c.drawCentredString(text_x, text_y - 5, size_text)
                        
                        if part.get('rotated'):
                            c.setFillColor(colors.red)
                            c.drawCentredString(text_x, text_y - 15, "[90°]")
                            c.setFillColor(colors.black)
                    else:
                        # Маленькая деталь - номер рядом
                        c.setFont(font_name, 6)
                        c.drawString(x_pdf + 2, y_pdf + 2, f"#{idx+1}")
                
                # ВИЗУАЛИЗАЦИЯ ЗАЗОРОВ между деталями
                # Собираем все детали с реальными координатами (без зазора)
                real_parts = []
                for part in sheet['parts']:
                    real_parts.append({
                        'x': part['x'] + HALF_GAP,
                        'y': part['y'] + HALF_GAP,
                        'width': part['width'] - 2 * HALF_GAP,
                        'height': part['height'] - 2 * HALF_GAP,
                        'x_with_gap': part['x'],
                        'y_with_gap': part['y'],
                        'w_with_gap': part['width'],
                        'h_with_gap': part['height']
                    })
                
                # Рисуем красные линии показывающие зазор 5мм
                c.setStrokeColor(colors.red)
                c.setDash(3, 3)  # Пунктирная линия
                c.setLineWidth(1.5)
                
                for i, p1 in enumerate(real_parts):
                    x1_real = sheet_x + p1['x'] * scale
                    y1_real = sheet_y + p1['y'] * scale
                    w1_real = p1['width'] * scale
                    h1_real = p1['height'] * scale
                    
                    for j, p2 in enumerate(real_parts):
                        if i >= j:
                            continue
                        
                        x2_real = sheet_x + p2['x'] * scale
                        y2_real = sheet_y + p2['y'] * scale
                        w2_real = p2['width'] * scale
                        h2_real = p2['height'] * scale
                        
                        gap_threshold = FULL_GAP * scale * 1.2  # Порог для определения соседних деталей
                        
                        # Вертикальный зазор (детали рядом слева-справа)
                        if abs((x1_real + w1_real) - x2_real) < gap_threshold:
                            # Проверяем вертикальное перекрытие
                            y_top = max(y1_real, y2_real)
                            y_bottom = min(y1_real + h1_real, y2_real + h2_real)
                            if y_bottom > y_top:  # Есть перекрытие
                                # Линия ровно посередине между деталями
                                gap_x = (x1_real + w1_real + x2_real) / 2
                                c.line(gap_x, y_top, gap_x, y_bottom)
                        
                        # Горизонтальный зазор (детали рядом сверху-снизу)
                        if abs((y1_real + h1_real) - y2_real) < gap_threshold:
                            # Проверяем горизонтальное перекрытие
                            x_left = max(x1_real, x2_real)
                            x_right = min(x1_real + w1_real, x2_real + w2_real)
                            if x_right > x_left:  # Есть перекрытие
                                # Линия ровно посередине между деталями
                                gap_y = (y1_real + h1_real + y2_real) / 2
                                c.line(x_left, gap_y, x_right, gap_y)
                
                c.setDash()  # Сбрасываем пунктир
                
                # Легенда о зазорах (всегда показываем)
                legend_y = sheet_y - 25
                c.setFont(font_bold, 9)
                c.setFillColor(colors.black)
                c.drawString(sheet_x, legend_y, "⚠ ВАЖНО:")
                legend_y -= 12
                
                c.setFont(font_name, 8)
                c.setStrokeColor(colors.red)
                c.setDash(3, 3)
                c.setLineWidth(1.5)
                c.line(sheet_x, legend_y - 4, sheet_x + 20, legend_y - 4)
                c.setDash()  # Сброс пунктира
                c.drawString(sheet_x + 25, legend_y - 6, "← Красная пунктирная линия = зазор 5мм между деталями (учтён автоматически)")
                
                legend_y -= 15
                
                # Легенда для маленьких деталей
                if any(p['width'] * scale < 30 or p['height'] * scale < 20 for p in sheet['parts']):
                    legend_y -= 5
                    c.setFont(font_bold, 9)
                    c.setFillColor(colors.black)
                    c.drawString(sheet_x, legend_y, "Маленькие детали:")
                    legend_y -= 12
                    
                    c.setFont(font_name, 7)
                    for idx, part in enumerate(sheet['parts']):
                        w_pdf = part['width'] * scale
                        h_pdf = part['height'] * scale
                        
                        if w_pdf < 30 or h_pdf < 20:
                            c.drawString(sheet_x, legend_y, 
                                       f"#{idx+1}: {part['name']} ({part['width']:.0f}×{part['height']:.0f})")
                            legend_y -= 10
                
                y_start = min(sheet_y, y_start - sheet_h) - 60
            
            # Страница с обрезками
            if waste_pieces:
                c.showPage()
                c.setFont(font_bold, 14)
                c.drawString(30, page_height - 30, "ОБРЕЗКИ ДЛЯ МАРКИРОВКИ")
                
                c.setFont(font_name, 10)
                c.drawString(30, page_height - 50, f"Всего обрезков: {len(waste_pieces)}")
                c.drawString(30, page_height - 65, "Маркируйте несмываемым маркером!")
                
                y_pos = page_height - 90
                
                # Заголовки таблицы
                c.setFont(font_bold, 9)
                c.drawString(30, y_pos, "№")
                c.drawString(80, y_pos, "Лист")
                c.drawString(130, y_pos, "Размер (мм)")
                c.drawString(250, y_pos, "Площадь (м²)")
                c.drawString(350, y_pos, "Использовать")
                c.drawString(450, y_pos, "Место для метки")
                
                y_pos -= 3
                c.setLineWidth(1)
                c.line(30, y_pos, page_width - 30, y_pos)
                y_pos -= 10
                
                # Данные
                c.setFont(font_name, 9)
                for waste in waste_pieces:
                    if y_pos < 50:
                        c.showPage()
                        y_pos = page_height - 50
                    
                    c.drawString(30, y_pos, waste['id'])
                    c.drawString(80, y_pos, f"№{waste['sheet_number']}")
                    c.drawString(130, y_pos, f"{waste['width_mm']:.0f} × {waste['height_mm']:.0f}")
                    c.drawString(250, y_pos, f"{waste['area_m2']:.4f}")
                    c.drawString(350, y_pos, "ДА" if waste['usable'] else "НЕТ")
                    
                    # Рамка для маркера
                    c.setStrokeColor(colors.grey)
                    c.setLineWidth(0.5)
                    c.rect(450, y_pos - 3, 100, 15)
                    
                    y_pos -= 20
            
            c.save()
            self.logger.info(f"✓ PDF визуализация создана: {output_file}")
            return output_file
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания PDF: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_image_for_gui(self, 
                            nesting_result: Dict,
                            canvas_width: int = 800,
                            canvas_height: int = 600) -> Image:
        """
        Создание изображения раскроя для отображения в GUI
        
        Returns:
            PIL Image для отображения в tkinter Canvas
        """
        
        if not PIL_AVAILABLE:
            self.logger.warning("PIL недоступен")
            return None
        
        try:
            # Создаем изображение
            img = Image.new('RGB', (canvas_width, canvas_height), color='white')
            draw = ImageDraw.Draw(img)
            
            # Пытаемся загрузить шрифт
            try:
                font_title = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 16)
                font_normal = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 10)
                font_small = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 8)
            except:
                font_title = ImageFont.load_default()
                font_normal = ImageFont.load_default()
                font_small = ImageFont.load_default()
            
            # Заголовок
            draw.text((10, 10), "РАСКЛАДКА НА ЛИСТЫ", fill='black', font=font_title)
            
            # Сводка
            summary = (f"Листов: {nesting_result['sheets_needed']} | " +
                      f"Использование: {nesting_result['utilization_percent']:.1f}% | " +
                      f"Обрезки: {nesting_result['overall_waste_percent']:.1f}%")
            draw.text((10, 35), summary, fill='blue', font=font_normal)
            
            # Рисуем листы
            y_offset = 60
            sheets_per_row = 2 if nesting_result['sheets_needed'] > 1 else 1
            
            for idx, sheet in enumerate(nesting_result['sheets']):
                # Позиция листа
                col = idx % sheets_per_row
                row = idx // sheets_per_row
                
                margin = 20
                available_width = (canvas_width - (sheets_per_row + 1) * margin) / sheets_per_row
                available_height = canvas_height - y_offset - 40
                
                # ПРАВИЛЬНЫЙ масштаб с сохранением пропорций
                scale_w = available_width / self.SHEET_WIDTH
                scale_h = available_height / self.SHEET_HEIGHT
                scale = min(scale_w, scale_h)
                
                # Размеры листа в пикселях
                sheet_w = self.SHEET_WIDTH * scale
                sheet_h = self.SHEET_HEIGHT * scale
                
                # Координаты листа
                sheet_x = margin + col * (available_width + margin)
                sheet_y = y_offset + row * (sheet_h + 50)
                
                # Рисуем контур листа
                draw.rectangle(
                    [sheet_x, sheet_y, sheet_x + sheet_w, sheet_y + sheet_h],
                    outline='black',
                    fill='#f0f0f0',
                    width=2
                )
                
                # Подписи размеров листа
                draw.text((sheet_x, sheet_y - 15), "2500 мм", fill='black', font=font_small)
                draw.text((sheet_x + sheet_w - 40, sheet_y + sheet_h + 5), "1250 мм", fill='black', font=font_small)
                
                # Номер листа
                draw.text((sheet_x + 5, sheet_y + 5), f"ЛИСТ #{sheet['number']}", fill='red', font=font_normal)
                
                # Рисуем детали В МАСШТАБЕ
                for part_idx, part in enumerate(sheet['parts']):
                    x_mm = part['x']
                    y_mm = part['y']
                    w_mm = part['width']
                    h_mm = part['height']
                    
                    # Переводим в пиксели
                    x_px = sheet_x + x_mm * scale
                    y_px = sheet_y + y_mm * scale
                    w_px = w_mm * scale
                    h_px = h_mm * scale
                    
                    # Цвет детали
                    color_rgb = self.part_colors_rgb[part_idx % len(self.part_colors_rgb)]
                    
                    # Рисуем прямоугольник детали
                    draw.rectangle(
                        [x_px, y_px, x_px + w_px, y_px + h_px],
                        outline='black',
                        fill=color_rgb,
                        width=1
                    )
                    
                    # Подпись детали (если помещается)
                    if w_px > 40 and h_px > 25:
                        # Сокращенное имя
                        name = part['name'][:25] if len(part['name']) > 25 else part['name']
                        
                        text_x = x_px + w_px / 2
                        text_y = y_px + h_px / 2
                        
                        # Размер текста для центрирования
                        bbox = draw.textbbox((0, 0), name, font=font_small)
                        text_w = bbox[2] - bbox[0]
                        
                        draw.text((text_x - text_w / 2, text_y - 10), name, fill='black', font=font_small)
                        draw.text((text_x - 20, text_y), f"{w_mm:.0f}×{h_mm:.0f}", fill='black', font=font_small)
                        
                        if part.get('rotated'):
                            draw.text((text_x - 10, text_y + 10), "[90°]", fill='red', font=font_small)
            
            return img
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания изображения: {e}")
            import traceback
            traceback.print_exc()
            return None


if __name__ == "__main__":
    # Тест визуализатора
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    print("Модуль визуализатора готов!")
    print("\nИспользование:")
    print("  visualizer = NestingVisualizer()")
    print("  pdf = visualizer.create_pdf_visualization(nesting_result, waste_pieces, 'project', 'order')")
    print("  img = visualizer.create_image_for_gui(nesting_result)")
