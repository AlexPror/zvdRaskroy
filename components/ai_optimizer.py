"""
AI Optimizer для v3.0
Умные рекомендации по оптимизации раскроя
"""

from typing import Dict, List, Tuple, Optional
from pathlib import Path
import re


class ConveyorKnowledgeBase:
    """
    База знаний о типовой комплектации конвекторов
    """
    
    def __init__(self):
        self.typical_parts = {
            "корпус": {
                "max_single_length": 2400,
                "keywords": ["корпус", "короб"],
                "required": True
            },
            "стенка": {
                "quantity": 2,
                "keywords": ["стенка"],
                "exclude_keywords": ["торц"],
                "required": True
            },
            "стенка_торцевая": {
                "quantity": 2,
                "keywords": ["стенка", "торц"],
                "typical_height": 145,
                "required": True
            },
            "распорка": {
                "keywords": ["распорка", "бассейн"],
                "typical_height": 132,
                "required": True
            },
            "крышка": {
                "quantity": 1,
                "keywords": ["крышка", "декоративн"],
                "required": False
            },
            "соединительная_пластина": {
                "quantity": 1,
                "keywords": ["соединительн", "пластина"],
                "required": False
            }
        }
        
        # Типовые размеры деталей
        self.typical_sizes = {
            "стенка_торцевая": {
                "height": 145,
                "typical_widths": [110, 120, 150, 160, 180, 200, 250, 300, 360]
            },
            "распорка": {
                "height": 132,
                "typical_widths": [110, 120, 150, 160, 180, 200, 250, 300, 360]
            },
            "стенка": {
                "height": 42.5,
                "typical_widths": [110, 120, 150, 160, 180, 200, 250, 300, 360]
            }
        }
    
    def calculate_korpus_quantity(self, L: float) -> int:
        """Сколько корпусов нужно для заданной длины"""
        if L < 2400:
            return 1
        elif L < 4800:
            return 2  # составной из 2х частей
        else:
            return 3  # составной из 3х частей
    
    def calculate_rasporka_quantity(self, L: float) -> int:
        """Сколько распорок нужно для заданной длины"""
        if L < 2000:
            return 2
        elif L < 3000:
            return 3
        else:
            return 4
    
    def detect_part_type(self, filename: str) -> Optional[str]:
        """
        Определить тип детали по названию файла
        """
        filename_lower = filename.lower()
        
        for part_type, info in self.typical_parts.items():
            # Проверить ключевые слова
            has_keywords = all(kw in filename_lower for kw in info['keywords'])
            
            # Проверить исключающие слова
            if 'exclude_keywords' in info:
                has_exclude = any(kw in filename_lower for kw in info['exclude_keywords'])
                if has_exclude:
                    continue
            
            if has_keywords:
                return part_type
        
        return None


