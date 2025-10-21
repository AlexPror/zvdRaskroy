#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Компонент для экспорта разверток в DXF
"""

import logging
from pathlib import Path
from typing import Dict, List
import time
from .base_component import BaseKompasComponent

class UnfoldingDxfExporter(BaseKompasComponent):
    """Компонент для экспорта чертежей-разверток в DXF формат"""
    
    def __init__(self):
        super().__init__()
    
    def export_to_dxf(self, drawing_path: str, output_path: str = None) -> Dict:
        """
        Экспорт чертежа в DXF
        
        Args:
            drawing_path: Путь к чертежу
            output_path: Путь для сохранения DXF (если None - в ту же папку)
            
        Returns:
            Dict с результатами
        """
        result = {
            'success': False,
            'output_file': None,
            'error': None
        }
        
        try:
            drawing_file = Path(drawing_path)
            
            if not drawing_file.exists():
                result['error'] = f"Файл не найден: {drawing_path}"
                return result
            
            # Определяем путь вывода
            if output_path:
                output_file = Path(output_path)
            else:
                output_file = drawing_file.with_suffix('.dxf')
            
            self.logger.info(f"Экспорт в DXF: {drawing_file.name}")
            self.logger.info(f"Выходной файл: {output_file.name}")
            
            if not self.connect_to_kompas():
                result['error'] = "Не удалось подключиться к КОМПАС-3D"
                return result
            
            # Открываем чертеж
            if not self.open_document(drawing_path):
                result['error'] = "Не удалось открыть чертеж"
                return result
            
            time.sleep(1)
            
            # Получаем активный документ
            active_doc = self.get_active_document()
            
            if not active_doc:
                result['error'] = "Активный документ не найден"
                return result
            
            # КРИТИЧНО: Обновляем чертеж перед экспортом
            self.logger.info("Обновление чертежа...")
            
            from win32com.client import Dispatch
            api5 = Dispatch("Kompas.Application.5")
            doc2d = api5.ActiveDocument2D
            
            if doc2d:
                try:
                    # Перестраиваем чертеж
                    rebuild_result = doc2d.ksRebuildDocument()
                    self.logger.info(f"ksRebuildDocument: {rebuild_result}")
                    time.sleep(2)
                    
                    # Сохраняем изменения
                    active_doc.Save()
                    self.logger.info("Изменения сохранены")
                    time.sleep(1)
                except Exception as e:
                    self.logger.warning(f"Ошибка обновления: {e}")
            
            self.logger.info("Сохранение в DXF...")
            
            # Получаем Document2D для использования ksSaveToDXF
            from win32com.client import Dispatch
            api5 = Dispatch("Kompas.Application.5")
            doc2d = api5.ActiveDocument2D
            
            if not doc2d:
                result['error'] = "ActiveDocument2D не найден"
                return result
            
            # Сохраняем в DXF через ksSaveToDXF
            try:
                # Удаляем существующий файл
                if output_file.exists():
                    output_file.unlink()
                
                # ksSaveToDXF - правильный метод экспорта
                saved = doc2d.ksSaveToDXF(str(output_file))
                
                self.logger.info(f"ksSaveToDXF result: {saved}")
                time.sleep(2)
                
                # Проверяем результат
                if output_file.exists():
                    file_size = output_file.stat().st_size
                    
                    result['success'] = True
                    result['output_file'] = str(output_file)
                    result['file_size'] = file_size
                    
                    self.logger.info(f"✓ DXF создан: {output_file.name} ({file_size:,} байт)")
                else:
                    result['error'] = "Файл DXF не создался"
                    self.logger.error(result['error'])
                
            except Exception as e:
                result['error'] = f"Ошибка SaveAs: {e}"
                self.logger.error(result['error'])
            
            # Закрываем чертеж
            self.close_document()
            
            return result
            
        except Exception as e:
            result['error'] = f"Общая ошибка: {e}"
            self.logger.error(result['error'])
            return result
        finally:
            self.disconnect_from_kompas()
    
    def export_all_unfoldings(self, project_path: str, output_folder: str = None) -> Dict:
        """
        Экспорт всех разверток в DXF
        
        Args:
            project_path: Путь к проекту
            output_folder: Папка для DXF (если None - в папку проекта)
            
        Returns:
            Dict с результатами
        """
        result = {
            'success': False,
            'exported': 0,
            'total': 0,
            'exported_files': [],
            'errors': []
        }
        
        try:
            project_path_obj = Path(project_path)
            
            # Находим развертки
            all_drawings = list(project_path_obj.glob("*.cdw"))
            unfoldings = [d for d in all_drawings if "развертка" in d.name.lower()]
            
            result['total'] = len(unfoldings)
            
            self.logger.info(f"Найдено разверток: {len(unfoldings)}")
            
            # Определяем папку вывода
            if output_folder:
                output_path = Path(output_folder)
                output_path.mkdir(parents=True, exist_ok=True)
            else:
                output_path = project_path_obj
            
            # Экспортируем каждую
            for unfolding in unfoldings:
                output_file = output_path / unfolding.with_suffix('.dxf').name
                
                export_result = self.export_to_dxf(str(unfolding), str(output_file))
                
                if export_result['success']:
                    result['exported'] += 1
                    result['exported_files'].append({
                        'source': str(unfolding),
                        'output': export_result['output_file'],
                        'size': export_result['file_size']
                    })
                else:
                    result['errors'].append(f"{unfolding.name}: {export_result['error']}")
            
            result['success'] = result['exported'] > 0
            
            self.logger.info(f"\n✓ Экспортировано: {result['exported']}/{result['total']}")
            
            return result
            
        except Exception as e:
            result['error'] = f"Общая ошибка: {e}"
            self.logger.error(result['error'])
            return result

