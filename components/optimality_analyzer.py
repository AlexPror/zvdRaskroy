#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Анализатор оптимальности габаритов
Определяет, насколько текущие габариты проекта оптимальны
с точки зрения использования материала
"""

import math
from typing import Dict, List, Tuple

class OptimalityAnalyzer:
    """Анализатор оптимальности габаритов конвектора"""
    
    SHEET_WIDTH = 2500  # мм
    SHEET_HEIGHT = 1250  # мм
    SHEET_AREA = SHEET_WIDTH * SHEET_HEIGHT / 1_000_000  # м2
    CUT_GAP = 5  # мм
    MAX_BEND_LENGTH = 2400  # мм
    
    # Классические магические длины (минимум обрезков)
    MAGIC_LENGTHS_CLASSIC = [
        {'L': 1200, 'N': 2, 'tolerance': 50, 'type': 'classic'},  # ±50 мм
        {'L': 800, 'N': 3, 'tolerance': 50, 'type': 'classic'},
        {'L': 600, 'N': 4, 'tolerance': 50, 'type': 'classic'},
        {'L': 2400, 'N': 1, 'tolerance': 50, 'type': 'classic'},
    ]
    
    # Комбинированные оптимальные длины (эффективны с мелкими деталями)
    MAGIC_LENGTHS_COMBO = [
        {'L': 1000, 'N': 2, 'tolerance': 50, 'type': 'combo', 'min_small_parts': 8},
        {'L': 1400, 'N': 1, 'tolerance': 50, 'type': 'combo', 'min_small_parts': 6},
        {'L': 1600, 'N': 1, 'tolerance': 50, 'type': 'combo', 'min_small_parts': 4},
    ]
    
    # Объединённый список
    MAGIC_LENGTHS = MAGIC_LENGTHS_CLASSIC + MAGIC_LENGTHS_COMBO
    
    def __init__(self):
        self.analysis_cache = {}
    
    def calculate_corpus_utilization(self, L: float, H: float) -> Dict:
        """Рассчитать использование для корпуса L x H"""
        
        # Учитываем деление длинных корпусов
        if L <= self.MAX_BEND_LENGTH:
            part_L = L
            parts_count = 1
        elif L <= self.MAX_BEND_LENGTH * 2:
            part_L = L / 2
            parts_count = 2
        else:
            part_L = L / 3
            parts_count = 3
        
        # Горизонтально
        n_x = int(self.SHEET_WIDTH / (part_L + self.CUT_GAP))
        n_y = int(self.SHEET_HEIGHT / (H + self.CUT_GAP))
        horizontal = n_x * n_y
        
        # Вертикально
        v_x = int(self.SHEET_WIDTH / (H + self.CUT_GAP))
        v_y = int(self.SHEET_HEIGHT / (part_L + self.CUT_GAP))
        vertical = v_x * v_y
        
        max_per_sheet = max(horizontal, vertical)
        orientation = "горизонтально" if horizontal >= vertical else "вертикально"
        
        if max_per_sheet == 0:
            return {
                'utilization': 0,
                'waste': 100,
                'category': 'impossible',
                'parts_per_sheet': 0
            }
        
        # Использование
        area = (part_L * H * max_per_sheet) / 1_000_000
        utilization = (area / self.SHEET_AREA) * 100
        waste = 100 - utilization
        
        # Категория
        if utilization >= 85:
            category = 'excellent'
            category_ru = 'ОТЛИЧНО'
            color = '#4CAF50'
        elif utilization >= 70:
            category = 'good'
            category_ru = 'ХОРОШО'
            color = '#8BC34A'
        elif utilization >= 55:
            category = 'medium'
            category_ru = 'СРЕДНЕ'
            color = '#FF9800'
        else:
            category = 'poor'
            category_ru = 'ПЛОХО'
            color = '#F44336'
        
        return {
            'utilization': utilization,
            'waste': waste,
            'category': category,
            'category_ru': category_ru,
            'color': color,
            'parts_per_sheet': max_per_sheet,
            'orientation': orientation,
            'split_parts': parts_count,
            'part_length': part_L
        }
    
    def analyze_parts_composition(self, parts_data: List[Dict], L: float, H: float) -> Dict:
        """
        Анализ состава проекта: соотношение крупных и мелких деталей
        
        Args:
            parts_data: Список деталей с полями width, height, area_m2, quantity
            L: Длина корпуса (мм)
            H: Высота корпуса (мм)
            
        Returns:
            Информация о составе проекта
        """
        if not parts_data:
            return {
                'has_composition_data': False,
                'small_parts_count': 0,
                'large_parts_count': 0,
                'is_combo_suitable': False
            }
        
        # Определяем "крупные" детали (близки к размерам корпуса)
        # и "мелкие" (значительно меньше)
        large_parts = []
        small_parts = []
        
        for part in parts_data:
            width = part.get('width', 0)
            height = part.get('height', 0)
            area = part.get('area_m2', 0)
            qty = part.get('quantity', 1)
            
            # Определяем, крупная ли деталь
            # Крупная: площадь > 50% от площади корпуса
            corpus_area = (L * H) / 1_000_000  # м²
            is_large = area > corpus_area * 0.5
            
            if is_large:
                large_parts.append({
                    'name': part.get('name', part.get('filename', 'Unknown')),
                    'width': width,
                    'height': height,
                    'area': area,
                    'quantity': qty,
                    'total_area': area * qty
                })
            else:
                small_parts.append({
                    'name': part.get('name', part.get('filename', 'Unknown')),
                    'width': width,
                    'height': height,
                    'area': area,
                    'quantity': qty,
                    'total_area': area * qty
                })
        
        # Считаем общие площади
        large_total_area = sum(p['total_area'] for p in large_parts)
        small_total_area = sum(p['total_area'] for p in small_parts)
        total_area = large_total_area + small_total_area
        
        # Соотношение площадей
        if total_area > 0:
            large_ratio = large_total_area / total_area
            small_ratio = small_total_area / total_area
        else:
            large_ratio = 0
            small_ratio = 0
        
        # Количество уникальных типов
        small_types_count = len(small_parts)
        large_types_count = len(large_parts)
        
        # Определяем, подходит ли для комбинированного раскроя
        # Условия:
        # 1. Есть хотя бы 4 типа мелких деталей
        # 2. Площадь мелких > 20% от общей
        is_combo_suitable = (small_types_count >= 4) and (small_ratio > 0.2)
        
        return {
            'has_composition_data': True,
            'large_parts_count': large_types_count,
            'small_parts_count': small_types_count,
            'large_parts': large_parts,
            'small_parts': small_parts,
            'large_total_area': large_total_area,
            'small_total_area': small_total_area,
            'large_ratio': large_ratio,
            'small_ratio': small_ratio,
            'is_combo_suitable': is_combo_suitable,
            'total_parts_types': len(parts_data)
        }
    
    def is_near_magic(self, L: float, composition: Dict = None) -> Tuple[bool, Dict]:
        """
        Проверить, близка ли длина L к магическому числу
        
        Args:
            L: Длина корпуса
            composition: Информация о составе проекта (опционально)
        """
        
        # Сначала проверяем классические магические
        for magic in self.MAGIC_LENGTHS_CLASSIC:
            if abs(L - magic['L']) <= magic['tolerance']:
                return True, magic
        
        # Если есть информация о составе, проверяем комбинированные
        if composition and composition.get('is_combo_suitable'):
            for magic in self.MAGIC_LENGTHS_COMBO:
                if abs(L - magic['L']) <= magic['tolerance']:
                    # Проверяем, достаточно ли мелких деталей
                    min_required = magic.get('min_small_parts', 0)
                    if composition['small_parts_count'] >= min_required:
                        return True, magic
        
        return False, {}
    
    def analyze_project_dimensions(self, L: float, H: float, W: float, 
                                   parts_data: List[Dict] = None) -> Dict:
        """
        Полный анализ габаритов проекта С УЧЁТОМ СОСТАВА ДЕТАЛЕЙ
        
        Args:
            L: Длина конвектора (мм)
            H: Высота конвектора (мм)
            W: Ширина конвектора (мм)
            parts_data: Данные о деталях (ВАЖНО!)
        
        Returns:
            Детальный анализ оптимальности
        """
        
        # НОВОЕ: Анализируем состав проекта
        composition = self.analyze_parts_composition(parts_data, L, H) if parts_data else None
        
        # Рассчитываем для корпуса
        corpus_result = self.calculate_corpus_utilization(L, H)
        
        # Проверяем на магическое число С УЧЁТОМ СОСТАВА
        is_magic, magic_info = self.is_near_magic(L, composition)
        
        # Рекомендация по улучшению С УЧЁТОМ СОСТАВА
        recommendations = []
        
        # НОВОЕ: Добавляем информацию о составе проекта
        if composition and composition['has_composition_data']:
            recommendations.append({
                'type': 'info',
                'text': f"Состав: {composition['large_parts_count']} крупн. + {composition['small_parts_count']} мелк. деталей"
            })
            
            if composition['is_combo_suitable']:
                recommendations.append({
                    'type': 'success',
                    'text': f"Проект подходит для комбинированного раскроя ({composition['small_parts_count']} мелких)"
                })
        
        if is_magic:
            magic_type = magic_info.get('type', 'classic')
            if magic_type == 'classic':
                recommendations.append({
                    'type': 'success',
                    'text': f"Отлично! L={L:.0f} - КЛАССИЧЕСКОЕ магическое число (L={magic_info['L']} мм)"
                })
            else:  # combo
                recommendations.append({
                    'type': 'success',
                    'text': f"Отлично! L={L:.0f} - КОМБИНИРОВАННОЕ оптимальное (L={magic_info['L']} мм с мелкими)"
                })
                if composition:
                    min_req = magic_info.get('min_small_parts', 0)
                    actual = composition['small_parts_count']
                    recommendations.append({
                        'type': 'info',
                        'text': f"Мелких деталей: {actual} (требуется минимум {min_req})"
                    })
        else:
            # Находим ближайшее магическое
            # Сначала классические
            closest_classic = min(self.MAGIC_LENGTHS_CLASSIC, 
                                key=lambda m: abs(m['L'] - L))
            
            # Если есть мелкие детали, ищем комбинированные
            closest_combo = None
            if composition and composition['is_combo_suitable']:
                suitable_combos = [m for m in self.MAGIC_LENGTHS_COMBO 
                                 if composition['small_parts_count'] >= m.get('min_small_parts', 0)]
                if suitable_combos:
                    closest_combo = min(suitable_combos, key=lambda m: abs(m['L'] - L))
            
            # Выбираем ближайшее
            if closest_combo and abs(L - closest_combo['L']) < abs(L - closest_classic['L']):
                closest_magic = closest_combo
                magic_type_str = "комбинированное"
            else:
                closest_magic = closest_classic
                magic_type_str = "классическое магическое"
            
            if corpus_result['category'] in ['poor', 'medium']:
                recommendations.append({
                    'type': 'warning',
                    'text': f"Рекомендуем изменить L={L:.0f} на {magic_type_str} L={closest_magic['L']} мм"
                })
                diff = abs(closest_magic['L'] - L)
                recommendations.append({
                    'type': 'info',
                    'text': f"Изменение: {'+' if L < closest_magic['L'] else '-'}{diff:.0f} мм"
                })
        
        # Проверка высоты
        if H > 150:
            recommendations.append({
                'type': 'info',
                'text': f"Высота H={H:.0f} довольно большая - меньше деталей в высоту"
            })
        elif H < 80:
            recommendations.append({
                'type': 'success',
                'text': f"Высота H={H:.0f} компактная - больше деталей на лист"
            })
        
        # Проверка ширины
        if W > 400:
            recommendations.append({
                'type': 'warning',
                'text': f"Ширина W={W:.0f} большая - много мелких деталей"
            })
        
        # Анализ с учетом деталей
        if parts_data:
            total_area = sum(p.get('area_m2', 0) * p.get('quantity', 1) 
                           for p in parts_data)
            
            sheets_needed = math.ceil(total_area / self.SHEET_AREA)
            actual_utilization = (total_area / (sheets_needed * self.SHEET_AREA)) * 100
            
            # Сравниваем теоретическое и фактическое
            theoretical_util = corpus_result['utilization']
            diff = actual_utilization - theoretical_util
            
            if diff < -15:
                recommendations.append({
                    'type': 'warning',
                    'text': f"Фактическое использование ({actual_utilization:.1f}%) ниже теоретического на {abs(diff):.1f}%"
                })
                recommendations.append({
                    'type': 'info',
                    'text': "Возможно, много нестандартных деталей или неоптимальный раскрой"
                })
        else:
            actual_utilization = corpus_result['utilization']
        
        return {
            'dimensions': {'L': L, 'H': H, 'W': W},
            'corpus_analysis': corpus_result,
            'composition': composition,  # НОВОЕ: Информация о составе
            'is_magic': is_magic,
            'magic_info': magic_info if is_magic else closest_magic,
            'magic_type': magic_info.get('type', 'unknown') if is_magic else None,  # НОВОЕ: Тип магического
            'recommendations': recommendations,
            'actual_utilization': actual_utilization,
            'zone': self._get_zone_name(actual_utilization),
            'zone_color': self._get_zone_color(actual_utilization)
        }
    
    def _get_zone_name(self, utilization: float) -> str:
        """Получить название зоны по использованию"""
        if utilization >= 85:
            return "ЗЕЛЁНАЯ ЗОНА (Отлично!)"
        elif utilization >= 70:
            return "ЖЁЛТАЯ ЗОНА (Хорошо)"
        elif utilization >= 55:
            return "ОРАНЖЕВАЯ ЗОНА (Средне)"
        else:
            return "КРАСНАЯ ЗОНА (Требует оптимизации)"
    
    def _get_zone_color(self, utilization: float) -> str:
        """Получить цвет зоны"""
        if utilization >= 85:
            return "#4CAF50"  # Зелёный
        elif utilization >= 70:
            return "#FFC107"  # Жёлтый
        elif utilization >= 55:
            return "#FF9800"  # Оранжевый
        else:
            return "#F44336"  # Красный
    
    def get_summary_text(self, analysis: Dict) -> str:
        """Получить текстовое резюме анализа"""
        
        result = analysis['corpus_analysis']
        dims = analysis['dimensions']
        
        text = f"ГАБАРИТЫ: H={dims['H']:.0f} W={dims['W']:.0f} L={dims['L']:.0f} мм\n"
        text += f"ЗОНА: {analysis['zone']}\n"
        text += f"Использование: {analysis['actual_utilization']:.1f}% | "
        text += f"Обрезки: {100 - analysis['actual_utilization']:.1f}%\n"
        
        if analysis['is_magic']:
            text += f"[MAGIC] Близко к магическому числу!\n"
        
        if result['split_parts'] > 1:
            text += f"Корпус делится на {result['split_parts']} части по {result['part_length']:.0f} мм\n"
        
        text += f"Деталей корпуса на лист: {result['parts_per_sheet']} шт\n"
        
        return text
    
    def get_visual_indicator(self, utilization: float) -> str:
        """Получить визуальный индикатор (текстовая шкала)"""
        
        # Создаем текстовую шкалу 0-100%
        filled = int(utilization / 5)  # 20 делений
        empty = 20 - filled
        
        bar = "█" * filled + "░" * empty
        
        return f"[{bar}] {utilization:.1f}%"

# Глобальный экземпляр
analyzer = OptimalityAnalyzer()