class AIOptimizer:
    """
    Умный оптимизатор с AI-рекомендациями
    """
    
    def __init__(self):
        self.knowledge_base = ConveyorKnowledgeBase()
        self.target_levels = {
            "good": (75, 85),      # ХОРОШО
            "excellent": (85, 95)  # ОТЛИЧНО
        }
    
    def analyze_project(self, files_data: List[Dict], nesting_result: Dict, 
                       project_dimensions: Dict) -> Dict:
        """
        Комплексный анализ текущего проекта
        
        Args:
            files_data: Список загруженных файлов с размерами
            nesting_result: Результат раскроя
            project_dimensions: Габариты проекта (H, W, L)
        
        Returns:
            Словарь с анализом и рекомендациями
        """
        # 1. Текущая утилизация
        current_util = nesting_result.get('utilization_percent', 0)
        
        # 2. Комплектность конвектора
        completeness = self._check_completeness(files_data, project_dimensions)
        
        # 3. Свободное место на листах
        free_spaces = self._calculate_free_spaces(nesting_result)
        
        # 4. Анализ оптимальности
        optimality_status = self._get_optimality_status(current_util)
        
        return {
            "current_utilization": current_util,
            "completeness": completeness,
            "free_spaces": free_spaces,
            "optimality_status": optimality_status,
            "project_dimensions": project_dimensions
        }
    
    def _check_completeness(self, files_data: List[Dict], 
                           project_dimensions: Dict) -> Dict:
        """
        Проверить комплектность конвектора
        """
        detected = {
            "корпус": 0,
            "стенка": 0,
            "стенка_торцевая": 0,
            "распорка": 0,
            "крышка": 0,
            "соединительная_пластина": 0
        }
        
        # Подсчитать количество каждого типа деталей
        for file_info in files_data:
            filename = file_info.get('filename', file_info.get('name', ''))
            quantity = file_info.get('quantity', 1)
            
            part_type = self.knowledge_base.detect_part_type(filename)
            if part_type and part_type in detected:
                detected[part_type] += quantity
        
        # Определить ожидаемое количество
        L = project_dimensions.get('L', 3000)
        
        expected = {
            "корпус": self.knowledge_base.calculate_korpus_quantity(L),
            "стенка": 2,
            "стенка_торцевая": 2,
            "распорка": self.knowledge_base.calculate_rasporka_quantity(L),
            "крышка": 1,
            "соединительная_пластина": 1
        }
        
        # Сравнить
        completeness_status = {}
        for part_type, expected_qty in expected.items():
            actual_qty = detected.get(part_type, 0)
            completeness_status[part_type] = {
                "expected": expected_qty,
                "actual": actual_qty,
                "missing": max(0, expected_qty - actual_qty),
                "extra": max(0, actual_qty - expected_qty),
                "status": "ok" if actual_qty >= expected_qty else "missing"
            }
        
        return completeness_status
    
    def _calculate_free_spaces(self, nesting_result: Dict) -> List[Dict]:
        """
        Рассчитать свободное место на листах
        """
        free_spaces = []
        
        sheets = nesting_result.get('sheets', [])
        for sheet_idx, sheet in enumerate(sheets):
            sheet_width = sheet.get('width', 2500)
            sheet_height = sheet.get('height', 1250)
            
            # Простой расчет: общая площадь - площадь деталей
            total_area = (sheet_width * sheet_height) / 1_000_000  # в м²
            parts_area = 0
            
            parts = sheet.get('parts', [])
            for part in parts:
                part_w = part.get('width', 0)
                part_h = part.get('height', 0)
                parts_area += (part_w * part_h) / 1_000_000
            
            free_area = total_area - parts_area
            
            # Найти наибольшую пустую область (упрощенно)
            # В реальности нужен более сложный алгоритм
            max_free_w = sheet_width
            max_free_h = free_area * 1_000_000 / sheet_width  # примерно
            
            free_spaces.append({
                "sheet_index": sheet_idx,
                "total_area_m2": total_area,
                "parts_area_m2": parts_area,
                "free_area_m2": free_area,
                "estimated_max_width": max_free_w,
                "estimated_max_height": max_free_h
            })
        
        return free_spaces
    
    def _get_optimality_status(self, utilization: float) -> str:
        """Определить статус оптимальности"""
        if utilization >= 95:
            return "magic"
        elif utilization >= 85:
            return "excellent"
        elif utilization >= 70:
            return "good"
        elif utilization >= 50:
            return "medium"
        else:
            return "bad"
    
    def generate_recommendations(self, analysis: Dict) -> Dict:
        """
        Генерация рекомендаций по оптимизации
        
        Returns:
            {
                "completeness_warnings": [...],
                "good_level": [...],
                "excellent_level": [...]
            }
        """
        recommendations = {
            "completeness_warnings": [],
            "good_level": [],
            "excellent_level": []
        }
        
        current_util = analysis['current_utilization']
        completeness = analysis['completeness']
        free_spaces = analysis['free_spaces']
        dimensions = analysis['project_dimensions']
        
        # 1. Проверка комплектности
        recommendations['completeness_warnings'] = self._generate_completeness_warnings(
            completeness
        )
        
        # 2. Рекомендации для уровня "ХОРОШО" (75-85%)
        if current_util < 75:
            recommendations['good_level'] = self._generate_level_recommendations(
                current_util=current_util,
                target_range=(75, 85),
                free_spaces=free_spaces,
                dimensions=dimensions,
                max_details=4
            )
        
        # 3. Рекомендации для уровня "ОТЛИЧНО" (85-95%)
        if current_util < 85:
            recommendations['excellent_level'] = self._generate_level_recommendations(
                current_util=current_util,
                target_range=(85, 95),
                free_spaces=free_spaces,
                dimensions=dimensions,
                max_details=10
            )
        
        return recommendations
    
    def _generate_completeness_warnings(self, completeness: Dict) -> List[Dict]:
        """
        Генерация предупреждений о некомплектности
        """
        warnings = []
        
        for part_type, status in completeness.items():
            if status['status'] == 'missing' and status['missing'] > 0:
                part_info = self.knowledge_base.typical_parts.get(part_type, {})
                if part_info.get('required', False):
                    warnings.append({
                        "part_type": part_type,
                        "missing_quantity": status['missing'],
                        "expected": status['expected'],
                        "actual": status['actual'],
                        "severity": "warning" if part_type in ["крышка"] else "error"
                    })
        
        return warnings
    
    def _generate_level_recommendations(self, current_util: float, 
                                       target_range: Tuple[float, float],
                                       free_spaces: List[Dict],
                                       dimensions: Dict,
                                       max_details: int) -> List[Dict]:
        """
        Генерация рекомендаций для достижения целевого уровня
        """
        recommendations = []
        
        # Целевая утилизация (середина диапазона)
        target_util = (target_range[0] + target_range[1]) / 2
        
        # Сколько нужно добавить площади
        total_sheet_area = sum(space['total_area_m2'] for space in free_spaces)
        current_parts_area = total_sheet_area * (current_util / 100)
        target_parts_area = total_sheet_area * (target_util / 100)
        needed_area = target_parts_area - current_parts_area
        
        if needed_area <= 0:
            return []
        
        # Получить типовые размеры деталей
        H = dimensions.get('H', 150)
        W = dimensions.get('W', 200)
        
        # Подобрать детали
        W_range = (W * 0.8, W * 1.2)  # ±20% от текущего W
        
        # Стенки торцевые
        tortsevaya_size = (145, W)
        tortsevaya_area = (145 * W) / 1_000_000
        
        # Распорки
        rasporka_size = (132, W)
        rasporka_area = (132 * W) / 1_000_000
        
        # Стенки
        stenka_size = (42.5, W)
        stenka_area = (42.5 * W) / 1_000_000
        
        # Простая эвристика: добавить детали пока не достигнем нужной площади
        added_area = 0
        detail_count = 0
        
        while added_area < needed_area and detail_count < max_details:
            # Приоритет: стенки торцевые, распорки, стенки
            if detail_count < 4:
                # Добавить стенку торцевую
                recommendations.append({
                    "part_type": "стенка_торцевая",
                    "size": tortsevaya_size,
                    "quantity": 2,
                    "area_per_piece": tortsevaya_area,
                    "total_area": tortsevaya_area * 2,
                    "from_projects": f"H={H}, W={int(W_range[0])}-{int(W_range[1])}"
                })
                added_area += tortsevaya_area * 2
                detail_count += 2
            elif detail_count < 8:
                # Добавить распорку
                recommendations.append({
                    "part_type": "распорка",
                    "size": rasporka_size,
                    "quantity": 2,
                    "area_per_piece": rasporka_area,
                    "total_area": rasporka_area * 2,
                    "from_projects": f"H={H}, W={int(W_range[0])}-{int(W_range[1])}"
                })
                added_area += rasporka_area * 2
                detail_count += 2
            else:
                # Добавить стенку
                recommendations.append({
                    "part_type": "стенка",
                    "size": stenka_size,
                    "quantity": 2,
                    "area_per_piece": stenka_area,
                    "total_area": stenka_area * 2,
                    "from_projects": f"H={H}, W={int(W_range[0])}-{int(W_range[1])}"
                })
                added_area += stenka_area * 2
                detail_count += 2
        
        # Прогноз утилизации
        predicted_parts_area = current_parts_area + added_area
        predicted_util = (predicted_parts_area / total_sheet_area) * 100
        
        # Добавить прогноз к каждой рекомендации
        for rec in recommendations:
            rec['predicted_utilization'] = predicted_util
        
        return recommendations


