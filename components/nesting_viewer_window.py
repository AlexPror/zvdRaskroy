#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Окно визуализации раскроя в GUI
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict
from PIL import Image, ImageTk

from .nesting_visualizer import NestingVisualizer


class NestingViewerWindow:
    """
    Окно для отображения раскроя в масштабе
    """
    
    def __init__(self, parent, nesting_result: Dict, project_name: str = "Проект"):
        self.parent = parent
        self.nesting_result = nesting_result
        self.project_name = project_name
        
        # Создаем окно
        self.window = tk.Toplevel(parent)
        self.window.title(f"Раскладка деталей: {project_name}")
        
        # Размер окна
        window_width = 1000
        window_height = 700
        
        # Центрируем
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        self.create_widgets()
        self.update_visualization()
    
    def create_widgets(self):
        """Создание виджетов"""
        
        # Заголовок
        header_frame = ttk.Frame(self.window, padding="10")
        header_frame.pack(fill=tk.X)
        
        ttk.Label(header_frame, 
                 text=f"📐 Раскладка: {self.project_name}",
                 font=('Arial', 14, 'bold')).pack(anchor=tk.W)
        
        # Информация
        info_frame = ttk.Frame(header_frame)
        info_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(info_frame, 
                 text=f"Листов: {self.nesting_result['sheets_needed']}",
                 font=('Arial', 10)).pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(info_frame,
                 text=f"Использование: {self.nesting_result['utilization_percent']:.1f}%",
                 font=('Arial', 10),
                 foreground='green').pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(info_frame,
                 text=f"Обрезки: {self.nesting_result['overall_waste_percent']:.1f}%",
                 font=('Arial', 10),
                 foreground='red').pack(side=tk.LEFT)
        
        # Разделитель
        ttk.Separator(self.window, orient='horizontal').pack(fill=tk.X, pady=5)
        
        # Canvas для изображения
        canvas_frame = ttk.Frame(self.window)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Создаем Canvas с прокруткой
        self.canvas = tk.Canvas(canvas_frame, bg='white')
        
        scrollbar_y = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        scrollbar_x = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        
        self.canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Кнопки
        buttons_frame = ttk.Frame(self.window, padding="10")
        buttons_frame.pack(fill=tk.X)
        
        ttk.Button(buttons_frame, text="Обновить", 
                  command=self.update_visualization).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(buttons_frame, text="Закрыть", 
                  command=self.window.destroy).pack(side=tk.RIGHT, padx=5)
    
    def update_visualization(self):
        """Обновление визуализации"""
        
        try:
            # Создаем изображение через визуализатор
            visualizer = NestingVisualizer()
            
            # Размер изображения под размер canvas
            canvas_width = 950
            canvas_height = 500
            
            img = visualizer.create_image_for_gui(
                self.nesting_result,
                canvas_width=canvas_width,
                canvas_height=canvas_height
            )
            
            if img:
                # Конвертируем в PhotoImage для tkinter
                self.photo = ImageTk.PhotoImage(img)
                
                # Очищаем canvas
                self.canvas.delete("all")
                
                # Отображаем изображение
                self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
                
                # Обновляем scrollregion
                self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            else:
                self.canvas.create_text(
                    475, 250,
                    text="Ошибка создания визуализации\nУстановите: pip install Pillow",
                    font=('Arial', 12),
                    fill='red',
                    justify=tk.CENTER
                )
        
        except Exception as e:
            self.canvas.create_text(
                475, 250,
                text=f"Ошибка визуализации:\n{str(e)}",
                font=('Arial', 12),
                fill='red',
                justify=tk.CENTER
            )
            import traceback
            traceback.print_exc()
    
    def update_nesting(self, new_nesting_result: Dict):
        """
        Обновление раскроя (при изменении параметров)
        """
        self.nesting_result = new_nesting_result
        self.update_visualization()


if __name__ == "__main__":
    # Тест окна
    print("Модуль окна визуализации готов!")
    print("\nИспользование:")
    print("  window = NestingViewerWindow(root, nesting_result, 'ZVD.LITE.140.300.2400')")

