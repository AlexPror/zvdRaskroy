"""
Projects Database для v3.0
База данных всех проектов для поиска подходящих деталей
"""

from pathlib import Path
from typing import List, Dict, Tuple, Optional
import json
import re
from datetime import datetime
import ezdxf


class ProjectsDatabase:
    """
    База данных проектов с индексацией по габаритам
    """
    
    def __init__(self, base_folder: Optional[str] = None):
        """
        Args:
            base_folder: Корневая папка с проектами (например: C:\Projects\)
        """
        self.base_folder = Path(base_folder) if base_folder else None
        self.projects = []
        self.index_by_dimensions = {}
        self.cache_file = Path("projects_database_cache.json")
    
    def scan_all_projects(self, base_folder: Optional[str] = None) -> int:
        """
        Сканировать все проекты в указанной папке
        
        Returns:
            Количество найденных проектов
        """
        if base_folder:
            self.base_folder = Path(base_folder)
        
        if not self.base_folder or not self.base_folder.exists():
            return 0
        
        print(f"🔍 Сканирование проектов в: {self.base_folder}")
        
        projects_found = 0
        
        # Рекурсивный поиск папок с проектами
        for folder in self.base_folder.rglob("*"):
            if folder.is_dir():
                # Проверить, это папка проекта?
                if self._is_project_folder(folder):
                    project_info = self._scan_project(folder)
                    if project_info:
                        self.projects.append(project_info)
                        self._index_project(project_info)
                        projects_found += 1
                        
                        if projects_found % 10 == 0:
                            print(f"  Найдено проектов: {projects_found}")
        
        print(f"✓ Всего проектов: {projects_found}")
        
        # Сохранить в кэш
        self.save_cache()
        
        return projects_found
    
    def _is_project_folder(self, folder: Path) -> bool:
        """
        Проверить, является ли папка проектом конвектора
        """
        folder_name = folder.name
        
        # Должно содержать цифры (габариты)
        if not any(char.isdigit() for char in folder_name):
            return False
        
        # Паттерны названий
        patterns = [
            r'ZVD[.\s]LITE[.\s]\d+[.\s]\d+[.\s]\d+',
            r'ZVD[.\s]TURBO[.\s]\d+[.\s]\d+[.\s]\d+',
            r'LITE[.\s]\d+[.\s]\d+[.\s]\d+',
            r'\d+[.\s]\d+[.\s]\d+',
        ]
        
        for pattern in patterns:
            if re.search(pattern, folder_name):
                # Проверить, есть ли DXF файлы внутри
                dxf_files = list(folder.rglob("*.dxf"))
                return len(dxf_files) > 0
        
        return False
    
    def _scan_project(self, folder: Path) -> Optional[Dict]:
        """
        Сканировать один проект
        """
        try:
            # Извлечь габариты из названия
            dimensions = self._extract_dimensions(folder.name)
            if not dimensions:
                return None
            
            # Найти все DXF файлы
            dxf_files = list(folder.rglob("*.dxf"))
            if not dxf_files:
                return None
            
            # Сканировать детали
            parts = []
            for dxf_file in dxf_files[:20]:  # максимум 20 файлов
                part_info = self._scan_dxf_file(dxf_file)
                if part_info:
                    parts.append(part_info)
            
            # Извлечь номер заказа
            order_match = re.search(r'([А-Я]-\d{6}-\d{4})', folder.name)
            order_number = order_match.group(1) if order_match else "unknown"
            
            return {
                "folder": str(folder),
                "folder_name": folder.name,
                "dimensions": dimensions,
                "order_number": order_number,
                "parts_count": len(parts),
                "parts": parts,
                "scanned_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"  ⚠ Ошибка сканирования {folder.name}: {e}")
            return None
    
    def _extract_dimensions(self, folder_name: str) -> Optional[Dict]:
        """
        Извлечь H, W, L из названия папки
        """
        # Найти все числа
        numbers = re.findall(r'\d+', folder_name)
        
        if len(numbers) < 3:
            return None
        
        # Первые 3 числа обычно H, W, L
        # Фильтр: разумные диапазоны
        candidates = []
        for num_str in numbers:
            num = int(num_str)
            if 100 <= num <= 5000:  # разумный диапазон для габаритов
                candidates.append(num)
        
        if len(candidates) >= 3:
            return {
                "H": candidates[0],
                "W": candidates[1],
                "L": candidates[2]
            }
        
        return None
    
    def _scan_dxf_file(self, dxf_path: Path) -> Optional[Dict]:
        """
        Сканировать один DXF файл
        """
        try:
            doc = ezdxf.readfile(str(dxf_path))
            modelspace = doc.modelspace()
            
            # Получить bounding box
            bbox = ezdxf.bbox.extents(modelspace, fast=True)
            if not bbox or not bbox.has_data:
                return None
            
            width = abs(bbox.extmax.x - bbox.extmin.x)
            height = abs(bbox.extmax.y - bbox.extmin.y)
            
            if width == 0 or height == 0:
                return None
            
            # Извлечь количество из названия
            quantity = self._extract_quantity(dxf_path.name)
            
            return {
                "filename": dxf_path.name,
                "width": round(width, 2),
                "height": round(height, 2),
                "area": round((width * height) / 1_000_000, 6),
                "quantity": quantity
            }
            
        except Exception as e:
            return None
    
    def _extract_quantity(self, filename: str) -> int:
        """
        Извлечь количество из названия файла
        """
        patterns = [
            r'(\d+)\s*шт',
            r'x\s*(\d+)',
            r'х\s*(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return 1
    
    def _index_project(self, project: Dict):
        """
        Индексировать проект по габаритам для быстрого поиска
        """
        dims = project['dimensions']
        H, W, L = dims['H'], dims['W'], dims['L']
        
        # Округлить до десятков для группировки
        H_group = (H // 10) * 10
        W_group = (W // 50) * 50
        
        key = f"H{H_group}_W{W_group}"
        
        if key not in self.index_by_dimensions:
            self.index_by_dimensions[key] = []
        
        self.index_by_dimensions[key].append(project)
    
    def find_projects_by_dimensions(self, H: int, W: int, 
                                   H_tolerance: float = 0.2,
                                   W_tolerance: float = 0.2) -> List[Dict]:
        """
        Найти проекты с похожими габаритами
        
        Args:
            H: Высота
            W: Ширина
            H_tolerance: Допуск по высоте (±20% по умолчанию)
            W_tolerance: Допуск по ширине (±20% по умолчанию)
        
        Returns:
            Список подходящих проектов
        """
        H_min = H * (1 - H_tolerance)
        H_max = H * (1 + H_tolerance)
        W_min = W * (1 - W_tolerance)
        W_max = W * (1 + W_tolerance)
        
        matching = []
        
        for project in self.projects:
            dims = project['dimensions']
            if (H_min <= dims['H'] <= H_max and 
                W_min <= dims['W'] <= W_max):
                matching.append(project)
        
        return matching
    
    def find_details_by_size(self, width_range: Tuple[float, float],
                            height_range: Tuple[float, float]) -> List[Dict]:
        """
        Найти детали определенного размера во всех проектах
        
        Returns:
            Список деталей с информацией о проекте
        """
        matching_details = []
        
        for project in self.projects:
            for part in project.get('parts', []):
                w = part['width']
                h = part['height']
                
                # Проверить, помещается ли в диапазон (с учетом поворота)
                if ((width_range[0] <= w <= width_range[1] and 
                     height_range[0] <= h <= height_range[1]) or
                    (width_range[0] <= h <= width_range[1] and 
                     height_range[0] <= w <= height_range[1])):
                    
                    matching_details.append({
                        "detail": part,
                        "project": {
                            "folder": project['folder'],
                            "dimensions": project['dimensions'],
                            "order": project['order_number']
                        }
                    })
        
        return matching_details
    
    def save_cache(self):
        """
        Сохранить базу данных в кэш
        """
        try:
            cache_data = {
                "scanned_at": datetime.now().isoformat(),
                "projects_count": len(self.projects),
                "projects": self.projects,
                "index": self.index_by_dimensions
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            print(f"✓ Кэш сохранен: {self.cache_file}")
            
        except Exception as e:
            print(f"⚠ Ошибка сохранения кэша: {e}")
    
    def load_cache(self) -> bool:
        """
        Загрузить базу данных из кэша
        
        Returns:
            True если успешно загружено
        """
        if not self.cache_file.exists():
            return False
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            self.projects = cache_data.get('projects', [])
            self.index_by_dimensions = cache_data.get('index', {})
            
            scanned_at = cache_data.get('scanned_at', '')
            projects_count = cache_data.get('projects_count', 0)
            
            print(f"✓ Кэш загружен: {projects_count} проектов (сканировано: {scanned_at})")
            return True
            
        except Exception as e:
            print(f"⚠ Ошибка загрузки кэша: {e}")
            return False
    
    def get_statistics(self) -> Dict:
        """
        Получить статистику базы данных
        """
        if not self.projects:
            return {"total": 0}
        
        total_parts = sum(p['parts_count'] for p in self.projects)
        
        # Распределение по H
        h_distribution = {}
        for p in self.projects:
            h = p['dimensions']['H']
            h_group = (h // 10) * 10
            h_distribution[h_group] = h_distribution.get(h_group, 0) + 1
        
        # Распределение по W
        w_distribution = {}
        for p in self.projects:
            w = p['dimensions']['W']
            w_group = (w // 50) * 50
            w_distribution[w_group] = w_distribution.get(w_group, 0) + 1
        
        return {
            "total_projects": len(self.projects),
            "total_parts": total_parts,
            "h_distribution": h_distribution,
            "w_distribution": w_distribution,
            "indexed_groups": len(self.index_by_dimensions)
        }


# Пример использования
if __name__ == "__main__":
    # Тест
    db = ProjectsDatabase()
    
    # Попробовать загрузить из кэша
    if db.load_cache():
        print("База данных загружена из кэша")
    else:
        print("Кэш не найден, нужно сканировать проекты")
        print("Используйте: db.scan_all_projects('C:\\Path\\To\\Projects')")
    
    # Статистика
    stats = db.get_statistics()
    print()
    print("СТАТИСТИКА БАЗЫ ДАННЫХ:")
    print(f"  Проектов: {stats['total_projects']}")
    print(f"  Деталей: {stats.get('total_parts', 0)}")
    print(f"  Групп в индексе: {stats.get('indexed_groups', 0)}")
    
    # Поиск примера
    if stats['total_projects'] > 0:
        print()
        print("ПРИМЕР ПОИСКА:")
        matching = db.find_projects_by_dimensions(H=150, W=200)
        print(f"  Проектов с H=150±20%, W=200±20%: {len(matching)}")