class AIRecommendationEngine:
    """
    Движок AI-рекомендаций (главный класс для использования)
    """
    
    def __init__(self):
        self.optimizer = AIOptimizer()
    
    def get_recommendations(self, files_data: List[Dict], 
                           nesting_result: Dict,
                           project_dimensions: Dict) -> Dict:
        """
        Получить все рекомендации для текущего проекта
        
        Args:
            files_data: Список файлов с размерами и количествами
            nesting_result: Результат раскроя
            project_dimensions: {'H': 150, 'W': 200, 'L': 3000}
        
        Returns:
            Полный набор рекомендаций
        """
        # Анализ проекта
        analysis = self.optimizer.analyze_project(
            files_data,
            nesting_result,
            project_dimensions
        )
        
        # Генерация рекомендаций
        recommendations = self.optimizer.generate_recommendations(analysis)
        
        # Форматирование для GUI
        formatted = self._format_for_gui(analysis, recommendations)
        
        return formatted
    
    def _format_for_gui(self, analysis: Dict, recommendations: Dict) -> Dict:
        """
        Форматировать рекомендации для отображения в GUI
        """
        return {
            "status": analysis['optimality_status'],
            "current_utilization": analysis['current_utilization'],
            
            "completeness": {
                "warnings": recommendations['completeness_warnings'],
                "has_issues": len(recommendations['completeness_warnings']) > 0
            },
            
            "good_level": {
                "target": "75-85% (ХОРОШО)",
                "recommendations": recommendations['good_level'],
                "has_recommendations": len(recommendations['good_level']) > 0
            },
            
            "excellent_level": {
                "target": "85-95% (ОТЛИЧНО)",
                "recommendations": recommendations['excellent_level'],
                "has_recommendations": len(recommendations['excellent_level']) > 0
            },
            
            "summary": self._create_summary(analysis, recommendations)
        }
    
    def _create_summary(self, analysis: Dict, recommendations: Dict) -> str:
        """
        Создать текстовое резюме
        """
        current_util = analysis['current_utilization']
        status = analysis['optimality_status']
        
        summary_parts = []
        
        # Текущий статус
        if status == "bad":
            summary_parts.append(f"⚠️ Текущая утилизация {current_util:.1f}% - ПЛОХО")
        elif status == "medium":
            summary_parts.append(f"⚠️ Текущая утилизация {current_util:.1f}% - СРЕДНЕ")
        elif status == "good":
            summary_parts.append(f"✓ Текущая утилизация {current_util:.1f}% - ХОРОШО")
        else:
            summary_parts.append(f"✓ Текущая утилизация {current_util:.1f}% - ОТЛИЧНО")
        
        # Предупреждения о комплектности
        warnings = recommendations['completeness_warnings']
        if warnings:
            summary_parts.append(f"\n⚠️ Обнаружено {len(warnings)} проблем с комплектностью")
        
        # Рекомендации
        if recommendations['good_level']:
            summary_parts.append("\n💡 Доступны рекомендации для улучшения до 75-85%")
        
        if recommendations['excellent_level']:
            summary_parts.append("\n✨ Доступны рекомендации для улучшения до 85-95%")
        
        return "\n".join(summary_parts)


