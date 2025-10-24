#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys

# Добавляем путь к модулям
sys.path.append(os.path.join(os.path.dirname(__file__), 'components'))

class SimpleGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Раскрой Деталей v2.0")
        self.root.geometry("800x600")
        
        # Переменные
        self.project_name = tk.StringVar()
        self.folder_path = tk.StringVar()
        
        self.create_widgets()
        
    def create_widgets(self):
        # Главный фрейм
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Название проекта
        ttk.Label(main_frame, text="Название проекта:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        ttk.Entry(main_frame, textvariable=self.project_name, width=50).grid(row=0, column=1, padx=(5, 0), pady=(0, 5), sticky=(tk.W, tk.E))
        
        # Выбор папки
        ttk.Label(main_frame, text="Папка с DXF файлами:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        folder_frame = ttk.Frame(main_frame)
        folder_frame.grid(row=1, column=1, padx=(5, 0), pady=(0, 5), sticky=(tk.W, tk.E))
        
        ttk.Entry(folder_frame, textvariable=self.folder_path, width=40).grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(folder_frame, text="Выбрать", command=self.select_folder).grid(row=0, column=1, padx=(5, 0))
        
        # Кнопки
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(20, 0), sticky=(tk.W, tk.E))
        
        ttk.Button(button_frame, text="Загрузить файлы", command=self.load_files).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(button_frame, text="Оптимизировать", command=self.optimize).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(button_frame, text="Создать отчеты", command=self.create_reports).grid(row=0, column=2)
        
        # Таблица
        self.tree = ttk.Treeview(main_frame, columns=('name', 'size', 'area'), show='headings', height=15)
        self.tree.heading('name', text='Название файла')
        self.tree.heading('size', text='Размер (мм)')
        self.tree.heading('area', text='Площадь (м²)')
        self.tree.grid(row=3, column=0, columnspan=2, pady=(20, 0), sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Скроллбар для таблицы
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=3, column=2, sticky=(tk.N, tk.S), pady=(20, 0))
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Настройка растягивания
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        folder_frame.columnconfigure(0, weight=1)
        
    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path.set(folder)
            
    def load_files(self):
        if not self.folder_path.get():
            messagebox.showwarning("Предупреждение", "Выберите папку с DXF файлами")
            return
            
        # Очищаем таблицу
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Загружаем файлы
        folder = self.folder_path.get()
        dxf_files = [f for f in os.listdir(folder) if f.endswith('.dxf')]
        
        for file in dxf_files:
            self.tree.insert('', 'end', values=(file, 'Не определен', 'Не рассчитано'))
            
        messagebox.showinfo("Информация", f"Загружено {len(dxf_files)} DXF файлов")
        
    def optimize(self):
        if not self.tree.get_children():
            messagebox.showwarning("Предупреждение", "Сначала загрузите файлы")
            return
            
        messagebox.showinfo("Информация", "Оптимизация запущена!\n(В полной версии здесь будет расчет раскроя)")
        
    def create_reports(self):
        if not self.tree.get_children():
            messagebox.showwarning("Предупреждение", "Сначала загрузите файлы")
            return
            
        project_name = self.project_name.get() or "Проект без названия"
        messagebox.showinfo("Информация", f"Создание отчетов для проекта: {project_name}\n(В полной версии здесь будет генерация PDF и Excel)")
        
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = SimpleGUI()
    app.run()
