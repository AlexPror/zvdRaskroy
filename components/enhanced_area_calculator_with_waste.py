#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Улучшенный компонент расчета площадей с визуализацией раскроя и учетом обрезков
"""

import logging
from typing import Dict, List
from pathlib import Path
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

from .advanced_area_calculator import AdvancedAreaCalculator
from .rectpack_optimizer import RectpackOptimizer
from .nesting_visualizer import NestingVisualizer


class EnhancedAreaCalculatorWithWaste(AdvancedAreaCalculator):
    """
    Расширенный калькулятор площадей с:
    - Оптимизацией раскроя (rectpack)
    - Визуализацией раскладки
    - Учетом обрезков с номерами
    - Экспортом обрезков в Excel
    """
    
    def __init__(self, use_array_manager: bool = True):
        super().__init__(use_array_manager)
        self.optimizer = RectpackOptimizer()
        self.visualizer = NestingVisualizer()
        self.waste_counter = 0  # Счетчик обрезков
        
    def calculate_with_nesting(self, project_path: str, order_number: str = None) -> Dict:
        """
        Расчет площадей с оптимальной раскладкой и учетом обрезков
        
        Returns:
            {
                'success': bool,
                'areas': {...},  # Обычные данные площадей
                'nesting': {...},  # Данные раскроя от rectpack
                'waste_pieces': [...],  # Обрезки с номерами
                'visualization_pdf': str,  # Путь к PDF с визуализацией
                'waste_excel': str  # Путь к Excel с обрезками
            }
        """
        
        # Сначала получаем обычные данные площадей
        areas_result = self.calculate_total_areas(project_path, order_number)
        
        if not areas_result['success']:
            return areas_result
        
        # Подготавливаем данные для раскроя
        parts_data = []
        for unf in areas_result.get('unfoldings', []):
            if unf.get('dimensions'):
                parts_data.append({
                    'name': unf['name'],
                    'width_mm': unf['dimensions']['width'],
                    'height_mm': unf['dimensions']['height'],
                    'area_m2': unf['area_m2'],
                    'quantity': unf.get('quantity', 1)
                })
        
        # Оптимизация раскроя
        nesting_result = {}
        if self.optimizer.is_available() and parts_data:
            self.logger.info("Запуск оптимизации раскроя...")
            nesting_result = self.optimizer.optimize_layout(
                parts_data,
                allow_rotation=True,
                algorithm='BFF'
            )
        else:
            self.logger.warning("Rectpack недоступен, раскрой не выполнен")
            nesting_result = {'success': False, 'error': 'rectpack not available'}
        
        # Генерируем обрезки с номерами
        waste_pieces = []
        if nesting_result.get('success'):
            waste_pieces = self._generate_waste_pieces(nesting_result, order_number)
        
        # Создаем визуализацию
        project_name = Path(project_path).stem
        vis_pdf = None
        waste_excel = None
        
        if nesting_result.get('success'):
            # PDF с визуализацией раскладки
            vis_pdf = self._create_visualization_pdf(
                nesting_result, 
                waste_pieces,
                project_name,
                order_number
            )
            
            # Excel с обрезками
            waste_excel = self._create_waste_excel(
                waste_pieces,
                project_name,
                order_number
            )
        
        # Объединяем результаты
        result = {
            'success': True,
            'areas': areas_result,
            'nesting': nesting_result,
            'waste_pieces': waste_pieces,
            'visualization_pdf': vis_pdf,
            'waste_excel': waste_excel
        }
        
        return result
    
    def _generate_waste_pieces(self, nesting_result: Dict, order_number: str = None) -> List[Dict]:
        """
        Генерация обрезков с уникальными номерами
        
        Returns:
            [
                {
                    'id': 'W-001',
                    'sheet_number': 1,
                    'width_mm': float,
                    'height_mm': float,
                    'area_m2': float,
                    'x': float,  # Координаты на листе
                    'y': float,
                    'usable': bool,  # Можно ли использовать (>500x500)
                    'order': str,
                    'date': str
                }
            ]
        """
        waste_pieces = []
        self.waste_counter = 0
        
        current_date = datetime.now().strftime("%d.%m.%Y")
        
        for sheet in nesting_result.get('sheets', []):
            sheet_num = sheet['number']
            
            # Рассчитываем свободные зоны на листе
            # Упрощенный подход: считаем один большой обрезок с площадью отходов
            waste_area_m2 = sheet['waste_area_m2']
            
            if waste_area_m2 > 0.01:  # Только если есть значимые обрезки
                self.waste_counter += 1
                
                # Примерные размеры обрезка (можно улучшить)
                # Для простоты берем квадратный корень площади
                approx_size_m = (waste_area_m2 ** 0.5)
                approx_size_mm = approx_size_m * 1000
                
                waste_id = f"W-{self.waste_counter:03d}"
                
                # Проверяем, можно ли использовать (больше 500x500 мм)
                usable = approx_size_mm >= 500
                
                waste_piece = {
                    'id': waste_id,
                    'sheet_number': sheet_num,
                    'width_mm': approx_size_mm,
                    'height_mm': approx_size_mm,
                    'area_m2': waste_area_m2,
                    'x': 0,  # Координаты можно уточнить
                    'y': 0,
                    'usable': usable,
                    'order': order_number or 'N/A',
                    'date': current_date,
                    'status': 'В наличии'
                }
                
                waste_pieces.append(waste_piece)
        
        return waste_pieces
    
    def _create_visualization_pdf(self, 
                                  nesting_result: Dict, 
                                  waste_pieces: List[Dict],
                                  project_name: str,
                                  order_number: str = None,
                                  cipher: str = None) -> str:
        """
        Создание PDF с визуализацией раскладки
        """
        return self.visualizer.create_pdf_visualization(
            nesting_result,
            waste_pieces,
            project_name,
            order_number,
            cipher=cipher
        )
    
    def _create_waste_excel(self, 
                           waste_pieces: List[Dict],
                           project_name: str,
                           order_number: str = None) -> str:
        """
        Создание Excel файла с базой обрезков
        """
        
        output_file = f"Обрезки_{project_name}_{order_number or 'проект'}.xlsx"
        
        # Проверяем, существует ли уже файл базы обрезков
        base_file = "База_обрезков.xlsx"
        
        try:
            if Path(base_file).exists():
                wb = openpyxl.load_workbook(base_file)
                ws = wb.active
            else:
                # Создаем новый файл
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Обрезки"
                
                # Заголовки
                headers = ['№', 'Проект', 'Заказ', 'Дата', 'Лист', 'Ширина (мм)', 
                          'Высота (мм)', 'Площадь (м²)', 'Использ.', 'Статус', 'Примечание']
                
                for col, header in enumerate(headers, 1):
                    cell = ws.cell(row=1, column=col, value=header)
                    cell.font = Font(bold=True, size=11)
                    cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
                    cell.font = Font(bold=True, color="FFFFFF")
                    cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Добавляем новые обрезки
            next_row = ws.max_row + 1
            
            for waste in waste_pieces:
                ws.cell(row=next_row, column=1, value=waste['id'])
                ws.cell(row=next_row, column=2, value=project_name)
                ws.cell(row=next_row, column=3, value=waste['order'])
                ws.cell(row=next_row, column=4, value=waste['date'])
                ws.cell(row=next_row, column=5, value=waste['sheet_number'])
                ws.cell(row=next_row, column=6, value=round(waste['width_mm'], 1))
                ws.cell(row=next_row, column=7, value=round(waste['height_mm'], 1))
                ws.cell(row=next_row, column=8, value=round(waste['area_m2'], 4))
                ws.cell(row=next_row, column=9, value='Да' if waste['usable'] else 'Нет')
                ws.cell(row=next_row, column=10, value=waste['status'])
                ws.cell(row=next_row, column=11, value='')
                
                next_row += 1
            
            # Автоширина столбцов
            for col in ws.columns:
                max_length = 0
                column = col[0].column_letter
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column].width = adjusted_width
            
            # Сохраняем
            wb.save(base_file)
            wb.save(output_file)  # Также сохраняем копию для проекта
            
            self.logger.info(f"Excel с обрезками создан: {output_file}")
            self.logger.info(f"База обрезков обновлена: {base_file}")
            
            return output_file
            
        except Exception as e:
            self.logger.error(f"Ошибка создания Excel: {e}")
            return None


if __name__ == "__main__":
    # Тест модуля
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    print("="*80)
    print("ТЕСТ УЛУЧШЕННОГО КАЛЬКУЛЯТОРА С ОБРЕЗКАМИ")
    print("="*80)
    print("\nМодуль готов к использованию!")
    print("\nВ программе используйте:")
    print("  calculator = EnhancedAreaCalculatorWithWaste()")
    print("  result = calculator.calculate_with_nesting(project_path, order_number)")
    print("\nРезультат содержит:")
    print("  - areas: площади деталей")
    print("  - nesting: оптимальная раскладка")
    print("  - waste_pieces: обрезки с номерами")
    print("  - visualization_pdf: PDF с раскладкой")
    print("  - waste_excel: Excel с обрезками")

