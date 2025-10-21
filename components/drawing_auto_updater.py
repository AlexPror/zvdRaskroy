#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Автоматическое обновление всех чертежей после копирования проекта
"""

import time
import pythoncom
from pathlib import Path
from typing import Dict
from win32com.client import Dispatch
from .base_component import BaseKompasComponent

class DrawingAutoUpdater(BaseKompasComponent):
    """Автоматическое открытие, пересборка и сохранение всех чертежей"""
    
    def __init__(self):
        super().__init__()
    
    def update_all_drawings(self, project_path: str) -> Dict:
        """
        Автоматическое обновление всех чертежей в проекте
        
        Args:
            project_path: Путь к проекту
            
        Returns:
            Dict с результатами
        """
        result = {
            'success': False,
            'drawings_updated': 0,
            'drawings_failed': 0,
            'updated_files': [],
            'errors': []
        }
        
        pythoncom.CoInitialize()
        
        try:
            self.logger.info("="*60)
            self.logger.info("АВТОМАТИЧЕСКОЕ ОБНОВЛЕНИЕ ЧЕРТЕЖЕЙ")
            self.logger.info("="*60)
            
            if not self.connect_to_kompas():
                result['errors'].append("Не удалось подключиться к КОМПАС-3D")
                return result
            
            project_path_obj = Path(project_path)
            
            # Находим все чертежи (включая развертки)
            all_drawings = list(project_path_obj.glob("*.cdw"))
            
            self.logger.info(f"\nНайдено чертежей: {len(all_drawings)}\n")
            
            api5 = Dispatch("Kompas.Application.5")
            api7 = Dispatch("Kompas.Application.7")
            
            for drawing in all_drawings:
                try:
                    self.logger.info(f"{'='*60}")
                    self.logger.info(f"{drawing.name}")
                    self.logger.info(f"{'='*60}")
                    
                    # Открываем чертеж
                    self.logger.info("  Открытие...")
                    doc = api7.Documents.Open(str(drawing), False, True)
                    time.sleep(1.5)
                    
                    if not doc:
                        self.logger.warning("  ✗ Не удалось открыть")
                        result['drawings_failed'] += 1
                        continue
                    
                    # Получаем 2D документ
                    doc2d = api5.ActiveDocument2D
                    
                    if not doc2d:
                        self.logger.warning("  ✗ Не 2D документ")
                        api7.ActiveDocument.Close(False)
                        result['drawings_failed'] += 1
                        continue
                    
                    # Определяем, это сборочный чертеж или нет
                    is_assembly = "конвектор" in drawing.name.lower() or "сборочный" in drawing.name.lower()
                    
                    # Пересобираем чертеж
                    self.logger.info("  Пересборка...")
                    rebuild_result = doc2d.ksRebuildDocument()
                    
                    # КРИТИЧНО: Для сборочного чертежа - больше времени!
                    if is_assembly:
                        self.logger.info("  (СБОРОЧНЫЙ ЧЕРТЕЖ - увеличенное время обновления)")
                        time.sleep(5)  # Даем 5 секунд на обновление!
                        
                        # ПОВТОРНАЯ ПЕРЕСБОРКА для надежности
                        self.logger.info("  Повторная пересборка...")
                        doc2d.ksRebuildDocument()
                        time.sleep(3)
                    else:
                        time.sleep(2)
                    
                    self.logger.info(f"  Результат пересборки: {rebuild_result}")
                    
                    # Сохраняем
                    self.logger.info("  Сохранение...")
                    api7.ActiveDocument.Save()
                    time.sleep(1 if is_assembly else 0.5)
                    
                    self.logger.info("  ✓ Готово")
                    
                    # Закрываем
                    api7.ActiveDocument.Close(False)
                    time.sleep(0.5)
                    
                    result['drawings_updated'] += 1
                    result['updated_files'].append(drawing.name)
                    self.logger.info("")
                
                except Exception as e:
                    error_msg = f"Ошибка {drawing.name}: {e}"
                    result['errors'].append(error_msg)
                    self.logger.error(f"  ✗ {error_msg}\n")
                    result['drawings_failed'] += 1
                    
                    # Пытаемся закрыть
                    try:
                        api7.ActiveDocument.Close(False)
                    except:
                        pass
            
            result['success'] = True
            
            self.logger.info("="*60)
            self.logger.info("ИТОГО:")
            self.logger.info(f"  Обновлено: {result['drawings_updated']}")
            self.logger.info(f"  Ошибок: {result['drawings_failed']}")
            self.logger.info("="*60)
            
        except Exception as e:
            error_msg = f"Общая ошибка: {e}"
            result['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        finally:
            pythoncom.CoUninitialize()
        
        return result
    
    def _detect_old_project_path(self, new_project_path: Path) -> str:
        """Определение старого пути по имени сборки"""
        try:
            assembly_files = list(new_project_path.glob("*.a3d"))
            
            if assembly_files:
                assembly_name = assembly_files[0].stem
                project_name = new_project_path.name
                
                # Если имена не совпадают - старое имя в сборке
                if assembly_name != project_name:
                    old_path = new_project_path.parent / assembly_name
                    return str(old_path)
            
            return None
        except:
            return None

