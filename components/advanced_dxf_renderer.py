#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ПРОДВИНУТЫЙ рендерер DXF с использованием современных технологий
"""

import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List, Dict
import logging

try:
    import ezdxf
    from ezdxf import recover
    EZDXF_AVAILABLE = True
except ImportError:
    EZDXF_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import cairo
    CAIRO_AVAILABLE = True
except ImportError:
    CAIRO_AVAILABLE = False

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import svgwrite
    SVGWRITE_AVAILABLE = True
except ImportError:
    SVGWRITE_AVAILABLE = False


class AdvancedDXFRenderer:
    """
    ПРОДВИНУТЫЙ рендерер DXF с поддержкой множества технологий
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        
        # Папка для кэширования
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(tempfile.gettempdir()) / "advanced_dxf_images"
        
        self.cache_dir.mkdir(exist_ok=True)
        
        # Проверяем доступность библиотек
        self.ezdxf_available = EZDXF_AVAILABLE
        self.pil_available = PIL_AVAILABLE
        self.cairo_available = CAIRO_AVAILABLE
        self.matplotlib_available = MATPLOTLIB_AVAILABLE
        self.svgwrite_available = SVGWRITE_AVAILABLE
        
        self.logger.info(f"Доступные технологии:")
        self.logger.info(f"  - ezdxf: {self.ezdxf_available}")
        self.logger.info(f"  - PIL: {self.pil_available}")
        self.logger.info(f"  - Cairo: {self.cairo_available}")
        self.logger.info(f"  - Matplotlib: {self.matplotlib_available}")
        self.logger.info(f"  - SVGWrite: {self.svgwrite_available}")
    
    def render_dxf_cairo(self, dxf_path: str, width_mm: float, height_mm: float, 
                        scale_mm_per_pixel: float = 0.1) -> Optional[str]:
        """
        Рендеринг DXF через Cairo (ВЫСОКОЕ КАЧЕСТВО)
        """
        if not self.cairo_available or not self.ezdxf_available:
            return None
        
        dxf_path = Path(dxf_path)
        if not dxf_path.exists():
            return None
        
        # Рассчитываем размеры
        width_px = int(width_mm / scale_mm_per_pixel)
        height_px = int(height_mm / scale_mm_per_pixel)
        
        # Создаем имя файла кэша
        cache_name = f"{dxf_path.stem}_cairo_{width_mm:.1f}x{height_mm:.1f}mm.png"
        cache_path = self.cache_dir / cache_name
        
        if cache_path.exists():
            return str(cache_path)
        
        try:
            # Загружаем DXF
            doc, auditor = recover.readfile(str(dxf_path))
            if auditor.has_errors:
                self.logger.warning(f"DXF файл {dxf_path} имеет ошибки")
            
            msp = doc.modelspace()
            if not msp:
                return None
            
            # Создаем поверхность Cairo
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width_px, height_px)
            ctx = cairo.Context(surface)
            
            # Настраиваем контекст для высокого качества
            ctx.set_antialias(cairo.ANTIALIAS_SUBPIXEL)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            
            # Белый фон
            ctx.set_source_rgb(1, 1, 1)
            ctx.paint()
            
            # Находим границы
            min_x = min_y = float('inf')
            max_x = max_y = float('-inf')
            
            for entity in msp:
                if hasattr(entity, 'dxf'):
                    if hasattr(entity.dxf, 'start') and hasattr(entity.dxf, 'end'):
                        start = entity.dxf.start
                        end = entity.dxf.end
                        min_x = min(min_x, start.x, end.x)
                        max_x = max(max_x, start.x, end.x)
                        min_y = min(min_y, start.y, end.y)
                        max_y = max(max_y, start.y, end.y)
            
            if min_x == float('inf'):
                min_x, min_y = 0, 0
                max_x, max_y = width_mm, height_mm
            
            # Масштабирование
            scale_x = width_px / (max_x - min_x)
            scale_y = height_px / (max_y - min_y)
            scale = min(scale_x, scale_y)
            
            # Смещение для центрирования
            offset_x = (width_px - (max_x - min_x) * scale) / 2
            offset_y = (height_px - (max_y - min_y) * scale) / 2
            
            # Рисуем объекты
            ctx.set_source_rgb(0, 0, 0)  # Черный цвет
            ctx.set_line_width(1.0)
            
            for entity in msp:
                if hasattr(entity, 'dxf'):
                    if hasattr(entity.dxf, 'start') and hasattr(entity.dxf, 'end'):
                        # Линия
                        start = entity.dxf.start
                        end = entity.dxf.end
                        
                        x1 = offset_x + (start.x - min_x) * scale
                        y1 = offset_y + (start.y - min_y) * scale
                        x2 = offset_x + (end.x - min_x) * scale
                        y2 = offset_y + (end.y - min_y) * scale
                        
                        ctx.move_to(x1, y1)
                        ctx.line_to(x2, y2)
                        ctx.stroke()
                    
                    elif hasattr(entity.dxf, 'center') and hasattr(entity.dxf, 'radius'):
                        # Круг
                        center = entity.dxf.center
                        radius = entity.dxf.radius
                        
                        cx = offset_x + (center.x - min_x) * scale
                        cy = offset_y + (center.y - min_y) * scale
                        r = radius * scale
                        
                        ctx.arc(cx, cy, r, 0, 2 * 3.14159)
                        ctx.stroke()
            
            # Сохраняем изображение
            surface.write_to_png(str(cache_path))
            surface.finish()
            
            self.logger.info(f"Cairo рендеринг: {width_mm:.1f}x{height_mm:.1f} мм = {width_px}x{height_px} пикселей")
            return str(cache_path)
            
        except Exception as e:
            self.logger.error(f"Ошибка Cairo рендеринга: {e}")
            return None
    
    def render_dxf_svg(self, dxf_path: str, width_mm: float, height_mm: float) -> Optional[str]:
        """
        Рендеринг DXF в SVG (ВЕКТОРНЫЙ ФОРМАТ)
        """
        if not self.svgwrite_available or not self.ezdxf_available:
            return None
        
        dxf_path = Path(dxf_path)
        if not dxf_path.exists():
            return None
        
        # Создаем имя файла кэша
        cache_name = f"{dxf_path.stem}_svg_{width_mm:.1f}x{height_mm:.1f}mm.svg"
        cache_path = self.cache_dir / cache_name
        
        if cache_path.exists():
            return str(cache_path)
        
        try:
            # Загружаем DXF
            doc, auditor = recover.readfile(str(dxf_path))
            if auditor.has_errors:
                self.logger.warning(f"DXF файл {dxf_path} имеет ошибки")
            
            msp = doc.modelspace()
            if not msp:
                return None
            
            # Создаем SVG
            dwg = svgwrite.Drawing(str(cache_path), size=(f"{width_mm}mm", f"{height_mm}mm"))
            dwg.viewbox(0, 0, width_mm, height_mm)
            
            # Находим границы
            min_x = min_y = float('inf')
            max_x = max_y = float('-inf')
            
            for entity in msp:
                if hasattr(entity, 'dxf'):
                    if hasattr(entity.dxf, 'start') and hasattr(entity.dxf, 'end'):
                        start = entity.dxf.start
                        end = entity.dxf.end
                        min_x = min(min_x, start.x, end.x)
                        max_x = max(max_x, start.x, end.x)
                        min_y = min(min_y, start.y, end.y)
                        max_y = max(max_y, start.y, end.y)
            
            if min_x == float('inf'):
                min_x, min_y = 0, 0
                max_x, max_y = width_mm, height_mm
            
            # Масштабирование
            scale_x = width_mm / (max_x - min_x)
            scale_y = height_mm / (max_y - min_y)
            scale = min(scale_x, scale_y)
            
            # Смещение для центрирования
            offset_x = (width_mm - (max_x - min_x) * scale) / 2
            offset_y = (height_mm - (max_y - min_y) * scale) / 2
            
            # Рисуем объекты
            for entity in msp:
                if hasattr(entity, 'dxf'):
                    if hasattr(entity.dxf, 'start') and hasattr(entity.dxf, 'end'):
                        # Линия
                        start = entity.dxf.start
                        end = entity.dxf.end
                        
                        x1 = offset_x + (start.x - min_x) * scale
                        y1 = offset_y + (start.y - min_y) * scale
                        x2 = offset_x + (end.x - min_x) * scale
                        y2 = offset_y + (end.y - min_y) * scale
                        
                        dwg.add(dwg.line((x1, y1), (x2, y2), stroke='black', stroke_width=0.1))
                    
                    elif hasattr(entity.dxf, 'center') and hasattr(entity.dxf, 'radius'):
                        # Круг
                        center = entity.dxf.center
                        radius = entity.dxf.radius
                        
                        cx = offset_x + (center.x - min_x) * scale
                        cy = offset_y + (center.y - min_y) * scale
                        r = radius * scale
                        
                        dwg.add(dwg.circle(center=(cx, cy), r=r, fill='none', stroke='black', stroke_width=0.1))
            
            # Сохраняем SVG
            dwg.save()
            
            self.logger.info(f"SVG рендеринг: {width_mm:.1f}x{height_mm:.1f} мм")
            return str(cache_path)
            
        except Exception as e:
            self.logger.error(f"Ошибка SVG рендеринга: {e}")
            return None
    
    def render_dxf_optimized_matplotlib(self, dxf_path: str, width_mm: float, height_mm: float, 
                                     scale_mm_per_pixel: float = 0.05) -> Optional[str]:
        """
        ОПТИМИЗИРОВАННЫЙ рендеринг через Matplotlib
        """
        if not self.matplotlib_available or not self.ezdxf_available:
            return None
        
        dxf_path = Path(dxf_path)
        if not dxf_path.exists():
            return None
        
        # Рассчитываем размеры
        width_px = int(width_mm / scale_mm_per_pixel)
        height_px = int(height_mm / scale_mm_per_pixel)
        
        # Создаем имя файла кэша
        cache_name = f"{dxf_path.stem}_opt_{width_mm:.1f}x{height_mm:.1f}mm.png"
        cache_path = self.cache_dir / cache_name
        
        if cache_path.exists():
            return str(cache_path)
        
        try:
            # Загружаем DXF
            doc, auditor = recover.readfile(str(dxf_path))
            if auditor.has_errors:
                self.logger.warning(f"DXF файл {dxf_path} имеет ошибки")
            
            msp = doc.modelspace()
            if not msp:
                return None
            
            # Создаем фигуру с ОЧЕНЬ высоким качеством
            fig, ax = plt.subplots(1, 1, figsize=(width_px/300, height_px/300), dpi=300)
            
            # Находим границы
            min_x = min_y = float('inf')
            max_x = max_y = float('-inf')
            
            for entity in msp:
                if hasattr(entity, 'dxf'):
                    if hasattr(entity.dxf, 'start') and hasattr(entity.dxf, 'end'):
                        start = entity.dxf.start
                        end = entity.dxf.end
                        min_x = min(min_x, start.x, end.x)
                        max_x = max(max_x, start.x, end.x)
                        min_y = min(min_y, start.y, end.y)
                        max_y = max(max_y, start.y, end.y)
            
            if min_x == float('inf'):
                min_x, min_y = 0, 0
                max_x, max_y = width_mm, height_mm
            
            # Устанавливаем границы
            ax.set_xlim(min_x, max_x)
            ax.set_ylim(min_y, max_y)
            ax.set_aspect('equal')
            ax.axis('off')
            
            # Рисуем объекты с ОЧЕНЬ высоким качеством
            for entity in msp:
                if hasattr(entity, 'dxf'):
                    if hasattr(entity.dxf, 'start') and hasattr(entity.dxf, 'end'):
                        # Линия
                        start = entity.dxf.start
                        end = entity.dxf.end
                        ax.plot([start.x, end.x], [start.y, end.y], 'k-', 
                               linewidth=0.5, antialiased=True, solid_capstyle='round')
                    
                    elif hasattr(entity.dxf, 'center') and hasattr(entity.dxf, 'radius'):
                        # Круг
                        center = entity.dxf.center
                        radius = entity.dxf.radius
                        circle = patches.Circle((center.x, center.y), radius, 
                                              fill=False, edgecolor='black', linewidth=0.5)
                        ax.add_patch(circle)
            
            # Сохраняем с высоким качеством (убираем quality для matplotlib)
            plt.tight_layout()
            plt.savefig(str(cache_path), bbox_inches='tight', pad_inches=0, 
                       facecolor='white', edgecolor='none', dpi=300,
                       format='png')
            plt.close(fig)
            
            self.logger.info(f"Оптимизированный Matplotlib: {width_mm:.1f}x{height_mm:.1f} мм = {width_px}x{height_px} пикселей")
            return str(cache_path)
            
        except Exception as e:
            self.logger.error(f"Ошибка оптимизированного Matplotlib: {e}")
            return None
    
    def get_best_rendering(self, dxf_path: str, width_mm: float, height_mm: float, 
                          scale_mm_per_pixel: float = 0.1) -> Optional[str]:
        """
        Получить ЛУЧШИЙ рендеринг из доступных технологий
        """
        # Приоритет технологий (от лучшего к худшему)
        methods = [
            ("Cairo", self.render_dxf_cairo),
            ("SVG", self.render_dxf_svg),
            ("Optimized Matplotlib", self.render_dxf_optimized_matplotlib)
        ]
        
        for method_name, method_func in methods:
            try:
                result = method_func(dxf_path, width_mm, height_mm, scale_mm_per_pixel)
                if result and Path(result).exists():
                    self.logger.info(f"Использован {method_name} для {Path(dxf_path).name}")
                    return result
            except Exception as e:
                self.logger.warning(f"Ошибка {method_name}: {e}")
                continue
        
        self.logger.error(f"Не удалось отрендерить {dxf_path} ни одним методом")
        return None
    
    def clear_cache(self):
        """Очистить кэш"""
        try:
            import shutil
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(exist_ok=True)
                self.logger.info("Кэш очищен")
        except Exception as e:
            self.logger.error(f"Ошибка очистки кэша: {e}")


# Глобальный экземпляр
advanced_dxf_renderer = AdvancedDXFRenderer()
