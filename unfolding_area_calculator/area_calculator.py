#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Универсальная утилита расчета площадей разверток
Для цеха - принимает файлы DXF от разных конструкторов
"""

import sys
import re
from pathlib import Path
from typing import List, Dict, Tuple

# Поддержка DXF
try:
    import ezdxf
    HAS_EZDXF = True
except ImportError:
    HAS_EZDXF = False

# Поддержка КОМПАС
try:
    import pythoncom
    from win32com.client import Dispatch
    HAS_KOMPAS = True
except ImportError:
    HAS_KOMPAS = False


class UnfoldingAreaCalculator:
    """Калькулятор площадей разверток"""
    
    # Зазоры для резки
    CUT_GAP = 5  # мм между деталями
    EDGE_MARGIN = 10  # мм от краев
    
    def __init__(self):
        self.results = []
    
    def extract_quantity_from_filename(self, filename: str) -> int:
        """
        Извлечь количество деталей из имени файла
        
        Примеры:
        - "004 - Корпус короба прямой 2шт (А-021025-1225).dxf" → 2
        - "005 - Распорка бассейна 4шт (А-021025-1225).dxf" → 4
        - "008 - Соединительная пластина 1шт.dxf" → 1
        - "005-02-Распорка бассейна верхняя 4 шт.dxf" → 4
        - "Крышка.dxf" → 1 (по умолчанию)
        
        Args:
            filename: Имя файла
            
        Returns:
            Количество деталей (по умолчанию 1)
        """
        # Паттерны для поиска количества:
        # "2шт", "4шт", "1шт" или "2 шт", "4 шт" и т.д.
        patterns = [
            r'(\d+)\s*шт',  # "2шт" или "2 шт"
            r'(\d+)\s*ШТ',  # "2ШТ" (верхний регистр)
            r'(\d+)\s*pcs', # "2pcs" (английский вариант)
            r'x(\d+)',      # "x2", "x4" (альтернативный формат)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                try:
                    quantity = int(match.group(1))
                    # Проверка на адекватность (не больше 999)
                    if 1 <= quantity <= 999:
                        return quantity
                except ValueError:
                    pass
        
        # По умолчанию 1 штука
        return 1
    
    def get_dimensions_from_dxf(self, dxf_path: str) -> Tuple[float, float]:
        """
        Получить габариты из DXF файла
        
        Returns:
            (width, height) в мм
        """
        if not HAS_EZDXF:
            raise ImportError("Библиотека ezdxf не установлена! pip install ezdxf")
        
        try:
            doc = ezdxf.readfile(dxf_path)
            msp = doc.modelspace()
            
            # Находим габариты
            min_x = min_y = float('inf')
            max_x = max_y = float('-inf')
            
            for entity in msp:
                try:
                    if hasattr(entity, 'dxf'):
                        # Линия
                        if hasattr(entity.dxf, 'start') and hasattr(entity.dxf, 'end'):
                            min_x = min(min_x, entity.dxf.start.x, entity.dxf.end.x)
                            max_x = max(max_x, entity.dxf.start.x, entity.dxf.end.x)
                            min_y = min(min_y, entity.dxf.start.y, entity.dxf.end.y)
                            max_y = max(max_y, entity.dxf.start.y, entity.dxf.end.y)
                        # Окружность/дуга
                        elif hasattr(entity.dxf, 'center'):
                            center = entity.dxf.center
                            radius = getattr(entity.dxf, 'radius', 0)
                            min_x = min(min_x, center.x - radius)
                            max_x = max(max_x, center.x + radius)
                            min_y = min(min_y, center.y - radius)
                            max_y = max(max_y, center.y + radius)
                except:
                    pass
            
            if min_x != float('inf'):
                width = abs(max_x - min_x)
                height = abs(max_y - min_y)
                return (width, height)
            
            return (None, None)
            
        except Exception as e:
            print(f"Ошибка чтения DXF {Path(dxf_path).name}: {e}")
            return (None, None)
    
    def get_dimensions_from_cdw(self, cdw_path: str) -> Tuple[float, float]:
        """
        Получить габариты из чертежа КОМПАС
        
        Returns:
            (width, height) в мм
        """
        if not HAS_KOMPAS:
            raise ImportError("КОМПАС API не доступен")
        
        pythoncom.CoInitialize()
        
        try:
            api5 = Dispatch("Kompas.Application.5")
            api7 = Dispatch("Kompas.Application.7")
            
            # Открываем чертеж
            doc = api7.Documents.Open(str(cdw_path), False, True)
            
            import time
            time.sleep(1)
            
            doc2d = api5.ActiveDocument2D
            
            if not doc2d:
                api7.ActiveDocument.Close(False)
                pythoncom.CoUninitialize()
                return (None, None)
            
            # Экспортируем во временный DXF
            import tempfile
            temp_dxf = tempfile.mktemp(suffix='.dxf')
            
            doc2d.ksSaveToDXF(temp_dxf)
            time.sleep(1)
            
            # Читаем габариты из DXF
            width, height = self.get_dimensions_from_dxf(temp_dxf)
            
            # Удаляем временный
            Path(temp_dxf).unlink(missing_ok=True)
            
            # Закрываем
            api7.ActiveDocument.Close(False)
            pythoncom.CoUninitialize()
            
            return (width, height)
            
        except Exception as e:
            print(f"Ошибка чтения CDW {Path(cdw_path).name}: {e}")
            try:
                pythoncom.CoUninitialize()
            except:
                pass
            return (None, None)
    
    def extract_quantity_from_filename(self, filename: str) -> int:
        """
        Извлечь количество из имени файла
        
        Примеры:
            "Корпус 2шт.dxf" -> 2
            "Стенка 1 шт.dxf" -> 1
            "Распорка.dxf" -> 1 (по умолчанию)
        
        Args:
            filename: Имя файла
            
        Returns:
            Количество деталей
        """
        import re
        
        # Ищем паттерны: "2шт", "2 шт", "2шт."
        patterns = [
            r'(\d+)\s*шт',  # "2шт" или "2 шт"
            r'(\d+)\s*ШТ',  # "2ШТ" или "2 ШТ" (верхний регистр)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                qty = int(match.group(1))
                if 1 <= qty <= 999:  # Разумные пределы
                    return qty
        
        # Если не найдено - по умолчанию 1
        return 1
    
    def calculate_file(self, file_path: str, quantity: int = None) -> Dict:
        """
        Рассчитать площадь одного файла
        
        Args:
            file_path: Путь к файлу развертки (.dxf)
            quantity: Количество деталей (если None - извлекается из имени файла)
            
        Returns:
            dict с результатами
        """
        file_path = Path(file_path)
        ext = file_path.suffix.lower()
        
        # НОВОЕ: Автоматическое извлечение количества из имени файла
        if quantity is None:
            quantity = self.extract_quantity_from_filename(file_path.name)
        
        # Только DXF формат (универсальный для всех CAD)
        if ext == '.dxf':
            width, height = self.get_dimensions_from_dxf(str(file_path))
        else:
            return {
                'success': False,
                'error': f'Неподдерживаемый формат: {ext}. Используйте DXF'
            }
        
        if not width or not height:
            return {
                'success': False,
                'error': 'Не удалось определить габариты'
            }
        
        # Расчет площадей
        area_mm2 = width * height
        area_m2 = area_mm2 / 1_000_000
        
        # С зазорами
        width_gap = width + self.CUT_GAP
        height_gap = height + self.CUT_GAP
        area_gap_mm2 = width_gap * height_gap
        area_gap_m2 = area_gap_mm2 / 1_000_000
        
        # Итого
        total_area = area_m2 * quantity
        total_area_gap = area_gap_m2 * quantity
        
        return {
            'success': True,
            'filename': file_path.name,
            'filepath': str(file_path.absolute()),  # ПОЛНЫЙ путь к DXF для рендеринга
            'width': width,
            'height': height,
            'area_mm2': area_mm2,
            'area_m2': area_m2,
            'area_with_gap': area_gap_m2,  # GUI ожидает 'area_with_gap'
            'quantity': quantity,
            'total_area': total_area,  # GUI ожидает 'total_area'
            'total_area_gap_m2': total_area_gap
        }
    
    def calculate_from_folder(self, folder_path: str) -> Dict:
        """
        Рассчитать все файлы в папке (для GUI)
        
        Args:
            folder_path: Путь к папке с развертками
            
        Returns:
            dict с результатами всех файлов
        """
        return self.calculate_folder(folder_path)
    
    def calculate_folder(self, folder_path: str, quantities: Dict[str, int] = None) -> Dict:
        """
        Рассчитать все файлы в папке
        
        Args:
            folder_path: Путь к папке с развертками
            quantities: Словарь {имя_файла: количество}
            
        Returns:
            dict с результатами всех файлов
        """
        folder = Path(folder_path)
        
        if not folder.exists():
            return {'success': False, 'error': 'Папка не найдена'}
        
        # Ищем файлы
        dxf_files = list(folder.glob('*.dxf'))
        cdw_files = list(folder.glob('*.cdw'))
        
        all_files = dxf_files + cdw_files
        
        if not all_files:
            return {'success': False, 'error': 'Файлы разверток не найдены'}
        
        results = []
        errors = []
        
        for file in all_files:
            # Определяем количество
            # 1. Пытаемся извлечь из имени файла
            qty = self.extract_quantity_from_filename(file.name)
            
            # 2. Если передан словарь quantities - он имеет приоритет
            if quantities and file.name in quantities:
                qty = quantities[file.name]
            
            result = self.calculate_file(str(file), qty)
            
            if result['success']:
                results.append(result)
            else:
                errors.append(f"{file.name}: {result.get('error', 'Ошибка')}")
        
        # Суммируем
        total_area = sum(r['total_area'] for r in results)
        total_area_gap = sum(r['total_area_gap_m2'] for r in results)
        
        return {
            'success': True,
            'files_count': len(results),
            'files': results,  # GUI ожидает 'files', а не 'results'
            'errors': errors,
            'total_area_m2': total_area,
            'total_area_gap_m2': total_area_gap
        }


if __name__ == "__main__":
    # Простой тест
    print("="*70)
    print("ТЕСТ КАЛЬКУЛЯТОРА ПЛОЩАДЕЙ")
    print("="*70)
    
    calc = UnfoldingAreaCalculator()
    
    # Тестовая папка
    test_folder = r"C:\Users\Vorob\Documents\ZVD GROUP\Параметризация\ZVD.LITE.154.160.1400\DXF"
    
    if Path(test_folder).exists():
        print(f"\nПапка: {test_folder}\n")
        
        # Указываем количества
        quantities = {
            "001 - Корпус короба прямой 1шт (1112 - 555).dxf": 1,
            "002 - Стенка торцевая 2шт (1112 - 555).dxf": 2,
            "003 - Стенка 2шт (1112 - 555).dxf": 2,
            "004 - Крышка декоративная 2шт (1112 - 555).dxf": 2,
            "005 - Распорка басеейна 1шт (1112 - 555).dxf": 2,
        }
        
        result = calc.calculate_folder(test_folder, quantities)
        
        if result['success']:
            print(f"Найдено файлов: {result['files_count']}")
            print(f"\nИТОГО:")
            print(f"  Площадь деталей: {result['total_area_m2']:.4f} м²")
            print(f"  С зазорами: {result['total_area_gap_m2']:.4f} м²")
        else:
            print(f"Ошибка: {result['error']}")
    else:
        print("Тестовая папка не найдена")
        print("\nИспользование:")
        print("  calc = UnfoldingAreaCalculator()")
        print("  result = calc.calculate_file('file.dxf', quantity=2)")

