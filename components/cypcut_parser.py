#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер файлов раскроя из CypCut для извлечения данных об обрезках
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import ezdxf
from shapely.geometry import Polygon, box
from shapely.ops import unary_union


class CypCutParser:
    """
    Парсер файлов раскроя из программы CypCut
    
    Поддерживаемые форматы:
    - DXF с геометрией раскладки
    - Excel отчеты CypCut (опционально)
    """
    
    def __init__(self, sheet_width: float = 2500, sheet_height: float = 1250):
        """
        Args:
            sheet_width: ширина листа в мм (по умолчанию 2500)
            sheet_height: высота листа в мм (по умолчанию 1250)
        """
        self.logger = logging.getLogger(__name__)
        self.sheet_width = sheet_width
        self.sheet_height = sheet_height
        
    def parse_cypcut_dxf(self, dxf_path: Path) -> Dict:
        """
        Парсит DXF файл раскроя из CypCut
        
        Returns:
            {
                'success': bool,
                'sheets': [  # Список листов
                    {
                        'sheet_number': int,
                        'parts': [  # Детали на листе
                            {
                                'name': str,
                                'bounds': (min_x, min_y, max_x, max_y),
                                'width': float,
                                'height': float,
                                'area_m2': float
                            }
                        ],
                        'waste_regions': [  # Обрезки
                            {
                                'bounds': (min_x, min_y, max_x, max_y),
                                'width': float,
                                'height': float,
                                'area_m2': float,
                                'usable': bool
                            }
                        ]
                    }
                ]
            }
        """
        try:
            self.logger.info(f"Парсинг DXF из CypCut: {dxf_path}")
            
            # Читаем DXF
            doc = ezdxf.readfile(dxf_path)
            msp = doc.modelspace()
            
            # Извлекаем детали по слоям или блокам
            parts = self._extract_parts_from_dxf(msp)
            
            if not parts:
                self.logger.warning("Детали не найдены в DXF")
                return {'success': False, 'error': 'No parts found'}
            
            # Группируем детали по листам
            sheets = self._group_parts_by_sheets(parts)
            
            # Для каждого листа находим обрезки
            for sheet in sheets:
                waste_regions = self._find_waste_regions(sheet['parts'])
                sheet['waste_regions'] = waste_regions
            
            return {
                'success': True,
                'sheets': sheets,
                'file_path': str(dxf_path),
                'parsed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка парсинга DXF: {e}")
            return {'success': False, 'error': str(e)}
    
    def _extract_parts_from_dxf(self, msp) -> List[Dict]:
        """
        Извлекает детали из DXF
        
        CypCut обычно создает:
        - Каждая деталь в отдельном слое (LAYER)
        - Или каждая деталь как INSERT блока
        - Или все в одном слое, но с текстовыми метками
        """
        parts = []
        
        # Метод 1: По блокам (INSERT)
        inserts = [e for e in msp if e.dxftype() == 'INSERT']
        
        for insert in inserts:
            try:
                # Получаем границы блока
                bbox = insert.bounding_box
                if bbox:
                    min_x, min_y = bbox.extmin.x, bbox.extmin.y
                    max_x, max_y = bbox.extmax.x, bbox.extmax.y
                    
                    width = abs(max_x - min_x)
                    height = abs(max_y - min_y)
                    area_m2 = (width * height) / 1_000_000
                    
                    parts.append({
                        'name': insert.dxf.name,
                        'bounds': (min_x, min_y, max_x, max_y),
                        'width': width,
                        'height': height,
                        'area_m2': area_m2
                    })
            except Exception as e:
                self.logger.debug(f"Ошибка обработки INSERT: {e}")
        
        # Метод 2: По слоям (если нет блоков)
        if not parts:
            layers = {}
            
            for entity in msp:
                if entity.dxftype() in ['LINE', 'LWPOLYLINE', 'POLYLINE', 'ARC', 'CIRCLE', 'SPLINE']:
                    layer = entity.dxf.layer
                    
                    if layer not in layers:
                        layers[layer] = []
                    
                    layers[layer].append(entity)
            
            # Для каждого слоя находим общие границы
            for layer_name, entities in layers.items():
                if layer_name.startswith('0'):  # Пропускаем служебные слои
                    continue
                
                bounds = self._get_entities_bounds(entities)
                if bounds:
                    min_x, min_y, max_x, max_y = bounds
                    width = abs(max_x - min_x)
                    height = abs(max_y - min_y)
                    area_m2 = (width * height) / 1_000_000
                    
                    parts.append({
                        'name': layer_name,
                        'bounds': bounds,
                        'width': width,
                        'height': height,
                        'area_m2': area_m2
                    })
        
        # Метод 3: По текстовым меткам рядом с геометрией
        if not parts:
            parts = self._extract_parts_by_text_labels(msp)
        
        self.logger.info(f"Найдено деталей: {len(parts)}")
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
    
    def _extract_parts_by_text_labels(self, msp) -> List[Dict]:
        """
        Извлекает детали по текстовым меткам
        (для случая, когда все в одном слое, но есть подписи)
        """
        parts = []
        
        # Собираем все текстовые объекты
        texts = []
        for entity in msp:
            if entity.dxftype() in ['TEXT', 'MTEXT']:
                try:
                    text_content = entity.dxf.text if hasattr(entity.dxf, 'text') else ''
                    text_pos = entity.dxf.insert if hasattr(entity.dxf, 'insert') else None
                    
                    if text_content and text_pos:
                        texts.append({
                            'text': text_content,
                            'x': text_pos.x,
                            'y': text_pos.y
                        })
                except:
                    continue
        
        # Для каждого текста ищем ближайшую геометрию
        # (это упрощенная реализация, можно улучшить)
        
        self.logger.info(f"Найдено текстовых меток: {len(texts)}")
        return parts
    
    def _group_parts_by_sheets(self, parts: List[Dict]) -> List[Dict]:
        """
        Группирует детали по листам
        
        Предполагаем, что детали расположены последовательно:
        - Лист 1: x от 0 до sheet_width
        - Лист 2: x от sheet_width до 2*sheet_width
        - И т.д.
        """
        sheets = []
        
        # Сортируем детали по X координате
        parts_sorted = sorted(parts, key=lambda p: p['bounds'][0])
        
        current_sheet = {
            'sheet_number': 1,
            'parts': [],
            'x_offset': 0
        }
        
        for part in parts_sorted:
            min_x = part['bounds'][0]
            
            # Если деталь вышла за границу листа
            if min_x - current_sheet['x_offset'] > self.sheet_width:
                # Закрываем текущий лист
                if current_sheet['parts']:
                    sheets.append(current_sheet)
                
                # Начинаем новый лист
                current_sheet = {
                    'sheet_number': len(sheets) + 1,
                    'parts': [],
                    'x_offset': min_x
                }
            
            # Нормализуем координаты детали относительно листа
            normalized_part = part.copy()
            normalized_bounds = (
                part['bounds'][0] - current_sheet['x_offset'],
                part['bounds'][1],
                part['bounds'][2] - current_sheet['x_offset'],
                part['bounds'][3]
            )
            normalized_part['bounds'] = normalized_bounds
            
            current_sheet['parts'].append(normalized_part)
        
        # Добавляем последний лист
        if current_sheet['parts']:
            sheets.append(current_sheet)
        
        self.logger.info(f"Детали сгруппированы на {len(sheets)} листов")
        return sheets
    
    def _find_waste_regions(self, parts: List[Dict]) -> List[Dict]:
        """
        Находит области обрезков на листе
        
        Алгоритм:
        1. Создаем полигон всего листа
        2. Вычитаем полигоны всех деталей
        3. Остается фигура обрезков
        4. Разбиваем на отдельные куски
        """
        try:
            # Полигон листа
            sheet_polygon = box(0, 0, self.sheet_width, self.sheet_height)
            
            # Полигоны деталей
            part_polygons = []
            for part in parts:
                min_x, min_y, max_x, max_y = part['bounds']
                part_poly = box(min_x, min_y, max_x, max_y)
                part_polygons.append(part_poly)
            
            # Объединяем все детали
            if part_polygons:
                parts_union = unary_union(part_polygons)
                
                # Вычитаем из листа
                waste_area = sheet_polygon.difference(parts_union)
                
                # Разбиваем на отдельные куски
                waste_regions = []
                
                if hasattr(waste_area, 'geoms'):
                    # MultiPolygon
                    waste_pieces = list(waste_area.geoms)
                else:
                    # Один полигон
                    waste_pieces = [waste_area]
                
                for i, piece in enumerate(waste_pieces):
                    bounds = piece.bounds  # (min_x, min_y, max_x, max_y)
                    width = bounds[2] - bounds[0]
                    height = bounds[3] - bounds[1]
                    area_m2 = piece.area / 1_000_000
                    
                    # Определяем, можно ли использовать этот обрезок
                    # (если размер >= 500x500 мм)
                    usable = width >= 500 and height >= 500
                    
                    waste_regions.append({
                        'bounds': bounds,
                        'width': width,
                        'height': height,
                        'area_m2': area_m2,
                        'usable': usable
                    })
                
                # Сортируем по площади (большие сначала)
                waste_regions.sort(key=lambda w: w['area_m2'], reverse=True)
                
                self.logger.info(f"Найдено обрезков: {len(waste_regions)}")
                return waste_regions
            
        except Exception as e:
            self.logger.error(f"Ошибка поиска обрезков: {e}")
        
        return []
    
    def extract_metadata_from_filename(self, filename: str) -> Dict:
        """
        Извлекает метаданные из имени файла CypCut
        
        Обычные форматы:
        - LITE_140_300_2400_А-180925.dxf
        - ZVD_TURBO_90_300_1500_А-190101.nc
        - Раскрой_А-180925-1801_18-10-2025.dxf
        """
        import re
        
        metadata = {}
        
        # Паттерн для конфигурации
        config_pattern = r'(LITE|TURBO|ZVD\.LITE|ZVD\.TURBO)[_\s]*(\d+)[_\s]*(\d+)[_\s]*(\d+)'
        match = re.search(config_pattern, filename, re.IGNORECASE)
        
        if match:
            series = match.group(1).upper().replace('ZVD.', '')
            h = int(match.group(2))
            b = int(match.group(3))
            l = int(match.group(4))
            
            # Сортируем размеры
            dims = sorted([h, b, l])
            metadata['config'] = f"{series}.{dims[0]}.{dims[1]}.{dims[2]}"
        
        # Паттерн для номера заказа
        order_pattern = r'[АA]-\d{6}(?:-\d{4})?'
        match = re.search(order_pattern, filename)
        
        if match:
            metadata['order_number'] = match.group(0)
        
        # Паттерн для даты
        date_pattern = r'(\d{2})-(\d{2})-(\d{4})'
        match = re.search(date_pattern, filename)
        
        if match:
            day, month, year = match.groups()
            metadata['date'] = f"{day}.{month}.{year}"
        
        return metadata


class WasteDatabaseManager:
    """
    Управление базой данных обрезков
    """
    
    def __init__(self, db_path: Path = Path("База_обрезков.xlsx")):
        self.logger = logging.getLogger(__name__)
        self.db_path = db_path
        self.waste_counter = self._get_last_waste_id()
    
    def _get_last_waste_id(self) -> int:
        """Получает последний ID обрезка из базы"""
        if not self.db_path.exists():
            return 0
        
        try:
            import openpyxl
            wb = openpyxl.load_workbook(self.db_path)
            ws = wb.active
            
            last_row = ws.max_row
            if last_row > 1:
                last_id = ws.cell(last_row, 1).value  # Первая колонка - ID
                if last_id and last_id.startswith('W-'):
                    return int(last_id.split('-')[1])
        except Exception as e:
            self.logger.warning(f"Ошибка чтения последнего ID: {e}")
        
        return 0
    
    def add_waste_records(
        self, 
        waste_regions: List[Dict], 
        project_name: str,
        order_number: str,
        material: str = "Оцинковка 1.5мм"
    ) -> List[Dict]:
        """
        Добавляет обрезки в базу данных
        
        Returns:
            Список обрезков с присвоенными ID
        """
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        
        # Создаем/открываем базу
        if self.db_path.exists():
            wb = openpyxl.load_workbook(self.db_path)
            ws = wb.active
        else:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Обрезки"
            
            # Создаем заголовки
            headers = [
                "ID", "Проект", "Заказ", "Дата", "Лист №",
                "Ширина (мм)", "Высота (мм)", "Площадь (м²)",
                "Материал", "Расположение", "Статус",
                "Использован в", "Рекомендации", "Примечание"
            ]
            
            for col, header in enumerate(headers, 1):
                cell = ws.cell(1, col, header)
                cell.font = Font(bold=True, size=12)
                cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
                cell.font = Font(bold=True, size=12, color="FFFFFF")
                cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Добавляем обрезки
        waste_records = []
        current_date = datetime.now().strftime("%d.%m.%Y")
        
        for waste in waste_regions:
            if not waste.get('usable', False):
                continue  # Пропускаем непригодные обрезки
            
            self.waste_counter += 1
            waste_id = f"W-{self.waste_counter:03d}"
            
            # Генерируем рекомендации
            recommendations = self._generate_recommendations(waste)
            
            row_data = [
                waste_id,
                project_name,
                order_number,
                current_date,
                waste.get('sheet_number', 1),
                round(waste['width'], 1),
                round(waste['height'], 1),
                round(waste['area_m2'], 4),
                material,
                "Стеллаж (укажите)",  # Пользователь заполнит вручную
                "В наличии",
                "",  # Использован в
                recommendations,
                ""  # Примечание
            ]
            
            row_num = ws.max_row + 1
            for col, value in enumerate(row_data, 1):
                cell = ws.cell(row_num, col, value)
                cell.alignment = Alignment(horizontal='center' if col <= 5 else 'left', 
                                          vertical='center')
            
            waste_record = waste.copy()
            waste_record['id'] = waste_id
            waste_record['date'] = current_date
            waste_records.append(waste_record)
        
        # Сохраняем
        wb.save(self.db_path)
        self.logger.info(f"Добавлено {len(waste_records)} обрезков в базу")
        
        return waste_records
    
    def _generate_recommendations(self, waste: Dict) -> str:
        """
        Генерирует рекомендации по использованию обрезка
        """
        width = waste['width']
        height = waste['height']
        
        recommendations = []
        
        # Большие обрезки (>1000мм)
        if width > 1000 or height > 1000:
            recommendations.append("Корпуса малых конвекторов")
        
        # Средние обрезки (500-1000мм)
        if 500 <= width <= 1000 and 500 <= height <= 1000:
            recommendations.append("Крышки")
            recommendations.append("Стенки торцевые")
        
        # Узкие длинные обрезки
        if width < 400 and height > 800:
            recommendations.append("Распорки")
            recommendations.append("Стенки продольные")
        
        # Маленькие обрезки
        if width < 500 and height < 500:
            recommendations.append("Мелкие детали")
        
        return ", ".join(recommendations) if recommendations else "Универсальный"
    
    def find_suitable_waste(
        self, 
        part_width: float, 
        part_height: float,
        material: str = "Оцинковка 1.5мм"
    ) -> Optional[Dict]:
        """
        Находит подходящий обрезок для детали
        
        Returns:
            {
                'waste_id': str,
                'width': float,
                'height': float,
                'area_m2': float,
                'location': str,
                'economy_rub': float,
                'recommendation': str
            }
        """
        if not self.db_path.exists():
            return None
        
        try:
            import openpyxl
            wb = openpyxl.load_workbook(self.db_path)
            ws = wb.active
            
            suitable_wastes = []
            
            # Пропускаем заголовок
            for row in range(2, ws.max_row + 1):
                waste_id = ws.cell(row, 1).value
                status = ws.cell(row, 11).value  # Статус
                waste_width = ws.cell(row, 6).value
                waste_height = ws.cell(row, 7).value
                waste_area = ws.cell(row, 8).value
                waste_material = ws.cell(row, 9).value
                waste_location = ws.cell(row, 10).value
                
                # Фильтруем: только "В наличии" и подходящий материал
                if status != "В наличии":
                    continue
                
                if waste_material != material:
                    continue
                
                # Проверяем размер (с запасом 10мм)
                gap = 10
                
                # Проверяем оба варианта ориентации
                fits_normal = (waste_width >= part_width + gap and 
                              waste_height >= part_height + gap)
                
                fits_rotated = (waste_width >= part_height + gap and 
                               waste_height >= part_width + gap)
                
                if fits_normal or fits_rotated:
                    suitable_wastes.append({
                        'waste_id': waste_id,
                        'width': waste_width,
                        'height': waste_height,
                        'area_m2': waste_area,
                        'location': waste_location,
                        'row': row
                    })
            
            # Сортируем по площади (минимальная площадь = меньше отходов)
            if suitable_wastes:
                suitable_wastes.sort(key=lambda w: w['area_m2'])
                best = suitable_wastes[0]
                
                # Расчет экономии
                part_area_m2 = (part_width * part_height) / 1_000_000
                material_cost_per_m2 = 3500  # руб/м²
                economy = part_area_m2 * material_cost_per_m2
                
                best['economy_rub'] = round(economy, 2)
                best['recommendation'] = f"Вырезать из обрезка {best['waste_id']}"
                
                return best
            
        except Exception as e:
            self.logger.error(f"Ошибка поиска обрезка: {e}")
        
        return None
    
    def mark_waste_as_used(self, waste_id: str, used_in_project: str):
        """Отмечает обрезок как использованный"""
        if not self.db_path.exists():
            return
        
        try:
            import openpyxl
            wb = openpyxl.load_workbook(self.db_path)
            ws = wb.active
            
            for row in range(2, ws.max_row + 1):
                if ws.cell(row, 1).value == waste_id:
                    ws.cell(row, 11, "Использован")  # Статус
                    ws.cell(row, 12, used_in_project)  # Использован в
                    wb.save(self.db_path)
                    self.logger.info(f"Обрезок {waste_id} отмечен как использованный")
                    break
        except Exception as e:
            self.logger.error(f"Ошибка обновления статуса: {e}")


