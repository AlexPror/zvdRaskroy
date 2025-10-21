#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Каскадное обновление переменных: сборка → детали
"""

import time
import pythoncom
from pathlib import Path
from typing import Dict
from win32com.client import Dispatch, gencache
from .base_component import BaseKompasComponent

class CascadingVariablesUpdater(BaseKompasComponent):
    """Обновление переменных с каскадным копированием из сборки в детали"""
    
    def __init__(self):
        super().__init__()
    
    def update_project_variables(self, project_path: str, h: int, b1: int, l1: int) -> Dict:
        """
        Полное обновление переменных в проекте:
        1. Обновляем H, B1, L1 в сборке
        2. Пересобираем сборку (все зависимые переменные пересчитаются!)
        3. Читаем ВСЕ переменные из сборки
        4. Записываем их значения в детали
        
        Args:
            project_path: Путь к проекту
            h, b1, l1: Новые значения
            
        Returns:
            Dict с результатами
        """
        result = {
            'success': False,
            'assembly_vars_updated': 0,
            'assembly_vars_calculated': {},
            'parts_updated': 0,
            'total_vars_in_parts': 0,
            'errors': []
        }
        
        pythoncom.CoInitialize()
        
        try:
            self.logger.info("="*60)
            self.logger.info("КАСКАДНОЕ ОБНОВЛЕНИЕ ПЕРЕМЕННЫХ")
            self.logger.info("="*60)
            self.logger.info(f"H={h}, B1={b1}, L1={l1}\n")
            
            if not self.connect_to_kompas():
                result['errors'].append("Не удалось подключиться к КОМПАС-3D")
                return result
            
            project_path_obj = Path(project_path)
            assembly_file = list(project_path_obj.glob("*.a3d"))[0]
            
            #==========================================================
            # ЭТАП 1: Обновление и пересчет переменных в сборке
            #==========================================================
            self.logger.info("ЭТАП 1: Обновление переменных в сборке")
            self.logger.info("="*60)
            
            if not self.open_document(str(assembly_file)):
                result['errors'].append("Не удалось открыть сборку")
                return result
            
            api5 = Dispatch("Kompas.Application.5")
            api7 = Dispatch("Kompas.Application.7")
            
            iDocument3D = api5.ActiveDocument3D
            iPart = iDocument3D.GetPart(-1)
            var_collection = iPart.VariableCollection()
            
            # 1.1 Обновляем базовые переменные
            self.logger.info("\n1.1. Обновление H, B1, L1:")
            
            base_vars = {'H': h, 'B1': b1, 'L1': l1}
            
            for var_name, var_value in base_vars.items():
                try:
                    var = var_collection.GetByName(var_name)
                    if var:
                        old = var.value
                        var.value = float(var_value)
                        var.Expression = str(var_value)
                        var.External = True
                        self.logger.info(f"  {var_name}: {old} → {var_value}")
                        result['assembly_vars_updated'] += 1
                    else:
                        self.logger.warning(f"  ⚠️ {var_name} не найдена!")
                except Exception as e:
                    self.logger.error(f"  ✗ {var_name}: {e}")
            
            # 1.2 Каскадная пересборка (чтобы пересчитались зависимые переменные!)
            self.logger.info("\n1.2. Каскадная пересборка (пересчет зависимых переменных):")
            
            for cycle in range(1, 4):
                self.logger.info(f"  Цикл {cycle}/3...")
                iPart.Update()
                time.sleep(1)
                iPart.RebuildModel()
                time.sleep(2)
                iDocument3D.RebuildDocument()
                time.sleep(2)
            
            self.logger.info("  ✓ Пересборка завершена")
            
            # 1.3 Читаем переменные и РАССЧИТЫВАЕМ зависимые значения
            self.logger.info("\n1.3. Чтение и расчет переменных:")
            
            all_calculated_vars = {}
            
            # Сначала читаем ВСЕ переменные (включая коэффициенты)
            for i in range(200):
                try:
                    var = var_collection.GetByIndex(i)
                    if var:
                        name = var.name if hasattr(var, 'name') else None
                        if name:
                            value = var.value if hasattr(var, 'value') else None
                            all_calculated_vars[name] = value
                except:
                    break
            
            # КРИТИЧНО: Рассчитываем зависимые переменные ВРУЧНУЮ!
            # (КОМПАС-3D не пересчитывает формулы автоматически!)
            
            if 'A2' in all_calculated_vars:
                all_calculated_vars['A1'] = h - all_calculated_vars['A2']
                self.logger.info(f"  Расчет: A1 = H - A2 = {h} - {all_calculated_vars['A2']} = {all_calculated_vars['A1']}")
            
            if 'A1' in all_calculated_vars:
                all_calculated_vars['A4'] = all_calculated_vars['A1'] - 5
                self.logger.info(f"  Расчет: A4 = A1 - 5 = {all_calculated_vars['A1']} - 5 = {all_calculated_vars['A4']}")
            
            if 'A1' in all_calculated_vars:
                # A3 может быть A1-20 или A1-10.5 в зависимости от шаблона
                # Проверяем текущее значение A3 в сборке для определения коэффициента
                if 'A3' in all_calculated_vars:
                    # Вычисляем коэффициент из исходного шаблона
                    coeff = all_calculated_vars['A1'] - all_calculated_vars['A3']
                    all_calculated_vars['A3'] = all_calculated_vars['A1'] - coeff
                    self.logger.info(f"  Расчет: A3 = A1 - {coeff} = {all_calculated_vars['A1']} - {coeff} = {all_calculated_vars['A3']}")
                else:
                    # По умолчанию используем -20
                    all_calculated_vars['A3'] = all_calculated_vars['A1'] - 20
                    self.logger.info(f"  Расчет: A3 = A1 - 20 = {all_calculated_vars['A1']} - 20 = {all_calculated_vars['A3']}")
            
            if 'B2' in all_calculated_vars:
                all_calculated_vars['B3'] = b1 - all_calculated_vars['B2'] * 2 - 6.9
                self.logger.info(f"  Расчет: B3 = B1 - B2*2 - 6.9 = {b1} - {all_calculated_vars['B2']}*2 - 6.9 = {all_calculated_vars['B3']}")
                
                all_calculated_vars['B4'] = b1 - all_calculated_vars['B2'] * 2 - 2.5
                self.logger.info(f"  Расчет: B4 = B1 - B2*2 - 2.5 = {b1} - {all_calculated_vars['B2']}*2 - 2.5 = {all_calculated_vars['B4']}")
            
            # B5 и B6 зависят только от B1
            all_calculated_vars['B5'] = b1 - 4
            self.logger.info(f"  Расчет: B5 = B1 - 4 = {b1} - 4 = {all_calculated_vars['B5']}")
            
            all_calculated_vars['B6'] = b1 - 60
            self.logger.info(f"  Расчет: B6 = B1 - 60 = {b1} - 60 = {all_calculated_vars['B6']}")
            
            if 'A2' in all_calculated_vars:
                all_calculated_vars['A5'] = all_calculated_vars['A2'] - 1.5
                self.logger.info(f"  Расчет: A5 = A2 - 1.5 = {all_calculated_vars['A2']} - 1.5 = {all_calculated_vars['A5']}")
            
            # УДАЛЕНО: Не добавляем A, B, L - они могут перезаписать A4, B4!
            # Если в сборке есть A, B, L - они уже прочитаны выше
            
            result['assembly_vars_calculated'] = all_calculated_vars
            
            # Логируем External переменные
            self.logger.info("\n  External переменные:")
            for i in range(200):
                try:
                    var = var_collection.GetByIndex(i)
                    if var:
                        name = var.name if hasattr(var, 'name') else None
                        if name:
                            is_external = var.External if hasattr(var, 'External') else False
                            if is_external and name in all_calculated_vars:
                                self.logger.info(f"    {name} = {all_calculated_vars[name]}")
                except:
                    break
            
            self.logger.info(f"\n  Всего переменных: {len(all_calculated_vars)}")
            
            # Сохраняем сборку
            api7.ActiveDocument.Save()
            self.logger.info("  ✓ Сборка сохранена")
            
            # Закрываем сборку
            api7.ActiveDocument.Close(False)
            time.sleep(1)
            
            #==========================================================
            # ЭТАП 2: Копирование переменных в детали
            #==========================================================
            self.logger.info("\n" + "="*60)
            self.logger.info("ЭТАП 2: Копирование переменных в детали")
            self.logger.info("="*60)
            
            part_files = list(project_path_obj.glob("*.m3d"))
            part_files = [p for p in part_files if not p.stem.startswith('-')]
            
            self.logger.info(f"\nНайдено деталей: {len(part_files)}\n")
            
            for part_file in part_files:
                try:
                    self.logger.info(f"{'='*60}")
                    self.logger.info(f"{part_file.name}")
                    self.logger.info(f"{'='*60}")
                    
                    if not self.open_document(str(part_file)):
                        self.logger.warning("  ✗ Не удалось открыть")
                        continue
                    
                    iDocument3D_part = api5.ActiveDocument3D
                    if not iDocument3D_part:
                        api7.ActiveDocument.Close(False)
                        continue
                    
                    iPart_detail = iDocument3D_part.GetPart(-1)
                    var_coll_part = iPart_detail.VariableCollection()
                    
                    if not var_coll_part:
                        api7.ActiveDocument.Close(False)
                        continue
                    
                    # Обновляем переменные в детали из сборки
                    updated_in_part = 0
                    
                    for var_name, var_value in all_calculated_vars.items():
                        # КРИТИЧНО: Пропускаем переменные экземпляров (v1398_B3, и т.д.)
                        # Они создаются КОМПАС-3D для каждого экземпляра детали в сборке
                        # и НЕ должны копироваться в файлы деталей!
                        if var_name.startswith('v') and '_' in var_name:
                            # Проверяем, это переменная экземпляра (v[цифры]_имя)
                            prefix = var_name.split('_')[0]
                            if prefix[1:].isdigit():  # v1398, v2456, и т.д.
                                continue  # Пропускаем!
                        
                        try:
                            var_in_part = var_coll_part.GetByName(var_name)
                            # КРИТИЧНО: Обновляем ТОЛЬКО если переменная УЖЕ ЕСТЬ в детали!
                            # Не создаем новые переменные!
                            if var_in_part:
                                old = var_in_part.value
                                
                                # ВСЕГДА обновляем, даже если значения совпадают!
                                
                                # КРИТИЧНО: ОЧИЩАЕМ Expression только если это НЕ формула!
                                # Если там строковый литерал или гиперссылка - удаляем
                                # Если там формула (содержит операторы) - НЕ ТРОГАЕМ!
                                current_expr = var_in_part.Expression if hasattr(var_in_part, 'Expression') else ''
                                
                                # Проверяем, есть ли в Expression формула или гиперссылка
                                has_formula = any(op in str(current_expr) for op in ['-', '+', '*', '/', 'if', '?'])
                                has_hyperlink = ':\\' in str(current_expr) or '|' in str(current_expr)
                                
                                if has_hyperlink:
                                    # Удаляем гиперссылку - ставим число
                                    try:
                                        var_in_part.Expression = str(var_value)
                                        var_in_part.value = var_value
                                    except:
                                        pass
                                elif has_formula:
                                    # Есть формула - ПРИНУДИТЕЛЬНО ПЕРЕСЧИТЫВАЕМ!
                                    # Удаляем и восстанавливаем формулу для пересчета
                                    try:
                                        saved_formula = var_in_part.Expression
                                        var_in_part.Expression = ""  # Очищаем
                                        time.sleep(0.1)
                                        var_in_part.Expression = saved_formula  # Восстанавливаем
                                        # Формула должна пересчитаться с новыми значениями!
                                    except:
                                        pass
                                else:
                                    # Нет формулы - обновляем как число
                                    try:
                                        var_in_part.Expression = str(var_value)
                                        var_in_part.value = var_value
                                    except:
                                        pass
                                
                                # External обязательно
                                if hasattr(var_in_part, 'External'):
                                    var_in_part.External = True
                                
                                # Логируем только если изменилось
                                if abs(old - var_value) > 0.01:
                                    self.logger.info(f"  {var_name}: {old} → {var_value}")
                                    updated_in_part += 1
                                else:
                                    # Всё равно считаем обновленной (External установлен!)
                                    updated_in_part += 1
                        except Exception as e:
                            pass
                    
                    if updated_in_part > 0:
                        # КРИТИЧНО: Пересборка детали для применения изменений
                        self.logger.info(f"\n  Пересборка...")
                        
                        iPart_detail.Update()
                        time.sleep(0.5)
                        iPart_detail.RebuildModel()
                        time.sleep(1)
                        
                        # КРИТИЧНО: RebuildDocument для детали!
                        iDocument3D_part.RebuildDocument()
                        time.sleep(1)
                        
                        # КРИТИЧНО: Агрессивное сохранение
                        api7.ActiveDocument.Save()
                        time.sleep(1)
                        
                        # Закрываем с сохранением
                        api7.ActiveDocument.Close(True)  # True = сохранить еще раз!
                        time.sleep(0.5)
                        
                        # КРИТИЧНО ДЛЯ РАСПОРКИ: Переоткрываем и пересобираем еще раз!
                        # Формулы в эскизах (например, A1-20) вычисляются при ОТКРЫТИИ файла
                        # и используют значения переменных НА МОМЕНТ ОТКРЫТИЯ!
                        # Поэтому нужно: обновить → закрыть → ПЕРЕОТКРЫТЬ → пересобрать!
                        if "Распорка" in part_file.name or "распорка" in part_file.name:
                            self.logger.info(f"  🔄 Дополнительная пересборка распорки (для формул в эскизах)...")
                            
                            # Ждем, чтобы файл точно закрылся
                            time.sleep(2)
                            
                            # Переоткрываем
                            if self.open_document(str(part_file)):
                                self.logger.info(f"     Распорка переоткрыта")
                                
                                iDocument3D_part2 = api5.ActiveDocument3D
                                iPart_detail2 = iDocument3D_part2.GetPart(-1)
                                var_coll_2 = iPart_detail2.VariableCollection()
                                
                                # Проверяем значения ПОСЛЕ переоткрытия
                                var_a3_check = var_coll_2.GetByName('A3')
                                if var_a3_check:
                                    self.logger.info(f"     A3 после переоткрытия: {var_a3_check.value}")
                                
                                # Множественная пересборка
                                for i in range(3):
                                    iPart_detail2.Update()
                                    time.sleep(0.5)
                                    iPart_detail2.RebuildModel()
                                    time.sleep(1)
                                    iDocument3D_part2.RebuildDocument()
                                    time.sleep(1)
                                
                                # Финальное сохранение
                                api7.ActiveDocument.Save()
                                time.sleep(2)
                                api7.ActiveDocument.Close(True)
                                time.sleep(1)
                                
                                self.logger.info(f"  ✓ Дополнительная пересборка завершена")
                        
                        self.logger.info(f"  ✓ Сохранено ({updated_in_part} переменных)")
                        
                        result['parts_updated'] += 1
                        result['total_vars_in_parts'] += updated_in_part
                    else:
                        self.logger.info(f"  (совпадающих переменных не найдено)")
                        api7.ActiveDocument.Close(False)
                    
                    time.sleep(0.5)
                    self.logger.info("")
                
                except Exception as e:
                    self.logger.error(f"  ✗ Ошибка: {e}")
                    try:
                        api7.ActiveDocument.Close(False)
                    except:
                        pass
            
            #==========================================================
            # ЭТАП 3: Финальная пересборка сборки (обновление геометрии!)
            #==========================================================
            self.logger.info("\n" + "="*60)
            self.logger.info("ЭТАП 3: Финальная пересборка сборки")
            self.logger.info("="*60)
            
            # Открываем сборку еще раз
            if self.open_document(str(assembly_file)):
                self.logger.info(f"Документ открыт: {assembly_file.name}\n")
                
                iDocument3D = api5.ActiveDocument3D
                iPart = iDocument3D.GetPart(-1)
                
                # КРИТИЧНО: Многократная пересборка для обновления геометрии деталей в сборке!
                self.logger.info("Финальная пересборка (обновление геометрии деталей):")
                for cycle in range(1, 4):
                    self.logger.info(f"  Цикл {cycle}/3...")
                    iPart.Update()
                    time.sleep(1)
                    iPart.RebuildModel()
                    time.sleep(2)
                    iDocument3D.RebuildDocument()
                    time.sleep(2)
                
                self.logger.info("  ✓ Финальная пересборка завершена\n")
                
                # Сохраняем
                api7.ActiveDocument.Save()
                time.sleep(1)
                
                # Закрываем
                api7.ActiveDocument.Close(False)
                
                self.logger.info("  ✓ Сборка сохранена и обновлена\n")
            
            result['success'] = True
            
            self.logger.info("="*60)
            self.logger.info("ИТОГО:")
            self.logger.info(f"  Сборка: {result['assembly_vars_updated']} базовых + {len(all_calculated_vars)} всего")
            self.logger.info(f"  Деталей обновлено: {result['parts_updated']}")
            self.logger.info(f"  Переменных в деталях: {result['total_vars_in_parts']}")
            self.logger.info("="*60)
            
        except Exception as e:
            error_msg = f"Ошибка: {e}"
            result['errors'].append(error_msg)
            self.logger.error(error_msg)
            import traceback
            self.logger.error(traceback.format_exc())
        
        finally:
            pythoncom.CoUninitialize()
        
        return result

