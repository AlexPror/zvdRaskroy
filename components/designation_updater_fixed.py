#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Компонент для обновления обозначений деталей (ИСПРАВЛЕННАЯ ВЕРСИЯ)
С правильной последовательностью: Update() + RebuildModel() + RebuildDocument() + Save() + Close(True)
"""

import logging
from pathlib import Path
from typing import Dict, List
from win32com.client import Dispatch, gencache
from .base_component import BaseKompasComponent
import time

class DesignationUpdaterFixed(BaseKompasComponent):
    """Компонент для обновления обозначений деталей с РАБОЧЕЙ логикой"""
    
    def __init__(self):
        super().__init__()
    
    def update_all_designations(self, project_path: str, H: int, B1: int, L1: int, order_number: str = None) -> Dict:
        """
        Обновление ВСЕХ обозначений (сборка + детали) с правильной логикой
        
        Логика обозначений:
        - Сборка: ZVD.LITE.H.B1.L1
        - Корпус короба (004): ZVD.LITE.H.B1.L1.XXX (с L1)
        - Остальные детали: ZVD.LITE.H.B1.XXX (без L1)
        
        Args:
            project_path: Путь к проекту
            H: Высота
            B1: Ширина
            L1: Длина
            
        Returns:
            Dict с результатами
        """
        result = {
            'success': False,
            'assembly_renamed': False,
            'parts_renamed': 0,
            'updated_parts': [],
            'errors': [],
            'error': None
        }
        
        try:
            self.logger.info("ОБНОВЛЕНИЕ ВСЕХ ОБОЗНАЧЕНИЙ")
            self.logger.info("=" * 50)
            self.logger.info(f"H={H}, B1={B1}, L1={L1}")
            
            if not self.connect_to_kompas():
                result['error'] = "Не удалось подключиться к КОМПАС-3D"
                return result
            
            project_path_obj = Path(project_path)
            
            # Формируем обозначения
            full_name = f"ZVD.LITE.{H}.{B1}.{L1}"
            short_name = f"ZVD.LITE.{H}.{B1}"
            
            # Получаем API
            api5_obj = Dispatch("Kompas.Application.5")
            api7_obj = Dispatch("Kompas.Application.7")
            kompas6_constants_3d = gencache.EnsureModule("{2CAF168C-7961-4B90-9DA2-701419BEEFE3}", 0, 1, 0).constants
            
            # ШАГ 1: ПЕРЕИМЕНОВАНИЕ СБОРКИ
            self.logger.info("\n--- ПЕРЕИМЕНОВАНИЕ СБОРКИ ---")
            
            assembly_files = list(project_path_obj.glob("*.a3d"))
            if not assembly_files:
                result['error'] = "Файл сборки не найден"
                return result
            
            assembly_file = assembly_files[0]
            self.logger.info(f"Файл сборки: {assembly_file.name}")
            
            # Переименовываем файл ПЕРЕД открытием
            new_assembly_name = f"{full_name}.a3d"
            new_assembly_path = project_path_obj / new_assembly_name
            
            if assembly_file.name != new_assembly_name:
                try:
                    self.logger.info(f"Переименование файла: {assembly_file.name} → {new_assembly_name}")
                    assembly_file.rename(new_assembly_path)
                    assembly_file = new_assembly_path  # Обновляем путь
                    self.logger.info(f"✓ Файл сборки переименован")
                except Exception as e:
                    error_msg = f"Ошибка переименования файла сборки: {e}"
                    result['errors'].append(error_msg)
                    self.logger.error(error_msg)
                    # Продолжаем работу с оригинальным именем
            
            try:
                doc3D_asm = api5_obj.Document3D
                doc3D_asm.Open(str(assembly_file), False)
                time.sleep(1)
                
                iDocument3D_asm = api5_obj.ActiveDocument3D
                iPart_asm = iDocument3D_asm.GetPart(kompas6_constants_3d.pTop_Part)
                
                old_asm = iPart_asm.marking
                iPart_asm.marking = full_name
                
                # REBUILD!
                iPart_asm.Update()
                iPart_asm.RebuildModel()
                iDocument3D_asm.RebuildDocument()
                time.sleep(1)
                
                # Сохраняем
                active_doc_asm = api7_obj.ActiveDocument
                active_doc_asm.Save()
                time.sleep(2)
                
                # Закрываем С СОХРАНЕНИЕМ
                active_doc_asm.Close(True)
                time.sleep(2)
                
                self.logger.info(f"✓ Сборка: '{old_asm}' → '{full_name}'")
                result['assembly_renamed'] = True
                
            except Exception as e:
                error_msg = f"Ошибка переименования сборки: {e}"
                result['errors'].append(error_msg)
                self.logger.error(error_msg)
            
            # ШАГ 2: ОБНОВЛЕНИЕ MARKING В СБОРКЕ (СНАЧАЛА!)
            # ВАЖНО: Сначала обновляем marking в сборке, чтобы знать правильные номера деталей
            self.logger.info("\n--- ОБНОВЛЕНИЕ MARKING В СБОРКЕ ---")
            self.logger.info("(определение правильных номеров для всех деталей)")
            
            # Словарь: {имя_файла_детали: (marking_из_сборки, наименование)}
            file_to_marking = {}
            
            try:
                # Открываем сборку
                assembly_files_reopen = list(project_path_obj.glob("*.a3d"))
                if assembly_files_reopen:
                    assembly_file_reopen = assembly_files_reopen[0]
                    
                    doc3D_asm2 = api5_obj.Document3D
                    doc3D_asm2.Open(str(assembly_file_reopen), False)
                    time.sleep(2)
                    
                    iDocument3D_asm2 = api5_obj.ActiveDocument3D
                    iPart_asm2 = iDocument3D_asm2.GetPart(kompas6_constants_3d.pTop_Part)
                    
                    # Находим все детали в сборке
                    asm_parts_count = 0
                    for i in range(100):
                        try:
                            p = iPart_asm2.GetPart(i)
                            if p:
                                asm_parts_count = i + 1
                            else:
                                break
                        except:
                            break
                    
                    self.logger.info(f"Детал ей в сборке: {asm_parts_count}")
                    
                    # КРИТИЧНО: Группируем детали по имени!
                    # Детали с одинаковым именем получают один номер!
                    name_to_number = {}  # {имя_детали: номер}
                    next_number = 1
                    
                    # Первый проход - присваиваем номера уникальным именам
                    for i in range(asm_parts_count):
                        try:
                            p = iPart_asm2.GetPart(i)
                            if not p:
                                continue
                            
                            old_mark = p.marking.strip() if hasattr(p, 'marking') else ""
                            p_name = p.name.strip() if hasattr(p, 'name') else ""
                            
                            # Пропускаем служебные
                            if not old_mark or old_mark.startswith('-'):
                                continue
                            
                            # Присваиваем номер (если еще не присвоен)
                            if p_name not in name_to_number:
                                name_to_number[p_name] = next_number
                                next_number += 1
                        except:
                            pass
                    
                    self.logger.info(f"\n  Уникальных деталей: {len(name_to_number)}")
                    for name, num in sorted(name_to_number.items(), key=lambda x: x[1]):
                        self.logger.info(f"    {num:03d} - {name}")
                    
                    # Второй проход - обновляем marking И СОХРАНЯЕМ соответствие файл->marking
                    updated_instances = 0
                    
                    for i in range(asm_parts_count):
                        try:
                            p = iPart_asm2.GetPart(i)
                            if not p:
                                continue
                            
                            old_mark = p.marking.strip() if hasattr(p, 'marking') else ""
                            p_name = p.name.strip() if hasattr(p, 'name') else ""
                            p_filename = p.fileName.strip() if hasattr(p, 'fileName') else ""
                            
                            # Пропускаем служебные
                            if not old_mark or old_mark.startswith('-'):
                                continue
                            
                            # Получаем номер для этого имени
                            part_id = f"{name_to_number[p_name]:03d}"
                            
                            # СПЕЦИАЛЬНАЯ ОБРАБОТКА для теплообменника
                            if "теплообменник" in p_name.lower():
                                # Для теплообменника не меняем базовое обозначение
                                # Только обновляем длину если нужно
                                new_mark = old_mark  # Оставляем как есть пока
                            elif "короба" in p_name.lower():
                                new_mark = f"{full_name}.{part_id}"
                            else:
                                new_mark = f"{short_name}.{part_id}"
                            
                            # СОХРАНЯЕМ соответствие fileName -> marking
                            if p_filename:
                                filename_normalized = Path(p_filename).name
                                if filename_normalized not in file_to_marking:
                                    file_to_marking[filename_normalized] = (new_mark, p_name, part_id)
                            
                            # Обновляем ТОЛЬКО если отличается
                            if old_mark != new_mark:
                                p.marking = new_mark
                                p.Update()
                                p.RebuildModel()
                                
                                self.logger.info(f"  [{i}] {p_name}: '{old_mark}' → '{new_mark}'")
                                updated_instances += 1
                            
                        except Exception as e:
                            self.logger.warning(f"Ошибка экземпляра {i}: {e}")
                    
                    if updated_instances > 0:
                        # Rebuild и сохранение сборки
                        iDocument3D_asm2.RebuildDocument()
                        time.sleep(1)
                        
                        active_doc2 = api7_obj.ActiveDocument
                        active_doc2.Save()
                        time.sleep(1)
                        
                        self.logger.info(f"✓ Обновлено экземпляров в сборке: {updated_instances}")
                    
                    # Закрываем
                    api7_obj.ActiveDocument.Close(True)
                    time.sleep(1)
                    
            except Exception as e:
                error_msg = f"Ошибка обновления экземпляров в сборке: {e}"
                result['errors'].append(error_msg)
                self.logger.error(error_msg)
            
            # ШАГ 3: ОБНОВЛЕНИЕ MARKING В ФАЙЛАХ ДЕТАЛЕЙ И ПЕРЕИМЕНОВАНИЕ ФАЙЛОВ
            self.logger.info("\n--- ОБНОВЛЕНИЕ MARKING В ФАЙЛАХ ДЕТАЛЕЙ ---")
            self.logger.info(f"Найдено соответствий файл->marking: {len(file_to_marking)}")
            
            renamed_count = 0
            files_to_rename = []  # [(старый_путь, новый_путь, marking)]
            
            for filename, (marking, part_name, part_id) in file_to_marking.items():
                try:
                    # Находим файл
                    part_files_found = list(project_path_obj.glob(filename))
                    if not part_files_found:
                        self.logger.warning(f"  ⚠ Файл не найден: {filename}")
                        continue
                    
                    part_file = part_files_found[0]
                    self.logger.info(f"\n  [{part_id}] {filename}")
                    
                    # Открываем файл детали
                    doc3D = api5_obj.Document3D
                    doc3D.Open(str(part_file), False)
                    time.sleep(0.5)
                    
                    iDocument3D = api5_obj.ActiveDocument3D
                    iPart = iDocument3D.GetPart(kompas6_constants_3d.pTop_Part)
                    
                    old_marking = iPart.marking
                    
                    # Для теплообменника - специальная обработка
                    if "теплообменник" in filename.lower():
                        heat_length = L1 - 300
                        old_parts = old_marking.split()
                        if len(old_parts) >= 2 and '.' in old_parts[0]:
                            size_parts = old_parts[0].split('.')
                            if len(size_parts) == 3:
                                size_parts[2] = str(heat_length)
                                new_marking = f"{'.'.join(size_parts)} {' '.join(old_parts[1:])}"
                            else:
                                new_marking = old_marking
                        else:
                            new_marking = old_marking
                        self.logger.info(f"    Теплообменник: '{old_marking}' → '{new_marking}'")
                    else:
                        # Обычная деталь - используем marking из сборки
                        new_marking = marking
                        self.logger.info(f"    Marking: '{old_marking}' → '{new_marking}'")
                    
                    # Обновляем marking
                    iPart.marking = new_marking
                    
                    # Обновляем наименование (добавляем номер заказа)
                    if order_number:
                        old_name = iPart.name if hasattr(iPart, 'name') else ""
                        
                        # Убираем старый номер заказа
                        import re
                        clean_name = re.sub(r'\s*\([^)]*\)\s*$', '', old_name).strip()
                        
                        # Добавляем новый
                        new_name = f"{clean_name} ({order_number})"
                        iPart.name = new_name
                        
                        self.logger.info(f"    Наименование: '{clean_name}' → '{new_name}'")
                    
                    # Rebuild и сохранение
                    iPart.Update()
                    iPart.RebuildModel()
                    iDocument3D.RebuildDocument()
                    time.sleep(0.5)
                    
                    active_doc = api7_obj.ActiveDocument
                    active_doc.Save()
                    time.sleep(0.5)
                    
                    active_doc.Close(True)
                    time.sleep(0.5)
                    
                    # Формируем новое имя файла по part_id
                    # Извлекаем оригинальное имя без номера
                    file_stem = part_file.stem
                    if " - " in file_stem:
                        file_description = file_stem.split(" - ", 1)[1]
                    else:
                        file_description = file_stem
                    
                    new_filename = f"{part_id} - {file_description}.m3d"
                    new_filepath = part_file.parent / new_filename
                    
                    # Сохраняем для последующего переименования
                    if part_file != new_filepath:
                        files_to_rename.append((part_file, new_filepath, marking))
                    
                    renamed_count += 1
                    
                except Exception as e:
                    error_msg = f"Ошибка обновления {filename}: {e}"
                    result['errors'].append(error_msg)
                    self.logger.error(f"    ✗ {error_msg}")
                    try:
                        api7_obj.ActiveDocument.Close(False)
                    except:
                        pass
            
            result['parts_renamed'] = renamed_count
            
            # Переименовываем файлы ПОСЛЕ закрытия всех документов
            self.logger.info(f"\n--- ПЕРЕИМЕНОВАНИЕ ФАЙЛОВ ДЕТАЛЕЙ ---")
            self.logger.info(f"Файлов к переименованию: {len(files_to_rename)}")
            
            for old_path, new_path, marking in files_to_rename:
                try:
                    self.logger.info(f"  '{old_path.name}' → '{new_path.name}'")
                    old_path.rename(new_path)
                except Exception as e:
                    self.logger.warning(f"    ⚠ Ошибка переименования: {e}")
            
            # ШАГ 4: ПЕРЕИМЕНОВАНИЕ СБОРОЧНОГО ЧЕРТЕЖА
            self.logger.info("\n--- ПЕРЕИМЕНОВАНИЕ СБОРОЧНОГО ЧЕРТЕЖА ---")
            
            # Ищем сборочный чертеж (с "Конвектор" в названии)
            assembly_drawings = [
                f for f in project_path_obj.glob("*.cdw")
                if "конвектор" in f.name.lower() or "сборочный" in f.name.lower()
            ]
            
            drawings_renamed = 0
            
            for asm_drw in assembly_drawings:
                try:
                    old_name = asm_drw.name
                    
                    # Формируем новое имя (заменяем старые параметры на новые)
                    # Было: "ZVD.LITE.90.260.1000 - Конвектор..."
                    # Станет: "ZVD.LITE.126.160.1400 - Конвектор..."
                    
                    # Извлекаем часть после " - " (название без параметров)
                    if " - " in old_name:
                        name_parts = old_name.split(" - ", 1)
                        description = name_parts[1]  # "Конвектор с естественной конвекцией.cdw"
                        new_drawing_name = f"{full_name} - {description}"
                    else:
                        # Если нет " - ", просто добавляем параметры в начало
                        new_drawing_name = f"{full_name} - {old_name}"
                    
                    new_drawing_path = asm_drw.parent / new_drawing_name
                    
                    if asm_drw != new_drawing_path:
                        self.logger.info(f"Чертеж: '{old_name}'")
                        self.logger.info(f"      → '{new_drawing_name}'")
                        
                        asm_drw.rename(new_drawing_path)
                        drawings_renamed += 1
                        self.logger.info(f"✓ Чертеж переименован")
                
                except Exception as e:
                    self.logger.warning(f"Ошибка переименования чертежа {asm_drw.name}: {e}")
            
            result['drawings_renamed'] = drawings_renamed
            result['success'] = result['assembly_renamed'] or renamed_count > 0 or drawings_renamed > 0
            
            self.logger.info(f"\n✓ Итого:")
            self.logger.info(f"  - Сборка переименована: {result['assembly_renamed']}")
            self.logger.info(f"  - Деталей переименовано: {renamed_count}")
            self.logger.info(f"  - Чертежей переименовано: {drawings_renamed}")
            
            return result
            
        except Exception as e:
            error_msg = f"Общая ошибка: {e}"
            result['error'] = error_msg
            self.logger.error(error_msg)
            import traceback
            traceback.print_exc()
            return result
        finally:
            self.disconnect_from_kompas()

