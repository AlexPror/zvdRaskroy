#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль приоритетной проверки обрезков перед новым проектом
ГЛАВНАЯ ЗАДАЧА: Предлагать обрезки ВМЕСТО новых листов
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional
from components.cypcut_parser import WasteDatabaseManager


class WastePriorityChecker:
    """
    Проверяет базу обрезков перед началом нового проекта
    Находит подходящие обрезки для деталей
    """
    
    def __init__(self, db_manager: WasteDatabaseManager = None):
        self.logger = logging.getLogger(__name__)
        self.db_manager = db_manager or WasteDatabaseManager()
    
    def check_for_project(self, parts: List[Dict], material: str = "Оцинковка 1.5мм") -> Dict:
        """
        Проверяет базу обрезков для нового проекта
        
        Args:
            parts: список деталей проекта [{'name': str, 'width': float, 'height': float, 'area_m2': float}]
            material: тип материала
        
        Returns:
            {
                'has_suitable_wastes': bool,
                'matches': [  # Список найденных совпадений
                    {
                        'part': {...},  # Деталь
                        'waste': {...},  # Подходящий обрезок
                        'economy_rub': float  # Экономия в рублях
                    }
                ],
                'total_economy_rub': float,
                'message': str  # Сообщение для пользователя
            }
        """
        
        self.logger.info(f"Проверка базы обрезков для {len(parts)} деталей...")
        
        matches = []
        total_economy = 0
        
        for part in parts:
            # Ищем подходящий обрезок
            suitable_waste = self.db_manager.find_suitable_waste(
                part_width=part['width'],
                part_height=part['height'],
                material=material
            )
            
            if suitable_waste:
                matches.append({
                    'part': part,
                    'waste': suitable_waste,
                    'economy_rub': suitable_waste['economy_rub']
                })
                
                total_economy += suitable_waste['economy_rub']
                
                self.logger.info(f"✓ Найден обрезок {suitable_waste['waste_id']} "
                               f"для детали '{part['name']}'")
        
        # Формируем результат
        has_matches = len(matches) > 0
        
        message = self._generate_message(matches, total_economy)
        
        return {
            'has_suitable_wastes': has_matches,
            'matches': matches,
            'total_economy_rub': total_economy,
            'parts_from_wastes': len(matches),
            'parts_from_sheets': len(parts) - len(matches),
            'message': message
        }
    
    def _generate_message(self, matches: List[Dict], total_economy: float) -> str:
        """Генерирует сообщение для пользователя"""
        
        if not matches:
            return "❌ Подходящих обрезков не найдено. Резать из новых листов."
        
        message = f"💡 ВНИМАНИЕ! НАЙДЕНЫ ПОДХОДЯЩИЕ ОБРЕЗКИ!\n\n"
        message += f"Можно использовать обрезки для {len(matches)} деталей:\n\n"
        
        for i, match in enumerate(matches, 1):
            part = match['part']
            waste = match['waste']
            
            message += f"{i}. Деталь: {part['name']}\n"
            message += f"   Нужно: {part['width']:.0f}×{part['height']:.0f} мм\n"
            message += f"   → Обрезок {waste['waste_id']}: {waste['width']:.0f}×{waste['height']:.0f} мм\n"
            message += f"   Расположение: {waste['location']}\n"
            message += f"   Экономия: {waste['economy_rub']:.0f} руб\n\n"
        
        message += f"💰 ОБЩАЯ ЭКОНОМИЯ: {total_economy:.0f} руб\n\n"
        message += f"❓ Использовать обрезки?"
        
        return message
    
    def mark_wastes_as_used(self, matches: List[Dict], project_name: str):
        """
        Отмечает обрезки как использованные
        
        Args:
            matches: список совпадений из check_for_project()
            project_name: название проекта, в котором использованы
        """
        
        for match in matches:
            waste_id = match['waste']['waste_id']
            
            self.db_manager.mark_waste_as_used(
                waste_id=waste_id,
                used_in_project=project_name
            )
            
            self.logger.info(f"✓ Обрезок {waste_id} отмечен как использованный в {project_name}")
    
    def get_waste_statistics(self) -> Dict:
        """
        Получает статистику по базе обрезков
        
        Returns:
            {
                'total': int,
                'available': int,
                'used': int,
                'total_area_available': float,
                'total_value_available': float,
                'reuse_percent': float
            }
        """
        
        return self.db_manager.get_statistics() if hasattr(self.db_manager, 'get_statistics') else {}


# Функция для интеграции в существующую программу
def check_wastes_before_nesting(parts_data: List[Dict], material: str = "Оцинковка 1.5мм") -> Dict:
    """
    ГЛАВНАЯ ФУНКЦИЯ: Проверяет обрезки ПЕРЕД раскроем
    
    Используйте эту функцию В НАЧАЛЕ обработки нового проекта
    
    Args:
        parts_data: список деталей [{'name': str, 'width': float, 'height': float}]
        material: тип материала
    
    Returns:
        результат проверки с подходящими обрезками
    
    Example:
        >>> parts = [
        ...     {'name': 'Корпус', 'width': 1500, 'height': 400},
        ...     {'name': 'Крышка', 'width': 250, 'height': 150}
        ... ]
        >>> result = check_wastes_before_nesting(parts)
        >>> if result['has_suitable_wastes']:
        ...     print(result['message'])
        ...     # Показать диалог пользователю
    """
    
    checker = WastePriorityChecker()
    return checker.check_for_project(parts_data, material)


