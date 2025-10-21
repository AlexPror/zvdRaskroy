#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Интерактивный редактор раскроя с Drag & Drop
Пользователь сам размещает детали на листе
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import math


class InteractiveNestingEditor:
    """
    Интерактивный редактор раскроя с перетаскиванием деталей
    """
    
    SHEET_WIDTH = 2500  # мм
    SHEET_HEIGHT = 1250  # мм
    
    def __init__(self, parent_window=None):
        self.logger = logging.getLogger(__name__)
        self.parent = parent_window
        
        # Цвета для деталей
        self.part_colors = [
            '#90CAF9',  # Светло-голубой
            '#A5D6A7',  # Светло-зеленый
            '#FFF59D',  # Светло-желтый
            '#F48FB1',  # Светло-розовый
            '#CE93D8',  # Светло-фиолетовый
            '#80DEEA',  # Светло-бирюзовый
        ]
        
        # Состояние
        self.window = None
        self.canvas = None
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        # Данные
        self.parts_data = []  # Исходные данные деталей
        self.placed_parts = []  # Размещенные детали
        self.sheet_rect = None  # Прямоугольник листа
        
        # Drag & Drop
        self.dragging = False
        self.drag_item = None
        self.drag_start_x = 0
        self.drag_start_y = 0
        
    def show_editor(self, parts_data: List[Dict], project_name: str = "Проект"):
        """
        Показать интерактивный редактор раскроя
        """
        try:
            # Сохраняем данные
            self.parts_data = parts_data.copy()
            self.placed_parts = []
            
            # Создаем окно
            self.window = tk.Toplevel(self.parent) if self.parent else tk.Tk()
            self.window.title(f"Редактор раскроя: {project_name}")
            self.window.geometry("1400x900")
            self.window.configure(bg='white')
            
            # Заголовок
            self._create_header(project_name)
            
            # Основной фрейм
            main_frame = tk.Frame(self.window, bg='white')
            main_frame.pack(fill='both', expand=True, padx=10, pady=5)
            
            # Левая панель - список деталей
            left_frame = tk.Frame(main_frame, bg='white', width=300)
            left_frame.pack(side='left', fill='y', padx=(0, 10))
            left_frame.pack_propagate(False)
            
            self._create_parts_list(left_frame)
            
            # Правая панель - Canvas с листом
            right_frame = tk.Frame(main_frame, bg='white')
            right_frame.pack(side='right', fill='both', expand=True)
            
            self._create_canvas_area(right_frame)
            
            # Кнопки управления
            self._create_control_buttons()
            
            self.logger.info(f"[OK] Редактор раскроя открыт: {project_name}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания редактора: {e}")
            messagebox.showerror("Ошибка", f"Не удалось создать редактор:\n{e}")
    
    def _create_header(self, project_name: str):
        """Создание заголовка"""
        header_frame = tk.Frame(self.window, bg='white')
        header_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(header_frame, text=f"РЕДАКТОР РАСКРОЯ: {project_name}", 
                font=('Arial', 14, 'bold'), bg='white').pack(side='left')
        
        # Информация о листе
        info_text = f"Лист: {self.SHEET_WIDTH}×{self.SHEET_HEIGHT} мм"
        tk.Label(header_frame, text=info_text, 
                font=('Arial', 10), bg='white', fg='blue').pack(side='right')
    
    def _create_parts_list(self, parent):
        """Создание списка деталей для перетаскивания"""
        tk.Label(parent, text="ДЕТАЛИ ДЛЯ РАЗМЕЩЕНИЯ:", 
                font=('Arial', 12, 'bold'), bg='white').pack(pady=(0, 10))
        
        # Скроллируемый список
        list_frame = tk.Frame(parent, bg='white')
        list_frame.pack(fill='both', expand=True)
        
        # Создаем Canvas для списка деталей
        list_canvas = tk.Canvas(list_frame, bg='#f0f0f0', height=400)
        list_scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=list_canvas.yview)
        list_canvas.configure(yscrollcommand=list_scrollbar.set)
        
        list_canvas.pack(side='left', fill='both', expand=True)
        list_scrollbar.pack(side='right', fill='y')
        
        # Создаем мини-прямоугольники для каждой детали
        y_pos = 10
        for idx, part in enumerate(self.parts_data):
            # Создаем мини-прямоугольник детали
            part_rect = list_canvas.create_rectangle(
                10, y_pos, 250, y_pos + 40,
                fill=self.part_colors[idx % len(self.part_colors)],
                outline='black', width=1,
                tags=f"part_{idx}"
            )
            
            # Подпись детали
            part_text = f"{part['name'][:30]}..."
            list_canvas.create_text(
                130, y_pos + 20,
                text=part_text, font=('Arial', 8),
                tags=f"part_{idx}"
            )
            
            # Размеры
            size_text = f"{part['width_mm']:.0f}×{part['height_mm']:.0f}"
            list_canvas.create_text(
                130, y_pos + 30,
                text=size_text, font=('Arial', 7),
                tags=f"part_{idx}"
            )
            
            # Привязываем события для перетаскивания
            list_canvas.tag_bind(f"part_{idx}", "<Button-1>", 
                                lambda e, idx=idx: self._start_drag_from_list(idx, e))
            list_canvas.tag_bind(f"part_{idx}", "<B1-Motion>", 
                                lambda e, idx=idx: self._drag_from_list(idx, e))
            list_canvas.tag_bind(f"part_{idx}", "<ButtonRelease-1>", 
                                lambda e, idx=idx: self._end_drag_from_list(idx, e))
            
            y_pos += 50
        
        # Обновляем область прокрутки
        list_canvas.configure(scrollregion=list_canvas.bbox("all"))
        
        # Инструкции
        tk.Label(parent, text="💡 Перетащите детали на лист", 
                font=('Arial', 9), bg='white', fg='blue').pack(pady=10)
    
    def _create_canvas_area(self, parent):
        """Создание области Canvas с листом"""
        # Фрейм для Canvas
        canvas_frame = tk.Frame(parent, bg='white')
        canvas_frame.pack(fill='both', expand=True)
        
        # Canvas с прокруткой
        self.canvas = tk.Canvas(canvas_frame, bg='white', 
                              width=800, height=600,
                              scrollregion=(0, 0, 2000, 2000))
        
        # Скроллбары
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient='vertical', command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient='horizontal', command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Размещаем элементы
        self.canvas.pack(side='left', fill='both', expand=True)
        v_scrollbar.pack(side='right', fill='y')
        h_scrollbar.pack(side='bottom', fill='x')
        
        # Рисуем лист
        self._draw_sheet()
        
        # Привязываем события Canvas
        self.canvas.bind('<Button-1>', self._on_canvas_click)
        self.canvas.bind('<B1-Motion>', self._on_canvas_drag)
        self.canvas.bind('<ButtonRelease-1>', self._on_canvas_release)
        self.canvas.bind('<MouseWheel>', self._on_mouse_wheel)
    
    def _draw_sheet(self):
        """Рисование листа на Canvas"""
        # Рассчитываем масштаб
        canvas_width = 800
        canvas_height = 600
        
        scale_w = canvas_width / self.SHEET_WIDTH
        scale_h = canvas_height / self.SHEET_HEIGHT
        self.scale = min(scale_w, scale_h) * 0.8
        
        # Размеры листа в Canvas
        sheet_w = self.SHEET_WIDTH * self.scale
        sheet_h = self.SHEET_HEIGHT * self.scale
        
        # Позиция листа (по центру)
        self.sheet_x = (canvas_width - sheet_w) / 2
        self.sheet_y = (canvas_height - sheet_h) / 2
        
        # Рисуем контур листа
        self.sheet_rect = self.canvas.create_rectangle(
            self.sheet_x, self.sheet_y,
            self.sheet_x + sheet_w, self.sheet_y + sheet_h,
            outline='black', width=3, fill='#f0f0f0',
            tags="sheet"
        )
        
        # Подписи размеров
        self.canvas.create_text(
            self.sheet_x + sheet_w / 2, self.sheet_y - 20,
            text=f"ЛИСТ {self.SHEET_WIDTH}×{self.SHEET_HEIGHT} мм",
            font=('Arial', 10, 'bold'), fill='red'
        )
        
        self.canvas.create_text(
            self.sheet_x - 30, self.sheet_y + sheet_h / 2,
            text=f"{self.SHEET_HEIGHT} мм", font=('Arial', 8), fill='black'
        )
        
        self.canvas.create_text(
            self.sheet_x + sheet_w / 2, self.sheet_y + sheet_h + 15,
            text=f"{self.SHEET_WIDTH} мм", font=('Arial', 8), fill='black'
        )
    
    def _create_control_buttons(self):
        """Создание кнопок управления"""
        control_frame = tk.Frame(self.window, bg='white')
        control_frame.pack(fill='x', padx=10, pady=5)
        
        # Кнопки масштаба
        tk.Button(control_frame, text="Масштаб 1:1", 
                command=lambda: self._set_scale(1.0)).pack(side='left', padx=5)
        tk.Button(control_frame, text="Поместить все", 
                command=self._fit_to_window).pack(side='left', padx=5)
        tk.Button(control_frame, text="Центрировать", 
                command=self._center_view).pack(side='left', padx=5)
        
        # Кнопки действий
        tk.Button(control_frame, text="Очистить лист", 
                command=self._clear_sheet, bg='#ffcccc').pack(side='left', padx=5)
        tk.Button(control_frame, text="Авторазмещение", 
                command=self._auto_place, bg='#ccffcc').pack(side='left', padx=5)
        
        # Кнопки сохранения
        tk.Button(control_frame, text="Сохранить раскрой", 
                command=self._save_nesting, bg='#ccccff').pack(side='right', padx=5)
        tk.Button(control_frame, text="Закрыть", 
                command=self.window.destroy).pack(side='right', padx=5)
    
    def _start_drag_from_list(self, part_idx: int, event):
        """Начало перетаскивания из списка"""
        self.dragging = True
        self.drag_item = part_idx
        self.drag_start_x = event.x
        self.drag_start_y = event.y
    
    def _drag_from_list(self, part_idx: int, event):
        """Перетаскивание из списка"""
        if not self.dragging:
            return
        
        # Показываем курсор перетаскивания
        # (В реальной реализации здесь можно показать призрак детали)
        pass
    
    def _end_drag_from_list(self, part_idx: int, event):
        """Завершение перетаскивания из списка"""
        if not self.dragging:
            return
        
        self.dragging = False
        
        # Проверяем, попали ли на лист
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        if self._is_point_on_sheet(canvas_x, canvas_y):
            # Размещаем деталь на листе
            self._place_part_on_sheet(part_idx, canvas_x, canvas_y)
    
    def _is_point_on_sheet(self, x: float, y: float) -> bool:
        """Проверка, находится ли точка на листе"""
        if not self.sheet_rect:
            return False
        
        coords = self.canvas.coords(self.sheet_rect)
        return (coords[0] <= x <= coords[2] and 
                coords[1] <= y <= coords[3])
    
    def _place_part_on_sheet(self, part_idx: int, x: float, y: float):
        """Размещение детали на листе"""
        part = self.parts_data[part_idx]
        
        # Рассчитываем размеры детали в Canvas
        part_w = part['width_mm'] * self.scale
        part_h = part['height_mm'] * self.scale
        
        # Проверяем, помещается ли деталь
        if not self._can_place_part(x, y, part_w, part_h):
            messagebox.showwarning("Предупреждение", 
                                 f"Деталь '{part['name']}' не помещается в этом месте!")
            return
        
        # Создаем прямоугольник детали
        part_rect = self.canvas.create_rectangle(
            x, y, x + part_w, y + part_h,
            fill=self.part_colors[part_idx % len(self.part_colors)],
            outline='black', width=1,
            tags=f"placed_part_{len(self.placed_parts)}"
        )
        
        # Подпись детали
        name_text = part['name'][:20] + "..." if len(part['name']) > 20 else part['name']
        self.canvas.create_text(
            x + part_w / 2, y + part_h / 2,
            text=name_text, font=('Arial', 7),
            tags=f"placed_part_{len(self.placed_parts)}"
        )
        
        # Сохраняем информацию о размещенной детали
        placed_part = {
            'part_idx': part_idx,
            'canvas_id': part_rect,
            'x': x,
            'y': y,
            'width': part_w,
            'height': part_h
        }
        
        self.placed_parts.append(placed_part)
        
        # Привязываем события для перетаскивания размещенной детали
        self.canvas.tag_bind(f"placed_part_{len(self.placed_parts)-1}", "<Button-1>", 
                            lambda e, idx=len(self.placed_parts)-1: self._start_drag_placed(idx, e))
        self.canvas.tag_bind(f"placed_part_{len(self.placed_parts)-1}", "<B1-Motion>", 
                            lambda e, idx=len(self.placed_parts)-1: self._drag_placed(idx, e))
        self.canvas.tag_bind(f"placed_part_{len(self.placed_parts)-1}", "<ButtonRelease-1>", 
                            lambda e, idx=len(self.placed_parts)-1: self._end_drag_placed(idx, e))
        
        self.logger.info(f"[OK] Размещена деталь: {part['name']}")
    
    def _can_place_part(self, x: float, y: float, w: float, h: float) -> bool:
        """Проверка возможности размещения детали"""
        # Проверяем границы листа
        if not self.sheet_rect:
            return False
        
        coords = self.canvas.coords(self.sheet_rect)
        if (x < coords[0] or y < coords[1] or 
            x + w > coords[2] or y + h > coords[3]):
            return False
        
        # Проверяем пересечения с другими деталями
        for placed in self.placed_parts:
            if (x < placed['x'] + placed['width'] and x + w > placed['x'] and
                y < placed['y'] + placed['height'] and y + h > placed['y']):
                return False
        
        return True
    
    def _start_drag_placed(self, placed_idx: int, event):
        """Начало перетаскивания размещенной детали"""
        self.dragging = True
        self.drag_item = placed_idx
        self.drag_start_x = event.x
        self.drag_start_y = event.y
    
    def _drag_placed(self, placed_idx: int, event):
        """Перетаскивание размещенной детали"""
        if not self.dragging:
            return
        
        # Обновляем позицию детали
        placed = self.placed_parts[placed_idx]
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        
        new_x = placed['x'] + dx
        new_y = placed['y'] + dy
        
        # Проверяем, можно ли разместить в новой позиции
        if self._can_place_part(new_x, new_y, placed['width'], placed['height']):
            # Обновляем позицию
            self.canvas.coords(placed['canvas_id'], 
                              new_x, new_y, 
                              new_x + placed['width'], new_y + placed['height'])
            
            # Обновляем подпись
            text_items = self.canvas.find_withtag(f"placed_part_{placed_idx}")
            for item in text_items:
                if self.canvas.type(item) == 'text':
                    self.canvas.coords(item, new_x + placed['width']/2, new_y + placed['height']/2)
            
            # Обновляем данные
            placed['x'] = new_x
            placed['y'] = new_y
            
            self.drag_start_x = event.x
            self.drag_start_y = event.y
    
    def _end_drag_placed(self, placed_idx: int, event):
        """Завершение перетаскивания размещенной детали"""
        self.dragging = False
    
    def _on_canvas_click(self, event):
        """Обработка клика на Canvas"""
        self.drag_start_x = event.x
        self.drag_start_y = event.y
    
    def _on_canvas_drag(self, event):
        """Обработка перетаскивания на Canvas"""
        if hasattr(self, 'drag_start_x'):
            dx = event.x - self.drag_start_x
            dy = event.y - self.drag_start_y
            self.canvas.scan_dragto(dx, dy, gain=1)
            self.drag_start_x = event.x
            self.drag_start_y = event.y
    
    def _on_canvas_release(self, event):
        """Обработка отпускания мыши на Canvas"""
        pass
    
    def _on_mouse_wheel(self, event):
        """Обработка колесика мыши для масштабирования"""
        if event.delta > 0:
            self.scale *= 1.1
        else:
            self.scale *= 0.9
        
        # Ограничиваем масштаб
        self.scale = max(0.1, min(5.0, self.scale))
        
        # Перерисовываем
        self._redraw_all()
    
    def _set_scale(self, scale: float):
        """Установить масштаб"""
        self.scale = scale
        self._redraw_all()
    
    def _fit_to_window(self):
        """Поместить все в окно"""
        self._set_scale(1.0)
        self._center_view()
    
    def _center_view(self):
        """Центрировать вид"""
        self.canvas.xview_moveto(0.5)
        self.canvas.yview_moveto(0.5)
    
    def _clear_sheet(self):
        """Очистить лист от всех деталей"""
        for placed in self.placed_parts:
            self.canvas.delete(placed['canvas_id'])
            # Удаляем подписи
            text_items = self.canvas.find_withtag(f"placed_part_{self.placed_parts.index(placed)}")
            for item in text_items:
                if self.canvas.type(item) == 'text':
                    self.canvas.delete(item)
        
        self.placed_parts.clear()
        self.logger.info("[OK] Лист очищен")
    
    def _auto_place(self):
        """Автоматическое размещение деталей"""
        # Простой алгоритм размещения слева направо
        x = self.sheet_x + 10
        y = self.sheet_y + 10
        
        for part_idx, part in enumerate(self.parts_data):
            part_w = part['width_mm'] * self.scale
            part_h = part['height_mm'] * self.scale
            
            # Если не помещается в текущую строку, переходим на новую
            if x + part_w > self.sheet_x + self.SHEET_WIDTH * self.scale - 10:
                x = self.sheet_x + 10
                y += max(p['height_mm'] for p in self.parts_data[:part_idx+1]) * self.scale + 10
            
            # Размещаем деталь
            self._place_part_on_sheet(part_idx, x, y)
            
            # Сдвигаем позицию
            x += part_w + 10
        
        self.logger.info("[OK] Автоматическое размещение завершено")
    
    def _redraw_all(self):
        """Перерисовка всех элементов"""
        # Очищаем Canvas
        self.canvas.delete("all")
        
        # Перерисовываем лист
        self._draw_sheet()
        
        # Перерисовываем размещенные детали
        for placed in self.placed_parts:
            part = self.parts_data[placed['part_idx']]
            part_w = part['width_mm'] * self.scale
            part_h = part['height_mm'] * self.scale
            
            # Обновляем размеры
            placed['width'] = part_w
            placed['height'] = part_h
            
            # Создаем новый прямоугольник
            placed['canvas_id'] = self.canvas.create_rectangle(
                placed['x'], placed['y'],
                placed['x'] + part_w, placed['y'] + part_h,
                fill=self.part_colors[placed['part_idx'] % len(self.part_colors)],
                outline='black', width=1,
                tags=f"placed_part_{self.placed_parts.index(placed)}"
            )
    
    def _save_nesting(self):
        """Сохранение раскроя"""
        if not self.placed_parts:
            messagebox.showwarning("Предупреждение", "Нет размещенных деталей!")
            return
        
        # Создаем результат раскроя
        nesting_result = {
            'success': True,
            'sheets_needed': 1,
            'sheets': [{
                'number': 1,
                'parts': []
            }],
            'utilization_percent': 0,
            'overall_waste_percent': 100
        }
        
        # Добавляем размещенные детали
        for placed in self.placed_parts:
            part = self.parts_data[placed['part_idx']]
            
            # Переводим координаты обратно в мм
            x_mm = (placed['x'] - self.sheet_x) / self.scale
            y_mm = (placed['y'] - self.sheet_y) / self.scale
            
            nesting_result['sheets'][0]['parts'].append({
                'name': part['name'],
                'x': x_mm,
                'y': y_mm,
                'width': part['width_mm'],
                'height': part['height_mm'],
                'rotated': False
            })
        
        # Рассчитываем статистику
        total_area = sum(p['area_m2'] for p in self.parts_data)
        sheet_area = (self.SHEET_WIDTH * self.SHEET_HEIGHT) / 1_000_000
        utilization = (total_area / sheet_area) * 100
        
        nesting_result['utilization_percent'] = utilization
        nesting_result['overall_waste_percent'] = 100 - utilization
        
        # Показываем результат
        messagebox.showinfo("Сохранено", 
                           f"Раскрой сохранен!\n\n"
                           f"Деталей: {len(self.placed_parts)}\n"
                           f"Использование: {utilization:.1f}%\n"
                           f"Обрезки: {100-utilization:.1f}%")
        
        self.logger.info(f"[OK] Раскрой сохранен: {len(self.placed_parts)} деталей")
        
        return nesting_result


if __name__ == "__main__":
    # Тест интерактивного редактора
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    print("="*70)
    print("ТЕСТ ИНТЕРАКТИВНОГО РЕДАКТОРА РАСКРОЯ")
    print("="*70)
    
    # Тестовые данные
    test_parts = [
        {
            'name': '004 - Корпус короба',
            'width_mm': 1200.0,
            'height_mm': 400.0,
            'area_m2': 0.48,
            'quantity': 1
        },
        {
            'name': '003 - Крышка декоративная',
            'width_mm': 287.7,
            'height_mm': 150.0,
            'area_m2': 0.0432,
            'quantity': 1
        },
        {
            'name': '006 - Стенка торцевая',
            'width_mm': 134.0,
            'height_mm': 298.0,
            'area_m2': 0.0399,
            'quantity': 1
        }
    ]
    
    # Создаем редактор
    editor = InteractiveNestingEditor()
    editor.show_editor(test_parts, "ТЕСТ_ПРОЕКТ")
    
    print("[OK] Редактор запущен!")
    print("TIP: Перетащите детали из списка на лист")
    print("TIP: Используйте 'Авторазмещение' для быстрого размещения")
