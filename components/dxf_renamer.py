"""
Компонент для переименования DXF файлов с номером заказа и количеством деталей
"""

import pythoncom
from win32com.client import Dispatch, gencache
import logging
from pathlib import Path
from typing import Dict
import time


class DxfRenamer:
    """Переименование DXF файлов разверток"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_part_quantity_from_assembly(self, assembly_path: str, part_marking: str) -> int:
        """
        Получить количество экземпляров детали в сборке ПО ОБОЗНАЧЕНИЮ (marking)
        
        Args:
            assembly_path: Путь к .a3d файлу
            part_marking: Обозначение детали (например, "ZVD.LITE.129.160.003")
        
        Returns:
            int: Количество экземпляров
        """
        quantity = 1  # По умолчанию
        
        try:
            pythoncom.CoInitialize()
            
            api5 = Dispatch("Kompas.Application.5")
            api5.Visible = False
            api7 = Dispatch("Kompas.Application.7")
            
            kompas_constants = gencache.EnsureModule(
                "{2CAF168C-7961-4B90-9DA2-701419BEEFE3}", 0, 1, 0
            ).constants
            
            # Открываем сборку
            doc = api7.Documents.Open(assembly_path, False, True)
            if not doc:
                return quantity
            
            time.sleep(1)
            
            iDocument3D = api5.ActiveDocument3D
            if not iDocument3D:
                doc.Close(False)
                return quantity
            
            iPart_asm = iDocument3D.GetPart(kompas_constants.pTop_Part)
            if not iPart_asm:
                doc.Close(False)
                return quantity
            
            # ТОЧНОЕ СРАВНЕНИЕ по marking (обозначению)!
            i = 0
            count = 0
            while True:
                try:
                    p = iPart_asm.GetPart(i)
                    if not p:
                        break
                    
                    p_marking = p.marking.strip() if hasattr(p, 'marking') else ""
                    
                    # Пропускаем служебные
                    if not p_marking or p_marking.startswith('-'):
                        i += 1
                        continue
                    
                    # ТОЧНОЕ сравнение по marking
                    if p_marking == part_marking:
                        count += 1
                    
                    i += 1
                except:
                    break
            
            quantity = count if count > 0 else 1
            
            self.logger.info(f"    Количество '{part_marking}' в сборке: {quantity}")
            
            # Закрываем
            doc.Close(False)
            
        except Exception as e:
            self.logger.warning(f"Ошибка получения количества для '{part_marking}': {e}")
        
        finally:
            try:
                pythoncom.CoUninitialize()
            except:
                pass
        
        return quantity
    
    def rename_dxf_files(self, project_path: str, order_number: str = None) -> Dict:
        """
        Переименование DXF файлов с добавлением номера заказа и количества
        
        Формат: "006 - Стенка торц 2шт (А-180925-1801).dxf"
        
        Args:
            project_path: Путь к папке проекта
            order_number: Номер заказа (опционально)
        
        Returns:
            dict: {'success': bool, 'renamed_count': int, 'errors': list}
        """
        result = {
            'success': False,
            'renamed_count': 0,
            'errors': []
        }
        
        try:
            project_path_obj = Path(project_path)
            dxf_folder = project_path_obj / "DXF"
            
            if not dxf_folder.exists():
                result['errors'].append("Папка DXF не найдена")
                return result
            
            # Находим сборку
            assembly_files = list(project_path_obj.glob("*.a3d"))
            if not assembly_files:
                result['errors'].append("Файл сборки не найден")
                return result
            
            assembly_path = str(assembly_files[0])
            
            # Находим все DXF файлы
            dxf_files = list(dxf_folder.glob("*.dxf"))
            
            self.logger.info(f"\nНайдено DXF файлов: {len(dxf_files)}")
            
            # НОВЫЙ ПОДХОД: Сопоставляем DXF с деталями (.m3d) по имени!
            # DXF: "Развертка корпуса короба.dxf"
            # M3D: "001 - Корпус короба.m3d"
            
            part_files = list(project_path_obj.glob("*.m3d"))
            
            for dxf_file in dxf_files:
                try:
                    old_name = dxf_file.stem  # Без расширения
                    
                    # Убираем "развертка" для поиска
                    dxf_clean = old_name.lower().replace("развертка", "").strip(" -")
                    
                    part_number = None
                    part_name = None
                    part_marking_for_count = None  # ВАЖНО: Для подсчета количества
                    
                    # МАППИНГ: Развертка DXF → Деталь M3D
                    # Явное сопоставление для известных случаев
                    # ВАЖНО: Более специфичные ключи должны проверяться ПЕРВЫМИ!
                    dxf_to_part_mapping = [
                        ("стенка торцевая", "стенка торцевая"),
                        ("стенки торцевой", "стенка торцевая"),
                        ("корпус короба", "корпус короба"),
                        ("корпуса короба", "корпус короба"),
                        ("крышка декоративная", "крышка декоративная"),
                        ("крышки декоративной", "крышка декоративная"),
                        ("распорки", "распорка"),
                        ("укороченной распорки", "накладка"),
                        ("стенки", "стенка"),  # Должно быть ПОСЛЕ "стенки торцевой"!
                        ("стенка", "стенка"),
                    ]
                    
                    # Проверяем маппинг (от более специфичных к общим)
                    # Используем список, а не словарь, чтобы контролировать порядок проверки
                    mapped_to_skip = False
                    for dxf_key, part_key in dxf_to_part_mapping:
                        # Проверяем, все ли ключевые слова из dxf_key есть в dxf_clean
                        dxf_key_words = set(dxf_key.split())
                        dxf_clean_words = set(dxf_clean.split())
                        
                        if dxf_key_words.issubset(dxf_clean_words):
                            if part_key == "накладка":
                                self.logger.info(f"  ⊗ Пропуск (Накладка): {dxf_file.name}")
                                mapped_to_skip = True
                                break
                            dxf_clean = part_key  # Заменяем для поиска
                            break
                    
                    if mapped_to_skip:
                        continue
                    
                    # Ищем соответствующую деталь
                    # Собираем кандидатов: (part_file, is_exact_match)
                    candidates = []
                    
                    for part_file in part_files:
                        # Пропускаем специальные детали
                        if "накладка" in part_file.name.lower():
                            continue
                        if "теплообменник" in part_file.name.lower():
                            continue
                        
                        part_clean = part_file.stem.lower()
                        
                        # Убираем номер из имени детали для сравнения
                        if " - " in part_clean:
                            part_name_only = part_clean.split(" - ", 1)[1]
                        else:
                            part_name_only = part_clean
                        
                        # Убираем номер заказа в скобках
                        if "(" in part_name_only:
                            part_name_only = part_name_only.split("(")[0].strip()
                        
                        # ТОЧНОЕ сравнение по ключевым словам
                        # ПРИОРИТЕТ: точное совпадение (все слова совпадают)
                        # Затем: dxf_words является подмножеством part_words
                        
                        dxf_words = set([w for w in dxf_clean.split() if len(w) > 3])
                        part_words = set([w for w in part_name_only.split() if len(w) > 3])
                        
                        # Ищем точное совпадение или большинство слов
                        common_words = dxf_words & part_words
                        
                        # Приоритет 1: ТОЧНОЕ совпадение (одинаковое количество слов)
                        exact_match = (dxf_words == part_words)
                        # Приоритет 2: Все слова из dxf есть в part
                        subset_match = (dxf_words and dxf_words.issubset(part_words))
                        
                        # Собираем кандидатов
                        if exact_match or subset_match:
                            # Извлекаем номер из имени файла
                            name_parts = part_file.stem.split(" - ")
                            if len(name_parts) > 0 and name_parts[0].strip().isdigit():
                                file_number = name_parts[0].strip()
                                # Добавляем в кандидаты: (приоритет, part_file, file_number, part_name_only)
                                # Приоритет: 1 = точное совпадение, 2 = подмножество
                                priority = 1 if exact_match else 2
                                candidates.append((priority, part_file, file_number, part_name_only))
                    
                    # Выбираем лучшего кандидата (с наименьшим приоритетом = точное совпадение)
                    if candidates:
                        candidates.sort(key=lambda x: x[0])  # Сортируем по приоритету
                        priority, part_file, file_number, part_name_only = candidates[0]
                        
                        # Извлекаем имя детали
                        name_parts = part_file.stem.split(" - ")
                        part_name = name_parts[1].strip() if len(name_parts) > 1 else part_name_only
                        
                        # Убираем номер заказа из part_name
                        if "(" in part_name:
                            part_name = part_name.split("(")[0].strip()
                        
                        # Формируем marking для подсчета в сборке
                        # УПРОЩЕНО: Теперь marking в файле совпадает с marking в сборке!
                        # Просто читаем marking из файла детали
                        import pythoncom as pc2
                        from win32com.client import Dispatch as Disp2
                        from win32com.client import gencache as gc2
                        
                        try:
                            pc2.CoInitialize()
                            api5_2 = Disp2("Kompas.Application.5")
                            api5_2.Visible = False
                            api7_2 = Disp2("Kompas.Application.7")
                            kc2 = gc2.EnsureModule("{2CAF168C-7961-4B90-9DA2-701419BEEFE3}", 0, 1, 0).constants
                            
                            match_type = "ТОЧНОЕ" if priority == 1 else "частичное"
                            self.logger.info(f"  '{dxf_file.name}' → '{part_file.name}' ({match_type})")
                            
                            # Открываем файл детали и читаем marking
                            doc2 = api7_2.Documents.Open(str(part_file), False, True)
                            if doc2:
                                time.sleep(0.3)
                                iDoc2 = api5_2.ActiveDocument3D
                                if iDoc2:
                                    iPart2 = iDoc2.GetPart(kc2.pTop_Part)
                                    if iPart2:
                                        real_marking = iPart2.marking.strip()
                                        self.logger.info(f"    Marking из файла: {real_marking}")
                                        
                                        # Используем marking из файла (он совпадает с marking в сборке!)
                                        part_marking_for_count = real_marking
                                        part_number = file_number
                                
                                doc2.Close(False)
                            
                            pc2.CoUninitialize()
                        except Exception as ex:
                            self.logger.warning(f"    ⚠ Ошибка чтения marking: {ex}")
                            part_number = file_number
                        
                        self.logger.info(f"  Подсчет количества: {part_marking_for_count}")
                    
                    if not part_number:
                        self.logger.warning(f"  ⚠ Не найдена деталь для: {dxf_file.name}")
                        continue
                    
                    # Получаем количество из сборки по РЕАЛЬНОМУ marking
                    if part_marking_for_count:
                        quantity = self.get_part_quantity_from_assembly(assembly_path, part_marking_for_count)
                        self.logger.info(f"    → Количество: {quantity} шт")
                    else:
                        self.logger.warning(f"    ⚠ Marking не получен, ставим 1 шт")
                        quantity = 1
                    
                    # Формируем новое имя
                    new_name_parts = [part_number, "-", part_name]
                    
                    # ВСЕГДА добавляем количество (даже если 1)
                    new_name_parts.append(f"{quantity}шт")
                    
                    # Добавляем номер заказа (если указан)
                    if order_number:
                        new_name_parts.append(f"({order_number})")
                    
                    new_name = " ".join(new_name_parts) + ".dxf"
                    new_path = dxf_file.parent / new_name
                    
                    if dxf_file != new_path:
                        self.logger.info(f"  '{dxf_file.name}'")
                        self.logger.info(f"  → '{new_name}' (кол-во: {quantity})")
                        
                        dxf_file.rename(new_path)
                        result['renamed_count'] += 1
                    
                except Exception as e:
                    error_msg = f"{dxf_file.name}: {e}"
                    result['errors'].append(error_msg)
                    self.logger.warning(f"Ошибка переименования: {error_msg}")
            
            result['success'] = result['renamed_count'] > 0
            
            self.logger.info(f"\n✓ Переименовано DXF: {result['renamed_count']}")
            
        except Exception as e:
            result['errors'].append(str(e))
            self.logger.error(f"Общая ошибка: {e}")
        
        return result


if __name__ == "__main__":
    # Тестирование
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    
    renamer = DxfRenamer()
    
    # Тест
    test_project = r"C:\Users\Vorob\Documents\ZVD GROUP\Параметризация\ZVD.LITE.126.160.1400"
    result = renamer.rename_dxf_files(test_project, "А-180925-1801")
    
    print(f"\nРезультат: {result}")

