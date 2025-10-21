"""
Компонент для расчета площади разверток из DXF файлов

Использует библиотеку ezdxf для чтения DXF и расчета площади
"""

import logging
from pathlib import Path
from typing import Dict, List
import math


class UnfoldingAreaCalculator:
    """Расчет площади разверток из DXF"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_dxf_area(self, dxf_path: str) -> Dict:
        """
        Расчет площади одной развертки из DXF
        
        Args:
            dxf_path: Путь к DXF файлу
        
        Returns:
            dict: {'success': bool, 'area_m2': float, 'area_mm2': float, 'error': str}
        """
        result = {
            'success': False,
            'area_m2': 0.0,
            'area_mm2': 0.0,
            'width_mm': 0.0,
            'height_mm': 0.0,
            'error': None
        }
        
        try:
            import ezdxf
            
            # Читаем DXF
            doc = ezdxf.readfile(dxf_path)
            msp = doc.modelspace()
            
            # Собираем все полилинии и линии
            total_area_mm2 = 0.0
            min_x, min_y = float('inf'), float('inf')
            max_x, max_y = float('-inf'), float('-inf')
            
            # Ищем замкнутые полилинии (контуры развертки)
            for entity in msp:
                if entity.dxftype() == 'LWPOLYLINE':
                    if entity.closed:
                        # Вычисляем площадь полилинии методом Гаусса
                        points = list(entity.get_points('xy'))
                        area = self._calculate_polygon_area(points)
                        total_area_mm2 += abs(area)
                        
                        # Обновляем габариты
                        for x, y in points:
                            min_x, max_x = min(min_x, x), max(max_x, x)
                            min_y, max_y = min(min_y, y), max(max_y, y)
                
                elif entity.dxftype() == 'POLYLINE':
                    if hasattr(entity, 'is_closed') and entity.is_closed:
                        points = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
                        area = self._calculate_polygon_area(points)
                        total_area_mm2 += abs(area)
                        
                        for x, y in points:
                            min_x, max_x = min(min_x, x), max(max_x, x)
                            min_y, max_y = min(min_y, y), max(max_y, y)
            
            # КРИТИЧНО: Если нет полилиний, собираем площадь из LINE объектов!
            # КОМПАС экспортирует контур как отдельные линии!
            if total_area_mm2 == 0:
                # Собираем все линии
                lines = [e for e in msp if e.dxftype() == 'LINE']
                
                if lines:
                    # Собираем габариты из всех линий
                    for line in lines:
                        start = line.dxf.start
                        end = line.dxf.end
                        
                        min_x = min(min_x, start.x, end.x)
                        max_x = max(max_x, start.x, end.x)
                        min_y = min(min_y, start.y, end.y)
                        max_y = max(max_y, start.y, end.y)
                    
                    # Грубая оценка площади через габариты
                    width = max_x - min_x
                    height = max_y - min_y
                    total_area_mm2 = width * height
                    
                    self.logger.info(f"  ℹ DXF содержит только LINE ({len(lines)} шт)")
                    self.logger.info(f"  ℹ Площадь рассчитана по габаритам (грубо!)")
            
            # Габариты
            result['width_mm'] = max_x - min_x if max_x != float('-inf') else 0.0
            result['height_mm'] = max_y - min_y if max_y != float('-inf') else 0.0
            
            # Площадь
            result['area_mm2'] = total_area_mm2
            result['area_m2'] = total_area_mm2 / 1_000_000  # мм² → м²
            result['success'] = True
            
            self.logger.info(f"  ✓ Площадь: {result['area_m2']:.6f} м² ({result['area_mm2']:.0f} мм²)")
            self.logger.info(f"  ✓ Габариты: {result['width_mm']:.1f} x {result['height_mm']:.1f} мм")
            
        except ImportError:
            result['error'] = "Библиотека ezdxf не установлена! Установите: pip install ezdxf"
            self.logger.error(result['error'])
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Ошибка расчета площади DXF: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
        
        return result
    
    def _calculate_polygon_area(self, points: List[tuple]) -> float:
        """
        Расчет площади полигона методом Гаусса (Shoelace formula)
        
        Args:
            points: Список точек [(x1, y1), (x2, y2), ...]
        
        Returns:
            float: Площадь в мм²
        """
        if len(points) < 3:
            return 0.0
        
        area = 0.0
        n = len(points)
        
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]
        
        return abs(area) / 2.0
    
    def calculate_all_unfoldings(self, project_path: str) -> Dict:
        """
        Расчет площадей всех разверток в проекте
        
        Args:
            project_path: Путь к папке проекта
        
        Returns:
            dict: {
                'success': bool,
                'total_area_m2': float,
                'parts': [{'name': str, 'area_m2': float, 'quantity': int}, ...],
                'errors': list
            }
        """
        result = {
            'success': False,
            'total_area_m2': 0.0,
            'total_area_with_quantity': 0.0,
            'parts': [],
            'errors': []
        }
        
        project_path = Path(project_path)
        dxf_folder = project_path / "DXF"
        
        if not dxf_folder.exists():
            result['error'] = f"Папка DXF не найдена: {dxf_folder}"
            self.logger.error(result['error'])
            return result
        
        # Находим все DXF файлы
        dxf_files = list(dxf_folder.glob("*.dxf"))
        
        if not dxf_files:
            result['error'] = "DXF файлы не найдены"
            self.logger.warning(result['error'])
            return result
        
        self.logger.info(f"\nНайдено DXF файлов: {len(dxf_files)}")
        
        for dxf_file in dxf_files:
            try:
                self.logger.info(f"\n  Файл: {dxf_file.name}")
                
                # Расчет площади
                area_result = self.calculate_dxf_area(str(dxf_file))
                
                if area_result['success']:
                    # Определяем количество из имени DXF файла
                    # Формат: "006 - Стенка торцевая 2шт (А-180925).dxf"
                    quantity = 1  # По умолчанию
                    
                    # Ищем "Xшт" в имени
                    import re
                    qty_match = re.search(r'(\d+)шт', dxf_file.stem)
                    if qty_match:
                        quantity = int(qty_match.group(1))
                        self.logger.info(f"  Количество из имени: {quantity} шт")
                    
                    part_info = {
                        'name': dxf_file.stem,
                        'area_m2': area_result['area_m2'],
                        'area_mm2': area_result['area_mm2'],
                        'width_mm': area_result['width_mm'],
                        'height_mm': area_result['height_mm'],
                        'quantity': quantity,
                        'total_area_m2': area_result['area_m2'] * quantity
                    }
                    
                    result['parts'].append(part_info)
                    result['total_area_m2'] += area_result['area_m2']
                    result['total_area_with_quantity'] += part_info['total_area_m2']
                else:
                    result['errors'].append(f"{dxf_file.name}: {area_result['error']}")
            
            except Exception as e:
                self.logger.error(f"Ошибка обработки {dxf_file.name}: {e}")
                result['errors'].append(f"{dxf_file.name}: {str(e)}")
        
        result['success'] = len(result['parts']) > 0
        
        self.logger.info(f"\n{'='*70}")
        self.logger.info(f"ИТОГО:")
        self.logger.info(f"  Деталей: {len(result['parts'])}")
        self.logger.info(f"  Общая площадь (без учета количества): {result['total_area_m2']:.6f} м²")
        self.logger.info(f"  Общая площадь (с учетом количества): {result['total_area_with_quantity']:.6f} м²")
        self.logger.info(f"{'='*70}")
        
        return result


if __name__ == "__main__":
    # Тестирование
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    
    calculator = UnfoldingAreaCalculator()
    
    # Тест
    test_project = r"C:\Users\Vorob\Documents\ZVD GROUP\Параметризация\ZVD.LITE.90.260.1000"
    result = calculator.calculate_all_unfoldings(test_project)
    
    print(f"\n\nРезультат: {result}")

