"""
Компонент для копирования проектов
"""
import shutil
import logging
from pathlib import Path
from typing import Dict
from .base_component import BaseKompasComponent

class ProjectCopier(BaseKompasComponent):
    """Компонент для копирования проектов КОМПАС-3D"""
    
    def __init__(self):
        super().__init__()
    
    def copy_project(self, source_path: str, target_folder: str, project_name: str) -> Dict:
        """
        Копирование проекта
        
        Args:
            source_path: Путь к исходному проекту
            target_folder: Папка назначения
            project_name: Имя нового проекта
            
        Returns:
            Dict с результатами копирования
        """
        result = {
            'success': False,
            'copied_path': None,
            'error': None
        }
        
        try:
            self.logger.info("НАЧАЛО КОПИРОВАНИЯ ПРОЕКТА")
            self.logger.info("=" * 40)
            
            source_path_obj = Path(source_path)
            target_path = Path(target_folder) / project_name
            
            # Проверяем исходный путь
            if not source_path_obj.exists():
                result['error'] = f"Исходная папка не найдена: {source_path}"
                return result
            
            if not source_path_obj.is_dir():
                result['error'] = f"Исходный путь не является папкой: {source_path}"
                return result
            
            # Проверяем целевую папку
            target_folder_obj = Path(target_folder)
            if not target_folder_obj.exists():
                self.logger.info(f"Создание целевой папки: {target_folder}")
                target_folder_obj.mkdir(parents=True, exist_ok=True)
            
            # Удаляем существующий проект если есть
            if target_path.exists():
                self.logger.info(f"Удаление существующего проекта: {target_path}")
                shutil.rmtree(target_path)
            
            # Копируем проект с фильтрацией
            self.logger.info(f"Копирование из {source_path} в {target_path}")
            
            # ОПТИМИЗАЦИЯ: Игнорируем временные файлы!
            def ignore_files(directory, files):
                """Фильтр для исключения ненужных файлов"""
                ignore_list = []
                for f in files:
                    # Игнорируем:
                    if f.endswith('.bak'):  # Резервные копии КОМПАС
                        ignore_list.append(f)
                    elif f.endswith('~'):  # Временные файлы
                        ignore_list.append(f)
                    elif f.startswith('~'):  # Временные файлы Excel
                        ignore_list.append(f)
                    elif f.endswith('.tmp'):  # Временные файлы
                        ignore_list.append(f)
                    elif f == 'Thumbs.db':  # Windows кеш
                        ignore_list.append(f)
                    elif f == '.DS_Store':  # macOS кеш
                        ignore_list.append(f)
                
                if ignore_list:
                    self.logger.info(f"  Пропущено файлов: {len(ignore_list)}")
                
                return ignore_list
            
            shutil.copytree(source_path, target_path, ignore=ignore_files)
            
            result['success'] = True
            result['copied_path'] = str(target_path)
            self.logger.info(f"Проект успешно скопирован: {target_path}")
            
            return result
            
        except Exception as e:
            error_msg = f"Ошибка копирования проекта: {e}"
            result['error'] = error_msg
            self.logger.error(error_msg)
            return result
    
    def rename_main_assembly(self, project_path: str, project_name: str) -> Dict:
        """
        Переименование главной сборки
        
        Args:
            project_path: Путь к проекту
            project_name: Имя проекта
            
        Returns:
            Dict с результатами переименования
        """
        result = {
            'success': False,
            'renamed_files': [],
            'error': None
        }
        
        try:
            self.logger.info("ПЕРЕИМЕНОВАНИЕ ГЛАВНОЙ СБОРКИ")
            self.logger.info("=" * 35)
            
            project_path_obj = Path(project_path)
            
            if not project_path_obj.exists():
                result['error'] = f"Папка проекта не найдена: {project_path}"
                return result
            
            # Ищем файлы сборки
            assembly_files = list(project_path_obj.glob("*.a3d"))
            if not assembly_files:
                result['error'] = "Файлы сборки (.a3d) не найдены"
                return result
            
            # Переименовываем главную сборку
            main_assembly = assembly_files[0]  # Берем первый найденный
            new_assembly_name = f"{project_name}.a3d"
            new_assembly_path = main_assembly.parent / new_assembly_name
            
            self.logger.info(f"Переименование: {main_assembly.name} -> {new_assembly_name}")
            main_assembly.rename(new_assembly_path)
            
            result['renamed_files'].append(str(new_assembly_path))
            result['success'] = True
            self.logger.info(f"Сборка переименована: {new_assembly_name}")
            
            return result
            
        except Exception as e:
            error_msg = f"Ошибка переименования сборки: {e}"
            result['error'] = error_msg
            self.logger.error(error_msg)
            return result
    
    def get_project_info(self, project_path: str) -> Dict:
        """
        Получение информации о проекте
        
        Args:
            project_path: Путь к проекту
            
        Returns:
            Dict с информацией о проекте
        """
        info = {
            'project_path': project_path,
            'assembly_files': [],
            'drawing_files': [],
            'part_files': [],
            'other_files': [],
            'total_files': 0
        }
        
        try:
            project_path_obj = Path(project_path)
            
            if not project_path_obj.exists():
                return info
            
            # Подсчет файлов по типам
            for file_path in project_path_obj.rglob("*"):
                if file_path.is_file():
                    suffix = file_path.suffix.lower()
                    
                    if suffix == '.a3d':
                        info['assembly_files'].append(str(file_path))
                    elif suffix == '.cdw':
                        info['drawing_files'].append(str(file_path))
                    elif suffix == '.m3d':
                        info['part_files'].append(str(file_path))
                    else:
                        info['other_files'].append(str(file_path))
                    
                    info['total_files'] += 1
            
            self.logger.info(f"Информация о проекте:")
            self.logger.info(f"  Сборки: {len(info['assembly_files'])}")
            self.logger.info(f"  Чертежи: {len(info['drawing_files'])}")
            self.logger.info(f"  Детали: {len(info['part_files'])}")
            self.logger.info(f"  Всего файлов: {info['total_files']}")
            
            return info
            
        except Exception as e:
            self.logger.error(f"Ошибка получения информации о проекте: {e}")
            return info
