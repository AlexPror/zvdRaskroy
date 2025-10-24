#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Читаем оригинальный файл
with open('unfolding_area_calculator/gui_calculator_enhanced.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Исправляем все проблемы с отступами
lines = content.split('\n')
fixed_lines = []

for i, line in enumerate(lines):
    # Проверяем проблемные строки и исправляем отступы
    if 'ws1[f\'A{row}\'].font = Font' in line and not line.startswith('        '):
        fixed_lines.append('        ws1[f\'A{row}\'].font = Font(size=14, bold=True, color="1976D2")')
    elif 'ws1.merge_cells(f\'A{row}:G{row}\')' in line and not line.startswith('        '):
        fixed_lines.append('        ws1.merge_cells(f\'A{row}:G{row}\')')
    elif 'ws1[f\'A{row}\'].alignment = Alignment' in line and not line.startswith('        '):
        fixed_lines.append('        ws1[f\'A{row}\'].alignment = Alignment(horizontal=\'center\')')
    elif 'row += 1' in line and not line.startswith('        '):
        fixed_lines.append('        row += 1')
    elif 'ws2[f\'A{row2}\'].alignment = Alignment' in line and not line.startswith('        '):
        fixed_lines.append('        ws2[f\'A{row2}\'].alignment = Alignment(horizontal=\'center\')')
    elif 'c.setFont(font_bold, 14)' in line and not line.startswith('        '):
        fixed_lines.append('        c.setFont(font_bold, 14)')
    else:
        fixed_lines.append(line)

# Записываем исправленный файл
with open('unfolding_area_calculator/gui_calculator_enhanced_fixed.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(fixed_lines))

print('Создана исправленная версия: gui_calculator_enhanced_fixed.py')