# Пример использования
if __name__ == "__main__":
    # Тестовый пример
    engine = AIRecommendationEngine()
    
    test_files = [
        {"name": "Корпус 2шт.dxf", "width": 1500, "height": 493, "quantity": 2},
        {"name": "Стенка 2шт.dxf", "width": 198, "height": 42.5, "quantity": 2},
        {"name": "Стенка торц 2шт.dxf", "width": 198, "height": 145, "quantity": 2},
        {"name": "Распорка 4шт.dxf", "width": 198, "height": 132, "quantity": 4}
    ]
    
    test_nesting = {
        "utilization_percent": 56.4,
        "sheets": [{
            "width": 2500,
            "height": 1250,
            "parts": test_files * 2  # примерно
        }]
    }
    
    test_dimensions = {"H": 150, "W": 200, "L": 3000}
    
    result = engine.get_recommendations(test_files, test_nesting, test_dimensions)
    
    print("=" * 60)
    print("AI-РЕКОМЕНДАЦИИ")
    print("=" * 60)
    print(result['summary'])
    print()
    
    if result['good_level']['has_recommendations']:
        print("РЕКОМЕНДАЦИИ ДЛЯ ХОРОШО (75-85%):")
        for rec in result['good_level']['recommendations']:
            print(f"  • {rec['part_type']}: {rec['size']} - {rec['quantity']} шт")
            print(f"    Прогноз: {rec['predicted_utilization']:.1f}%")
        print()
    
    if result['excellent_level']['has_recommendations']:
        print("РЕКОМЕНДАЦИИ ДЛЯ ОТЛИЧНО (85-95%):")
        for rec in result['excellent_level']['recommendations']:
            print(f"  • {rec['part_type']}: {rec['size']} - {rec['quantity']} шт")
            print(f"    Прогноз: {rec['predicted_utilization']:.1f}%")

