#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Извлечение габаритов проекта из структуры папок
Автоматически находит корень проекта и определяет параметры
"""

from pathlib import Path
import re
from typing import Dict, Optional, List

class ProjectDimensionExtractor:
    """Извлекатель габаритов из структуры проекта"""
    
    def __init__(self):
        pass
    
    def find_project_root(self, dxf_folder: Path) -> Optional[Path]:
        """
        Найти корень проекта (папку с названием типа ZVD.LITE.110.360.1200)
        
        Структура проекта обычно:
        ZVD.LITE.110.360.1200/
            ├── DXF/  ← мы здесь
            ├── Чертежи/
            └── Сборка/
        
        Или:
        Заказы/
            ├── ZVD.LITE.110.360.1200/
            │   └── ЛАЗЕРНАЯ РЕЗКА/
            │       └── DXF/  ← или здесь
        """
        
        current = dxf_folder
        found_folders = []  # Список всех проверенных папок
        
        # Поднимаемся вверх по структуре, ищем папку с паттерном
        for i in range(10):  # Увеличено до 10 уровней вверх
            found_folders.append(current)
            
            if self._is_project_folder(current):
                return current
            
            # Поднимаемся на уровень выше
            parent = current.parent
            if parent == current:  # Достигли корня диска
                break
            current = parent
        
        # Если не нашли среди родительских, ищем среди соседних папок
        # (может быть структура где DXF в одной папке, а название проекта в соседней)
        for folder in found_folders:
            parent = folder.parent
            if parent.exists():
                for sibling in parent.iterdir():
                    if sibling.is_dir() and self._is_project_folder(sibling):
                        return sibling
        
        # Если не нашли, возвращаем исходную папку
        return dxf_folder
    
    def _is_project_folder(self, folder: Path) -> bool:
        """Проверить, является ли папка корнем проекта"""
        name = folder.name
        
        # Паттерны названий проектов:
        # ZVD.LITE.110.360.1200 (классический формат)
        # ZVD.LITE 150.200.3000 (с пробелами вместо точек между числами)
        # ZVD LITE 150 200 3000 (все через пробелы)
        # LITE.110.360.1200
        
        patterns = [
            # Классические форматы (все через точки)
            r'ZVD\.(LITE|TURBO)\.\d+\.\d+\.\d+',
            r'(LITE|TURBO)\.\d+\.\d+\.\d+',
            r'ZVD\.\d+\.\d+\.\d+',
            
            # Форматы с пробелами между числами
            r'ZVD\.(LITE|TURBO)\s+\d+[\.\s]\d+[\.\s]\d+',
            r'(LITE|TURBO)\s+\d+[\.\s]\d+[\.\s]\d+',
            
            # Все через пробелы
            r'ZVD\s+(LITE|TURBO)\s+\d+\s+\d+\s+\d+',
            r'ZVD\s+\d+\s+\d+\s+\d+',
        ]
        
        for pattern in patterns:
            if re.match(pattern, name, re.IGNORECASE):
                return True
        
        return False
    
    def extract_dimensions(self, folder: Path) -> Optional[Dict]:
        """
        Извлечь габариты H, W, L из названия папки
        
        Args:
            folder: Путь к папке проекта
        
        Returns:
            {'H': int, 'W': int, 'L': int} или None
        """
        
        name = folder.name
        
        # Паттерны для извлечения чисел
        # ZVD.LITE.110.360.1200 → [110, 360, 1200]
        # ZVD.LITE 150.200.3000 → [150, 200, 3000]
        # ZVD LITE 150 200 3000 → [150, 200, 3000]
        # LITE.154.160.1400 → [154, 160, 1400]
        
        # Разбиваем по точкам и пробелам
        parts = re.split(r'[\.\s]+', name)
        
        numbers = []
        for part in parts:
            # Извлекаем все цифры из части
            digits = ''.join(filter(str.isdigit, part))
            if digits:
                try:
                    num = int(digits)
                    # Фильтруем разумные значения
                    if 50 <= num <= 10000:  # Разумный диапазон для габаритов
                        numbers.append(num)
                except:
                    pass
        
        # Нужно минимум 3 числа: H, W, L
        if len(numbers) >= 3:
            # Для формата ZVD.LITE.H.W.L числа идут по порядку
            # Просто берём первые 3 числа в том порядке, как они идут
            H = numbers[0]
            W = numbers[1]
            L = numbers[2]
            
            # Проверяем, что числа в разумных диапазонах
            if (50 <= H <= 250 and 150 <= W <= 500 and 500 <= L <= 5000):
                return {'H': H, 'W': W, 'L': L}
            
            # Если не подходят, пробуем другую комбинацию
            # Возможно, порядок другой или есть лишние числа
            for i in range(len(numbers) - 2):
                h, w, l = numbers[i], numbers[i+1], numbers[i+2]
                if (50 <= h <= 250 and 150 <= w <= 500 and 500 <= l <= 5000):
                    return {'H': h, 'W': w, 'L': l}
            
            # Fallback: берём первые 3 числа как есть
            return {'H': numbers[0], 'W': numbers[1], 'L': numbers[2]}
        
        return None
    
    def extract_order_info(self, folder: Path) -> Dict:
        """
        Извлечь информацию о заказе из названия папки
        
        Примеры:
        - "ZVD.LITE 150.200.3000  А-021025-1225" → 
          {cipher: "ZVD.LITE.150.200.3000", order: "А-021025-1225"}
        - "ZVD.LITE.110.360.1200" → 
          {cipher: "ZVD.LITE.110.360.1200", order: None}
        
        Returns:
            {'cipher': str, 'order': str или None}
        """
        name = folder.name
        
        # Паттерн для извлечения номера заказа (обычно в формате А-XXXXXX-XXXX)
        order_pattern = r'([АA]-\d{6}-\d{4})'
        order_match = re.search(order_pattern, name, re.IGNORECASE)
        order_number = order_match.group(1) if order_match else None
        
        # Извлекаем шифр конвектора (всё до номера заказа или всё название)
        if order_number:
            # Убираем номер заказа и лишние пробелы
            cipher = name.replace(order_number, '').strip()
        else:
            cipher = name
        
        # Дополнительная очистка шифра от лишних символов
        cipher = re.sub(r'\s+', ' ', cipher)  # Убираем множественные пробелы
        cipher = cipher.strip()
        
        return {
            'cipher': cipher,
            'order': order_number
        }
    
    def count_conveyors_in_project(self, project_root: Path) -> int:
        """
        Подсчитать количество конвекторов в проекте
        
        Логика:
        - Если есть подпапки с разными названиями → несколько конвекторов
        - Если DXF файлы в одной папке → 1 конвектор
        
        Returns:
            Количество конвекторов (по умолчанию 1)
        """
        
        # Ищем папки с названиями типа "Конвектор 1", "Киевская площадь 1" и т.д.
        subfolders = []
        
        for item in project_root.rglob('*'):
            if item.is_dir():
                # Ищем уникальные названия в скобках (Название объекта 1)
                matches = re.findall(r'\(([^)]+)\)', item.name)
                for match in matches:
                    if match not in subfolders:
                        subfolders.append(match)
        
        # Если нашли несколько объектов → возвращаем их количество
        if subfolders:
            return len(subfolders)
        
        # По умолчанию - 1 конвектор
        return 1
    
    def analyze_project_structure(self, dxf_folder_path: str) -> Dict:
        """
        Полный анализ структуры проекта
        
        Args:
            dxf_folder_path: Путь к папке с DXF файлами
        
        Returns:
            Информация о проекте: габариты, количество конвекторов, корень, шифр, заказ
        """
        
        dxf_folder = Path(dxf_folder_path)
        
        # Находим корень проекта
        project_root = self.find_project_root(dxf_folder)
        
        # Извлекаем габариты
        dimensions = self.extract_dimensions(project_root)
        
        # Считаем конвекторы
        conveyors_count = self.count_conveyors_in_project(project_root)
        
        # Извлекаем информацию о заказе
        order_info = self.extract_order_info(project_root)
        
        return {
            'dxf_folder': dxf_folder,
            'project_root': project_root,
            'project_name': project_root.name,
            'dimensions': dimensions,
            'conveyors_count': conveyors_count,
            'cipher': order_info['cipher'],
            'order_number': order_info['order'],
            'is_valid': dimensions is not None
        }

# Глобальный экземпляр
extractor = ProjectDimensionExtractor()




