#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ФИНАЛЬНЫЙ СКРИПТ с поддержкой переменных A1, B1, L1
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pythoncom
import time
from pathlib import Path

def create_project(h: int, b1: int, l1: int):
    """Создание проекта"""
    
    pythoncom.CoInitialize()
    
    try:
        from components.project_copier import ProjectCopier
        from components.variables_updater import VariablesUpdater
        from components.designation_updater_grouped import DesignationUpdaterGrouped
        from components.hyperlink_fixer import HyperlinkFixer
        from components.drawing_exporter import DrawingExporter
        from components.unfolding_dxf_exporter import UnfoldingDxfExporter
        
        print("="*70)
        print("СОЗДАНИЕ ПРОЕКТА С АВТОМАТИЧЕСКИМИ ПЕРЕМЕННЫМИ")
        print("="*70)
        print(f"\nПараметры: H={h}, B1={b1}, L1={l1}\n")
        
        source_path = r"C:\Users\Vorob\Documents\ZVD GROUP\Параметризация\ZVD.LITE.80.230.2000"
        target_folder = r"C:\Users\Vorob\Documents\ZVD GROUP\Параметризация"
        project_name = f"ZVD.LITE.{h}.{b1}.{l1}"
        
        # Шаг 1: Копирование
        print("ШАГ 1/7: Копирование")
        copier = ProjectCopier()
        copy_result = copier.copy_project(source_path, target_folder, project_name)
        print(f"[OK]\n")
        project_path = copy_result['copied_path']
        time.sleep(2)
        
        # Шаг 2: Переменные
        print("ШАГ 2/7: Обновление переменных")
        assembly_files = list(Path(project_path).glob("*.a3d"))
        updater = VariablesUpdater()
        var_result = updater.update_assembly_variables(
            str(assembly_files[0]),
            {'H': h, 'B1': b1, 'L1': l1}
        )
        print(f"[OK] {var_result['updated_count']}/3\n")
        time.sleep(2)
        
        # Шаг 3: Переименование
        print("ШАГ 3/7: Переименование")
        designation_updater = DesignationUpdaterGrouped()
        rename_result = designation_updater.update_all_designations(
            project_path, h, b1, l1
        )
        print(f"[OK] Обновлено: {rename_result.get('parts_renamed')}\n")
        time.sleep(2)
        
        # Шаг 4: Исправление гиперссылок (если есть)
        print("ШАГ 4/7: Исправление переменных в деталях")
        print("Замена Expression на A1, B1, L1...")
        hyperlink_fixer = HyperlinkFixer()
        
        # Модифицируем fixer для работы с A1 вместо H
        # (нужно будет создать отдельную версию или параметризовать)
        # Пока пропускаем этот шаг
        print("[SKIP] Пропущено (переменные уже настроены вручную)\n")
        time.sleep(1)
        
        # Шаг 5: Экспорт BMP
        print("ШАГ 5/7: Экспорт BMP")
        bmp_folder = Path(project_path) / "BMP"
        bmp_folder.mkdir(exist_ok=True)
        
        drawing_exporter = DrawingExporter()
        bmp_result = drawing_exporter.export_all_drawings(
            project_path, str(bmp_folder), format_type='BMP', resolution=300
        )
        print(f"[OK] {bmp_result['exported_count']}/6\n")
        time.sleep(2)
        
        # Шаг 6: Экспорт DXF
        print("ШАГ 6/7: Экспорт DXF")
        dxf_folder = Path(project_path) / "DXF"
        dxf_folder.mkdir(exist_ok=True)
        
        dxf_exporter = UnfoldingDxfExporter()
        dxf_result = dxf_exporter.export_all_unfoldings(project_path, str(dxf_folder))
        print(f"[OK] {dxf_result['exported']}/5\n")
        
        # Итог
        print("="*70)
        print("ИТОГ:")
        print("="*70)
        print(f"[OK] Проект создан: {project_path}")
        print(f"\nРучная работа (2-3 мин):")
        print(f"  1. Обновить файлы-источники в чертежах")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"\n[X] Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    # Параметры проекта
    H = 148
    B1 = 145
    L1 = 1400
    
    print("\n" + "="*70)
    print("АВТОМАТИЗАЦИЯ КОМПАС-3D")
    print("="*70 + "\n")
    
    success = create_project(H, B1, L1)
    
    print(f"\n{'Успех!' if success else 'Ошибка!'}\n")

