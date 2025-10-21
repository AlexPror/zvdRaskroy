#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Оптимизатор раскроя с использованием библиотеки rectpack
Интеграция в систему ZVD
"""

import logging
from typing import Dict, List, Tuple

try:
    from rectpack import newPacker, PackingMode, PackingBin
    RECTPACK_AVAILABLE = True
except ImportError:
    RECTPACK_AVAILABLE = False


class RectpackOptimizer:
    """
    Оптимизатор раскроя деталей на листы с использованием rectpack
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
    
    def optimize_layout(self, 
                       parts_data: List[Dict],
                       allow_rotation: bool = True,
                       algorithm: str = 'BFF') -> Dict:
        """
        Оптимизация раскладки деталей на листы
        
        Args:
            parts_data: Список деталей с габаритами
                [{'name': str, 'width_mm': float, 'height_mm': float, 
                  'area_m2': float, 'quantity': int}, ...]
            allow_rotation: Разрешить поворот деталей на 90°
            algorithm: 'BNF' (Best Fit) или 'BFF' (Best Fit First)
        
        Returns:
            dict с результатами раскроя:
            {
                'success': bool,
                'sheets_needed': int,
                'sheets': [
                    {
                        'number': int,
                        'parts': [
                            {'name': str, 'x': int, 'y': int, 
                             'width': int, 'height': int, 'rotated': bool}
                        ],
                        'used_area_m2': float,
                        'waste_area_m2': float,
                        'waste_percent': float
                    }
                ],
                'total_used_area_m2': float,
                'total_waste_area_m2': float,
                'overall_waste_percent': float,
                'utilization_percent': float
            }
        """
        
        if not RECTPACK_AVAILABLE:
            self.logger.error("❌ Rectpack не доступен!")
            return {'success': False, 'error': 'rectpack not installed'}
        
        try:
            # Создаем упаковщик
            # rectpack поддерживает разные алгоритмы через pack_algo
            # Используем MaxRects (по умолчанию) - один из лучших алгоритмов
            packer = newPacker(
                mode=PackingMode.Offline,  # Все детали известны заранее
                rotation=allow_rotation
            )
            
            # Добавляем листы (достаточно для любого проекта)
            MAX_SHEETS = 20
            usable_width = self.SHEET_WIDTH - 2 * self.EDGE_MARGIN
            usable_height = self.SHEET_HEIGHT - 2 * self.EDGE_MARGIN
            
            for i in range(MAX_SHEETS):
                packer.add_bin(usable_width, usable_height, bid=i+1)
            
            # Подготавливаем детали с учетом количества
            parts_map = {}  # id -> информация о детали
            part_id = 0
            
            for part in parts_data:
                quantity = part.get('quantity', 1)
                base_name = part['name']
                
                for inst in range(quantity):
                    part_id += 1
                    unique_id = f"part_{part_id}"
                    
                    # Габариты с учетом зазора для резки
                    w = int(part['width_mm']) + self.CUT_GAP
                    h = int(part['height_mm']) + self.CUT_GAP
                    
                    # Добавляем деталь в упаковщик
                    packer.add_rect(w, h, rid=unique_id)
                    
                    # Сохраняем информацию
                    parts_map[unique_id] = {
                        'name': base_name,
                        'filename': part.get('filename', base_name),  # Имя файла
                        'filepath': part.get('filepath', ''),  # Путь к файлу
                        'original_width': part['width_mm'],
                        'original_height': part['height_mm'],
                        'area_m2': part['area_m2'],
                        'instance': inst + 1,
                        'total_quantity': quantity
                    }
            
            # УПАКОВЫВАЕМ!
            self.logger.info(f"Запуск оптимизации раскроя...")
            self.logger.info(f"  Деталей: {len(parts_map)}")
            self.logger.info(f"  Алгоритм: {algorithm}")
            self.logger.info(f"  Поворот: {'Да' if allow_rotation else 'Нет'}")
            
            packer.pack()
            
            # Собираем результаты
            sheets = []
            total_used_area_m2 = 0
            
            for bin_obj in packer:
                if len(bin_obj) == 0:
                    continue  # Пропускаем пустые листы
                
                sheet = {
                    'number': bin_obj.bid,
                    'parts': [],
                    'used_area_m2': 0
                }
                
                for rect in bin_obj:
                    part_info = parts_map[rect.rid]
                    
                    # Проверяем, была ли деталь повернута
                    # (если ширина не совпадает с оригинальной + зазор)
                    expected_width = int(part_info['original_width']) + self.CUT_GAP
                    rotated = (rect.width != expected_width)
                    
                    sheet['parts'].append({
                        'name': part_info['name'],
                        'filename': part_info.get('filename', part_info['name']),  # Имя файла
                        'filepath': part_info.get('filepath', ''),  # Путь к файлу
                        'x': rect.x + self.EDGE_MARGIN,
                        'y': rect.y + self.EDGE_MARGIN,
                        'width': int(part_info['original_width']),
                        'height': int(part_info['original_height']),
                        'rotated': rotated,
                        'instance': part_info['instance'],
                        'total_quantity': part_info['total_quantity'],
                        'original_width': part_info.get('original_width', part_info['original_width']),  # Дублируем для явности
                        'original_height': part_info.get('original_height', part_info['original_height'])
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
            self.logger.info(f"\n✓ Оптимизация завершена:")
            self.logger.info(f"  Листов требуется: {sheets_needed}")
            self.logger.info(f"  Использование материала: {utilization_percent:.1f}%")
            self.logger.info(f"  Обрезки: {overall_waste_percent:.1f}%")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка оптимизации: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    def compare_with_simple(self, parts_data: List[Dict]) -> Dict:
        """
        Сравнение rectpack с простым алгоритмом FFD
        
        Returns:
            {
                'rectpack': результат rectpack,
                'simple': результат FFD,
                'improvement_percent': улучшение в %
            }
        """
        
        # Оптимизация с rectpack
        rectpack_result = self.optimize_layout(parts_data, allow_rotation=True, algorithm='BFF')
        
        # Простая оценка FFD (сортировка по площади, укладка последовательно)
        parts_sorted = sorted(parts_data, key=lambda x: x['area_m2'] * x.get('quantity', 1), reverse=True)
        
        current_sheet_area = 0
        sheets_simple = 1
        
        for part in parts_sorted:
            quantity = part.get('quantity', 1)
            part_area = part['area_m2'] * quantity
            
            if current_sheet_area + part_area <= self.SHEET_AREA_M2:
                current_sheet_area += part_area
            else:
                sheets_simple += 1
                current_sheet_area = part_area
        
        total_area = sum(p['area_m2'] * p.get('quantity', 1) for p in parts_data)
        simple_waste = ((sheets_simple * self.SHEET_AREA_M2) - total_area) / (sheets_simple * self.SHEET_AREA_M2) * 100
        
        simple_result = {
            'sheets_needed': sheets_simple,
            'utilization_percent': 100 - simple_waste,
            'overall_waste_percent': simple_waste
        }
        
        if rectpack_result['success']:
            improvement = simple_result['overall_waste_percent'] - rectpack_result['overall_waste_percent']
            
            return {
                'rectpack': rectpack_result,
                'simple': simple_result,
                'improvement_percent': improvement,
                'improvement_description': f"Rectpack на {improvement:.1f}% эффективнее FFD"
            }
        else:
            return {
                'rectpack': rectpack_result,
                'simple': simple_result,
                'improvement_percent': 0,
                'improvement_description': "Rectpack недоступен"
            }


if __name__ == "__main__":
    # Тестирование
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    optimizer = RectpackOptimizer()
    
    if not optimizer.is_available():
        print("\n❌ Rectpack не установлен!")
        print("Установите: pip install rectpack")
        exit(1)
    
    # Тестовые данные
    test_parts = [
        {'name': 'Корпус короба', 'width_mm': 473.7, 'height_mm': 1800, 'area_m2': 0.8527, 'quantity': 1},
        {'name': 'Крышка декоративная', 'width_mm': 150, 'height_mm': 287.7, 'area_m2': 0.0432, 'quantity': 2},
        {'name': 'Распорка бассейна', 'width_mm': 298.1, 'height_mm': 83.3, 'area_m2': 0.0248, 'quantity': 2},
        {'name': 'Распорка верхняя', 'width_mm': 285.7, 'height_mm': 33.9, 'area_m2': 0.0097, 'quantity': 1},
        {'name': 'Стенка торцевая', 'width_mm': 298.1, 'height_mm': 84.8, 'area_m2': 0.0253, 'quantity': 2},
        {'name': 'Стенка', 'width_mm': 296, 'height_mm': 40, 'area_m2': 0.0118, 'quantity': 2},
    ]
    
    print("\n" + "="*80)
    print("ТЕСТ ОПТИМИЗАЦИИ РАСКРОЯ")
    print("="*80)
    print(f"\nТестовый проект: LITE.90.300.1800")
    print(f"Деталей: {sum(p['quantity'] for p in test_parts)} шт")
    print(f"Площадь деталей: {sum(p['area_m2'] * p['quantity'] for p in test_parts):.4f} м2")
    
    # Сравнение
    comparison = optimizer.compare_with_simple(test_parts)
    
    print("\n" + "="*80)
    print("СРАВНЕНИЕ АЛГОРИТМОВ")
    print("="*80)
    
    print(f"\n[FFD] Простой алгоритм:")
    print(f"   Листов: {comparison['simple']['sheets_needed']}")
    print(f"   Использование: {comparison['simple']['utilization_percent']:.1f}%")
    print(f"   Обрезки: {comparison['simple']['overall_waste_percent']:.1f}%")
    
    if comparison['rectpack']['success']:
        print(f"\n[RECTPACK] BFF + поворот:")
        print(f"   Листов: {comparison['rectpack']['sheets_needed']}")
        print(f"   Использование: {comparison['rectpack']['utilization_percent']:.1f}%")
        print(f"   Обрезки: {comparison['rectpack']['overall_waste_percent']:.1f}%")
        
        print(f"\n>>> {comparison['improvement_description']}")
    
    print("\n" + "="*80)
    print("[OK] Тест завершен!")
    print("="*80)

