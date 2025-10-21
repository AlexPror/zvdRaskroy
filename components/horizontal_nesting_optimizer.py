#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Оптимизатор раскроя с ПРИНУДИТЕЛЬНОЙ горизонтальной ориентацией
Все детали размещаются горизонтально по одной стороне листа
"""

import logging
from typing import Dict, List, Tuple
import math

try:
    from rectpack import newPacker, PackingMode, PackingBin
    RECTPACK_AVAILABLE = True
except ImportError:
    RECTPACK_AVAILABLE = False


class HorizontalNestingOptimizer:
    """
    Оптимизатор раскроя с горизонтальной ориентацией деталей
    Все детали принудительно поворачиваются горизонтально
    """
    
    # Размеры стандартного листа
    SHEET_WIDTH = 2500  # мм
    SHEET_HEIGHT = 1250  # мм
    SHEET_AREA_MM2 = SHEET_WIDTH * SHEET_HEIGHT
    SHEET_AREA_M2 = SHEET_AREA_MM2 / 1_000_000
    
    # Зазоры
    CUT_GAP = 2.5  # мм - ПОЛОВИНА зазора (между деталями будет 2.5+2.5=5мм)
    EDGE_MARGIN = 10  # мм от края листа
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        if not RECTPACK_AVAILABLE:
            self.logger.warning("⚠️  Библиотека rectpack не установлена!")
            self.logger.warning("   Установите: pip install rectpack")
    
    def is_available(self) -> bool:
        """Проверка доступности rectpack"""
        return RECTPACK_AVAILABLE
    
    def _force_horizontal_orientation(self, parts_data: List[Dict]) -> List[Dict]:
        """
        Принудительно поворачивает все детали горизонтально
        Если высота > ширины, то меняет их местами
        """
        horizontal_parts = []
        
        for part in parts_data:
            width = part['width_mm']
            height = part['height_mm']
            
            # Если деталь вертикальная (высота > ширины), поворачиваем
            if height > width:
                # Меняем местами ширину и высоту
                new_width = height
                new_height = width
                rotated = True
            else:
                # Деталь уже горизонтальная
                new_width = width
                new_height = height
                rotated = False
            
            # Создаем копию детали с горизонтальной ориентацией
            horizontal_part = part.copy()
            horizontal_part['width_mm'] = new_width
            horizontal_part['height_mm'] = new_height
            horizontal_part['rotated'] = rotated
            
            horizontal_parts.append(horizontal_part)
            
            if rotated:
                self.logger.debug(f"Повернута: {part['name']} {width}×{height} → {new_width}×{new_height}")
        
        return horizontal_parts
    
    def optimize_layout(self, 
                       parts_data: List[Dict],
                       algorithm: str = 'BFF') -> Dict:
        """
        Оптимизация раскладки с ПРИНУДИТЕЛЬНОЙ горизонтальной ориентацией
        
        Args:
            parts_data: Список деталей с габаритами
            algorithm: 'BNF' (Best Fit) или 'BFF' (Best Fit First)
        
        Returns:
            dict с результатами раскроя
        """
        
        if not RECTPACK_AVAILABLE:
            self.logger.error("❌ Rectpack не доступен!")
            return {'success': False, 'error': 'rectpack not installed'}
        
        try:
            # ПРИНУДИТЕЛЬНО поворачиваем все детали горизонтально
            self.logger.info("🔄 Принудительная горизонтальная ориентация...")
            horizontal_parts = self._force_horizontal_orientation(parts_data)
            
            # Создаем упаковщик БЕЗ поворота (все детали уже горизонтальные)
            packer = newPacker(
                mode=PackingMode.Offline,
                rotation=False  # НЕ разрешаем дополнительный поворот
            )
            
            # Добавляем листы
            MAX_SHEETS = 20
            usable_width = self.SHEET_WIDTH - 2 * self.EDGE_MARGIN
            usable_height = self.SHEET_HEIGHT - 2 * self.EDGE_MARGIN
            
            for i in range(MAX_SHEETS):
                packer.add_bin(usable_width, usable_height, bid=i+1)
            
            # Подготавливаем детали
            parts_map = {}
            part_id = 0
            
            for part in horizontal_parts:
                quantity = part.get('quantity', 1)
                base_name = part['name']
                
                for inst in range(quantity):
                    part_id += 1
                    unique_id = f"part_{part_id}"
                    
                    # Габариты с учетом зазора
                    w = int(part['width_mm']) + self.CUT_GAP
                    h = int(part['height_mm']) + self.CUT_GAP
                    
                    # Добавляем деталь
                    packer.add_rect(w, h, rid=unique_id)
                    
                    # Сохраняем информацию
                    parts_map[unique_id] = {
                        'name': base_name,
                        'original_width': part['width_mm'],
                        'original_height': part['height_mm'],
                        'area_m2': part['area_m2'],
                        'instance': inst + 1,
                        'total_quantity': quantity,
                        'was_rotated': part.get('rotated', False)
                    }
            
            # УПАКОВЫВАЕМ!
            self.logger.info(f"Запуск оптимизации раскроя...")
            self.logger.info(f"  Деталей: {len(parts_map)}")
            self.logger.info(f"  Алгоритм: {algorithm}")
            self.logger.info(f"  Ориентация: Все горизонтально")
            
            packer.pack()
            
            # Собираем результаты
            sheets = []
            total_used_area_m2 = 0
            
            for bin_obj in packer:
                if len(bin_obj) == 0:
                    continue
                
                sheet = {
                    'number': bin_obj.bid,
                    'parts': [],
                    'used_area_m2': 0
                }
                
                for rect in bin_obj:
                    part_info = parts_map[rect.rid]
                    
                    sheet['parts'].append({
                        'name': part_info['name'],
                        'x': rect.x + self.EDGE_MARGIN,
                        'y': rect.y + self.EDGE_MARGIN,
                        'width': int(part_info['original_width']),
                        'height': int(part_info['original_height']),
                        'rotated': part_info['was_rotated'],  # Показываем, была ли повернута
                        'instance': part_info['instance'],
                        'total_quantity': part_info['total_quantity']
                    })
                    
                    sheet['used_area_m2'] += part_info['area_m2']
                
                # Рассчитываем обрезки
                sheet['waste_area_m2'] = self.SHEET_AREA_M2 - sheet['used_area_m2']
                sheet['waste_percent'] = (sheet['waste_area_m2'] / self.SHEET_AREA_M2) * 100
                
                sheets.append(sheet)
                total_used_area_m2 += sheet['used_area_m2']
            
            sheets_needed = len(sheets)
            total_sheet_area_m2 = sheets_needed * self.SHEET_AREA_M2
            total_waste_area_m2 = total_sheet_area_m2 - total_used_area_m2
            overall_waste_percent = (total_waste_area_m2 / total_sheet_area_m2) * 100 if total_sheet_area_m2 > 0 else 0
            utilization_percent = (total_used_area_m2 / total_sheet_area_m2) * 100 if total_sheet_area_m2 > 0 else 0
            
            result = {
                'success': True,
                'sheets_needed': sheets_needed,
                'sheets': sheets,
                'total_used_area_m2': total_used_area_m2,
                'total_waste_area_m2': total_waste_area_m2,
                'overall_waste_percent': overall_waste_percent,
                'utilization_percent': utilization_percent
            }
            
            # Логируем результаты
            self.logger.info(f"\n[OK] Оптимизация завершена:")
            self.logger.info(f"  Листов требуется: {sheets_needed}")
            self.logger.info(f"  Использование материала: {utilization_percent:.1f}%")
            self.logger.info(f"  Обрезки: {overall_waste_percent:.1f}%")
            
            # Показываем, какие детали были повернуты
            rotated_count = sum(1 for part in horizontal_parts if part.get('rotated', False))
            if rotated_count > 0:
                self.logger.info(f"  Повернуто деталей: {rotated_count}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"[ERROR] Ошибка оптимизации: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}


if __name__ == "__main__":
    # Тестирование
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    optimizer = HorizontalNestingOptimizer()
    
    if not optimizer.is_available():
        print("\n[ERROR] Rectpack не установлен!")
        print("Установите: pip install rectpack")
        exit(1)
    
    # Тестовые данные (как в demo_waste_tracking.py)
    test_parts = [
        {
            'name': '004 - Корпус короба (Киевская площадь 1)',
            'width_mm': 400.0,   # Оригинальные размеры
            'height_mm': 1200.0,
            'area_m2': 0.48,
            'quantity': 1
        },
        {
            'name': '003 - Крышка декоративная (Киевская площадь 1)',
            'width_mm': 150.0,
            'height_mm': 287.7,
            'area_m2': 0.0432,
            'quantity': 1
        },
        {
            'name': '006 - Стенка торцевая (Киевская площадь 1)',
            'width_mm': 134.0,
            'height_mm': 298.0,
            'area_m2': 0.0399,
            'quantity': 1
        },
        {
            'name': '005.01 - Распорка бассейна (Киевская площадь 1)',
            'width_mm': 122.0,
            'height_mm': 298.0,
            'area_m2': 0.0364,
            'quantity': 1
        },
        {
            'name': '007 - Стенка (Киевская площадь 1)',
            'width_mm': 40.0,
            'height_mm': 296.0,
            'area_m2': 0.0118,
            'quantity': 1
        },
        {
            'name': '005.02 - Распорка бассейна верхняя (Котел-НН)',
            'width_mm': 36.0,
            'height_mm': 291.0,
            'area_m2': 0.0105,
            'quantity': 1
        }
    ]
    
    print("\n" + "="*80)
    print("ТЕСТ ГОРИЗОНТАЛЬНОЙ ОРИЕНТАЦИИ")
    print("="*80)
    print(f"\nТестовый проект: ДЕМО_ЛАЙТ")
    print(f"Деталей: {sum(p['quantity'] for p in test_parts)} шт")
    print(f"Площадь деталей: {sum(p['area_m2'] * p['quantity'] for p in test_parts):.4f} м2")
    
    # Оптимизация
    result = optimizer.optimize_layout(test_parts)
    
    if result['success']:
        print(f"\n[OK] Результат:")
        print(f"   Листов: {result['sheets_needed']}")
        print(f"   Использование: {result['utilization_percent']:.1f}%")
        print(f"   Обрезки: {result['overall_waste_percent']:.1f}%")
        
        print(f"\nДетали на листах:")
        for sheet in result['sheets']:
            print(f"\n  ЛИСТ №{sheet['number']}:")
            for part in sheet['parts']:
                rotation_text = " [90°]" if part['rotated'] else ""
                print(f"    • {part['name']}: {part['width']}x{part['height']}{rotation_text}")
    else:
        print(f"[ERROR] Ошибка: {result.get('error')}")
    
    print("\n" + "="*80)
    print("[OK] Тест завершен!")
    print("="*80)
