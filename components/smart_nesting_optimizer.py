#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
УМНЫЙ оптимизатор раскроя
Комбинирует маленькие и большие детали для лучшего заполнения
"""

import logging
import os
from typing import Dict, List, Tuple
import rectpack
from rectpack import newPacker, PackingMode, PackingBin, SORT_AREA, SORT_PERI


class SmartNestingOptimizer:
    """
    Умный оптимизатор - комбинирует детали разных размеров
    """
    
    SHEET_WIDTH = 2500  # мм
    SHEET_HEIGHT = 1250  # мм
    CUT_GAP = 2.5  # мм - ПОЛОВИНА зазора (между деталями будет 2.5+2.5=5мм)
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def optimize_smart(self, parts_data: List[Dict], allow_rotation: bool = True) -> Dict:
        """
        УМНАЯ оптимизация с комбинированием маленьких и больших деталей
        
        Args:
            parts_data: Список деталей с их параметрами
            allow_rotation: Разрешить поворот деталей на 90°
            
        Returns:
            Словарь с результатами раскроя
        """
        try:
            self.logger.info(f"[START] Умная оптимизация {len(parts_data)} деталей")
            
            # Разворачиваем детали с учетом количества
            all_parts = []
            for idx, part in enumerate(parts_data):
                qty = part.get('quantity', 1)
                for i in range(qty):
                    # Получаем имя детали (может быть 'name' или 'filename')
                    part_name = part.get('name') or part.get('filename', f'Деталь_{idx}')
                    
                    width = part.get('width_mm') or part.get('width', 100)
                    height = part.get('height_mm') or part.get('height', 100)
                    
                    # ВАЖНО: Поворачиваем деталь горизонтально (ширина > высоты)
                    if height > width:
                        width, height = height, width  # Меняем местами
                    
                    all_parts.append({
                        'original_idx': idx,
                        'instance': i + 1,
                        'name': part_name,
                        'filename': part.get('filename', part_name),  # Имя файла
                        'filepath': part.get('filepath', ''),  # Путь к DXF
                        'width': width,
                        'height': height,
                        'area': part.get('area_m2') or part.get('area', 0.01),
                        'was_rotated': width != (part.get('width_mm') or part.get('width', width)),  # Запоминаем что повернули
                        'original_width': part.get('original_width') or part.get('width_mm') or width,  # ОРИГИНАЛ из DXF
                        'original_height': part.get('original_height') or part.get('height_mm') or height  # ОРИГИНАЛ из DXF
                    })
            
            total_parts = len(all_parts)
            self.logger.info(f"[INFO] Всего деталей для размещения: {total_parts}")
            
            # Сортируем детали по площади (большие сначала)
            all_parts.sort(key=lambda p: p['width'] * p['height'], reverse=True)
            
            # Пробуем упаковать с разными стратегиями
            best_result = None
            best_sheets = float('inf')
            
            strategies = [
                ('BIG_FIRST', self._pack_big_first),
                ('MIXED', self._pack_mixed),
                ('LAYERED', self._pack_layered)
            ]
            
            for strategy_name, strategy_func in strategies:
                self.logger.info(f"[TRY] Стратегия: {strategy_name}")
                result = strategy_func(all_parts, allow_rotation)
                
                if result and result['sheets_needed'] < best_sheets:
                    best_sheets = result['sheets_needed']
                    best_result = result
                    self.logger.info(f"[OK] {strategy_name}: {best_sheets} листов, {result['utilization_percent']:.1f}%")
            
            if not best_result:
                return {
                    'success': False,
                    'error': 'Не удалось разместить детали ни одной стратегией'
                }
            
            self.logger.info(f"[BEST] Лучший результат: {best_sheets} листов")
            return best_result
            
        except Exception as e:
            self.logger.error(f"[ERROR] Ошибка оптимизации: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _pack_big_first(self, parts: List[Dict], allow_rotation: bool) -> Dict:
        """Стратегия 1: Большие детали первыми, потом заполняем пустоты маленькими"""
        
        # МАКСИМАЛЬНО ПЛОТНАЯ упаковка
        packer = newPacker(
            mode=PackingMode.Online,  # ONLINE - упаковывает последовательно, плотно
            pack_algo=rectpack.MaxRectsBssf,  # Best Short Side Fit - самый плотный
            rotation=False,  # НЕ поворачиваем - мы уже повернули!
            sort_algo=SORT_AREA  # Сортировка по площади
        )
        
        # Добавляем МНОГО листов (будут использованы только нужные)
        for i in range(100):
            packer.add_bin(self.SHEET_WIDTH, self.SHEET_HEIGHT)
        
        # Добавляем детали (с зазором)
        # В Online режиме упаковка происходит автоматически при добавлении!
        for idx, part in enumerate(parts):
            packer.add_rect(
                width=part['width'] + self.CUT_GAP,
                height=part['height'] + self.CUT_GAP,
                rid=idx
            )
        
        # НЕ нужен pack() в Online режиме - он упаковывает автоматически!
        
        # Собираем результаты
        return self._collect_results(packer, parts)
    
    def _pack_mixed(self, parts: List[Dict], allow_rotation: bool) -> Dict:
        """Стратегия 2: Смешанная упаковка - чередуем большие и маленькие"""
        
        # Делим на большие и маленькие
        total_area = sum(p['width'] * p['height'] for p in parts)
        avg_area = total_area / len(parts)
        
        big_parts = [p for p in parts if p['width'] * p['height'] > avg_area]
        small_parts = [p for p in parts if p['width'] * p['height'] <= avg_area]
        
        self.logger.info(f"[INFO] Больших: {len(big_parts)}, Маленьких: {len(small_parts)}")
        
        # Создаем новый список, чередуя большие и маленькие
        mixed_parts = []
        big_idx = 0
        small_idx = 0
        
        while big_idx < len(big_parts) or small_idx < len(small_parts):
            # Добавляем большую деталь
            if big_idx < len(big_parts):
                mixed_parts.append(big_parts[big_idx])
                big_idx += 1
            
            # Добавляем несколько маленьких
            for _ in range(3):  # До 3 маленьких после каждой большой
                if small_idx < len(small_parts):
                    mixed_parts.append(small_parts[small_idx])
                    small_idx += 1
        
        # МАКСИМАЛЬНО ПЛОТНАЯ упаковка
        packer = newPacker(
            mode=PackingMode.Online,  # ONLINE - плотная упаковка
            pack_algo=rectpack.MaxRectsBssf,  # Best Short Side Fit
            rotation=False  # НЕ поворачиваем - мы уже повернули!
        )
        
        # Добавляем листы
        for i in range(100):
            packer.add_bin(self.SHEET_WIDTH, self.SHEET_HEIGHT)
        
        # Добавляем детали в смешанном порядке
        # В Online режиме упаковка происходит автоматически!
        for idx, part in enumerate(mixed_parts):
            packer.add_rect(
                width=part['width'] + self.CUT_GAP,
                height=part['height'] + self.CUT_GAP,
                rid=parts.index(part)  # Используем оригинальный индекс
            )
        
        # НЕ нужен pack() в Online режиме!
        
        return self._collect_results(packer, parts)
    
    def _pack_layered(self, parts: List[Dict], allow_rotation: bool) -> Dict:
        """Стратегия 3: Послойная упаковка - сначала все большие, потом все маленькие"""
        
        # Сортируем по размеру
        sorted_parts = sorted(parts, key=lambda p: p['width'] * p['height'], reverse=True)
        
        # МАКСИМАЛЬНО ПЛОТНАЯ упаковка
        packer = newPacker(
            mode=PackingMode.Online,  # ONLINE - плотная упаковка
            pack_algo=rectpack.MaxRectsBssf,  # Best Short Side Fit
            rotation=False,  # НЕ поворачиваем - мы уже повернули!
            sort_algo=SORT_PERI  # Сортировка по периметру
        )
        
        # Добавляем листы
        for i in range(100):
            packer.add_bin(self.SHEET_WIDTH, self.SHEET_HEIGHT)
        
        # Добавляем детали
        # В Online режиме упаковка происходит автоматически!
        for idx, part in enumerate(sorted_parts):
            packer.add_rect(
                width=part['width'] + self.CUT_GAP,
                height=part['height'] + self.CUT_GAP,
                rid=parts.index(part)
            )
        
        # НЕ нужен pack() в Online режиме!
        
        return self._collect_results(packer, parts)
    
    def _collect_results(self, packer, parts: List[Dict]) -> Dict:
        """Сбор результатов упаковки"""
        
        sheets = []
        total_parts_placed = 0
        
        for bin_idx, bin_pack in enumerate(packer):
            if not bin_pack:
                continue
            
            sheet_parts = []
            for rect in bin_pack:
                part = parts[rect.rid]
                
                # Координаты и размеры с учетом зазора
                # rect.x, rect.y - координаты с зазором
                # rect.width, rect.height - размеры с зазором
                sheet_parts.append({
                    'name': part['name'],
                    'filename': part.get('filename', part['name']),
                    'filepath': part.get('filepath', ''),  # Путь к DXF для рендеринга
                    'x': rect.x,  # Координаты с зазором
                    'y': rect.y,
                    'width': rect.width,  # Размеры С зазором (как в rectpack)
                    'height': rect.height,
                    'real_width': part['width'],  # РЕАЛЬНЫЕ размеры без зазора
                    'real_height': part['height'],  # РЕАЛЬНЫЕ размеры без зазора
                    'rotated': part.get('was_rotated', False)  # Была ли повернута
                })
                total_parts_placed += 1
            
            if sheet_parts:
                sheets.append({
                    'number': len(sheets) + 1,
                    'parts': sheet_parts
                })
        
        if total_parts_placed < len(parts):
            return None  # Не все детали поместились
        
        # Расчет статистики
        total_parts_area = sum(p['area'] for p in parts)
        sheet_area = (self.SHEET_WIDTH * self.SHEET_HEIGHT) / 1_000_000  # м²
        total_sheets_area = len(sheets) * sheet_area
        
        utilization = (total_parts_area / total_sheets_area) * 100 if total_sheets_area > 0 else 0
        waste = 100 - utilization
        
        # Расчет параметров резки
        total_cut_length = self._calculate_total_cut_length(parts)
        total_contours = self._calculate_total_contours(parts)
        cutting_time = self._calculate_cutting_time(total_cut_length)
        
        return {
            'success': True,
            'sheets_needed': len(sheets),
            'sheets': sheets,
            'total_parts': len(parts),
            'utilization_percent': utilization,
            'overall_waste_percent': waste,
            'total_parts_area_m2': total_parts_area,
            'total_sheets_area_m2': total_sheets_area,
            'total_cut_length_mm': total_cut_length,
            'total_contours': total_contours,
            'cutting_time_minutes': cutting_time
        }
    
    def _calculate_total_cut_length(self, parts: List[Dict]) -> float:
        """Расчет общей длины реза для всех деталей с учетом всех контуров"""
        total_length = 0.0
        
        for part in parts:
            # Базовый периметр прямоугольника
            base_perimeter = 2 * (part['width'] + part['height'])
            
            # Анализ DXF файла для подсчета всех контуров
            filepath = part.get('filepath', '')
            if filepath and os.path.exists(filepath):
                try:
                    # Анализируем DXF файл для подсчета всех контуров
                    contours_count = self._count_holes_in_dxf(filepath)
                    # Каждый дополнительный контур добавляет к длине реза
                    # (1 контур уже учтен в базовом периметре)
                    additional_contours = max(0, contours_count - 1)
                    additional_cut_length = additional_contours * 50  # 50мм на дополнительный контур
                    total_length += base_perimeter + additional_cut_length
                except Exception as e:
                    print(f"[DEBUG] Ошибка анализа DXF для длины реза: {e}")
                    # Если не удалось проанализировать DXF, используем базовый расчет
                    total_length += base_perimeter
            else:
                # Если нет DXF файла, используем базовый расчет
                total_length += base_perimeter
        
        return total_length
    
    def _calculate_total_contours(self, parts: List[Dict]) -> int:
        """Расчет общего количества контуров (внешний + все внутренние контуры)"""
        total_contours = 0
        
        for part in parts:
            # Анализ DXF файла для подсчета всех контуров
            filepath = part.get('filepath', '')
            if filepath and os.path.exists(filepath):
                try:
                    # Анализируем DXF файл для подсчета всех контуров
                    contours_count = self._count_holes_in_dxf(filepath)
                    total_contours += contours_count
                except Exception as e:
                    print(f"[DEBUG] Ошибка анализа DXF для контуров: {e}")
                    # Если не удалось проанализировать DXF, используем базовый расчет
                    total_contours += 1
            else:
                # Если нет DXF файла, используем базовый расчет
                total_contours += 1
        
        return total_contours
    
    def _count_holes_in_dxf(self, filepath: str) -> int:
        """Подсчет замкнутых контуров в DXF файле (как в боте)"""
        try:
            import ezdxf
            
            # Загружаем DXF файл
            doc = ezdxf.readfile(filepath)
            msp = doc.modelspace()
            
            contours_count = 0
            
            # Анализируем только замкнутые контуры
            for entity in msp:
                entity_type = entity.dxftype()
                
                # Круги (отверстия) - только реальные отверстия
                if entity_type == 'CIRCLE':
                    radius = entity.dxf.radius
                    if 1.75 <= radius <= 50:  # Реальные отверстия от 3.5мм до 100мм диаметр
                        contours_count += 1
                
                # Полилинии - только замкнутые контуры
                elif entity_type == 'LWPOLYLINE':
                    if entity.closed:  # Только замкнутые полилинии
                        vertices = len(entity.get_points())
                        if vertices >= 4:  # Минимум 4 вершины для замкнутого контура
                            contours_count += 1
                
                # Полилинии старого типа
                elif entity_type == 'POLYLINE':
                    if entity.is_closed:  # Только замкнутые полилинии
                        vertices = len(entity.vertices)
                        if vertices >= 4:
                            contours_count += 1
                
                # Эллипсы (замкнутые контуры)
                elif entity_type == 'ELLIPSE':
                    contours_count += 1
                
                # Сплайны (замкнутые кривые)
                elif entity_type == 'SPLINE':
                    contours_count += 1
            
            # Всегда добавляем внешний контур детали (минимум 1)
            contours_count += 1
            
            return contours_count
            
        except Exception as e:
            print(f"[DEBUG] Ошибка анализа DXF {filepath}: {e}")
            return 1  # Минимум 1 контур (внешний)
    
    def _calculate_cutting_time(self, cut_length_mm: float) -> float:
        """Расчет времени резки"""
        # Скорость резки лазером: ~3 м/мин = 3000 мм/мин
        CUTTING_SPEED_MM_PER_MIN = 3000.0
        
        # Время = длина / скорость
        cutting_time = cut_length_mm / CUTTING_SPEED_MM_PER_MIN
        
        # Добавляем время на позиционирование (примерно 10% от времени резки)
        positioning_time = cutting_time * 0.1
        
        return cutting_time + positioning_time


if __name__ == "__main__":
    # Тест
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    print("="*70)
    print("ТЕСТ УМНОГО ОПТИМИЗАТОРА")
    print("="*70)
    
    # Тестовые данные - разные размеры
    test_parts = [
        {'name': 'Корпус большой', 'width_mm': 1200, 'height_mm': 400, 'area_m2': 0.48, 'quantity': 2},
        {'name': 'Крышка', 'width_mm': 287, 'height_mm': 150, 'area_m2': 0.043, 'quantity': 5},
        {'name': 'Стенка', 'width_mm': 134, 'height_mm': 298, 'area_m2': 0.04, 'quantity': 8},
        {'name': 'Распорка', 'width_mm': 122, 'height_mm': 298, 'area_m2': 0.036, 'quantity': 10},
    ]
    
    optimizer = SmartNestingOptimizer()
    result = optimizer.optimize_smart(test_parts, allow_rotation=True)
    
    if result['success']:
        print(f"\n[OK] РЕЗУЛЬТАТ:")
        print(f"  Листов: {result['sheets_needed']}")
        print(f"  Деталей всего: {result['total_parts']}")
        print(f"  Использование: {result['utilization_percent']:.1f}%")
        print(f"  Обрезки: {result['overall_waste_percent']:.1f}%")
        
        for sheet in result['sheets']:
            print(f"\n  ЛИСТ #{sheet['number']}: {len(sheet['parts'])} деталей")
    else:
        print(f"\n[ERROR] {result['error']}")

