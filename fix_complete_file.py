#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Читаем оригинальный файл
with open('unfolding_area_calculator/gui_calculator_enhanced.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Исправляем все проблемы с отступами
lines = content.split('\n')
fixed_lines = []

for i, line in enumerate(lines):
    # Исправляем строки с неправильными отступами
    if line.strip().startswith('ws1[f\'A{row}\'].font = Font') and not line.startswith('        '):
        fixed_lines.append('        ws1[f\'A{row}\'].font = Font(size=14, bold=True, color="1976D2")')
    elif line.strip().startswith('ws1.merge_cells(f\'A{row}:G{row}\')') and not line.startswith('        '):
        fixed_lines.append('        ws1.merge_cells(f\'A{row}:G{row}\')')
    elif line.strip().startswith('ws1[f\'A{row}\'].alignment = Alignment') and not line.startswith('        '):
        fixed_lines.append('        ws1[f\'A{row}\'].alignment = Alignment(horizontal=\'center\')')
    elif line.strip().startswith('row += 1') and not line.startswith('        '):
        fixed_lines.append('        row += 1')
    elif line.strip().startswith('ws2[f\'A{row2}\'].alignment = Alignment') and not line.startswith('        '):
        fixed_lines.append('        ws2[f\'A{row2}\'].alignment = Alignment(horizontal=\'center\')')
    elif line.strip().startswith('c.setFont(font_bold, 14)') and not line.startswith('        '):
        fixed_lines.append('        c.setFont(font_bold, 14)')
    elif line.strip().startswith('c.setFont(font_normal, 10)') and not line.startswith('        '):
        fixed_lines.append('        c.setFont(font_normal, 10)')
    elif line.strip().startswith('c.drawString(') and not line.startswith('        '):
        # Исправляем отступы для drawString
        fixed_lines.append('        ' + line.strip())
    elif line.strip().startswith('c.drawCentredString(') and not line.startswith('        '):
        # Исправляем отступы для drawCentredString
        fixed_lines.append('        ' + line.strip())
    elif line.strip().startswith('c.showPage()') and not line.startswith('        '):
        # Исправляем отступы для showPage
        fixed_lines.append('        ' + line.strip())
    else:
        fixed_lines.append(line)

# Записываем исправленный файл
with open('unfolding_area_calculator/gui_calculator_enhanced_fixed.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(fixed_lines))

print('Создана исправленная версия с правильными отступами')
