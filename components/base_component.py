"""
Базовый компонент для работы с КОМПАС-3D
"""
import logging
import pythoncom
import sys
from typing import Dict, Optional
from win32com.client import Dispatch

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

class BaseKompasComponent:
    """Базовый класс для всех компонентов КОМПАС-3D"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.application = None
        self.connected = False
    
    def connect_to_kompas(self) -> bool:
        """Подключение к КОМПАС-3D"""
        try:
            if self.connected:
                return True
                
            pythoncom.CoInitialize()
            self.logger.info("Подключение к КОМПАС-3D v7...")
            self.application = Dispatch("Kompas.Application.7")
            self.application.Visible = True
            self.logger.info("Подключение к КОМПАС-3D успешно")
            self.connected = True
            return True
        except Exception as e:
            self.logger.error(f"Ошибка подключения к КОМПАС-3D: {e}")
            self.connected = False
            return False
    
    def disconnect_from_kompas(self):
        """Отключение от КОМПАС-3D"""
        try:
            if self.application:
                self.application = None
            if self.connected:
                pythoncom.CoUninitialize()
                self.connected = False
                self.logger.info("Отключение от КОМПАС-3D")
        except Exception as e:
            self.logger.error(f"Ошибка отключения от КОМПАС-3D: {e}")
    
    def is_connected(self) -> bool:
        """Проверка подключения"""
        return self.connected and self.application is not None
    
    def get_active_document(self):
        """Получение активного документа"""
        if not self.is_connected():
            return None
        try:
            return self.application.ActiveDocument
        except Exception as e:
            self.logger.error(f"Ошибка получения активного документа: {e}")
            return None
    
    def close_all_documents(self):
        """Закрытие всех открытых документов"""
        try:
            if not self.is_connected():
                return False
                
            documents = self.application.Documents
            doc_count = documents.Count
            
            for i in range(doc_count - 1, -1, -1):
                try:
                    doc = documents.Item(i)
                    if doc:
                        self.logger.info(f"Закрытие документа: {doc.Name}")
                        doc.Close(False)
                except Exception as e:
                    self.logger.warning(f"Ошибка закрытия документа {i}: {e}")
            
            import time
            time.sleep(1)
            self.logger.info("Все документы закрыты")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка закрытия документов: {e}")
            return False
    
    def open_document(self, file_path: str) -> bool:
        """Открытие документа"""
        try:
            if not self.is_connected():
                return False
                
            from pathlib import Path
            if not Path(file_path).exists():
                self.logger.error(f"Файл не найден: {file_path}")
                return False
            
            doc = self.application.Documents.Open(file_path, False)
            if not doc:
                self.logger.error("Не удалось открыть документ")
                return False
            
            self.application.ActiveDocument = doc
            self.logger.info(f"Документ открыт: {doc.Name}")
            
            import time
            time.sleep(1)
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка открытия документа: {e}")
            return False
    
    def close_document(self, save=False):
        """Закрытие активного документа
        
        Args:
            save: Сохранить изменения перед закрытием (по умолчанию False)
        """
        try:
            if not self.is_connected():
                return False
                
            active_doc = self.get_active_document()
            if active_doc:
                doc_name = active_doc.Name
                active_doc.Close(save)
                self.logger.info(f"Документ закрыт: {doc_name} (save={save})")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Ошибка закрытия документа: {e}")
            return False
