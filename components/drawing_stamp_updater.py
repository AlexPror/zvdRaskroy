"""
Компонент для обновления штампа чертежа в КОМПАС-3D

Функции:
1. Обновление обозначения (шифра) в штампе через флаги свойств документа
2. Изменение текста в технических требованиях (строка "Заказ:")
"""

import pythoncom
from win32com.client import Dispatch, gencache
import time
import logging
from pathlib import Path
from typing import Dict, Optional


class DrawingStampUpdater:
    """Обновление штампа и тех. требований чертежа"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api5 = None
        self.api7 = None
        self.kompas_constants = None
    
    def connect_kompas(self):
        """Подключение к КОМПАС-3D"""
        try:
            pythoncom.CoInitialize()
            
            self.api5 = Dispatch("Kompas.Application.5")
            self.api5.Visible = True
            
            self.api7 = Dispatch("Kompas.Application.7")
            
            # Константы
            self.kompas_constants = gencache.EnsureModule(
                "{2CAF168C-7961-4B90-9DA2-701419BEEFE3}", 0, 1, 0
            ).constants
            
            self.logger.info("✓ Подключение к КОМПАС-3D v7")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка подключения к КОМПАС-3D: {e}")
            return False
    
    def disconnect_kompas(self):
        """Отключение от КОМПАС-3D"""
        try:
            pythoncom.CoUninitialize()
        except:
            pass
    
    def update_drawing_designation(self, drawing_path: str, new_designation: str) -> Dict:
        """
        Обновление обозначения (шифра) в штампе чертежа
        
        Метод: Устанавливаем флаг "Обозначение" в свойствах документа,
        чтобы штамп автоматически подтягивал значение из свойств.
        
        Args:
            drawing_path: Путь к файлу чертежа (.cdw)
            new_designation: Новое обозначение (например, "ZVD.LITE.90.260.003")
        
        Returns:
            dict: {'success': bool, 'old_designation': str, 'new_designation': str}
        """
        result = {
            'success': False,
            'old_designation': '',
            'new_designation': new_designation,
            'error': None
        }
        
        if not self.connect_kompas():
            result['error'] = "Не удалось подключиться к КОМПАС-3D"
            return result
        
        try:
            self.logger.info(f"Открытие чертежа: {Path(drawing_path).name}")
            
            # Открываем чертеж
            doc = self.api7.Documents.Open(drawing_path, False, True)
            if not doc:
                result['error'] = "Не удалось открыть чертеж"
                return result
            
            time.sleep(1)
            
            # Получаем интерфейс ksDocument2D (API5)
            iDocument2D = self.api5.ActiveDocument2D
            if not iDocument2D:
                result['error'] = "Не удалось получить интерфейс 2D документа"
                doc.Close(False)
                return result
            
            # Получаем параметры документа (ksDocumentParam)
            doc_param = iDocument2D.GetDocumentParam()
            if not doc_param:
                result['error'] = "Не удалось получить параметры документа"
                doc.Close(False)
                return result
            
            # Сохраняем старое обозначение
            result['old_designation'] = doc_param.marking if hasattr(doc_param, 'marking') else ''
            
            # КРИТИЧНО: Устанавливаем новое обозначение
            doc_param.marking = new_designation
            
            # КРИТИЧНО: Устанавливаем флаг "Обозначение из свойств"
            # Это заставит штамп обновиться автоматически!
            if hasattr(doc_param, 'markingFromSource'):
                doc_param.markingFromSource = True
                self.logger.info("  ✓ Флаг 'Обозначение из источника' установлен")
            
            # Применяем изменения
            iDocument2D.SetDocumentParam(doc_param)
            
            # Rebuild чертежа (обновление штампа)
            iDocument2D.ksRebuildDocument()
            time.sleep(0.5)
            
            # Сохраняем
            doc.Save()
            time.sleep(0.5)
            
            self.logger.info(f"  ✓ Обозначение обновлено: '{result['old_designation']}' → '{new_designation}'")
            
            # Закрываем
            doc.Close(True)
            
            result['success'] = True
            
        except Exception as e:
            self.logger.error(f"Ошибка обновления обозначения: {e}")
            result['error'] = str(e)
            import traceback
            self.logger.error(traceback.format_exc())
        
        finally:
            self.disconnect_kompas()
        
        return result
    
    def update_technical_requirements(self, drawing_path: str, order_number: str) -> Dict:
        """
        Обновление строки "Заказ:" в технических требованиях чертежа
        
        Args:
            drawing_path: Путь к файлу чертежа (.cdw)
            order_number: Новый номер заказа
        
        Returns:
            dict: {'success': bool, 'old_text': str, 'new_text': str}
        """
        result = {
            'success': False,
            'old_text': '',
            'new_text': f'Заказ: "{order_number}"',
            'error': None
        }
        
        if not self.connect_kompas():
            result['error'] = "Не удалось подключиться к КОМПАС-3D"
            return result
        
        try:
            self.logger.info(f"Открытие чертежа: {Path(drawing_path).name}")
            
            # Открываем чертеж
            doc = self.api7.Documents.Open(drawing_path, False, True)
            if not doc:
                result['error'] = "Не удалось открыть чертеж"
                return result
            
            time.sleep(1)
            
            # Получаем интерфейс ksDocument2D (API5)
            iDocument2D = self.api5.ActiveDocument2D
            if not iDocument2D:
                result['error'] = "Не удалось получить интерфейс 2D документа"
                doc.Close(False)
                return result
            
            # МЕТОД 1: Через технические требования (ksTextLine)
            # Получаем спецификацию (там хранятся тех. требования)
            spec = iDocument2D.GetSpecification()
            if spec:
                # Ищем строку с "Заказ:"
                line_count = spec.ksGetTechReqColumnCount()
                self.logger.info(f"  Строк в тех. требованиях: {line_count}")
                
                for i in range(line_count):
                    line = spec.ksGetTechReqColumn(i)
                    if line and "Заказ:" in str(line):
                        result['old_text'] = str(line)
                        # Обновляем строку
                        spec.ksSetTechReqColumn(i, result['new_text'])
                        self.logger.info(f"  ✓ Строка обновлена: '{result['old_text']}' → '{result['new_text']}'")
                        break
            
            # МЕТОД 2: Если не нашли через спецификацию, ищем текстовый объект
            # (Этот метод сложнее, но надежнее для некоторых версий КОМПАС)
            if not result['old_text']:
                self.logger.warning("  ⚠ Не удалось найти через спецификацию, пробую через текстовые объекты...")
                # TODO: Реализовать поиск через DrawingContainer → TextItems
            
            # Rebuild и сохранение
            iDocument2D.ksRebuildDocument()
            time.sleep(0.5)
            doc.Save()
            time.sleep(0.5)
            
            # Закрываем
            doc.Close(True)
            
            result['success'] = True
            
        except Exception as e:
            self.logger.error(f"Ошибка обновления тех. требований: {e}")
            result['error'] = str(e)
            import traceback
            self.logger.error(traceback.format_exc())
        
        finally:
            self.disconnect_kompas()
        
        return result
    
    def update_all_drawings_in_project(self, project_path: str, h: int, b1: int, l1: int, 
                                       order_number: Optional[str] = None) -> Dict:
        """
        Обновление штампов во всех чертежах проекта
        ОПТИМИЗИРОВАНО: Открывает каждый чертеж только 1 раз!
        
        Args:
            project_path: Путь к папке проекта
            h, b1, l1: Параметры для формирования обозначения
            order_number: Номер заказа (опционально)
        
        Returns:
            dict: {'success': bool, 'updated_count': int, 'errors': list}
        """
        result = {
            'success': False,
            'updated_count': 0,
            'errors': []
        }
        
        if not self.connect_kompas():
            result['errors'].append("Не удалось подключиться к КОМПАС-3D")
            return result
        
        try:
            project_path = Path(project_path)
            
            # Находим все чертежи (кроме разверток)
            drawing_files = [
                f for f in project_path.glob("*.cdw")
                if "развертка" not in f.name.lower() and "разверт" not in f.name.lower()
            ]
            
            self.logger.info(f"\nНайдено чертежей: {len(drawing_files)}")
            
            # Формируем базовое обозначение
            short_name = f"ZVD.LITE.{h}.{b1}"
            
            for drawing_file in drawing_files:
                try:
                    # Определяем номер детали из имени файла
                    part_number = "001"
                    name_parts = drawing_file.stem.split(" - ")
                    if len(name_parts) > 0 and name_parts[0].strip().isdigit():
                        part_number = name_parts[0].strip()
                    
                    # Формируем полное обозначение
                    designation = f"{short_name}.{part_number}"
                    
                    self.logger.info(f"\n  Чертеж: {drawing_file.name}")
                    self.logger.info(f"  Обозначение: {designation}")
                    
                    # === ОТКРЫВАЕМ ЧЕРТЕЖ ОДИН РАЗ ===
                    doc = self.api7.Documents.Open(str(drawing_file), False, True)
                    if not doc:
                        result['errors'].append(f"{drawing_file.name}: Не удалось открыть")
                        continue
                    
                    time.sleep(1)
                    
                    iDocument2D = self.api5.ActiveDocument2D
                    if not iDocument2D:
                        result['errors'].append(f"{drawing_file.name}: Не удалось получить интерфейс 2D")
                        doc.Close(False)
                        continue
                    
                    # 1. Обновляем обозначение
                    doc_param = iDocument2D.GetDocumentParam()
                    if doc_param:
                        old_designation = doc_param.marking if hasattr(doc_param, 'marking') else ''
                        doc_param.marking = designation
                        
                        if hasattr(doc_param, 'markingFromSource'):
                            doc_param.markingFromSource = True
                        
                        iDocument2D.SetDocumentParam(doc_param)
                        self.logger.info(f"  ✓ Обозначение: '{old_designation}' → '{designation}'")
                    
                    # 2. Обновляем номер заказа (если указан)
                    if order_number:
                        spec = iDocument2D.GetSpecification()
                        if spec:
                            line_count = spec.ksGetTechReqColumnCount()
                            updated = False
                            
                            for i in range(line_count):
                                line = spec.ksGetTechReqColumn(i)
                                if line and "Заказ:" in str(line):
                                    new_text = f'Заказ: "{order_number}"'
                                    spec.ksSetTechReqColumn(i, new_text)
                                    self.logger.info(f"  ✓ Заказ: {order_number}")
                                    updated = True
                                    break
                            
                            if not updated:
                                self.logger.warning(f"  ⚠ Строка 'Заказ:' не найдена")
                    
                    # 3. Rebuild и сохранение
                    iDocument2D.ksRebuildDocument()
                    time.sleep(0.5)
                    doc.Save()
                    time.sleep(0.5)
                    
                    # 4. Закрываем
                    doc.Close(True)
                    
                    result['updated_count'] += 1
                    
                except Exception as e:
                    self.logger.error(f"Ошибка обработки {drawing_file.name}: {e}")
                    result['errors'].append(f"{drawing_file.name}: {str(e)}")
            
            result['success'] = result['updated_count'] > 0
            
        finally:
            self.disconnect_kompas()
        
        return result


if __name__ == "__main__":
    # Тестирование
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    
    updater = DrawingStampUpdater()
    
    # Тест 1: Обновление обозначения
    test_drawing = r"C:\Users\Vorob\Documents\ZVD GROUP\Параметризация\ZVD.LITE.90.260.1000\001 - Корпус короба.cdw"
    result = updater.update_drawing_designation(test_drawing, "ZVD.LITE.90.260.001")
    print(f"\nРезультат: {result}")

