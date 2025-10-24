#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Читаем файл
with open('unfolding_area_calculator/gui_calculator_enhanced.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Исправляем проблемные строки
if len(lines) > 1689:
    lines[1689] = '        ws1[f\'A{row}\'].font = Font(size=14, bold=True, color="1976D2")\n'
    print('Исправлена строка 1690')

if len(lines) > 1690:
    lines[1690] = '        ws1.merge_cells(f\'A{row}:G{row}\')\n'
    print('Исправлена строка 1691')

if len(lines) > 1691:
    lines[1691] = '        ws1[f\'A{row}\'].alignment = Alignment(horizontal=\'center\')\n'
    print('Исправлена строка 1692')

# Записываем исправленный файл
with open('unfolding_area_calculator/gui_calculator_enhanced.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Файл исправлен')
