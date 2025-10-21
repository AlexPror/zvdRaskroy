#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Продвинутый компонент для расчета площадей разверток с учетом количества деталей
"""

import time
import pythoncom
from pathlib import Path
from typing import Dict, List
from win32com.client import Dispatch, gencache
from .base_component import BaseKompasComponent

# Опциональный импорт менеджера массивов
try:
    from .array_quantity_manager import ArrayQuantityManager
except ImportError:
    ArrayQuantityManager = None

class AdvancedAreaCalculator(BaseKompasComponent):
    """Расчет площадей разверток с учетом количества деталей в сборке"""
    
    def __init__(self, use_array_manager: bool = True):
        super().__init__()
        self.kompas6_constants_3d = gencache.EnsureModule(
            "{2CAF168C-7961-4B90-9DA2-701419BEEFE3}", 0, 1, 0
        ).constants
        self.array_manager = ArrayQuantityManager() if (use_array_manager and ArrayQuantityManager) else None
    
    def calculate_total_areas(self, project_path: str, order_number: str = None) -> Dict:
        """
        Полный расчет площадей с учетом количества деталей
        
        Args:
            project_path: Путь к проекту
            
        Returns:
            Dict с результатами
        """
        result = {
            'success': False,
            'total_area': 0,
            'total_area_with_quantity': 0,
            'unfoldings': [],
            'errors': []
        }
        
        pythoncom.CoInitialize()
        
        try:
            self.logger.info("РАСЧЕТ ПЛОЩАДЕЙ С УЧЕТОМ КОЛИЧЕСТВА")
            self.logger.info("=" * 60)
            
            if not self.connect_to_kompas():
                result['errors'].append("Не удалось подключиться к КОМПАС-3D")
                return result
            
            # 1. Получаем количество деталей из сборки
            part_quantities = self._get_part_quantities(project_path)
            
            if not part_quantities:
                result['errors'].append("Не удалось получить количество деталей из сборки")
                return result
            
            # 2. Рассчитываем площади разверток
            area_data = self._calculate_unfolding_areas(project_path, order_number)
            
            if not area_data:
                result['errors'].append("Не удалось рассчитать площади")
                return result
            
            # 3. Применяем менеджер массивов (если включен)
            if self.array_manager:
                # Извлекаем L1 из имени проекта
                L1 = None
                try:
                    project_name = Path(project_path).name
                    parts = project_name.split('.')
                    if len(parts) >= 4:  # ZVD.LITE.H.B1.L1
                        L1 = int(parts[4])
                except:
                    pass
                
                self.logger.info(f"\n⚙️  Применение правил массивов (L1={L1})...")
                part_quantities = self.array_manager.apply_to_quantities(
                    part_quantities, L1=L1, project_name=Path(project_path).name
                )
            
            # 4. Сопоставляем развертки с деталями
            self.logger.info(f"\n{'='*60}")
            self.logger.info("СОПОСТАВЛЕНИЕ И РАСЧЕТ:")
            self.logger.info(f"{'='*60}\n")
            
            for unfolding in area_data:
                name = unfolding['name']
                area = unfolding['area_m2']
                
                # Находим количество по имени (упрощенное сопоставление)
                quantity = self._match_part_quantity(name, part_quantities)
                
                total_area = area * quantity
                
                self.logger.info(f"{name}")
                self.logger.info(f"  Площадь 1 шт: {area:.4f} м²")
                self.logger.info(f"  Количество: {quantity} шт")
                self.logger.info(f"  Итого: {total_area:.4f} м²")
                self.logger.info("")
                
                unfolding['quantity'] = quantity
                unfolding['total_area_m2'] = total_area
                
                result['unfoldings'].append(unfolding)
                result['total_area'] += area
                result['total_area_with_quantity'] += total_area
            
            result['success'] = True
            
            self.logger.info(f"{'='*60}")
            self.logger.info("ИТОГО:")
            self.logger.info(f"  Уникальных деталей: {len(result['unfoldings'])}")
            self.logger.info(f"  Площадь (без количества): {result['total_area']:.4f} м²")
            self.logger.info(f"  ОБЩАЯ ПЛОЩАДЬ: {result['total_area_with_quantity']:.4f} м²")
            self.logger.info(f"{'='*60}")
            
        except Exception as e:
            error_msg = f"Ошибка расчета: {e}"
            result['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        finally:
            pythoncom.CoUninitialize()
        
        return result
    
    def _get_part_quantities(self, project_path: str) -> Dict[str, int]:
        """
        Получение количества деталей из сборки
        
        Returns:
            Dict с именами деталей и их количеством
        """
        quantities = {}
        
        try:
            project_path_obj = Path(project_path)
            assembly_files = list(project_path_obj.glob("*.a3d"))
            
            if not assembly_files:
                self.logger.warning("Файл сборки не найден")
                return quantities
            
            assembly_file = assembly_files[0]
            self.logger.info(f"Анализ сборки: {assembly_file.name}\n")
            
            # Открываем сборку
            if not self.open_document(str(assembly_file)):
                self.logger.error("Не удалось открыть сборку")
                return quantities
            
            active_doc = self.get_active_document()
            if not active_doc:
                return quantities
            
            # Используем API5 для получения 3D документа
            api5 = Dispatch("Kompas.Application.5")
            iDocument3D = api5.ActiveDocument3D  # Без скобок - это свойство, не метод
            
            if not iDocument3D:
                self.logger.error("Не удалось получить 3D документ")
                return quantities
            
            # pTop_Part = -1 (константа для главной детали сборки)
            iPart = iDocument3D.GetPart(-1)
            if not iPart:
                self.logger.error("Не удалось получить TopPart")
                return quantities
            
            # 🔍 ПРОВЕРКА ПЕРЕМЕННЫХ МАССИВОВ
            array_variables = {}
            var_collection = iPart.VariableCollection()
            if var_collection:
                self.logger.info("🔍 Поиск переменных массивов...")
                
                # Расширенный список ключевых слов для поиска
                keywords = ['количество', 'кол', 'chislo', 'число', 'count', 'qty', 
                           'распорок', 'rasporok', 'array', 'массив', 'shag']
                
                found_any = False
                for i in range(300):  # Увеличили диапазон
                    try:
                        var = var_collection.GetByIndex(i)
                        if var:
                            name = var.name if hasattr(var, 'name') else ''
                            name_lower = name.lower()
                            
                            # Проверяем по ключевым словам ИЛИ если имя содержит цифры и связано с распорками
                            if any(keyword in name_lower for keyword in keywords):
                                try:
                                    value = int(var.value) if hasattr(var, 'value') else 0
                                    array_variables[name] = value
                                    self.logger.info(f"  ✓ {name} = {value}")
                                    found_any = True
                                except:
                                    pass
                    except:
                        break
                
                if not found_any:
                    self.logger.info("  (переменные массивов не найдены)")
                    # Пробуем найти переменную chisloRasporok напрямую
                    try:
                        var = var_collection.GetByName("chisloRasporok")
                        if var:
                            value = int(var.value) if hasattr(var, 'value') else 0
                            array_variables["chisloRasporok"] = value
                            self.logger.info(f"  ✓ chisloRasporok = {value} (найдена напрямую)")
                            found_any = True
                    except:
                        pass
                    
                    # Если не найдена - рассчитываем по формуле от L1
                    if not found_any:
                        try:
                            var_L1 = var_collection.GetByName("L1")
                            if var_L1:
                                L1 = float(var_L1.value) if hasattr(var_L1, 'value') else 0
                                
                                # Формула: if(L1<1500; 2; if(L1<2000; 3; if(L1<=2400; 4; 5)))
                                if L1 < 1500:
                                    rasporok_qty = 2
                                elif L1 < 2000:
                                    rasporok_qty = 3
                                elif L1 <= 2400:
                                    rasporok_qty = 4
                                else:
                                    rasporok_qty = 5
                                
                                array_variables["chisloRasporok"] = rasporok_qty
                                self.logger.info(f"  ✓ chisloRasporok = {rasporok_qty} (рассчитано по L1={L1:.0f})")
                                found_any = True
                        except:
                            pass
                
                self.logger.info("")
            
            # Подсчет деталей по именам
            part_name_count = {}
            
            parts_count = 0
            for i in range(100):
                try:
                    part = iPart.GetPart(i)
                    if part:
                        parts_count = i + 1
                    else:
                        break
                except:
                    break
            
            self.logger.info(f"Найдено деталей в сборке: {parts_count}\n")
            
            for i in range(parts_count):
                try:
                    part = iPart.GetPart(i)
                    if part:
                        # Получаем имя детали
                        part_name = part.name.strip()
                        
                        # Фильтруем служебные детали
                        marking = part.marking.strip()
                        if not marking or marking.startswith('-'):
                            continue
                        
                        # Считаем количество
                        if part_name in part_name_count:
                            part_name_count[part_name] += 1
                        else:
                            part_name_count[part_name] = 1
                
                except Exception as e:
                    self.logger.warning(f"Ошибка обработки детали {i}: {e}")
            
            # Выводим результат
            self.logger.info("Количество деталей:")
            for name, count in sorted(part_name_count.items()):
                # Применяем переменные массивов
                final_count = count
                
                if array_variables:
                    for var_name, var_value in array_variables.items():
                        # Сопоставляем переменную с деталью
                        if any(keyword in name.lower() for keyword in ['распорк', 'rasporok']) and \
                           any(keyword in var_name.lower() for keyword in ['распорок', 'rasporok']):
                            final_count = var_value
                            self.logger.info(f"  {name}: {count} шт → {final_count} шт (из {var_name})")
                            break
                
                if final_count == count:
                    self.logger.info(f"  {name}: {count} шт")
                
                quantities[name] = final_count
            
            # Закрываем сборку
            self.close_document(save=False)
            time.sleep(0.5)
            
        except Exception as e:
            self.logger.error(f"Ошибка получения количества: {e}")
        
        return quantities
    
    def _calculate_unfolding_areas(self, project_path: str, order_number: str = None) -> List[Dict]:
        """Расчет площадей разверток"""
        unfoldings = []
        
        try:
            project_path_obj = Path(project_path)
            all_drawings = list(project_path_obj.glob("*.cdw"))
            unfolding_drawings = [f for f in all_drawings 
                                 if "развертка" in f.name.lower()]
            
            # Получаем список деталей для сопоставления
            part_files = list(project_path_obj.glob("*.m3d"))
            
            self.logger.info(f"\nНайдено чертежей разверток: {len(unfolding_drawings)}\n")
            
            api5_obj = Dispatch("Kompas.Application.5")
            api7_obj = Dispatch("Kompas.Application.7")
            
            for drawing_file in unfolding_drawings:
                try:
                    # Открываем чертеж
                    doc = api7_obj.Documents.Open(str(drawing_file), False, True)
                    time.sleep(1.5)
                    
                    # Получаем 2D документ
                    doc2d = api5_obj.ActiveDocument2D
                    
                    if not doc2d:
                        api7_obj.ActiveDocument.Close(False)
                        continue
                    
                    # Экспортируем во временный DXF
                    import tempfile
                    temp_dxf = tempfile.mktemp(suffix='.dxf')
                    
                    doc2d.ksSaveToDXF(temp_dxf)
                    time.sleep(1)
                    
                    # Читаем габариты
                    width, height = self._get_dimensions_from_dxf(temp_dxf)
                    
                    # Удаляем временный файл
                    Path(temp_dxf).unlink(missing_ok=True)
                    
                    if width and height:
                        area = width * height / 1_000_000  # мм² → м²
                        
                        # Получаем правильное имя из соответствующего .m3d файла
                        display_name = self._get_proper_name_from_parts(drawing_file.stem, part_files)
                        
                        # Если в имени нет номера заказа, но он передан - добавляем
                        if order_number and '(' not in display_name:
                            display_name = f"{display_name} ({order_number})"
                        
                        unfoldings.append({
                            'name': display_name,
                            'width': width,
                            'height': height,
                            'area_m2': area
                        })
                    
                    # Закрываем чертеж
                    try:
                        if api7_obj.ActiveDocument:
                            api7_obj.ActiveDocument.Close(False)
                        time.sleep(0.5)
                    except:
                        pass
                    
                except Exception as e:
                    self.logger.warning(f"Ошибка {drawing_file.name}: {e}")
                    try:
                        if api7_obj.ActiveDocument:
                            api7_obj.ActiveDocument.Close(False)
                    except:
                        pass
            
        except Exception as e:
            self.logger.error(f"Ошибка расчета площадей: {e}")
        
        return unfoldings
    
    def _get_proper_name_from_parts(self, drawing_stem: str, part_files: List[Path]) -> str:
        """
        Получает правильное имя детали из .m3d файла вместо имени чертежа развертки
        
        Args:
            drawing_stem: Имя файла чертежа без расширения (например, "Развертка стенки")
            part_files: Список файлов деталей .m3d
            
        Returns:
            Правильное имя детали с номером и номером заказа
        """
        # Убираем слово "развертка" для поиска
        clean_name = drawing_stem.lower().replace("развертка", "").strip(" -")
        clean_name = ' '.join(clean_name.split())
        
        # Маппинг аналогично dxf_renamer.py
        mapping = [
            ("стенка торцевая", "стенка торцевая"),
            ("стенки торцевой", "стенка торцевая"),
            ("корпус короба", "корпус короба"),
            ("корпуса короба", "корпус короба"),
            ("крышка декоративная", "крышка декоративная"),
            ("крышки декоративной", "крышка декоративная"),
            ("распорки", "распорка"),
            ("распорка", "распорка"),
            ("стенки", "стенка"),
            ("стенка", "стенка"),
        ]
        
        # Применяем маппинг
        for dxf_key, part_key in mapping:
            dxf_key_words = set(dxf_key.split())
            clean_words = set(clean_name.split())
            
            if dxf_key_words.issubset(clean_words):
                clean_name = part_key
                break
        
        # Ищем соответствующую деталь
        candidates = []
        
        for part_file in part_files:
            # Пропускаем специальные детали
            if any(skip in part_file.name.lower() for skip in ["накладка", "теплообменник"]):
                continue
            
            part_clean = part_file.stem.lower()
            
            # Убираем номер из имени детали
            if " - " in part_clean:
                part_name_only = part_clean.split(" - ", 1)[1]
            else:
                part_name_only = part_clean
            
            # Убираем номер заказа в скобках для сравнения
            if "(" in part_name_only:
                part_name_only = part_name_only.split("(")[0].strip()
            
            # Сравниваем по ключевым словам
            clean_words = set([w for w in clean_name.split() if len(w) > 3])
            part_words = set([w for w in part_name_only.split() if len(w) > 3])
            
            # Точное совпадение или подмножество
            exact_match = (clean_words == part_words)
            subset_match = (clean_words and clean_words.issubset(part_words))
            
            if exact_match or subset_match:
                priority = 1 if exact_match else 2
                candidates.append((priority, part_file.stem))
        
        # Выбираем лучшего кандидата
        if candidates:
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]
        
        # Если не нашли - возвращаем оригинальное имя
        return drawing_stem
    
    def _get_dimensions_from_dxf(self, dxf_path: str) -> tuple:
        """Извлечение габаритов из DXF файла"""
        try:
            import ezdxf
            
            doc = ezdxf.readfile(dxf_path)
            msp = doc.modelspace()
            
            # Находим габариты всех объектов
            min_x = min_y = float('inf')
            max_x = max_y = float('-inf')
            
            for entity in msp:
                try:
                    if hasattr(entity, 'dxf'):
                        if hasattr(entity.dxf, 'start') and hasattr(entity.dxf, 'end'):
                            # Линия
                            min_x = min(min_x, entity.dxf.start.x, entity.dxf.end.x)
                            max_x = max(max_x, entity.dxf.start.x, entity.dxf.end.x)
                            min_y = min(min_y, entity.dxf.start.y, entity.dxf.end.y)
                            max_y = max(max_y, entity.dxf.start.y, entity.dxf.end.y)
                        elif hasattr(entity.dxf, 'center'):
                            # Окружность/дуга
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
            return (None, None)
    
    def _match_part_quantity(self, unfolding_name: str, quantities: Dict[str, int]) -> int:
        """
        Сопоставление развертки с деталью для определения количества
        
        Args:
            unfolding_name: Имя чертежа развертки (например, "Развертка корпуса")
            quantities: Словарь с количеством деталей
            
        Returns:
            Количество деталей
        """
        # Очищаем имя развертки от лишних слов и пробелов
        clean_name = unfolding_name.lower().replace("развертка", "").strip()
        clean_name = ' '.join(clean_name.split())  # Убираем лишние пробелы
        
        # Ищем точное совпадение в деталях
        for detail_name, count in quantities.items():
            detail_lower = detail_name.lower().strip()
            detail_lower = ' '.join(detail_lower.split())  # Убираем лишние пробелы
            
            # Прямое совпадение (с учетом различных вариантов)
            if clean_name == detail_lower:
                return count
            
            # Проверяем частичное вхождение
            if clean_name in detail_lower or detail_lower in clean_name:
                # Дополнительная проверка: если это стенка торцевая vs стенка
                if 'торцевая' in clean_name and 'торцевая' not in detail_lower:
                    continue
                if 'торцевая' not in clean_name and 'торцевая' in detail_lower:
                    continue
                return count
        
        # Поиск по ключевым словам с учетом падежей
        # Используем корни слов для сопоставления
        keywords_priority = [
            # (паттерн в развертке, [паттерны в названии детали])
            ('корпус', ['корпус']),  # корпуса, корпусу и тд
            ('крышк', ['крышк']),  # крышка, крышки и тд
            ('распорк', ['распорк']),  # распорка, распорки и тд
            ('торцев', ['торцев']),  # торцевая, торцевой и тд (ПЕРВЫМ!)
            ('стенк', ['стенк']),  # стенка, стенки и тд
        ]
        
        for key, keywords in keywords_priority:
            if key in clean_name:
                for detail_name, count in quantities.items():
                    detail_lower = detail_name.lower()
                    # Специальная проверка для торцевой стенки
                    if key == 'торцев':
                        if 'торцев' in detail_lower:
                            return count
                    elif key == 'стенк':
                        # Для стенки проверяем, что это НЕ торцевая
                        if 'стенк' in detail_lower and 'торцев' not in detail_lower and 'торцев' not in clean_name:
                            return count
                    else:
                        # Для остальных - простая проверка
                        for keyword in keywords:
                            if keyword in detail_lower:
                                return count
        
        # По умолчанию - 1 шт
        self.logger.warning(f"  ВНИМАНИЕ: Количество для '{unfolding_name}' не найдено, принято 1 шт")
        return 1

