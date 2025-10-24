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
        ПРОСТОЙ АНАЛИЗ ОПТИМАЛЬНОСТИ НА ОСНОВЕ РЕАЛЬНЫХ ФАКТОВ
        
        Args:
            L: Длина конвектора (мм)
            H: Высота конвектора (мм)
            W: Ширина конвектора (мм)
            parts_data: Данные о деталях
        
        Returns:
            Простой анализ на основе реальных фактов заполнения листа
        """
        
        # РЕАЛЬНЫЕ ФАКТЫ: Анализируем фактическое заполнение листа
        real_facts = self._analyze_real_sheet_utilization(L, H, parts_data)
        
        # Простые рекомендации на основе фактов
        recommendations = []
        
        # Факт 1: Сколько площади занято
        if real_facts['occupied_area_m2'] > 0:
            recommendations.append({
                'type': 'info',
                'text': f"Занято площади: {real_facts['occupied_area_m2']:.2f} м²"
            })
        
        # Факт 2: Сколько площади свободно
        if real_facts['free_area_m2'] > 0:
            recommendations.append({
                'type': 'success',
                'text': f"Свободно площади: {real_facts['free_area_m2']:.2f} м²"
            })
            
            # Факт 3: Что можно добавить в свободное место
            if real_facts['can_add_large_parts'] > 0:
                recommendations.append({
                    'type': 'success',
                    'text': f"Можно добавить {real_facts['can_add_large_parts']} крупных деталей"
                })
            
            if real_facts['can_add_small_parts'] > 0:
                recommendations.append({
                    'type': 'info',
                    'text': f"Можно добавить {real_facts['can_add_small_parts']} мелких деталей"
                })
        
        # Факт 4: Процент использования
        utilization_percent = real_facts['utilization_percent']
        recommendations.append({
            'type': 'info',
            'text': f"Использование листа: {utilization_percent:.1f}%"
        })
        
        # Факт 5: Сколько листов нужно
        if real_facts['sheets_needed'] > 0:
            recommendations.append({
                'type': 'info',
                'text': f"Требуется листов: {real_facts['sheets_needed']} шт"
            })
        
        # Факт 6: Экономия материала
        if real_facts['waste_area_m2'] > 0:
            recommendations.append({
                'type': 'warning',
                'text': f"Обрезки: {real_facts['waste_area_m2']:.2f} м²"
            })
        
        return {
            'dimensions': {'L': L, 'H': H, 'W': W},
            'real_facts': real_facts,
            'recommendations': recommendations,
            'actual_utilization': utilization_percent,
            'zone': self._get_zone_name(utilization_percent),
            'zone_color': self._get_zone_color(utilization_percent)
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
        """Получить текстовое резюме анализа на основе реальных фактов"""
        
        dims = analysis['dimensions']
        facts = analysis.get('real_facts', {})
        
        text = f"ГАБАРИТЫ: H={dims['H']:.0f} W={dims['W']:.0f} L={dims['L']:.0f} мм\n"
        text += f"ЗОНА: {analysis['zone']}\n"
        text += f"Использование: {analysis['actual_utilization']:.1f}%\n"
        
        # РЕАЛЬНЫЕ ФАКТЫ
        if facts:
            text += f"Занято площади: {facts['occupied_area_m2']:.2f} м²\n"
            text += f"Свободно площади: {facts['free_area_m2']:.2f} м²\n"
            text += f"Обрезки: {facts['waste_area_m2']:.2f} м²\n"
            
            if facts.get('max_corpus_per_sheet', 0) > 0:
                text += f"Корпусов на лист: {facts['max_corpus_per_sheet']} шт\n"
            
            if facts.get('can_add_large_parts', 0) > 0:
                text += f"Можно добавить крупных: {facts['can_add_large_parts']} шт\n"
            
            if facts.get('can_add_small_parts', 0) > 0:
                text += f"Можно добавить мелких: {facts['can_add_small_parts']} шт\n"
        
        return text
    
    def get_visual_indicator(self, utilization: float) -> str:
        """Получить визуальный индикатор (текстовая шкала)"""
        
        # Создаем текстовую шкалу 0-100%
        filled = int(utilization / 5)  # 20 делений
        empty = 20 - filled
        
        bar = "█" * filled + "░" * empty
        
        return f"[{bar}] {utilization:.1f}%"
    
    def _analyze_real_sheet_utilization(self, L: float, H: float, parts_data: List[Dict] = None) -> Dict:
        """
        АНАЛИЗ РЕАЛЬНОГО ЗАПОЛНЕНИЯ ЛИСТА НА ОСНОВЕ ФАКТОВ
        
        Args:
            L: Длина корпуса (мм)
            H: Высота корпуса (мм)
            parts_data: Данные о деталях
        
        Returns:
            Реальные факты о заполнении листа
        """
        
        # ФАКТ 1: Сколько корпусов помещается на лист
        n_x = int(self.SHEET_WIDTH / (L + self.CUT_GAP))
        n_y = int(self.SHEET_HEIGHT / (H + self.CUT_GAP))
        max_corpus_per_sheet = n_x * n_y
        
        if max_corpus_per_sheet == 0:
            return {
                'occupied_area_m2': 0,
                'free_area_m2': self.SHEET_AREA,
                'utilization_percent': 0,
                'sheets_needed': 0,
                'waste_area_m2': self.SHEET_AREA,
                'can_add_large_parts': 0,
                'can_add_small_parts': 0
            }
        
        # ФАКТ 2: Площадь одного корпуса
        corpus_area = (L * H) / 1_000_000  # м²
        
        # ФАКТ 3: Площадь, занятая корпусами на листе
        occupied_area = max_corpus_per_sheet * corpus_area
        
        # ФАКТ 4: Свободная площадь на листе
        free_area = self.SHEET_AREA - occupied_area
        
        # ФАКТ 5: Процент использования
        utilization_percent = (occupied_area / self.SHEET_AREA) * 100
        
        # ФАКТ 6: Анализ деталей (если есть данные)
        can_add_large_parts = 0
        can_add_small_parts = 0
        
        if parts_data:
            # Считаем общую площадь всех деталей
            total_parts_area = sum(p.get('area_m2', 0) * p.get('quantity', 1) 
                            for p in parts_data)
            
            # Сколько листов нужно для всех деталей
            sheets_needed = math.ceil(total_parts_area / self.SHEET_AREA)
            
            # Анализируем, что можно добавить в свободное место
            for part in parts_data:
                part_area = part.get('area_m2', 0)
                if part_area > 0:
                    # Крупная деталь: больше 0.1 м²
                    if part_area > 0.1 and part_area <= free_area:
                        can_add_large_parts += 1
                    # Мелкая деталь: меньше 0.1 м²
                    elif part_area <= 0.1 and part_area <= free_area * 0.5:
                        can_add_small_parts += 1
        else:
            sheets_needed = 1
        
        # ФАКТ 7: Обрезки (неиспользуемая площадь)
        waste_area = free_area
        
        return {
            'occupied_area_m2': occupied_area,
            'free_area_m2': free_area,
            'utilization_percent': utilization_percent,
            'sheets_needed': sheets_needed,
            'waste_area_m2': waste_area,
            'can_add_large_parts': can_add_large_parts,
            'can_add_small_parts': can_add_small_parts,
            'max_corpus_per_sheet': max_corpus_per_sheet
        }
    
    def _calculate_remaining_areas(self, L: float, H: float, composition: Dict = None) -> Dict:
        """
        Анализ оставшихся областей на листах и рекомендации по их заполнению
        
        Args:
            L: Длина корпуса
            H: Высота корпуса  
            composition: Состав проекта
            
        Returns:
            Рекомендации по заполнению областей
        """
        # Рассчитываем, сколько корпусов помещается на лист
        n_x = int(self.SHEET_WIDTH / (L + self.CUT_GAP))
        n_y = int(self.SHEET_HEIGHT / (H + self.CUT_GAP))
        max_corpus_per_sheet = n_x * n_y
        
        # Площадь одного корпуса
        corpus_area = (L * H) / 1_000_000  # м²
        
        # Оставшаяся площадь на листе
        used_area = max_corpus_per_sheet * corpus_area
        remaining_area = self.SHEET_AREA - used_area
        
        # Анализируем, что можно разместить в оставшихся областях
        large_areas = 0
        small_areas = 0
        suggested_parts = []
        
        # Если есть информация о составе проекта
        if composition and composition.get('has_composition_data'):
            # Анализируем мелкие детали из проекта
            small_parts = composition.get('small_parts', [])
            
            # Считаем, сколько мелких деталей можно добавить
            for part in small_parts:
                part_area = part['area']
                if part_area <= remaining_area * 0.1:  # Деталь занимает < 10% оставшейся площади
                    small_areas += 1
                    suggested_parts.append(part['name'][:20])  # Сокращаем название
            
            # Если есть крупные детали, которые могут поместиться
            large_parts = composition.get('large_parts', [])
            for part in large_parts:
                part_area = part['area']
                if part_area <= remaining_area * 0.3:  # Деталь занимает < 30% оставшейся площади
                    large_areas += 1
                    suggested_parts.append(part['name'][:20])
        else:
            # Общие рекомендации без анализа состава
            if remaining_area > 0.5:  # Больше 0.5 м² свободно
                large_areas = 1
                suggested_parts.append("крупные детали")
            
            if remaining_area > 0.1:  # Больше 0.1 м² свободно
                small_areas = 3
                suggested_parts.append("мелкие детали")
        
        return {
            'remaining_area_m2': remaining_area,
            'large_areas': large_areas,
            'small_areas': small_areas,
            'suggested_parts': suggested_parts[:5]  # Максимум 5 предложений
        }

# Глобальный экземпляр
analyzer = OptimalityAnalyzer()

