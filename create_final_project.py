#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ФИНАЛЬНЫЙ СКРИПТ создания проекта КОМПАС-3D
Все функции в одном месте
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pythoncom
import time
from pathlib import Path

def create_project(h: int, b1: int, l1: int):
    """Создание проекта с заданными параметрами"""
    
    pythoncom.CoInitialize()
    
    try:
        from components.project_copier import ProjectCopier
        from components.variables_updater import VariablesUpdater
        from components.designation_updater_grouped import DesignationUpdaterGrouped
        from components.drawing_exporter import DrawingExporter
        from components.unfolding_dxf_exporter import UnfoldingDxfExporter
        
        print("="*70)
        print("СОЗДАНИЕ ПРОЕКТА КОМПАС-3D")
        print("="*70)
        print(f"\nПараметры: H={h}, B1={b1}, L1={l1}")
        
        source_path = r"C:\Users\Vorob\Documents\ZVD GROUP\Параметризация\ZVD.LITE.80.230.2000"
        target_folder = r"C:\Users\Vorob\Documents\ZVD GROUP\Параметризация"
        project_name = f"ZVD.LITE.{h}.{b1}.{l1}"
        
        print(f"Имя проекта: {project_name}\n")
        
        # Шаг 1: Копирование
        print("="*70)
        print("ШАГ 1/6: Копирование проекта")
        print("="*70)
        
        copier = ProjectCopier()
        copy_result = copier.copy_project(source_path, target_folder, project_name)
        
        if not copy_result['success']:
            print(f"[X] Ошибка: {copy_result['error']}")
            return False
        
        print(f"[OK] Проект скопирован\n")
        project_path = copy_result['copied_path']
        time.sleep(2)
        
        # Шаг 2: Переменные
        print("="*70)
        print("ШАГ 2/6: Обновление переменных")
        print("="*70)
        
        assembly_files = list(Path(project_path).glob("*.a3d"))
        updater = VariablesUpdater()
        var_result = updater.update_assembly_variables(
            str(assembly_files[0]),
            {'H': h, 'B1': b1, 'L1': l1}
        )
        
        if not var_result['success']:
            print(f"[X] Ошибка: {var_result.get('error')}")
            return False
        
        print(f"[OK] Переменные обновлены: {var_result['updated_count']}/3\n")
        time.sleep(2)
        
        # Шаг 3: Переименование
        print("="*70)
        print("ШАГ 3/6: Переименование сборки и деталей")
        print("="*70)
        
        designation_updater = DesignationUpdaterGrouped()
        rename_result = designation_updater.update_all_designations(
            project_path, h, b1, l1
        )
        
        if not rename_result['success']:
            print(f"[X] Ошибка: {rename_result.get('errors')}")
            return False
        
        print(f"[OK] Сборка переименована: {rename_result.get('assembly_renamed')}")
        print(f"[OK] Обновлено экземпляров: {rename_result.get('parts_renamed')}\n")
        time.sleep(2)
        
        # Шаг 4: Экспорт BMP
        print("="*70)
        print("ШАГ 4/6: Экспорт чертежей в BMP")
        print("="*70)
        
        bmp_folder = Path(project_path) / "BMP"
        bmp_folder.mkdir(exist_ok=True)
        
        drawing_exporter = DrawingExporter()
        bmp_result = drawing_exporter.export_all_drawings(
            project_path, str(bmp_folder), format_type='BMP', resolution=300
        )
        
        if not bmp_result['success']:
            print(f"[!] Предупреждение: {bmp_result.get('error')}")
        
        print(f"[OK] Экспортировано: {bmp_result['exported_count']} чертежей\n")
        time.sleep(2)
        
        # Шаг 5: Экспорт DXF
        print("="*70)
        print("ШАГ 5/6: Экспорт разверток в DXF")
        print("="*70)
        
        dxf_folder = Path(project_path) / "DXF"
        dxf_folder.mkdir(exist_ok=True)
        
        dxf_exporter = UnfoldingDxfExporter()
        dxf_result = dxf_exporter.export_all_unfoldings(project_path, str(dxf_folder))
        
        if not dxf_result['success']:
            print(f"[!] Предупреждение: {dxf_result.get('error')}")
        
        print(f"[OK] Экспортировано: {dxf_result['exported']} разверток\n")
        
        # Шаг 6: Проверка
        print("="*70)
        print("ШАГ 6/6: Проверка результатов")
        print("="*70)
        
        # Проверка файлов
        assembly_file_check = list(Path(project_path).glob("*.a3d"))
        expected_name = f"ZVD.LITE.{h}.{b1}.{l1}.a3d"
        
        if assembly_file_check and assembly_file_check[0].name == expected_name:
            print(f"[OK] Файл сборки: {expected_name}")
        else:
            print(f"[!] Файл сборки: {assembly_file_check[0].name if assembly_file_check else 'НЕ НАЙДЕН'}")
        
        bmp_files = list(bmp_folder.glob("*.bmp"))
        print(f"[OK] BMP файлов: {len(bmp_files)}")
        
        dxf_files = list(dxf_folder.glob("*.dxf"))
        print(f"[OK] DXF файлов: {len(dxf_files)}")
        
        # Итог
        print(f"\n{'='*70}")
        print("ИТОГ:")
        print(f"{'='*70}\n")
        
        print(f"[OK] Проект создан успешно!")
        print(f"\nПуть: {project_path}")
        print(f"\nСтруктура:")
        print(f"  - {expected_name}")
        print(f"  - BMP/ ({len(bmp_files)} файлов)")
        print(f"  - DXF/ ({len(dxf_files)} файлов)")
        
        print(f"\n{'='*70}")
        print("РУЧНАЯ РАБОТА:")
        print(f"{'='*70}\n")
        
        print("Осталось вручную (2-3 минуты):")
        print("  1. Обновить файлы-источники в чертежах (6 штук)")
        print("     Дерево чертежа -> Вид -> ПКМ -> Параметры вида")
        print("     -> Файл-источник -> Выбрать открытую деталь")
        
        print(f"\n{'='*70}")
        print("[SUCCESS] ПРОЕКТ ГОТОВ!")
        print(f"{'='*70}\n")
        
        return True
        
    except Exception as e:
        print(f"\n[X] КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    # ========================================
    # НАСТРОЙКА: Измените параметры здесь
    # ========================================
    
    H = 147      # Высота
    B1 = 145     # Ширина
    L1 = 1400    # Длина
    
    # ========================================
    
    print("\n" + "="*70)
    print("ФИНАЛЬНАЯ СИСТЕМА АВТОМАТИЗАЦИИ КОМПАС-3D")
    print("="*70 + "\n")
    
    success = create_project(H, B1, L1)
    
    if success:
        print("\n✓ Завершено успешно!")
    else:
        print("\n✗ Завершено с ошибками")
    
    print()

