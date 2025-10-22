#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Автоматический тест функций v3.0
Проверяет: rectpack, AI-рекомендации, базу данных
"""

import sys
from pathlib import Path

# Добавляем пути
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'unfolding_area_calculator'))

def test_imports():
    """Тест 1: Проверка всех импортов"""
    print("\n" + "="*70)
    print("ТЕСТ 1: Проверка импортов")
    print("="*70)
    
    try:
        import rectpack
        print("[OK] rectpack imported")
    except:
        print("[FAIL] ERROR: rectpack not installed")
        return False
    
    try:
        from components.rectpack_optimizer import RectpackOptimizer
        print("[OK] RectpackOptimizer imported")
    except Exception as e:
        print(f"[FAIL] ERROR: {e}")
        return False
    
    try:
        from components.ai_optimizer import AIRecommendationEngine
        print("[OK] AIRecommendationEngine imported")
    except Exception as e:
        print(f"[FAIL] ERROR: {e}")
        return False
    
    try:
        from components.projects_database import ProjectsDatabase
        print("[OK] ProjectsDatabase imported")
    except Exception as e:
        print(f"[FAIL] ERROR: {e}")
        return False
    
    print("\n[SUCCESS] All imports OK!")
    return True


def test_rectpack_optimizer():
    """Тест 2: Проверка RectpackOptimizer"""
    print("\n" + "="*70)
    print("ТЕСТ 2: RectpackOptimizer")
    print("="*70)
    
    try:
        from components.rectpack_optimizer import RectpackOptimizer
        
        optimizer = RectpackOptimizer()
        print(f"[OK] Optimizer created")
        print(f"[OK] rectpack available: {optimizer.is_available()}")
        
        if not optimizer.is_available():
            print("[FAIL] ERROR: rectpack not available")
            return False
        
        # Тестовые данные
        test_parts = [
            {'name': 'Корпус', 'width_mm': 600, 'height_mm': 800, 'area_m2': 0.48, 'quantity': 1},
            {'name': 'Стенка', 'width_mm': 300, 'height_mm': 600, 'area_m2': 0.18, 'quantity': 2},
            {'name': 'Распорка', 'width_mm': 200, 'height_mm': 400, 'area_m2': 0.08, 'quantity': 3},
        ]
        
        print(f"\nТестирую раскрой {len(test_parts)} типов деталей...")
        
        # Тест с поворотом
        result = optimizer.optimize_layout(test_parts, allow_rotation=True, algorithm='BFF')
        
        if not result['success']:
            print(f"[FAIL] ERROR: {result.get('error', 'Unknown')}")
            return False
        
        print(f"\n[OK] Layout optimization completed!")
        print(f"  Sheets: {result['sheets_needed']}")
        print(f"  Utilization: {result['utilization_percent']:.1f}%")
        print(f"  Waste: {result['overall_waste_percent']:.1f}%")
        
        if result['sheets_needed'] > 0:
            print(f"\n[SUCCESS] RectpackOptimizer works!")
            return True
        else:
            print(f"[FAIL] ERROR: No sheets in result")
            return False
            
    except Exception as e:
        print(f"[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ai_recommendations():
    """Тест 3: Проверка AI-рекомендаций"""
    print("\n" + "="*70)
    print("ТЕСТ 3: AI-рекомендации")
    print("="*70)
    
    try:
        from components.ai_optimizer import AIRecommendationEngine
        
        engine = AIRecommendationEngine()
        print("[OK] AI Engine created")
        
        # Тестовые данные
        test_files = [
            {"name": "Корпус 2шт.dxf", "width": 1500, "height": 493, "quantity": 2},
            {"name": "Стенка 2шт.dxf", "width": 198, "height": 42.5, "quantity": 2},
            {"name": "Стенка торц 2шт.dxf", "width": 198, "height": 145, "quantity": 2},
            {"name": "Распорка 4шт.dxf", "width": 198, "height": 132, "quantity": 4}
        ]
        
        test_nesting = {
            "utilization_percent": 56.4,
            "sheets_needed": 1,
            "sheets": [{
                "width": 2500,
                "height": 1250,
                "parts": []
            }]
        }
        
        test_dimensions = {"H": 150, "W": 200, "L": 3000}
        
        print(f"\nПолучаю AI-рекомендации...")
        result = engine.get_recommendations(test_files, test_nesting, test_dimensions)
        
        print(f"\n[OK] Recommendations received!")
        print(f"  Status: {result['status']}")
        print(f"  Utilization: {result['current_utilization']:.1f}%")
        print(f"  Completeness issues: {result['completeness']['has_issues']}")
        print(f"  Good level recommendations: {result['good_level']['has_recommendations']}")
        print(f"  Excellent level recommendations: {result['excellent_level']['has_recommendations']}")
        
        print(f"\n[SUCCESS] AI recommendations work!")
        return True
        
    except Exception as e:
        print(f"[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_projects_database():
    """Тест 4: Проверка ProjectsDatabase"""
    print("\n" + "="*70)
    print("ТЕСТ 4: База данных проектов")
    print("="*70)
    
    try:
        from components.projects_database import ProjectsDatabase
        
        db = ProjectsDatabase()
        print("[OK] Database created")
        
        # Попытка загрузить кэш
        if db.load_cache():
            stats = db.get_statistics()
            print(f"[OK] Cache loaded")
            print(f"  Projects: {stats['total_projects']}")
            print(f"  Parts: {stats.get('total_parts', 0)}")
        else:
            print("  (No cache - this is normal)")
        
        # Тест поиска
        matching = db.find_projects_by_dimensions(H=150, W=200)
        print(f"\n[OK] Project search works")
        print(f"  Found projects (H=150, W=200): {len(matching)}")
        
        print(f"\n[SUCCESS] Database works!")
        return True
        
    except Exception as e:
        print(f"[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_gui_import():
    """Тест 5: Проверка импорта GUI"""
    print("\n" + "="*70)
    print("ТЕСТ 5: Импорт GUI")
    print("="*70)
    
    try:
        from gui_calculator_enhanced import EnhancedUnfoldingAreaGUI
        print("[OK] GUI imported")
        print("  (GUI ready to run)")
        
        print(f"\n[SUCCESS] GUI imports without errors!")
        return True
        
    except Exception as e:
        print(f"[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Запуск всех тестов"""
    print("\n" + "="*70)
    print("[TEST] AVTOMATICHESKOE TESTIROVANIE v3.0")
    print("="*70)
    
    results = {
        "Импорты": test_imports(),
        "RectpackOptimizer": test_rectpack_optimizer(),
        "AI-рекомендации": test_ai_recommendations(),
        "База данных": test_projects_database(),
        "GUI импорт": test_gui_import(),
    }
    
    # Итоги
    print("\n" + "="*70)
    print("ITOGI TESTIROVANIYA")
    print("="*70)
    
    for name, passed in results.items():
        status = "[OK]  " if passed else "[FAIL]"
        print(f"{status} | {name}")
    
    total = len(results)
    passed = sum(results.values())
    failed = total - passed
    
    print("\n" + "="*70)
    print(f"Total tests:  {total}")
    print(f"Passed:       {passed}")
    print(f"Failed:       {failed}")
    
    if failed == 0:
        print("\n[SUCCESS] VSE TESTY PROJDENY! v3.0 gotova k ispolzovaniyu!")
        return 0
    else:
        print(f"\n[WARNING] {failed} test(ov) provaleno. Trebuetsya ispravlenie.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

