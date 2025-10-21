#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Рендеринг реальных контуров DXF
Вместо прямоугольников показывает настоящую геометрию детали
"""

import logging
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import ezdxf
from ezdxf.addons import geo


class DXFContourRenderer:
    """
    Рендеринг реальных контуров из DXF файлов
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.contours_cache = {}  # Кэш загруженных контуров
    
    def get_contour_polyline(self, dxf_path: str) -> Optional[List[Tuple[float, float]]]:
        """
        Извлечь контур детали из DXF как список точек (полилиния)
        
        Args:
            dxf_path: Путь к DXF файлу
            
        Returns:
            Список точек [(x, y), ...] или None
        """
        try:
            # Проверяем кэш
            if dxf_path in self.contours_cache:
                return self.contours_cache[dxf_path]
            
            # Читаем DXF
            doc = ezdxf.readfile(dxf_path)
            msp = doc.modelspace()
            
            # Собираем все линии и полилинии
            points = []
            
            # LINE entities
            for line in msp.query('LINE'):
                points.append((line.dxf.start.x, line.dxf.start.y))
                points.append((line.dxf.end.x, line.dxf.end.y))
            
            # LWPOLYLINE entities
            for lwpolyline in msp.query('LWPOLYLINE'):
                with lwpolyline.points() as pts:
                    for point in pts:
                        points.append((point[0], point[1]))
            
            # POLYLINE entities
            for polyline in msp.query('POLYLINE'):
                for vertex in polyline.vertices:
                    points.append((vertex.dxf.location.x, vertex.dxf.location.y))
            
            # ARC entities (аппроксимируем дугами с точками)
            for arc in msp.query('ARC'):
                # Аппроксимируем дугу 20 точками
                import math
                start_angle = math.radians(arc.dxf.start_angle)
                end_angle = math.radians(arc.dxf.end_angle)
                radius = arc.dxf.radius
                center = (arc.dxf.center.x, arc.dxf.center.y)
                
                num_segments = 20
                for i in range(num_segments + 1):
                    angle = start_angle + (end_angle - start_angle) * i / num_segments
                    x = center[0] + radius * math.cos(angle)
                    y = center[1] + radius * math.sin(angle)
                    points.append((x, y))
            
            # CIRCLE entities (аппроксимируем окружность)
            for circle in msp.query('CIRCLE'):
                import math
                radius = circle.dxf.radius
                center = (circle.dxf.center.x, circle.dxf.center.y)
                
                num_segments = 36
                for i in range(num_segments + 1):
                    angle = 2 * math.pi * i / num_segments
                    x = center[0] + radius * math.cos(angle)
                    y = center[1] + radius * math.sin(angle)
                    points.append((x, y))
            
            if not points:
                self.logger.warning(f"[WARN] Контур не найден в {Path(dxf_path).name}")
                return None
            
            # Нормализуем контур (смещаем к (0,0))
            min_x = min(p[0] for p in points)
            min_y = min(p[1] for p in points)
            
            normalized = [(p[0] - min_x, p[1] - min_y) for p in points]
            
            # Сохраняем в кэш
            self.contours_cache[dxf_path] = normalized
            
            self.logger.info(f"[OK] Контур загружен: {Path(dxf_path).name}, {len(normalized)} точек")
            return normalized
            
        except Exception as e:
            self.logger.error(f"[ERROR] Ошибка чтения контура {dxf_path}: {e}")
            return None
    
    def draw_contour_on_canvas(self, canvas, contour: List[Tuple[float, float]], 
                              x: float, y: float, scale: float, 
                              fill_color: str = '#90CAF9', outline_color: str = 'black'):
        """
        Нарисовать контур на Tkinter Canvas
        
        Args:
            canvas: Tkinter Canvas
            contour: Список точек контура
            x, y: Позиция на Canvas
            scale: Масштаб отображения
            fill_color: Цвет заливки
            outline_color: Цвет контура
        """
        if not contour or len(contour) < 2:
            return None
        
        # Преобразуем точки контура в координаты Canvas
        canvas_points = []
        for px, py in contour:
            canvas_x = x + px * scale
            canvas_y = y + py * scale
            canvas_points.extend([canvas_x, canvas_y])
        
        # Рисуем полигон
        polygon_id = canvas.create_polygon(
            canvas_points,
            fill=fill_color,
            outline=outline_color,
            width=1
        )
        
        return polygon_id
    
    def draw_contour_on_pdf(self, pdf_canvas, contour: List[Tuple[float, float]], 
                           x: float, y: float, scale: float, 
                           fill_color: Tuple[float, float, float] = (0.5, 0.7, 0.9)):
        """
        Нарисовать контур в PDF (reportlab)
        
        Args:
            pdf_canvas: reportlab Canvas
            contour: Список точек контура
            x, y: Позиция в PDF
            scale: Масштаб отображения
            fill_color: RGB цвет (0-1, 0-1, 0-1)
        """
        if not contour or len(contour) < 2:
            return
        
        from reportlab.lib import colors as pdf_colors
        
        # Создаем path для отрисовки
        path = pdf_canvas.beginPath()
        
        # Первая точка
        first_point = contour[0]
        path.moveTo(x + first_point[0] * scale, y + first_point[1] * scale)
        
        # Остальные точки
        for px, py in contour[1:]:
            path.lineTo(x + px * scale, y + py * scale)
        
        # Закрываем контур
        path.close()
        
        # Рисуем с заливкой
        pdf_canvas.setFillColorRGB(*fill_color)
        pdf_canvas.setStrokeColor(pdf_colors.black)
        pdf_canvas.setLineWidth(0.5)
        pdf_canvas.drawPath(path, fill=1, stroke=1)


if __name__ == "__main__":
    # Тест рендерера
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    print("="*70)
    print("ТЕСТ РЕНДЕРЕРА DXF КОНТУРОВ")
    print("="*70)
    
    renderer = DXFContourRenderer()
    
    # Пример: загрузка контура из DXF
    test_dxf = Path("test.dxf")
    if test_dxf.exists():
        contour = renderer.get_contour_polyline(str(test_dxf))
        if contour:
            print(f"\n[OK] Контур загружен: {len(contour)} точек")
            print(f"  Первая точка: {contour[0]}")
            print(f"  Последняя точка: {contour[-1]}")
        else:
            print("\n[ERROR] Не удалось загрузить контур")
    else:
        print("\n[INFO] Тестовый файл не найден")
        print("  Создайте test.dxf для тестирования")

