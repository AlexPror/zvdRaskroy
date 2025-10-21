#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Анализатор DXF файлов раскроя для вычисления реальных обрезков
Работает с DXF файлами, созданными технологом в CypCut
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import ezdxf
from shapely.geometry import Polygon, box, Point
from shapely.ops import unary_union
import re


class DXFNestingAnalyzer:
    """
    Анализирует DXF файл раскроя и вычисляет реальные обрезки
    """
    
    def __init__(self, sheet_width: float = 2500, sheet_height: float = 1250):
        """
        Args:
            sheet_width: ширина листа в мм
            sheet_height: высота листа в мм
        """
        self.logger = logging.getLogger(__name__)
        self.sheet_width = sheet_width
        self.sheet_height = sheet_height
    
    def analyze_nesting_dxf(self, dxf_path: Path) -> Dict:
        """
        Анализирует DXF файл раскроя от CypCut
        
        Returns:
            {
                'success': bool,
                'sheets': [  # Список листов
                    {
                        'sheet_number': int,
                        'parts': [список деталей],
                        'waste_regions': [список обрезков]
                    }
                ],
                'metadata': {
                    'project': str,
                    'order': str,
                    'date': str
                }
            }
        """
        try:
            self.logger.info(f"Анализ DXF раскроя: {dxf_path}")
            
            # Извлекаем метаданные из имени файла
            metadata = self._extract_metadata_from_filename(dxf_path.name)
            
            # Читаем DXF
            doc = ezdxf.readfile(dxf_path)
            msp = doc.modelspace()
            
            # Находим все детали
            parts = self._extract_parts_from_nesting(msp)
            
            if not parts:
                self.logger.warning("Детали не найдены в DXF")
                return {'success': False, 'error': 'No parts found'}
            
            self.logger.info(f"Найдено деталей: {len(parts)}")
            
            # Группируем по листам (по X координате)
            sheets = self._group_parts_into_sheets(parts)
            
            # Для каждого листа вычисляем обрезки
            for sheet in sheets:
                waste_regions = self._calculate_waste_regions(
                    sheet['parts'],
                    sheet_number=sheet['sheet_number']
                )
                sheet['waste_regions'] = waste_regions
            
            return {
                'success': True,
                'sheets': sheets,
                'metadata': metadata,
                'file_path': str(dxf_path),
                'analyzed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка анализа DXF: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def _extract_parts_from_nesting(self, msp) -> List[Dict]:
        """
        Извлекает детали из DXF раскроя
        
        CypCut может создавать раскрой по-разному:
        - Каждая деталь в отдельном слое
        - Все в одном слое, но разные блоки
        - Группы объектов
        """
        parts = []
        
        # Метод 1: По слоям (LAYER)
        layers = {}
        
        for entity in msp:
            if entity.dxftype() in ['LINE', 'LWPOLYLINE', 'POLYLINE', 'ARC', 'CIRCLE', 'SPLINE']:
                layer = entity.dxf.layer
                
                if layer not in layers:
                    layers[layer] = []
                
                layers[layer].append(entity)
        
        # Анализируем каждый слой
        for layer_name, entities in layers.items():
            # Пропускаем служебные слои
            if layer_name.startswith('0') or layer_name.upper() in ['DEFPOINTS', 'DIMENSIONS']:
                continue
            
            bounds = self._get_entities_bounds(entities)
            
            if bounds:
                min_x, min_y, max_x, max_y = bounds
                width = abs(max_x - min_x)
                height = abs(max_y - min_y)
                
                # Фильтруем слишком маленькие объекты (метки, размеры)
                if width < 10 or height < 10:
                    continue
                
                area_m2 = (width * height) / 1_000_000
                
                parts.append({
                    'name': layer_name,
                    'bounds': bounds,
                    'width': width,
                    'height': height,
                    'area_m2': area_m2,
                    'entities': entities
                })
        
        # Если слоев мало, пробуем найти по блокам
        if len(parts) < 2:
            self.logger.info("Мало деталей по слоям, пробуем по блокам...")
            parts = self._extract_parts_by_blocks(msp)
        
        return parts
    
    def _extract_parts_by_blocks(self, msp) -> List[Dict]:
        """Извлекает детали по блокам (INSERT)"""
        parts = []
        
        for entity in msp:
            if entity.dxftype() == 'INSERT':
                try:
                    bbox = entity.bounding_box
                    if bbox:
                        min_x, min_y = bbox.extmin.x, bbox.extmin.y
                        max_x, max_y = bbox.extmax.x, bbox.extmax.y
                        
                        width = abs(max_x - min_x)
                        height = abs(max_y - min_y)
                        
                        if width < 10 or height < 10:
                            continue
                        
                        area_m2 = (width * height) / 1_000_000
                        
                        parts.append({
                            'name': entity.dxf.name,
                            'bounds': (min_x, min_y, max_x, max_y),
                            'width': width,
                            'height': height,
                            'area_m2': area_m2
                        })
                except Exception as e:
                    self.logger.debug(f"Ошибка обработки блока: {e}")
        
        return parts
    
    def _get_entities_bounds(self, entities) -> Optional[Tuple[float, float, float, float]]:
        """Получает общие границы для списка объектов"""
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for entity in entities:
            try:
                if entity.dxftype() == 'LINE':
                    min_x = min(min_x, entity.dxf.start.x, entity.dxf.end.x)
                    max_x = max(max_x, entity.dxf.start.x, entity.dxf.end.x)
                    min_y = min(min_y, entity.dxf.start.y, entity.dxf.end.y)
                    max_y = max(max_y, entity.dxf.start.y, entity.dxf.end.y)
                    
                elif entity.dxftype() in ['LWPOLYLINE', 'POLYLINE']:
                    points = entity.get_points('xy') if hasattr(entity, 'get_points') else []
                    for point in points:
                        min_x = min(min_x, point[0])
                        max_x = max(max_x, point[0])
                        min_y = min(min_y, point[1])
                        max_y = max(max_y, point[1])
                        
                elif entity.dxftype() == 'CIRCLE':
                    cx, cy = entity.dxf.center.x, entity.dxf.center.y
                    r = entity.dxf.radius
                    min_x = min(min_x, cx - r)
                    max_x = max(max_x, cx + r)
                    min_y = min(min_y, cy - r)
                    max_y = max(max_y, cy + r)
                    
                elif hasattr(entity, 'bounding_box'):
                    bbox = entity.bounding_box
                    if bbox:
                        min_x = min(min_x, bbox.extmin.x)
                        max_x = max(max_x, bbox.extmax.x)
                        min_y = min(min_y, bbox.extmin.y)
                        max_y = max(max_y, bbox.extmax.y)
            except:
                continue
        
        if min_x != float('inf'):
            return (min_x, min_y, max_x, max_y)
        
        return None
    
    def _group_parts_into_sheets(self, parts: List[Dict]) -> List[Dict]:
        """
        Группирует детали по листам
        
        Предполагаем, что листы расположены последовательно по X
        """
        sheets = []
        
        # Сортируем детали по X
        parts_sorted = sorted(parts, key=lambda p: p['bounds'][0])
        
        current_sheet = {
            'sheet_number': 1,
            'parts': [],
            'x_offset': 0
        }
        
        for part in parts_sorted:
            min_x = part['bounds'][0]
            
            # Если деталь далеко справа - новый лист
            if current_sheet['parts'] and (min_x - current_sheet['x_offset']) > self.sheet_width * 1.1:
                # Закрываем текущий лист
                sheets.append(current_sheet)
                
                # Начинаем новый
                current_sheet = {
                    'sheet_number': len(sheets) + 1,
                    'parts': [],
                    'x_offset': min_x
                }
            
            # Нормализуем координаты относительно листа
            if not current_sheet['parts']:
                current_sheet['x_offset'] = min_x
            
            normalized_bounds = (
                part['bounds'][0] - current_sheet['x_offset'],
                part['bounds'][1],
                part['bounds'][2] - current_sheet['x_offset'],
                part['bounds'][3]
            )
            
            normalized_part = part.copy()
            normalized_part['bounds'] = normalized_bounds
            
            current_sheet['parts'].append(normalized_part)
        
        # Добавляем последний лист
        if current_sheet['parts']:
            sheets.append(current_sheet)
        
        self.logger.info(f"Детали сгруппированы на {len(sheets)} листов")
        return sheets
    
    def _calculate_waste_regions(self, parts: List[Dict], sheet_number: int) -> List[Dict]:
        """
        Вычисляет области обрезков на листе
        
        Алгоритм:
        1. Полигон листа 2500×1250
        2. Вычитаем полигоны всех деталей
        3. Остаются обрезки
        """
        try:
            # Полигон листа
            sheet_polygon = box(0, 0, self.sheet_width, self.sheet_height)
            
            # Полигоны деталей
            part_polygons = []
            
            for part in parts:
                min_x, min_y, max_x, max_y = part['bounds']
                
                # Добавляем небольшой запас (зазор резки ~5мм)
                gap = 5
                part_poly = box(
                    max(0, min_x - gap),
                    max(0, min_y - gap),
                    min(self.sheet_width, max_x + gap),
                    min(self.sheet_height, max_y + gap)
                )
                part_polygons.append(part_poly)
            
            # Объединяем все детали
            if part_polygons:
                parts_union = unary_union(part_polygons)
                
                # Вычитаем из листа
                waste_area = sheet_polygon.difference(parts_union)
                
                # Разбиваем на отдельные куски
                waste_regions = []
                
                if hasattr(waste_area, 'geoms'):
                    waste_pieces = list(waste_area.geoms)
                else:
                    waste_pieces = [waste_area]
                
                for piece in waste_pieces:
                    bounds = piece.bounds  # (min_x, min_y, max_x, max_y)
                    width = bounds[2] - bounds[0]
                    height = bounds[3] - bounds[1]
                    area_m2 = piece.area / 1_000_000
                    
                    # Фильтруем слишком маленькие обрезки
                    min_size = 200  # мм
                    if width < min_size or height < min_size:
                        continue
                    
                    # Определяем пригодность (>= 300×300 мм)
                    usable = width >= 300 and height >= 300
                    
                    waste_regions.append({
                        'sheet_number': sheet_number,
                        'bounds': bounds,
                        'width': width,
                        'height': height,
                        'area_m2': area_m2,
                        'usable': usable
                    })
                
                # Сортируем по площади (большие сначала)
                waste_regions.sort(key=lambda w: w['area_m2'], reverse=True)
                
                self.logger.info(f"Лист {sheet_number}: найдено {len(waste_regions)} обрезков")
                return waste_regions
            
        except Exception as e:
            self.logger.error(f"Ошибка расчета обрезков: {e}")
        
        return []
    
    def _extract_metadata_from_filename(self, filename: str) -> Dict:
        """
        Извлекает метаданные из имени файла
        
        Примеры:
        - "001 - Корпус короба прямой 1шт (А-12158-1544).dxf"
        - "Раскрой_А-12158-1544_2025-10-18.dxf"
        - "ZVD.LITE.154.160.1400_А-12158.dxf"
        """
        metadata = {
            'project': None,
            'order': None,
            'date': datetime.now().strftime("%d.%m.%Y")
        }
        
        # Паттерн для номера заказа
        order_pattern = r'[АA]-\d{5,6}(?:-\d{4})?'
        match = re.search(order_pattern, filename)
        if match:
            metadata['order'] = match.group(0)
        
        # Паттерн для конфигурации
        config_pattern = r'(LITE|TURBO|ZVD\.LITE|ZVD\.TURBO)[.\s]*(\d+)[.\s]*(\d+)[.\s]*(\d+)'
        match = re.search(config_pattern, filename, re.IGNORECASE)
        if match:
            series = match.group(1).upper().replace('ZVD.', '')
            dims = sorted([int(match.group(2)), int(match.group(3)), int(match.group(4))])
            metadata['project'] = f"{series}.{dims[0]}.{dims[1]}.{dims[2]}"
        
        # Паттерн для даты
        date_pattern = r'(\d{4})-(\d{2})-(\d{2})'
        match = re.search(date_pattern, filename)
        if match:
            year, month, day = match.groups()
            metadata['date'] = f"{day}.{month}.{year}"
        
        return metadata


