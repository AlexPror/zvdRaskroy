#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Рендерер DXF в изображения СТРОГО В МАСШТАБЕ
"""

import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple
import logging

try:
    import ezdxf
    from ezdxf import recover
    EZDXF_AVAILABLE = True
except ImportError:
    EZDXF_AVAILABLE = False

try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class DXFImageRenderer:
    """
    Конвертер DXF файлов в изображения СТРОГО В МАСШТАБЕ
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        
        # Папка для кэширования изображений
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(tempfile.gettempdir()) / "dxf_images"
        
        self.cache_dir.mkdir(exist_ok=True)
        
        # Проверяем доступность библиотек
        self.ezdxf_available = EZDXF_AVAILABLE
        self.pil_available = PIL_AVAILABLE
        self.matplotlib_available = MATPLOTLIB_AVAILABLE
        
        if not self.ezdxf_available:
            self.logger.warning("ezdxf не установлен - DXF контуры недоступны")
        if not self.pil_available:
            self.logger.warning("PIL не установлен - изображения недоступны")
        if not self.matplotlib_available:
            self.logger.warning("matplotlib не установлен - рендеринг недоступен")
    
    def get_dxf_image_scaled(self, dxf_path: str, width_mm: float, height_mm: float, 
                           scale_mm_per_pixel: float = 0.1) -> Optional[str]:
        """
        Получить изображение DXF файла СТРОГО В МАСШТАБЕ
        
        Args:
            dxf_path: Путь к DXF файлу
            width_mm: Ширина детали в мм
            height_mm: Высота детали в мм  
            scale_mm_per_pixel: Масштаб - мм на пиксель (0.5 = 0.5 мм/пиксель)
            
        Returns:
            Путь к созданному изображению или None
        """
        if not self.ezdxf_available or not self.matplotlib_available:
            return None
        
        dxf_path = Path(dxf_path)
        if not dxf_path.exists():
            return None
        
        # Рассчитываем размеры изображения в пикселях СТРОГО ПО МАСШТАБУ
        image_width_px = int(width_mm / scale_mm_per_pixel)
        image_height_px = int(height_mm / scale_mm_per_pixel)
        
        # Создаем имя файла кэша с учетом масштаба
        cache_name = f"{dxf_path.stem}_{width_mm:.1f}x{height_mm:.1f}mm_{scale_mm_per_pixel:.2f}scale.png"
        cache_path = self.cache_dir / cache_name
        
        # Проверяем кэш
        if cache_path.exists():
            return str(cache_path)
        
        try:
            # Загружаем DXF
            doc, auditor = recover.readfile(str(dxf_path))
            if auditor.has_errors:
                self.logger.warning(f"DXF файл {dxf_path} имеет ошибки")
            
            # Получаем границы
            msp = doc.modelspace()
            if not msp:
                return None
            
            # Находим границы всех объектов в мм
            min_x = min_y = float('inf')
            max_x = max_y = float('-inf')
            
            for entity in msp:
                if hasattr(entity, 'dxf'):
                    if hasattr(entity.dxf, 'start') and hasattr(entity.dxf, 'end'):
                        # Линия
                        start = entity.dxf.start
                        end = entity.dxf.end
                        min_x = min(min_x, start.x, end.x)
                        max_x = max(max_x, start.x, end.x)
                        min_y = min(min_y, start.y, end.y)
                        max_y = max(max_y, start.y, end.y)
                    elif hasattr(entity.dxf, 'center') and hasattr(entity.dxf, 'radius'):
                        # Круг
                        center = entity.dxf.center
                        radius = entity.dxf.radius
                        min_x = min(min_x, center.x - radius)
                        max_x = max(max_x, center.x + radius)
                        min_y = min(min_y, center.y - radius)
                        max_y = max(max_y, center.y + radius)
            
            if min_x == float('inf'):
                # Если не нашли объекты, используем размеры по умолчанию
                min_x, min_y = 0, 0
                max_x, max_y = width_mm, height_mm
            
            # Рассчитываем размеры DXF в мм
            dxf_width_mm = max_x - min_x
            dxf_height_mm = max_y - min_y
            
            if dxf_width_mm <= 0 or dxf_height_mm <= 0:
                return None
            
            # Создаем фигуру matplotlib СТРОГО В МАСШТАБЕ с ВЫСОКИМ КАЧЕСТВОМ
            # Увеличиваем DPI для лучшего качества
            high_dpi = 300  # Высокое разрешение
            fig, ax = plt.subplots(1, 1, figsize=(image_width_px/high_dpi, image_height_px/high_dpi), dpi=high_dpi)
            
            # Устанавливаем границы СТРОГО ПО МАСШТАБУ
            ax.set_xlim(min_x, max_x)
            ax.set_ylim(min_y, max_y)
            ax.set_aspect('equal')
            ax.axis('off')
            
            # Рисуем объекты с УЛУЧШЕННЫМ КАЧЕСТВОМ
            for entity in msp:
                if hasattr(entity, 'dxf'):
                    if hasattr(entity.dxf, 'start') and hasattr(entity.dxf, 'end'):
                        # Линия с улучшенным качеством
                        start = entity.dxf.start
                        end = entity.dxf.end
                        ax.plot([start.x, end.x], [start.y, end.y], 'k-', 
                               linewidth=1.0, antialiased=True, solid_capstyle='round')
                    elif hasattr(entity.dxf, 'center') and hasattr(entity.dxf, 'radius'):
                        # Круг с улучшенным качеством
                        center = entity.dxf.center
                        radius = entity.dxf.radius
                        circle = patches.Circle((center.x, center.y), radius, 
                                              fill=False, edgecolor='black', linewidth=1.0)
                        ax.add_patch(circle)
            
            # Сохраняем как изображение СТРОГО В МАСШТАБЕ с ВЫСОКИМ КАЧЕСТВОМ
            plt.tight_layout()
            plt.savefig(str(cache_path), bbox_inches='tight', pad_inches=0, 
                       facecolor='white', edgecolor='none', dpi=high_dpi,
                       format='png')  # ИСПРАВЛЕНО: убраны quality и optimize (для matplotlib недоступны)
            plt.close(fig)
            
            self.logger.info(f"Создано изображение DXF в масштабе: {width_mm:.1f}x{height_mm:.1f} мм = {image_width_px}x{image_height_px} пикселей")
            
            return str(cache_path)
            
        except Exception as e:
            self.logger.error(f"Ошибка создания изображения из DXF {dxf_path}: {e}")
            return None
    
    def draw_scaled_image_on_canvas(self, canvas, dxf_path: str, x: int, y: int, 
                                  width_mm: float, height_mm: float, 
                                  scale_mm_per_pixel: float = 0.5):
        """
        Нарисовать DXF изображение на Tkinter Canvas СТРОГО В МАСШТАБЕ
        
        Args:
            canvas: Tkinter Canvas
            dxf_path: Путь к DXF файлу
            x, y: Координаты на canvas (пиксели)
            width_mm, height_mm: Размеры детали в мм
            scale_mm_per_pixel: Масштаб canvas (мм на пиксель)
        """
        if not self.pil_available:
            return
        
        try:
            from PIL import ImageTk
            
            # Получаем изображение DXF в правильном масштабе
            image_path = self.get_dxf_image_scaled(dxf_path, width_mm, height_mm, scale_mm_per_pixel)
            if not image_path or not Path(image_path).exists():
                return
            
            # Рассчитываем размеры на canvas в пикселях
            canvas_width_px = int(width_mm / scale_mm_per_pixel)
            canvas_height_px = int(height_mm / scale_mm_per_pixel)
            
            # Загружаем и масштабируем изображение с ВЫСОКИМ КАЧЕСТВОМ
            with Image.open(image_path) as img:
                # Улучшаем качество изображения
                img = img.convert('RGBA')
                
                # Растягиваем на нужные размеры СТРОГО ПО МАСШТАБУ с высоким качеством
                resized = img.resize((canvas_width_px, canvas_height_px), Image.Resampling.LANCZOS)
                
                # Дополнительное улучшение качества
                resized = resized.filter(Image.Filter.SHARPEN)
                
                photo = ImageTk.PhotoImage(resized)
                
                # Создаем изображение на canvas
                canvas.create_image(x + canvas_width_px//2, y + canvas_height_px//2, 
                                 image=photo, anchor='center')
                
                # Сохраняем ссылку чтобы изображение не удалилось
                canvas.image_refs = getattr(canvas, 'image_refs', [])
                canvas.image_refs.append(photo)
                
        except Exception as e:
            self.logger.error(f"Ошибка рисования DXF изображения на canvas: {e}")
    
    def draw_scaled_image_on_pdf(self, pdf_canvas, dxf_path: str, x: float, y: float, 
                               width_mm: float, height_mm: float, 
                               scale_mm_per_point: float = 0.352778):
        """
        Нарисовать DXF изображение в PDF СТРОГО В МАСШТАБЕ
        
        Args:
            pdf_canvas: ReportLab canvas
            dxf_path: Путь к DXF файлу
            x, y: Координаты (в точках PDF)
            width_mm, height_mm: Размеры детали в мм
            scale_mm_per_point: Масштаб PDF (мм на точку PDF, по умолчанию 0.352778)
        """
        try:
            from reportlab.lib.utils import ImageReader
            from reportlab.lib.units import mm
            
            # Получаем изображение DXF в правильном масштабе
            image_path = self.get_dxf_image_scaled(dxf_path, width_mm, height_mm, 0.5)  # 0.5 мм/пиксель
            if not image_path or not Path(image_path).exists():
                return
            
            # Рассчитываем размеры в точках PDF СТРОГО ПО МАСШТАБУ
            width_points = width_mm / scale_mm_per_point
            height_points = height_mm / scale_mm_per_point
            
            # Загружаем изображение
            pdf_canvas.drawImage(
                ImageReader(image_path),
                x, y, width_points, height_points,
                preserveAspectRatio=False,  # Растягиваем на весь прямоугольник
                mask='auto'
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка рисования DXF изображения в PDF: {e}")
    
    def clear_cache(self):
        """Очистить кэш изображений"""
        try:
            import shutil
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(exist_ok=True)
                self.logger.info("Кэш изображений очищен")
        except Exception as e:
            self.logger.error(f"Ошибка очистки кэша: {e}")


# Глобальный экземпляр для использования в других модулях
dxf_image_renderer = DXFImageRenderer()