#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Интерактивная визуализация раскроя на Canvas
Показывает раскрой в масштабе в отдельном окне
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Dict, List, Tuple
import math


class NestingCanvasViewer:
    """
    Интерактивная визуализация раскроя на Canvas
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
        
        # Создаем окно
        self.window = None
        self.canvas = None
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
    def show_nesting(self, nesting_result: Dict, project_name: str = "Проект"):
        """
        Показать раскрой в отдельном окне
        """
        try:
            # Создаем окно
            self.window = tk.Toplevel(self.parent) if self.parent else tk.Tk()
            self.window.title(f"Раскрой: {project_name}")
            self.window.geometry("1200x800")
            self.window.configure(bg='white')
            
            # Заголовок
            header_frame = tk.Frame(self.window, bg='white')
            header_frame.pack(fill='x', padx=10, pady=5)
            
            tk.Label(header_frame, text=f"РАСКРОЙ: {project_name}", 
                    font=('Arial', 14, 'bold'), bg='white').pack(side='left')
            
            # Информация
            info_text = (f"Листов: {nesting_result['sheets_needed']} | "
                        f"Использование: {nesting_result['utilization_percent']:.1f}% | "
                        f"Обрезки: {nesting_result['overall_waste_percent']:.1f}%")
            tk.Label(header_frame, text=info_text, 
                    font=('Arial', 10), bg='white', fg='blue').pack(side='right')
            
            # Основной фрейм с Canvas
            main_frame = tk.Frame(self.window, bg='white')
            main_frame.pack(fill='both', expand=True, padx=10, pady=5)
            
            # Создаем Canvas с прокруткой
            canvas_frame = tk.Frame(main_frame, bg='white')
            canvas_frame.pack(fill='both', expand=True)
            
            self.canvas = tk.Canvas(canvas_frame, bg='white', 
                                  width=1000, height=600,
                                  scrollregion=(0, 0, 2000, 2000))
            
            # Скроллбары
            v_scrollbar = ttk.Scrollbar(canvas_frame, orient='vertical', command=self.canvas.yview)
            h_scrollbar = ttk.Scrollbar(canvas_frame, orient='horizontal', command=self.canvas.xview)
            self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
            
            # Размещаем элементы
            self.canvas.pack(side='left', fill='both', expand=True)
            v_scrollbar.pack(side='right', fill='y')
            h_scrollbar.pack(side='bottom', fill='x')
            
            # Привязываем события мыши для масштабирования
            self.canvas.bind('<Button-1>', self._on_canvas_click)
            self.canvas.bind('<B1-Motion>', self._on_canvas_drag)
            self.canvas.bind('<MouseWheel>', self._on_mouse_wheel)
            
            # Кнопки управления
            control_frame = tk.Frame(self.window, bg='white')
            control_frame.pack(fill='x', padx=10, pady=5)
            
            tk.Button(control_frame, text="Масштаб 1:1", 
                    command=lambda: self._set_scale(1.0)).pack(side='left', padx=5)
            tk.Button(control_frame, text="Поместить все", 
                    command=self._fit_to_window).pack(side='left', padx=5)
            tk.Button(control_frame, text="Центрировать", 
                    command=self._center_view).pack(side='left', padx=5)
            tk.Button(control_frame, text="Закрыть", 
                    command=self.window.destroy).pack(side='right', padx=5)
            
            # Рисуем раскрой
            self._draw_nesting(nesting_result)
            
            # Центрируем вид
            self._center_view()
            
            self.logger.info(f"✓ Окно раскроя открыто: {project_name}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания окна раскроя: {e}")
            messagebox.showerror("Ошибка", f"Не удалось создать окно раскроя:\n{e}")
    
    def _draw_nesting(self, nesting_result: Dict):
        """
        Рисуем раскрой на Canvas
        """
        try:
            # Очищаем Canvas
            self.canvas.delete("all")
            
            # Рассчитываем масштаб для помещения всех листов
            total_sheets = len(nesting_result['sheets'])
            if total_sheets == 0:
                return
            
            # Размеры для размещения всех листов
            sheets_per_row = min(2, total_sheets)  # Максимум 2 листа в ряд
            rows = math.ceil(total_sheets / sheets_per_row)
            
            # Размеры области для всех листов
            total_width = sheets_per_row * self.SHEET_WIDTH + (sheets_per_row - 1) * 100  # 100мм между листами
            total_height = rows * self.SHEET_HEIGHT + (rows - 1) * 100
            
            # Масштаб для помещения в окно
            canvas_width = 1000
            canvas_height = 600
            scale_w = canvas_width / total_width
            scale_h = canvas_height / total_height
            self.scale = min(scale_w, scale_h) * 0.8  # 80% от максимального размера
            
            # Рисуем каждый лист
            for idx, sheet in enumerate(nesting_result['sheets']):
                # Позиция листа
                col = idx % sheets_per_row
                row = idx // sheets_per_row
                
                sheet_x = col * (self.SHEET_WIDTH + 100) * self.scale
                sheet_y = row * (self.SHEET_HEIGHT + 100) * self.scale
                
                # Рисуем контур листа
                self._draw_sheet(sheet, sheet_x, sheet_y)
                
                # Рисуем детали
                self._draw_parts(sheet, sheet_x, sheet_y)
            
            # Обновляем область прокрутки
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка рисования раскроя: {e}")
    
    def _draw_sheet(self, sheet: Dict, x: float, y: float):
        """
        Рисуем контур листа
        """
        # Контур листа
        self.canvas.create_rectangle(
            x, y, 
            x + self.SHEET_WIDTH * self.scale, 
            y + self.SHEET_HEIGHT * self.scale,
            outline='black', width=3, fill='#f0f0f0'
        )
        
        # Подписи размеров
        self.canvas.create_text(
            x + self.SHEET_WIDTH * self.scale / 2, y - 20,
            text=f"ЛИСТ №{sheet['number']} (2500×1250 мм)",
            font=('Arial', 10, 'bold'), fill='red'
        )
        
        self.canvas.create_text(
            x - 30, y + self.SHEET_HEIGHT * self.scale / 2,
            text="1250 мм", font=('Arial', 8), fill='black'
        )
        
        self.canvas.create_text(
            x + self.SHEET_WIDTH * self.scale / 2, y + self.SHEET_HEIGHT * self.scale + 15,
            text="2500 мм", font=('Arial', 8), fill='black'
        )
        
        # Информация о листе
        info_text = (f"Деталей: {len(sheet['parts'])} | "
                    f"Использование: {100 - sheet['waste_percent']:.1f}% | "
                    f"Обрезки: {sheet['waste_percent']:.1f}%")
        self.canvas.create_text(
            x + self.SHEET_WIDTH * self.scale / 2, y + self.SHEET_HEIGHT * self.scale + 35,
            text=info_text, font=('Arial', 8), fill='blue'
        )
    
    def _draw_parts(self, sheet: Dict, sheet_x: float, sheet_y: float):
        """
        Рисуем детали на листе
        """
        for idx, part in enumerate(sheet['parts']):
            # Координаты детали в мм
            x_mm = part['x']
            y_mm = part['y']
            w_mm = part['width']
            h_mm = part['height']
            
            # Переводим в координаты Canvas
            x_canvas = sheet_x + x_mm * self.scale
            y_canvas = sheet_y + y_mm * self.scale
            w_canvas = w_mm * self.scale
            h_canvas = h_mm * self.scale
            
            # Цвет детали
            color = self.part_colors[idx % len(self.part_colors)]
            
            # Рисуем деталь
            self.canvas.create_rectangle(
                x_canvas, y_canvas,
                x_canvas + w_canvas, y_canvas + h_canvas,
                outline='black', width=1, fill=color
            )
            
            # Подпись детали (если помещается)
            if w_canvas > 50 and h_canvas > 30:
                # Сокращенное имя
                name = part['name'][:20] if len(part['name']) > 20 else part['name']
                
                # Размеры
                size_text = f"{w_mm:.0f}×{h_mm:.0f}"
                
                # Центрируем текст
                text_x = x_canvas + w_canvas / 2
                text_y = y_canvas + h_canvas / 2
                
                self.canvas.create_text(
                    text_x, text_y - 5,
                    text=name, font=('Arial', 7), fill='black'
                )
                self.canvas.create_text(
                    text_x, text_y + 5,
                    text=size_text, font=('Arial', 6), fill='black'
                )
                
                # Индикатор поворота
                if part.get('rotated'):
                    self.canvas.create_text(
                        text_x, text_y + 15,
                        text="[90°]", font=('Arial', 6), fill='red'
                    )
            else:
                # Маленькая деталь - номер
                self.canvas.create_text(
                    x_canvas + 5, y_canvas + 5,
                    text=f"#{idx+1}", font=('Arial', 6), fill='black'
                )
    
    def _on_canvas_click(self, event):
        """Обработка клика мыши"""
        self.last_x = event.x
        self.last_y = event.y
    
    def _on_canvas_drag(self, event):
        """Обработка перетаскивания"""
        if hasattr(self, 'last_x'):
            dx = event.x - self.last_x
            dy = event.y - self.last_y
            self.canvas.scan_dragto(dx, dy, gain=1)
            self.last_x = event.x
            self.last_y = event.y
    
    def _on_mouse_wheel(self, event):
        """Обработка колесика мыши для масштабирования"""
        if event.delta > 0:
            self.scale *= 1.1
        else:
            self.scale *= 0.9
        
        # Ограничиваем масштаб
        self.scale = max(0.1, min(5.0, self.scale))
        
        # Перерисовываем
        if hasattr(self, 'nesting_result'):
            self._draw_nesting(self.nesting_result)
    
    def _set_scale(self, scale: float):
        """Установить масштаб"""
        self.scale = scale
        if hasattr(self, 'nesting_result'):
            self._draw_nesting(self.nesting_result)
    
    def _fit_to_window(self):
        """Поместить все в окно"""
        self._set_scale(1.0)
        self._center_view()
    
    def _center_view(self):
        """Центрировать вид"""
        self.canvas.xview_moveto(0.5)
        self.canvas.yview_moveto(0.5)


if __name__ == "__main__":
    # Тест Canvas визуализатора
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    print("Модуль Canvas визуализатора готов!")
    print("\nИспользование:")
    print("  viewer = NestingCanvasViewer()")
    print("  viewer.show_nesting(nesting_result, 'project_name')")
