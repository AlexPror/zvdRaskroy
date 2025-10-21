#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ГИБРИДНЫЙ рендерер DXF - простые прямоугольники с подписями для безопасности
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


class HybridDXFRenderer:
    """
    ГИБРИДНЫЙ рендерер - простые прямоугольники с информацией о файле
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        
        # Папка для кэширования
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(tempfile.gettempdir()) / "hybrid_dxf_images"
        
        self.cache_dir.mkdir(exist_ok=True)
        
        # Проверяем доступность библиотек
        self.ezdxf_available = EZDXF_AVAILABLE
        self.pil_available = PIL_AVAILABLE
        
        self.logger.info(f"Гибридный рендерер инициализирован:")
        self.logger.info(f"  - ezdxf: {self.ezdxf_available}")
        self.logger.info(f"  - PIL: {self.pil_available}")
    
    def get_dxf_info(self, dxf_path: str) -> Dict:
        """
        Получить информацию о DXF файле для подписи
        """
        if not self.ezdxf_available:
            return {'filename': Path(dxf_path).name, 'entities': 0, 'layers': 0}
        
        try:
            doc, auditor = recover.readfile(str(dxf_path))
            if auditor.has_errors:
                self.logger.warning(f"DXF файл {dxf_path} имеет ошибки")
            
            msp = doc.modelspace()
            if not msp:
                return {'filename': Path(dxf_path).name, 'entities': 0, 'layers': 0}
            
            # Считаем объекты
            entities_count = len(list(msp))
            layers_count = len(doc.layers)
            
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
                max_x, max_y = 100, 100
            
            return {
                'filename': Path(dxf_path).name,
                'entities': entities_count,
                'layers': layers_count,
                'bounds': {
                    'min_x': min_x,
                    'min_y': min_y,
                    'max_x': max_x,
                    'max_y': max_y,
                    'width': max_x - min_x,
                    'height': max_y - min_y
                }
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка анализа DXF {dxf_path}: {e}")
            return {'filename': Path(dxf_path).name, 'entities': 0, 'layers': 0}
    
    def create_hybrid_image(self, dxf_path: str, width_mm: float, height_mm: float, 
                          scale_mm_per_pixel: float = 0.5) -> Optional[str]:
        """
        Создать ГИБРИДНОЕ изображение - простой прямоугольник с информацией
        """
        if not self.pil_available:
            return None
        
        dxf_path = Path(dxf_path)
        if not dxf_path.exists():
            return None
        
        # Рассчитываем размеры
        width_px = int(width_mm / scale_mm_per_pixel)
        height_px = int(height_mm / scale_mm_per_pixel)
        
        # Создаем имя файла кэша
        cache_name = f"{dxf_path.stem}_hybrid_{width_mm:.1f}x{height_mm:.1f}mm.png"
        cache_path = self.cache_dir / cache_name
        
        if cache_path.exists():
            return str(cache_path)
        
        try:
            # Получаем информацию о DXF
            dxf_info = self.get_dxf_info(dxf_path)
            
            # Создаем изображение
            img = Image.new('RGBA', (width_px, height_px), (255, 255, 255, 255))
            draw = ImageDraw.Draw(img)
            
            # Рисуем ПРОСТОЙ прямоугольник с рамкой
            border_width = max(2, width_px // 100)  # Толщина рамки
            draw.rectangle(
                [border_width, border_width, width_px - border_width, height_px - border_width],
                fill=(240, 240, 240, 255),  # Светло-серый фон
                outline=(0, 0, 0, 255),     # Черная рамка
                width=border_width
            )
            
            # Добавляем ПОДПИСИ для безопасности
            try:
                # Пытаемся загрузить шрифт
                font_large = ImageFont.truetype("arial.ttf", size=max(12, width_px // 20))
                font_small = ImageFont.truetype("arial.ttf", size=max(8, width_px // 30))
            except:
                # Fallback на стандартный шрифт
                font_large = ImageFont.load_default()
                font_small = ImageFont.load_default()
            
            # Название файла (укороченное)
            filename = dxf_info['filename']
            if len(filename) > 20:
                filename = filename[:17] + "..."
            
            # Размеры текста
            text_bbox = draw.textbbox((0, 0), filename, font=font_large)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            # Позиционируем текст по центру
            text_x = (width_px - text_width) // 2
            text_y = (height_px - text_height) // 2 - 10
            
            # Рисуем название файла
            draw.text((text_x, text_y), filename, fill=(0, 0, 0, 255), font=font_large)
            
            # Добавляем информацию о файле
            info_text = f"{dxf_info['entities']} об. | {dxf_info['layers']} сл."
            if dxf_info['bounds']['width'] > 0:
                info_text += f" | {dxf_info['bounds']['width']:.0f}×{dxf_info['bounds']['height']:.0f}мм"
            
            # Размеры информационного текста
            info_bbox = draw.textbbox((0, 0), info_text, font=font_small)
            info_width = info_bbox[2] - info_bbox[0]
            info_height = info_bbox[3] - info_bbox[1]
            
            # Позиционируем информационный текст
            info_x = (width_px - info_width) // 2
            info_y = text_y + text_height + 5
            
            # Рисуем информационный текст
            draw.text((info_x, info_y), info_text, fill=(100, 100, 100, 255), font=font_small)
            
            # Добавляем УГЛОВЫЕ МАРКЕРЫ для ориентации
            corner_size = max(5, width_px // 50)
            
            # Левый верхний угол
            draw.rectangle(
                [border_width, border_width, border_width + corner_size, border_width + corner_size],
                fill=(0, 0, 0, 255)
            )
            
            # Правый верхний угол
            draw.rectangle(
                [width_px - border_width - corner_size, border_width, 
                 width_px - border_width, border_width + corner_size],
                fill=(0, 0, 0, 255)
            )
            
            # Левый нижний угол
            draw.rectangle(
                [border_width, height_px - border_width - corner_size, 
                 border_width + corner_size, height_px - border_width],
                fill=(0, 0, 0, 255)
            )
            
            # Правый нижний угол
            draw.rectangle(
                [width_px - border_width - corner_size, height_px - border_width - corner_size, 
                 width_px - border_width, height_px - border_width],
                fill=(0, 0, 0, 255)
            )
            
            # Сохраняем изображение
            img.save(str(cache_path), 'PNG', quality=95, optimize=True)
            
            self.logger.info(f"Гибридное изображение: {width_mm:.1f}x{height_mm:.1f} мм = {width_px}x{height_px} пикселей")
            return str(cache_path)
            
        except Exception as e:
            self.logger.error(f"Ошибка создания гибридного изображения: {e}")
            return None
    
    def draw_hybrid_on_canvas(self, canvas, dxf_path: str, x: int, y: int, 
                            width_mm: float, height_mm: float, 
                            scale_mm_per_pixel: float = 0.5):
        """
        Нарисовать ГИБРИДНОЕ изображение на Tkinter Canvas
        """
        if not self.pil_available:
            return
        
        try:
            from PIL import ImageTk
            
            # Получаем гибридное изображение
            image_path = self.create_hybrid_image(dxf_path, width_mm, height_mm, scale_mm_per_pixel)
            if not image_path or not Path(image_path).exists():
                return
            
            # Рассчитываем размеры на canvas
            canvas_width_px = int(width_mm / scale_mm_per_pixel)
            canvas_height_px = int(height_mm / scale_mm_per_pixel)
            
            # Загружаем и масштабируем изображение
            with Image.open(image_path) as img:
                resized = img.resize((canvas_width_px, canvas_height_px), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(resized)
                
                canvas.create_image(x + canvas_width_px//2, y + canvas_height_px//2, 
                                 image=photo, anchor='center')
                
                # Сохраняем ссылку
                canvas.image_refs = getattr(canvas, 'image_refs', [])
                canvas.image_refs.append(photo)
                
        except Exception as e:
            self.logger.error(f"Ошибка рисования гибридного изображения: {e}")
    
    def draw_hybrid_on_pdf(self, pdf_canvas, dxf_path: str, x: float, y: float, 
                          width_mm: float, height_mm: float, 
                          scale_mm_per_point: float = 0.5):
        """
        Нарисовать ГИБРИДНОЕ изображение в PDF
        """
        try:
            from reportlab.lib.utils import ImageReader
            
            # Получаем гибридное изображение
            image_path = self.create_hybrid_image(dxf_path, width_mm, height_mm, scale_mm_per_point)
            if not image_path or not Path(image_path).exists():
                return
            
            # Рассчитываем размеры в точках PDF
            width_points = width_mm / scale_mm_per_point
            height_points = height_mm / scale_mm_per_point
            
            # Загружаем изображение
            pdf_canvas.drawImage(
                ImageReader(image_path),
                x, y, width_points, height_points,
                preserveAspectRatio=False,
                mask='auto'
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка рисования гибридного изображения в PDF: {e}")
    
    def clear_cache(self):
        """Очистить кэш"""
        try:
            import shutil
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(exist_ok=True)
                self.logger.info("Кэш гибридных изображений очищен")
        except Exception as e:
            self.logger.error(f"Ошибка очистки кэша: {e}")


# Глобальный экземпляр
hybrid_dxf_renderer = HybridDXFRenderer()
