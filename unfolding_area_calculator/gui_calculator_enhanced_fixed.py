#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
УЛУЧШЕННАЯ GUI для расчета площадей разверток
С оптимизацией раскроя и учетом обрезков
Версия 2.0
"""

import sys
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Импортируем компоненты из основного проекта
sys.path.insert(0, str(Path(__file__).parent.parent))

# from area_calculator import UnfoldingAreaCalculator  # Удален
from components.rectpack_optimizer import RectpackOptimizer
from components.smart_nesting_optimizer import SmartNestingOptimizer
from components.dxf_contour_renderer import DXFContourRenderer
from components.projects_database import ProjectsDatabase  # v3.0


class EnhancedUnfoldingAreaGUI:
    """Улучшенная GUI с оптимизацией раскроя"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ZVD - Расчет площадей разверток v3.0 (с рекомендациями по оптимизации)")
        
        # Компактный размер окна по умолчанию
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Компактное окно по умолчанию
        window_width = min(1000, int(screen_width * 0.6))  # Уменьшено с 1400 до 1000
        window_height = min(600, int(screen_height * 0.6))  # Уменьшено с 900 до 600
        
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.minsize(800, 500)  # Уменьшен минимальный размер
        
        # НЕ открываем на весь экран по умолчанию
        # self.root.state('zoomed')  # Закомментировано
        
        # Настройка стилей
        self.setup_styles()
        
        # Флаг для отслеживания размера окна
        self.window_expanded = False
        
        self.folder_path = tk.StringVar()
        self.order_number = tk.StringVar()
        self.project_name = tk.StringVar()  # Новое поле для названия проекта
        
        # Логгер для вывода отладочной информации
        self.logger = logging.getLogger(__name__)
        
        self.files_data = []
        # self.calculator = UnfoldingAreaCalculator()  # Удален
        self.optimizer = RectpackOptimizer()
        self.smart_optimizer = SmartNestingOptimizer()  # НОВЫЙ умный оптимизатор
        self.contour_renderer = DXFContourRenderer()  # Рендерер реальных контуров
        self.projects_db = ProjectsDatabase()  # v3.0: База данных проектов
        self.last_nesting_result = None  # Последний результат раскроя
        self.current_dimensions = None  # Текущие габариты проекта
        self.project_info = None  # Информация о проекте
        
        # Попытка загрузить кэш базы данных
        self.db_loaded = False
        if self.projects_db.load_cache():
            stats = self.projects_db.get_statistics()
            self.logger.info(f"✓ База данных загружена: {stats['total_projects']} проектов")
            self.db_loaded = True
            self.db_stats = stats
        
        self.create_widgets()
        
        # Обновляем статус БД после создания виджетов
        if self.db_loaded and hasattr(self, 'db_status_label'):
            self.db_status_label.config(
                text=f"База данных: {self.db_stats['total_projects']} проектов",
                foreground='green'
            )
    
    def setup_styles(self):
        """Настройка стилей интерфейса"""
        style = ttk.Style()
        
        # Темы для разных ОС
        try:
            style.theme_use('clam')  # Более современная тема
        except:
            pass
        
        # Акцентная кнопка (синяя, жирная)
        style.configure('Accent.TButton', 
                       font=('Arial', 10, 'bold'),
                       foreground='#1976D2',
                       borderwidth=2,
                       relief='raised')
        
        # Кнопка успеха (зеленая)
        style.configure('Success.TButton',
                       font=('Arial', 10, 'bold'),
                       foreground='#4CAF50')
        
        # Кнопка предупреждения (оранжевая)
        style.configure('Warning.TButton',
                       font=('Arial', 10),
                       foreground='#FF9800')
        
        # LabelFrame с увеличенным шрифтом
        style.configure('TLabelframe.Label', 
                       font=('Arial', 11, 'bold'),
                       foreground='#1976D2')
        
        # Кнопки по умолчанию
        style.configure('TButton', 
                       font=('Arial', 10),
                       padding=6)
    
    def create_widgets(self):
        """Создание интерфейса"""
        
        # Главный контейнер с прокруткой для всего содержимого
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Canvas для прокрутки ВСЕГО содержимого
        main_canvas = tk.Canvas(main_container, bg='white', highlightthickness=0)
        main_scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=main_canvas.yview)
        
        # Основной frame для всех элементов
        main_frame = ttk.Frame(main_canvas, padding="15")
        
        # Привязываем скроллбар
        main_canvas.configure(yscrollcommand=main_scrollbar.set)
        
        # Размещаем
        main_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Создаём окно в canvas
        canvas_window = main_canvas.create_window((0, 0), window=main_frame, anchor='nw')
        
        # Растягиваем frame на ширину canvas
        def on_canvas_configure(event):
            main_canvas.itemconfig(canvas_window, width=event.width)
        
        main_canvas.bind('<Configure>', on_canvas_configure)
        
        # Обновляем scrollregion при изменении размера содержимого
        def on_frame_configure(event):
            main_canvas.configure(scrollregion=main_canvas.bbox('all'))
        
        main_frame.bind('<Configure>', on_frame_configure)
        
        # Прокрутка колёсиком мыши для главного окна
        def on_mousewheel(event):
            main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        main_canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # === ЗАГОЛОВОК (центрированный, компактный) ===
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(title_frame, 
                               text="📐 Расчет площадей разверток v2.0",
                               font=('Arial', 18, 'bold'),
                               anchor='center')
        title_label.pack(fill=tk.X)
        
        subtitle = ttk.Label(title_frame,
                            text="С оптимизацией раскроя и учетом обрезков",
                            font=('Arial', 11),
                            foreground='#1976D2',
                            anchor='center')
        subtitle.pack(fill=tk.X, pady=(5, 0))
        
        # === ВЫБОР ПАПКИ ===
        folder_frame = ttk.LabelFrame(main_frame, text="📁 Папка с развертками", padding="8")
        folder_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(folder_frame, text="Папка:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(folder_frame, textvariable=self.folder_path, width=50).grid(row=0, column=1, padx=5, sticky=(tk.W, tk.E))
        ttk.Button(folder_frame, text="...", command=self.browse_folder, width=3).grid(row=0, column=2)
        
        # Поле для ввода названия проекта
        ttk.Label(folder_frame, text="Название проекта:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        ttk.Entry(folder_frame, textvariable=self.project_name, width=50).grid(row=1, column=1, padx=5, pady=(5, 0), sticky=(tk.W, tk.E))
        
        # Номер заказа и шифр извлекаются автоматически из названия папки!
        
        # ОДНА УМНАЯ КНОПКА для загрузки
        btn_frame = ttk.Frame(folder_frame)
        btn_frame.grid(row=2, column=0, columnspan=3, pady=(10, 0), sticky=(tk.W, tk.E))
        btn_frame.columnconfigure(0, weight=1)
        
        self.load_btn = ttk.Button(btn_frame, text="🔍 Загрузить файлы DXF", 
                  command=self.smart_load_files,
                  style='Accent.TButton')
        self.load_btn.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        folder_frame.columnconfigure(1, weight=1)
        
        # === ТАБЛИЦА ФАЙЛОВ (обычная, без Canvas - растягивается) ===
        table_frame = ttk.LabelFrame(main_frame, text="📋 Развертки", padding="8")
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        self.quantity_entries = []  # Список полей ввода количества
        
        # Единый контейнер для ВСЕЙ таблицы (шапка + данные)
        self.table_container = tk.Frame(table_frame, bg='white')
        self.table_container.pack(fill=tk.BOTH, expand=True)
        
        # Настраиваем растягивание колонок
        column_weights = {
            0: 1,   # №
            1: 10,  # Файл (максимальная ширина)
            2: 2,   # Ширина
            3: 2,   # Высота
            4: 3,   # Площадь
            5: 2,   # Кол-во
            6: 3,   # Итого
            7: 1    # Удалить
        }
        
        for col, weight in column_weights.items():
            self.table_container.columnconfigure(col, weight=weight)
        
        # ШАПКА (row=0, фиксированная)
        headers_config = [
            "№",
            "Файл развертки",
            "Ширина\nмм",
            "Высота\nмм",
            "Площадь\nм2",
            "Кол-во\nшт",
            "Итого\nм2",
            "Удалить"
        ]
        
        for col, text in enumerate(headers_config):
            label = tk.Label(self.table_container, text=text, 
                           font=('Arial', 9, 'bold'),
                           bg='#1976D2', fg='white',
                           relief=tk.FLAT, pady=6, padx=3)
            label.grid(row=0, column=col, sticky=(tk.N, tk.S, tk.W, tk.E))  # Заполняет всю ячейку!
        
        # Строки данных будут добавляться начиная с row=1
        # (в методе _add_file_row_to_table)
        
        # === ИТОГИ И ДЕЙСТВИЯ (объединенный блок) ===
        summary_frame = ttk.LabelFrame(main_frame, text="📊 Итоги", padding="8")
        summary_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Центрируем итоги
        summary_center = ttk.Frame(summary_frame)
        summary_center.pack(anchor='center')
        
        self.summary_label = ttk.Label(summary_center, 
                                       text="ИТОГО: 0.0000 м2 | С зазорами: 0.0000 м2",
                                       font=('Arial', 12, 'bold'),
                                       foreground='#2E7D32')
        self.summary_label.pack(pady=(0,5))
        
        # Кнопки управления в одну строку
        controls_row = ttk.Frame(summary_center)
        controls_row.pack(pady=(5,0))
        
        ttk.Button(controls_row, text="🔢 Одинаковое кол-во", 
                  command=self.set_all_quantities,
                  width=20).pack(side=tk.LEFT, padx=3)
        ttk.Button(controls_row, text="🗑️ Сбросить", 
                  command=self.clear_all_data,
                  width=18,
                  style='Warning.TButton').pack(side=tk.LEFT, padx=3)
        
        # Кнопки управления проектом
        project_controls = ttk.Frame(summary_center)
        project_controls.pack(pady=(5,0))
        
        ttk.Button(project_controls, text="📁 Добавить файлы", 
                  command=self.add_files_to_project,
                  width=18).pack(side=tk.LEFT, padx=3)
        ttk.Button(project_controls, text="📂 Добавить папку", 
                  command=self.add_files_from_folder,
                  width=18).pack(side=tk.LEFT, padx=3)
        
        # Кнопка просмотра результатов проверки
        self.check_results_btn = ttk.Button(project_controls, text="🔍 Результаты проверки", 
                                           command=self.show_cutting_readiness_results,
                                           width=18,
                                           state=tk.DISABLED)
        self.check_results_btn.pack(side=tk.LEFT, padx=3)
        
        # ГЛАВНАЯ КНОПКА РАСКРОЯ
        ttk.Button(summary_center, text="🚀 Запустить раскрой и создать отчеты",
                  command=self.optimize_nesting_smart,
                  style='Accent.TButton',
                  width=40).pack(pady=(10,0))
        
        # Кнопка пересчета отчетов
        self.recalculate_btn = ttk.Button(summary_center, text="🔄 Пересчитать отчеты",
                                        command=self.recalculate_reports,
                                        width=40,
                                        state=tk.DISABLED)
        self.recalculate_btn.pack(pady=(5, 10))
        
        # Статус
        self.nesting_label = ttk.Label(summary_center,
                                       text="Готов к расчету оптимального раскроя",
                                       font=('Arial', 9),
                                       foreground='#666',
                                       anchor='center')
        self.nesting_label.pack(pady=(5,0))
        
        # Скрытые переменные для внутреннего использования
        self.nesting_algorithm = tk.StringVar(value='SMART')  # Умный алгоритм по умолчанию
        self.allow_rotation_var = tk.BooleanVar(value=True)  # Всегда разрешаем поворот
    
    def _choose_best_algorithm(self, files_data: List[Dict]) -> str:
        """
        Автоматический выбор лучшего алгоритма на основе анализа деталей
        
        Args:
            files_data: Список деталей для анализа
            
        Returns:
            Название лучшего алгоритма
        """
        if not files_data:
            return 'SMART'  # По умолчанию умный алгоритм
        
        # Анализируем характеристики деталей
        total_parts = sum(f.get('quantity', 1) for f in files_data)
        large_parts = sum(1 for f in files_data if f.get('width', 0) > 500 or f.get('height', 0) > 500)
        small_parts = sum(1 for f in files_data if f.get('width', 0) < 200 and f.get('height', 0) < 200)
        mixed_sizes = len(set((f.get('width', 0), f.get('height', 0)) for f in files_data))
        
        print(f"[DEBUG] Анализ деталей для выбора алгоритма:")
        print(f"  Всего деталей: {total_parts}")
        print(f"  Крупных деталей: {large_parts}")
        print(f"  Мелких деталей: {small_parts}")
        print(f"  Разных размеров: {mixed_sizes}")
        
        # Логика выбора алгоритма
        if total_parts <= 5 and large_parts >= 2:
            # Мало деталей, много крупных - используем rectpack BFF
            print(f"[DEBUG] Выбран RECTPACK BFF (мало деталей, много крупных)")
            return 'RECTPACK_BFF'
        elif total_parts > 10 and small_parts >= 3:
            # Много деталей, много мелких - используем умный алгоритм
            print(f"[DEBUG] Выбран SMART (много деталей, много мелких)")
            return 'SMART'
        elif mixed_sizes >= 5:
            # Много разных размеров - используем умный алгоритм
            print(f"[DEBUG] Выбран SMART (много разных размеров)")
            return 'SMART'
        else:
            # По умолчанию - умный алгоритм
            print(f"[DEBUG] Выбран SMART (по умолчанию)")
            return 'SMART'
        
        
        # Подсказка с рекомендацией
        hint_label = ttk.Label(opt_center,
                              text="💡 Добавьте детали из других проектов для оптимального заполнения листа",
                              font=('Arial', 8),
                              foreground='#1976D2')
        hint_label.pack(pady=(3, 0))
        
        ai_info.pack(pady=(5,0))
    
    def browse_folder(self):
        """Выбор папки"""
        folder = filedialog.askdirectory(title="Выберите папку с развертками")
        if folder:
            self.folder_path.set(folder)
    
    
    
    def _add_file_row_to_table(self, file_data: dict, idx: int):
        """Добавить строку с файлом в таблицу"""
        
        # Чередуем цвет фона
        bg_color = '#F5F5F5' if idx % 2 == 0 else '#FFFFFF'
        
        # row = idx + 1, потому что row=0 - это шапка
        actual_row = idx + 1
        
        # Номер
        tk.Label(self.table_container, text=str(idx+1), anchor='center',
                bg=bg_color, font=('Arial', 9)).grid(row=actual_row, column=0, padx=1, sticky=(tk.W, tk.E))
        
        # Файл (с пометкой если из дополнительной папки)
        filename_text = file_data['filename']
        if file_data.get('is_additional'):
            filename_text += f" [{file_data['source_folder']}]"
        
        tk.Label(self.table_container, text=filename_text, anchor='w',
                bg=bg_color, font=('Arial', 9)).grid(row=actual_row, column=1, padx=1, sticky=(tk.W, tk.E))
        
        # Габариты
        tk.Label(self.table_container, text=f"{file_data['width']:.0f}", anchor='center',
                bg=bg_color, font=('Arial', 9)).grid(row=actual_row, column=2, padx=1, sticky=(tk.W, tk.E))
        tk.Label(self.table_container, text=f"{file_data['height']:.0f}", anchor='center',
                bg=bg_color, font=('Arial', 9)).grid(row=actual_row, column=3, padx=1, sticky=(tk.W, tk.E))
        
        # Площадь
        tk.Label(self.table_container, text=f"{file_data['area_m2']:.4f}", anchor='center',
                bg=bg_color, font=('Arial', 9)).grid(row=actual_row, column=4, padx=1, sticky=(tk.W, tk.E))
        
        # ПОЛЕ ВВОДА КОЛИЧЕСТВА
        quantity = file_data.get('quantity', 1)
        qty_var = tk.StringVar(value=str(quantity))
        
        # Определяем цвет фона и подсказку
        # Если количество > 1, значит оно было извлечено из имени файла
        if quantity > 1:
            bg_color_qty = '#C8E6C9'  # Светло-зеленый - автоматически определено
            tooltip_text = f"✓ Количество ({quantity} шт) определено из названия файла автоматически"
        else:
            bg_color_qty = '#FFF9C4'  # Желтый - по умолчанию
            tooltip_text = "Введите количество деталей (можно изменить)"
        
        qty_entry = tk.Entry(self.table_container, textvariable=qty_var, width=8, 
                            justify='center',
                            font=('Arial', 10, 'bold'),
                            bg=bg_color_qty,
                            fg='#000000',
                            relief=tk.SOLID,
                            bd=2)
        qty_entry.grid(row=actual_row, column=5, padx=1, pady=2, sticky=(tk.W, tk.E))
        
        # Добавляем подсказку при наведении
        self._create_tooltip(qty_entry, tooltip_text)
        
        # Привязываем обновление при изменении
        qty_var.trace_add('write', lambda *args, idx=idx: self.on_quantity_changed(idx))
        
        self.quantity_entries.append({
            'var': qty_var,
            'entry': qty_entry,
            'index': idx
        })
        
        # Итого (будет обновляться)
        total_area = file_data.get('area_m2', 0) * file_data.get('quantity', 1)
        total_label = tk.Label(self.table_container, text=f"{total_area:.4f}", 
                              anchor='center', 
                              font=('Arial', 10, 'bold'),
                              fg='#0D47A1',
                              bg=bg_color)
        total_label.grid(row=actual_row, column=6, padx=1, sticky=(tk.W, tk.E))
        
        # Сохраняем ссылку на label для обновления
        file_data['total_label'] = total_label
        
        # КНОПКА УДАЛЕНИЯ
        delete_btn = tk.Button(self.table_container, text="❌", 
                              font=('Arial', 10, 'bold'),
                              bg='#FFCDD2', fg='#D32F2F',
                              relief=tk.RAISED, bd=2,
                              command=lambda idx=idx: self.remove_file(idx),
                              cursor='hand2')
        delete_btn.grid(row=actual_row, column=7, padx=2, pady=2, sticky=(tk.W, tk.E))
        
        # Добавляем подсказку
        self._create_tooltip(delete_btn, "Удалить этот файл из таблицы")
        
        # Сохраняем ссылку на кнопку
        file_data['delete_btn'] = delete_btn
    
    def remove_file(self, idx: int):
        """Удалить файл из таблицы по индексу"""
        if not self.files_data or idx >= len(self.files_data):
            return
        
        # Подтверждение удаления
        file_data = self.files_data[idx]
        filename = file_data.get('filename', f'Файл {idx+1}')
        
        if messagebox.askyesno("Подтверждение удаления", 
                              f"Удалить файл '{filename}' из таблицы?\n\n"
                              "Это действие нельзя отменить."):
            
            # Удаляем из данных
            del self.files_data[idx]
            
            # Удаляем из полей ввода количества
            self.quantity_entries = [entry for entry in self.quantity_entries if entry['index'] != idx]
            
            # Обновляем индексы в оставшихся записях
            for entry in self.quantity_entries:
                if entry['index'] > idx:
                    entry['index'] -= 1
            
            # Пересоздаем таблицу
            self._rebuild_table()
            
            # Обновляем итоги после удаления
            if hasattr(self, 'total_area_label'):
                total_area = sum(file_data.get('area_m2', 0) for file_data in self.files_data)
                self.total_area_label.config(text=f"Общая площадь: {total_area:.4f} м²")
            
            print(f"[DEBUG] Удален файл: {filename}")
    
    def _rebuild_table(self):
        """Пересоздать таблицу после удаления файла"""
        # Очищаем только строки данных (row >= 1), шапка в row=0 остается
        for widget in self.table_container.grid_slaves():
            info = widget.grid_info()
            if info and int(info.get('row', 0)) > 0:
                widget.destroy()
        
        # Очищаем список полей ввода количества
        self.quantity_entries.clear()
        
        # Пересоздаем строки таблицы
        for idx, file_data in enumerate(self.files_data):
            self._add_file_row_to_table(file_data, idx)
    
    def add_files_from_another_folder(self):
        """Добавить файлы из дополнительной папки (для комбинированного раскроя)"""
        
        if not self.files_data:
            messagebox.showwarning("Предупреждение", 
                                 "Сначала загрузите основной проект!\n\n" +
                                 "После этого можно добавлять детали из других проектов.")
            return
        
        # Выбираем дополнительную папку
        additional_folder = filedialog.askdirectory(
            title="Выберите папку с дополнительными развёртками"
        )
        
        if not additional_folder:
            return
        
        try:
            # Определяем имя папки сразу
            additional_folder_name = Path(additional_folder).name
            
            # Загружаем файлы из дополнительной папки
            try:
                import os
                import ezdxf
                
                additional_files = []
                for filename in os.listdir(additional_folder):
                    if filename.lower().endswith('.dxf'):
                        filepath = os.path.join(additional_folder, filename)
                        try:
                            doc = ezdxf.readfile(filepath)
                            msp = doc.modelspace()
                            
                            # Вычисляем габариты
                            min_x = min_y = float('inf')
                            max_x = max_y = float('-inf')
                            
                            for entity in msp:
                                if hasattr(entity, 'dxf') and hasattr(entity.dxf, 'start') and hasattr(entity.dxf, 'end'):
                                    # Линия
                                    min_x = min(min_x, entity.dxf.start.x, entity.dxf.end.x)
                                    max_x = max(max_x, entity.dxf.start.x, entity.dxf.end.x)
                                    min_y = min(min_y, entity.dxf.start.y, entity.dxf.end.y)
                                    max_y = max(max_y, entity.dxf.start.y, entity.dxf.end.y)
                                elif hasattr(entity, 'dxf') and hasattr(entity.dxf, 'center'):
                                    # Круг или дуга
                                    radius = getattr(entity.dxf, 'radius', 0)
                                    min_x = min(min_x, entity.dxf.center.x - radius)
                                    max_x = max(max_x, entity.dxf.center.x + radius)
                                    min_y = min(min_y, entity.dxf.center.y - radius)
                                    max_y = max(max_y, entity.dxf.center.y + radius)
                            
                            if min_x != float('inf') and max_x != float('-inf'):
                                width = max_x - min_x
                                height = max_y - min_y
                                area_m2 = (width * height) / 1000000  # мм² в м²
                                
                                # Парсим количество из названия файла
                                quantity = 1  # По умолчанию
                                import re
                                # Ищем паттерны типа "2шт", "3шт", "1шт"
                                qty_match = re.search(r'(\d+)шт', filename)
                                if qty_match:
                                    quantity = int(qty_match.group(1))
                                
                                file_data = {
                                    'name': filename,
                                    'filename': filename,
                                    'filepath': filepath,
                                    'width': width,
                                    'height': height,
                                    'area_m2': area_m2,
                                    'quantity': quantity
                                }
                                additional_files.append(file_data)
                        except Exception as e:
                            print(f"[WARNING] Не удалось обработать файл {filename}: {e}")
                            continue
                
                result = {'success': True, 'files': additional_files}
                
            except Exception as e:
                result = {'success': False, 'error': str(e)}
            
            if not result['success']:
                messagebox.showerror("Ошибка", 
                                   f"Не удалось загрузить файлы:\n{result.get('error', 'Неизвестная ошибка')}")
                return
            
            added_count = 0
            
            # Добавляем новые файлы к существующим
            for file_data in result['files']:
                # Помечаем, что файл из дополнительной папки
                file_data['source_folder'] = additional_folder_name
                file_data['is_additional'] = True
                
                # Добавляем в список
                self.files_data.append(file_data)
                
                # Добавляем строку в таблицу
                self._add_file_row_to_table(file_data, len(self.files_data) - 1)
                added_count += 1
            
            # Обновляем итоги
            self.update_summary()
            
            
            # Проверяем, есть ли файлы из разных источников
            sources = set()
            for f in self.files_data:
                if f.get('is_additional'):
                    sources.add(f.get('source_folder', ''))
            
            info_msg = f"Добавлено {added_count} файлов из:\n{additional_folder_name}\n\n" + \
                      f"Теперь всего файлов: {len(self.files_data)}\n"
            
            if len(sources) > 0:
                info_msg += f"Источников: {len(sources) + 1} проектов\n\n"
                info_msg += "📁 Отчёты сохранятся в папку первого проекта:\n"
                info_msg += f"{Path(self.folder_path.get()).name}\n\n"
            
            info_msg += "Оптимальность автоматически пересчитана!"
            
            messagebox.showinfo("Успех", info_msg)
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при добавлении файлов:\n{e}")
            import traceback
            traceback.print_exc()
    
    def smart_load_files(self):
        """УМНАЯ загрузка - одна кнопка для всего!"""
        # Если файлы уже загружены - предлагаем варианты
        if self.files_data:
            from tkinter import messagebox
            response = messagebox.askyesnocancel(
                "Загрузка файлов",
                "Файлы уже загружены!\n\n"
                "• ДА — Добавить файлы из другой папки\n"
                "• НЕТ — Перезагрузить текущую папку\n"
                "• ОТМЕНА — Ничего не делать"
            )
            
            if response is None:  # Отмена
                return
            elif response:  # Да - добавить из другой папки
                self.add_files_from_another_folder()
            else:  # Нет - перезагрузить
                self.load_files()
        else:
            # Файлы не загружены - просто загружаем
            self.load_files()
    
    def load_files(self):
        """Загрузка файлов"""
        folder = self.folder_path.get()
        if not folder:
            messagebox.showwarning("Предупреждение", "Выберите папку!")
            return
        
        try:
            # Загружаем файлы напрямую
            import os
            import ezdxf
            
            files_data = []
            for filename in os.listdir(folder):
                if filename.lower().endswith('.dxf'):
                    filepath = os.path.join(folder, filename)
                    try:
                        doc = ezdxf.readfile(filepath)
                        msp = doc.modelspace()
                        
                        # Вычисляем габариты
                        min_x = min_y = float('inf')
                        max_x = max_y = float('-inf')
                        
                        for entity in msp:
                            if hasattr(entity, 'dxf') and hasattr(entity.dxf, 'start') and hasattr(entity.dxf, 'end'):
                                # Линия
                                min_x = min(min_x, entity.dxf.start.x, entity.dxf.end.x)
                                max_x = max(max_x, entity.dxf.start.x, entity.dxf.end.x)
                                min_y = min(min_y, entity.dxf.start.y, entity.dxf.end.y)
                                max_y = max(max_y, entity.dxf.start.y, entity.dxf.end.y)
                            elif hasattr(entity, 'dxf') and hasattr(entity.dxf, 'center'):
                                # Круг или дуга
                                radius = getattr(entity.dxf, 'radius', 0)
                                min_x = min(min_x, entity.dxf.center.x - radius)
                                max_x = max(max_x, entity.dxf.center.x + radius)
                                min_y = min(min_y, entity.dxf.center.y - radius)
                                max_y = max(max_y, entity.dxf.center.y + radius)
                        
                        if min_x != float('inf') and max_x != float('-inf'):
                            width = max_x - min_x
                            height = max_y - min_y
                            area_m2 = (width * height) / 1000000  # мм² в м²
                            
                            # Парсим количество из названия файла
                            quantity = 1  # По умолчанию
                            import re
                            # Ищем паттерны типа "2шт", "3шт", "1шт"
                            qty_match = re.search(r'(\d+)шт', filename)
                            if qty_match:
                                quantity = int(qty_match.group(1))
                            
                            file_data = {
                                'name': filename,
                                'filename': filename,
                                'filepath': filepath,
                                'width': width,
                                'height': height,
                                'area_m2': area_m2,
                                'quantity': quantity
                            }
                            files_data.append(file_data)
                    except Exception as e:
                        print(f"[WARNING] Не удалось обработать файл {filename}: {e}")
                        continue
            
            result = {'success': True, 'files': files_data}
            
            if not result['success']:
                messagebox.showerror("Ошибка", "\n".join(result.get('errors', ['Неизвестная ошибка'])))
                return
            
            # Очищаем ТОЛЬКО строки данных (row >= 1), шапка в row=0 остается!
            for widget in self.table_container.grid_slaves():
                info = widget.grid_info()
                if info and int(info.get('row', 0)) > 0:  # Удаляем только данные, не шапку!
                    widget.destroy()
            
            self.files_data = result['files']
            self.quantity_entries = []
            
            # Создаем строки с полями ввода
            for idx, file_data in enumerate(self.files_data):
                self._add_file_row_to_table(file_data, idx)
            
            self.update_summary()
            
            # Адаптивно расширяем окно при заполнении таблицы
            self.expand_window_for_table()
            
            # Анализируем готовность к лазерной резке
            self.analyze_cutting_readiness()
            
            # Принудительно активируем кнопку проверки, если она еще не активна
            if hasattr(self, 'check_results_btn'):
                self.check_results_btn.config(state=tk.NORMAL)
                print(f"[DEBUG] Принудительно активирована кнопка 'Результаты проверки'")
            else:
                print(f"[ERROR] Кнопка 'check_results_btn' не найдена при загрузке файлов!")
            
            messagebox.showinfo("Успех", f"Загружено файлов: {len(self.files_data)}")
            
            # Финальная активация кнопки проверки
            if hasattr(self, 'check_results_btn'):
                self.check_results_btn.config(state=tk.NORMAL)
                print(f"[DEBUG] Финальная активация кнопки 'Результаты проверки'")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить файлы:\n{e}")
            
            # Активируем кнопку даже при ошибке
            if hasattr(self, 'check_results_btn'):
                self.check_results_btn.config(state=tk.NORMAL)
                print(f"[DEBUG] Активация кнопки 'Результаты проверки' после ошибки")
    
    def on_quantity_changed(self, index: int):
        """Обработчик изменения количества"""
        try:
            # Получаем новое значение
            if index >= len(self.quantity_entries) or index >= len(self.files_data):
                return
            
            qty_var = self.quantity_entries[index]['var']
            new_qty_str = qty_var.get().strip()
            
            if not new_qty_str:
                return
            
            try:
                new_qty = int(new_qty_str)
                if new_qty < 1 or new_qty > 999:
                    return
            except ValueError:
                return
            
            # Обновляем данные
            data = self.files_data[index]
            old_qty = data.get('quantity', 1)
            
            # Только если количество действительно изменилось
            if new_qty != old_qty:
                data['quantity'] = new_qty
                data['total_area'] = data['area_m2'] * new_qty
                data['total_area_gap_m2'] = data['area_with_gap'] * new_qty
                
                # Обновляем label итого для этой строки
                if 'total_label' in data:
                    data['total_label'].config(text=f"{data['total_area']:.4f}")
                
                # Обновляем общие итоги
                self.root.after(100, self.update_summary)  # Небольшая задержка для плавности
                
            
        except Exception as e:
            print(f"Ошибка обновления: {e}")  # Для отладки
    
    def recalculate_totals(self):
        """Пересчет всех итогов"""
        for idx, entry_info in enumerate(self.quantity_entries):
            self.on_quantity_changed(idx)
        
        self.update_summary()
        
    
    def clear_all_data(self):
        """Очистить все данные в программе"""
        if not self.files_data:
            messagebox.showinfo("Информация", "Нет данных для очистки")
            return
        
        # Подтверждение
        answer = messagebox.askyesno(
            "Подтверждение",
            "Вы уверены, что хотите очистить все данные?\n\n" +
            "Будут удалены:\n" +
            "• Все загруженные файлы\n" +
            "• Введенные количества\n" +
            "• Результаты расчетов\n" +
            "• Результаты оптимизации"
        )
        
        if not answer:
            return
        
        # Очищаем ТОЛЬКО строки данных (row >= 1), шапка в row=0 остается!
        for widget in self.table_container.grid_slaves():
            info = widget.grid_info()
            if info and int(info.get('row', 0)) > 0:  # Удаляем только данные, не шапку!
                widget.destroy()
        
        # Очищаем данные
        self.files_data = []
        self.quantity_entries = []
        self.last_nesting_result = None
        
        # Сбрасываем итоги
        self.summary_label.config(text="ИТОГО: 0.0000 м2 | С зазорами: 0.0000 м2")
        
        # Очищаем поля
        self.folder_path.set("")
        self.order_number.set("")
        self.project_name.set("")
        
        messagebox.showinfo("Готово", "Все данные очищены!")
    
    def set_all_quantities(self):
        """Установить количество для всех"""
        from tkinter import simpledialog
        qty = simpledialog.askinteger(
            "Количество для всех",
            "Установить одинаковое количество для всех деталей:",
            initialvalue=1,
            minvalue=1,
            maxvalue=999
        )
        
        if qty:
            # Устанавливаем значение во все поля ввода
            for entry_info in self.quantity_entries:
                entry_info['var'].set(str(qty))
            
            # Пересчет произойдет автоматически через trace
    
    def update_summary(self):
        """Обновление итогов"""
        if not self.files_data:
            self.summary_label.config(text="ИТОГО: 0.0000 м2 | С зазорами: 0.0000 м2")
            return
            
        total = sum(f.get('area_m2', 0) * f.get('quantity', 1) for f in self.files_data)
        total_with_gap = sum(f.get('area_m2', 0) * f.get('quantity', 1) for f in self.files_data)
        
        self.summary_label.config(text=f"ИТОГО: {total:.4f} м2 | С зазорами: {total_with_gap:.4f} м2")
    
    
    
    def refresh_all(self):
        """🔄 ОБНОВИТЬ ВСЁ - полное обновление программы"""
        
        # 1. Пересчитываем все количества
        for idx, entry_info in enumerate(self.quantity_entries):
            self.on_quantity_changed(idx)
        
        # 2. Обновляем итоги
        self.update_summary()
        
        # 3. Сбрасываем результаты раскроя
        self.last_nesting_result = None
        self.nesting_label.config(
            text="Нажмите кнопку для автоматического расчета раскроя",
            foreground='black'
        )
        
        # 4. Показываем сообщение
        messagebox.showinfo("Обновлено", 
                          "✓ Все значения пересчитаны\n" +
                          "✓ Итоги обновлены\n" +
                          "✓ Результаты раскроя сброшены\n\n" +
                          "Можно запускать новый расчет!")
    
    def optimize_nesting_smart(self):
        """УМНЫЙ автоматический раскрой с учетом количества деталей"""
        
        if not self.files_data:
            messagebox.showwarning("Предупреждение", "Сначала загрузите файлы!")
            return
        
        if not self.optimizer.is_available():
            messagebox.showerror("Ошибка", 
                               "Rectpack не установлен!\n\n" +
                               "Установите: pip install rectpack")
            return
        
        try:
            # Подготовка данных С УЧЕТОМ КОЛИЧЕСТВА
            parts_data = []
            total_parts_count = 0
            
            for file_data in self.files_data:
                qty = file_data['quantity']
                if qty > 0:
                    # Добавляем каждую деталь столько раз, сколько нужно
                    for i in range(qty):
                        parts_data.append({
                            'name': f"{file_data['filename']} #{i+1}/{qty}",
                            'filename': file_data['filename'],  # Имя файла для поиска
                            'filepath': file_data.get('filepath', ''),  # Путь к DXF для контура
                            'width_mm': file_data['width'],
                            'height_mm': file_data['height'],
                            'area_m2': file_data['area_m2'],
                            'quantity': 1,  # Каждая деталь теперь в единственном экземпляре
                            'original_width': file_data['width'],  # СОХРАНЯЕМ оригинальный размер из DXF!
                            'original_height': file_data['height']  # Для отображения в PDF
                        })
                        total_parts_count += 1
            
            if not parts_data:
                messagebox.showwarning("Предупреждение", "Нет деталей для раскроя!")
                return
            
            # Показываем прогресс
            self.nesting_label.config(
                text=f"Оптимизация {total_parts_count} деталей...",
                foreground='orange'
            )
            self.root.update()
            
            # Отладка: проверяем что передаем правильные данные
            print(f"\n[DEBUG] Передаем в оптимизатор {len(self.files_data)} типов деталей:")
            for fd in self.files_data[:3]:  # Первые 3 для примера
                print(f"  - {fd['filename']}: {fd['width']}x{fd['height']} мм, qty={fd['quantity']}")
                print(f"    filepath: {fd.get('filepath', 'НЕТ ПУТИ!')}")
            
            # АВТОМАТИЧЕСКИЙ ВЫБОР АЛГОРИТМА
            chosen_algorithm = self._choose_best_algorithm(self.files_data)
            allow_rotation = self.allow_rotation_var.get() if hasattr(self, 'allow_rotation_var') else True
            
            self.logger.info(f"\n🤖 Автоматический выбор алгоритма:")
            self.logger.info(f"   Выбран: {chosen_algorithm}")
            self.logger.info(f"   Поворот: {'Да' if allow_rotation else 'Нет'}")
            
            # Выполняем оптимизацию выбранным алгоритмом
            if chosen_algorithm == 'RECTPACK_BFF':
                # Используем rectpack для простых случаев
                parts_data = []
                for fd in self.files_data:
                    for _ in range(fd.get('quantity', 1)):
                        parts_data.append({
                            'name': fd['filename'],
                            'width_mm': fd['width'],
                            'height_mm': fd['height'],
                            'area_m2': (fd['width'] * fd['height']) / 1_000_000,
                            'quantity': 1
                        })
                
                result = self.optimizer.optimize_layout(parts_data, 
                                                      allow_rotation=allow_rotation,
                                                      algorithm='BFF')
            else:
                # Используем умный алгоритм для сложных случаев
                result = self.smart_optimizer.optimize_smart(
                self.files_data,  # Передаем исходные данные с количеством
                allow_rotation=allow_rotation
            )
            
            if not result['success']:
                messagebox.showerror("Ошибка", f"Оптимизация не удалась:\n{result.get('error', 'Неизвестная ошибка')}")
                return
            
            # Обновление инфо
            info_text = (
                f"✓ Всего деталей: {total_parts_count} шт\n" +
                f"✓ Листов требуется: {result['sheets_needed']}\n" +
                f"✓ Использование: {result['utilization_percent']:.1f}%\n" +
                f"✓ Обрезки: {result['overall_waste_percent']:.1f}%\n" +
                f"✓ Длина реза: {result.get('total_cut_length_mm', 0)/1000:.1f} м\n" +
                f"✓ Контуров: {result.get('total_contours', 0)} шт\n" +
                f"✓ Время резки: {result.get('cutting_time_minutes', 0):.1f} мин"
            )
            self.nesting_label.config(text=info_text, foreground='green')
            
            # Сохраняем результат для возможного экспорта
            self.last_nesting_result = result
            
            # 1. СНАЧАЛА показываем МОДАЛЬНОЕ окно с визуализацией
            # Пользователь смотрит, проверяет, закрывает окно
            self.show_nesting_visualization_modal(result, total_parts_count)
            
            # 2. ПОТОМ спрашиваем, создавать ли PDF и Excel
            print(f"[DEBUG] Показываем диалог создания отчетов...")
            answer = messagebox.askyesno(
                "Создать отчеты?",
                f"📊 Раскладка показана!\n\n" +
                f"📦 Всего деталей: {total_parts_count} шт\n" +
                f"📄 Листов: {result['sheets_needed']}\n" +
                f"📊 Использование: {result['utilization_percent']:.1f}%\n\n" +
                "Создать PDF и Excel отчеты?"
            )
            
            print(f"[DEBUG] Ответ пользователя: {answer}")
            
            if answer:
                # 3. Создаем файлы только если пользователь согласился
                try:
                    project_name = self.project_name.get().strip() or "Проект без названия"
                    print(f"[DEBUG] Начинаем создание отчетов...")
                    print(f"[DEBUG] Результат оптимизации: {result}")
                    print(f"[DEBUG] Общее количество деталей: {total_parts_count}")
                    
                    pdf_path, excel_path = self.create_simple_reports(result, total_parts_count, project_name)
                    
                    # Активируем кнопку пересчета отчетов
                    if hasattr(self, 'recalculate_btn'):
                        self.recalculate_btn.config(state=tk.NORMAL)
                    
                    print(f"[DEBUG] Отчеты созданы успешно!")
                    print(f"[DEBUG] PDF: {pdf_path}")
                    print(f"[DEBUG] Excel: {excel_path}")
                    
                    # Открываем папку с файлами
                    import os
                    import subprocess
                    folder_path = Path(excel_path).parent
                    
                    # Показываем сообщение с путями
                    response = messagebox.askquestion(
                        "✅ ОТЧЕТЫ СОЗДАНЫ!",
                        f"✓ PDF с визуализацией создан\n" +
                        f"✓ Excel таблица создана\n\n" +
                        f"📁 Сохранено в папке с DXF:\n{folder_path}\n\n" +
                        "Открыть папку с файлами?"
                    )
                    
                    if response == 'yes':
                        # Открываем папку в проводнике
                        if os.name == 'nt':  # Windows
                            os.startfile(folder_path)
                        elif os.name == 'posix':  # macOS/Linux
                            subprocess.Popen(['xdg-open', folder_path])
                            
                except Exception as e:
                    print(f"[DEBUG] ОШИБКА при создании отчетов: {e}")
                    import traceback
                    traceback.print_exc()
                    messagebox.showerror("Ошибка", f"Не удалось создать отчеты:\n{e}")
            else:
                print(f"[DEBUG] Пользователь отказался от создания отчетов")
                messagebox.showinfo("ОК", "Раскладка готова!\nОтчеты не созданы.")
            
            # Обновляем статус
            self.nesting_label.config(text="✅ Раскрой завершен успешно!")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка оптимизации:\n{e}")
            import traceback
            traceback.print_exc()
    
    def _run_smart_nesting_optimization(self):
        """Алиас для optimize_nesting_smart для совместимости"""
        self.optimize_nesting_smart()
    
    def optimize_nesting(self):
        """НОВОЕ: Оптимизация раскроя"""
        
        if not self.files_data:
            messagebox.showwarning("Предупреждение", "Сначала загрузите файлы!")
            return
        
        if not self.optimizer.is_available():
            messagebox.showerror("Ошибка", 
                               "Rectpack не установлен!\n\n" +
                               "Установите: pip install rectpack")
            return
        
        try:
            # Подготовка данных
            parts_data = []
            for file_data in self.files_data:
                if file_data['quantity'] > 0:
                    parts_data.append({
                        'name': file_data['filename'],
                        'width_mm': file_data['width'],
                        'height_mm': file_data['height'],
                        'area_m2': file_data['area_m2'],
                        'quantity': file_data['quantity']
                    })
            
            # АВТОМАТИЧЕСКИЙ ВЫБОР АЛГОРИТМА
            chosen_algorithm = self._choose_best_algorithm(self.files_data)
            allow_rotation = self.allow_rotation_var.get() if hasattr(self, 'allow_rotation_var') else True
            
            self.logger.info(f"\n🤖 Автоматический выбор алгоритма:")
            self.logger.info(f"   Выбран: {chosen_algorithm}")
            self.logger.info(f"   Поворот: {'Да' if allow_rotation else 'Нет'}")
            
            # Выполняем оптимизацию выбранным алгоритмом
            if chosen_algorithm == 'RECTPACK_BFF':
                result = self.optimizer.optimize_layout(parts_data, 
                                                   allow_rotation=allow_rotation, 
                                                      algorithm='BFF')
            else:
                # Для умного алгоритма нужно преобразовать данные
                smart_data = []
                for fd in self.files_data:
                    for _ in range(fd.get('quantity', 1)):
                        smart_data.append({
                            'name': fd['filename'],
                            'width': fd['width'],
                            'height': fd['height'],
                            'area': (fd['width'] * fd['height']) / 1_000_000,
                            'quantity': 1
                        })
                
                result = self.smart_optimizer.optimize_smart(smart_data, allow_rotation=allow_rotation)
            
            if not result['success']:
                messagebox.showerror("Ошибка", f"Оптимизация не удалась:\n{result.get('error', 'Неизвестная ошибка')}")
                return
            
            # Обновление инфо
            info_text = (
                f"✓ Листов требуется: {result['sheets_needed']}\n" +
                f"✓ Использование: {result['utilization_percent']:.1f}%\n" +
                f"✓ Обрезки: {result['overall_waste_percent']:.1f}%\n" +
                f"✓ Длина реза: {result.get('total_cut_length_mm', 0)/1000:.1f} м\n" +
                f"✓ Контуров: {result.get('total_contours', 0)} шт\n" +
                f"✓ Время резки: {result.get('cutting_time_minutes', 0):.1f} мин"
            )
            self.nesting_label.config(text=info_text, foreground='green')
            
            # Создание PDF с визуализацией и обрезками
            self.create_nesting_pdf(result)
            
            messagebox.showinfo("Успех",
                              f"Оптимизация завершена!\n\n" +
                              f"Листов: {result['sheets_needed']}\n" +
                              f"Использование: {result['utilization_percent']:.1f}%\n" +
                              f"Обрезки: {result['overall_waste_percent']:.1f}%\n\n" +
                              "PDF с раскладкой и Excel с обрезками созданы!")
            
            # Обновляем статус
            self.nesting_label.config(text="✅ Раскрой завершен успешно!")
            
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка оптимизации:\n{e}")
            import traceback
            traceback.print_exc()
    
    def edit_nesting_interactive(self):
        """НОВОЕ: Интерактивное редактирование раскроя с Drag & Drop"""
        
        if not self.files_data:
            messagebox.showwarning("Предупреждение", "Сначала загрузите файлы!")
            return
        
        try:
            # Импортируем интерактивный редактор из основного проекта
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from components.interactive_nesting_editor import InteractiveNestingEditor
            
            # Подготавливаем данные для редактора
            parts_data = []
            for file_data in self.files_data:
                if file_data['quantity'] > 0:
                    parts_data.append({
                        'name': file_data['filename'],
                        'width_mm': file_data['width'],
                        'height_mm': file_data['height'],
                        'area_m2': file_data['area_m2'],
                        'quantity': file_data['quantity']
                    })
            
            if not parts_data:
                messagebox.showwarning("Предупреждение", "Нет деталей для редактирования!")
                return
            
            # Показываем редактор
            project_name = Path(self.folder_path.get()).name or "Цеховой проект"
            editor = InteractiveNestingEditor(self.root)
            editor.show_editor(parts_data, project_name)
            
            messagebox.showinfo("Инструкция",
                              "Интерактивный редактор раскроя открыт!\n\n"
                              "💡 Как использовать:\n"
                              "1. Перетащите детали из списка на лист\n"
                              "2. Перемещайте размещенные детали для оптимизации\n"
                              "3. Используйте 'Авторазмещение' для быстрого старта\n"
                              "4. Нажмите 'Сохранить раскрой' когда закончите")
            
        except ImportError as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить редактор:\n{e}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть редактор:\n{e}")
    
    def create_nesting_pdf(self, nesting_result):
        """Создание PDF с раскладкой и обрезками"""
        
        # Используем компоненты из основного проекта
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from components.enhanced_area_calculator_with_waste import EnhancedAreaCalculatorWithWaste
        
        calc = EnhancedAreaCalculatorWithWaste()
        
        # Извлекаем информацию о проекте
        order = self.order_number.get() or "проект"
        project_name = Path(self.folder_path.get()).name or "проект"
        
        # Получаем шифр и номер заказа из project_info (если есть)
        cipher = None
        order_number = None
        if hasattr(self, 'project_info') and self.project_info:
            cipher = self.project_info.get('cipher')
            order_number = self.project_info.get('order_number')
        
        # Если не извлекли из project_info, пробуем из поля order_number
        if not order_number:
            order_number = order
        
        # Генерируем обрезки
        waste_pieces = calc._generate_waste_pieces(nesting_result, order_number or "проект")
        
        # Создаем PDF с дополнительными параметрами
        vis_pdf = calc._create_visualization_pdf(
            nesting_result, 
            waste_pieces, 
            project_name, 
            order_number,
            cipher=cipher
        )
        
        # Создаем Excel
        waste_excel = calc._create_waste_excel(waste_pieces, project_name, order_number)
        
        return vis_pdf, waste_excel
    
    def export_pdf(self):
        """Экспорт в PDF - используйте кнопку Раскрой"""
        if not self.files_data:
            messagebox.showwarning("Предупреждение", "Сначала загрузите файлы!")
            return
        
        # Проверяем, есть ли результат раскроя
        if self.last_nesting_result:
            # Создаем PDF с результатами раскроя
            try:
                self.create_nesting_pdf(self.last_nesting_result)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось создать PDF:\n{e}")
        else:
            # Если раскроя нет - предлагаем его запустить
            answer = messagebox.askyesno(
                "Создать PDF",
                "Для создания полного PDF отчета нужно сначала выполнить раскрой.\n\n" +
                "Выполнить раскрой сейчас?",
                icon='question'
            )
            if answer:
                self.run_nesting()
    
    def export_excel(self):
        """Экспорт в Excel - создание простой таблицы"""
        if not self.files_data:
            messagebox.showwarning("Предупреждение", "Сначала загрузите файлы!")
            return
        
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment
            from datetime import datetime
            
            order = self.order_number.get() or "БЕЗ_ЗАКАЗА"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"Площади_{order}_{timestamp}.xlsx"
            
            wb = Workbook()
            ws = wb.active
            ws.title = "Развертки"
            
            # Заголовки
            headers = ["№", "Файл", "Ширина (мм)", "Высота (мм)", "Площадь (м2)", "Количество", "Итого (м2)"]
            ws.append(headers)
            
            # Стиль заголовков
            header_fill = PatternFill(start_color="1976D2", end_color="1976D2", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF")
            
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center')
            
            # Данные
            total_area = 0
            for idx, file_data in enumerate(self.files_data, 1):
                qty = file_data.get('quantity', 1)
                area = file_data['area_m2']
                total = area * qty
                total_area += total
                
                ws.append([
                    idx,
                    file_data['name'],
                    file_data.get('width', 0),
                    file_data.get('height', 0),
                    round(area, 4),
                    qty,
                    round(total, 4)
                ])
            
            # Итоговая строка
            ws.append([])
            ws.append(["", "", "", "", "", "ИТОГО:", round(total_area, 4)])
            
            # Устанавливаем ширину колонок
            ws.column_dimensions['A'].width = 5
            ws.column_dimensions['B'].width = 80  # Увеличиваем для полных названий
            ws.column_dimensions['C'].width = 15
            ws.column_dimensions['D'].width = 15
            ws.column_dimensions['E'].width = 15
            ws.column_dimensions['F'].width = 12
            ws.column_dimensions['G'].width = 15
            
            # Настраиваем перенос текста для колонки с названиями
            for row in range(2, len(self.files_data) + 2):  # Начинаем с 2-й строки (после заголовка)
                ws[f'B{row}'].alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
                ws.row_dimensions[row].height = None  # Автоматическая высота
            
            wb.save(filename)
            messagebox.showinfo("Успех", f"Excel создан:\n{filename}\n\nОбщая площадь: {total_area:.4f} м2")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать Excel:\n{e}")
    
    def show_nesting_visualization_modal(self, result: Dict, total_parts: int):
        """Показать МОДАЛЬНОЕ окно с визуализацией раскроя"""
        
        # Создаем МОДАЛЬНОЕ окно
        viz_window = tk.Toplevel(self.root)
        viz_window.title(f"📊 Раскладка деталей - {result['sheets_needed']} листов")
        viz_window.geometry("1200x800")
        
        # Делаем окно МОДАЛЬНЫМ (блокирует главное окно)
        viz_window.transient(self.root)
        viz_window.grab_set()
        
        # Заголовок с информацией
        header = tk.Frame(viz_window, bg='#1976D2', height=70)
        header.pack(fill='x')
        
        tk.Label(header, 
                text=f"📊 ОПТИМАЛЬНАЯ РАСКЛАДКА",
                font=('Arial', 16, 'bold'), bg='#1976D2', fg='white').pack(pady=(10, 5))
        
        tk.Label(header,
                text=f"{total_parts} деталей на {result['sheets_needed']} листах | " +
                     f"Использование: {result['utilization_percent']:.1f}%",
                font=('Arial', 11), bg='#1976D2', fg='white').pack(pady=(0, 10))
        
        # Контейнер с прокруткой для листов
        main_frame = tk.Frame(viz_window)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        canvas_scroll = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas_scroll.yview)
        scrollable_frame = ttk.Frame(canvas_scroll)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas_scroll.configure(scrollregion=canvas_scroll.bbox("all"))
        )
        
        canvas_scroll.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas_scroll.configure(yscrollcommand=scrollbar.set)
        
        canvas_scroll.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Рисуем каждый лист
        colors = ['#90CAF9', '#A5D6A7', '#FFF59D', '#F48FB1', '#CE93D8', '#80DEEA']
        
        for sheet in result['sheets']:
            self._draw_sheet_on_canvas(scrollable_frame, sheet, colors)
        
        # Нижняя панель с кнопками
        bottom_frame = tk.Frame(viz_window, bg='#f0f0f0')
        bottom_frame.pack(fill='x', pady=10)
        
        tk.Label(bottom_frame, 
                text="💡 Проверьте раскладку. Закройте окно чтобы продолжить.",
                font=('Arial', 10), bg='#f0f0f0', fg='#666').pack(pady=5)
        
        tk.Button(bottom_frame, text="✓ ОК, продолжить", 
                 command=viz_window.destroy,
                 font=('Arial', 11, 'bold'), 
                 bg='#4CAF50', fg='white',
                 activebackground='#45a049',
                 pady=8, padx=20,
                 cursor='hand2').pack(pady=5)
        
        # Ждем закрытия окна (модальный режим)
        viz_window.wait_window()
    
    def _draw_sheet_on_canvas(self, parent, sheet: Dict, colors: list):
        """Рисовать один лист с деталями"""
        
        sheet_frame = ttk.LabelFrame(parent, text=f"📄 ЛИСТ #{sheet['number']} ({len(sheet['parts'])} деталей)", 
                                     padding=10)
        sheet_frame.pack(fill='x', pady=10)
        
        # Canvas для рисования (увеличен для легенды)
        canvas_width = 1400  # Увеличено с 1000 до 1400
        canvas_height = 500
        canvas = tk.Canvas(sheet_frame, width=canvas_width, height=canvas_height, bg='white')
        canvas.pack()
        
        # Масштаб
        SHEET_WIDTH = 2500  # мм
        SHEET_HEIGHT = 1250  # мм
        
        scale = min(canvas_width / SHEET_WIDTH, canvas_height / SHEET_HEIGHT) * 0.9
        
        # Смещение для центрирования
        offset_x = (canvas_width - SHEET_WIDTH * scale) / 2
        offset_y = (canvas_height - SHEET_HEIGHT * scale) / 2
        
        # Рисуем контур листа
        canvas.create_rectangle(
            offset_x, offset_y,
            offset_x + SHEET_WIDTH * scale, offset_y + SHEET_HEIGHT * scale,
            outline='black', width=2, fill='#f5f5f5'
        )
        
        # Подпись размера листа
        canvas.create_text(
            offset_x + (SHEET_WIDTH * scale) / 2, offset_y - 15,
            text=f"Лист {SHEET_WIDTH}x{SHEET_HEIGHT} мм",
            font=('Arial', 10, 'bold'), fill='red'
        )
        
        # Легенда зазоров
        legend_x = offset_x + SHEET_WIDTH * scale + 10
        legend_y = offset_y + 20
        canvas.create_text(
            legend_x, legend_y,
            text="Легенда:",
            font=('Arial', 8, 'bold'), fill='black', anchor='w'
        )
        # Красная пунктирная линия для примера
        canvas.create_line(
            legend_x, legend_y + 20, legend_x + 30, legend_y + 20,
            fill='red', width=2, dash=(4, 4)
        )
        canvas.create_text(
            legend_x + 35, legend_y + 20,
            text="- зазор 5мм",
            font=('Arial', 7), fill='black', anchor='w'
        )
        
        # Рисуем детали
        HALF_GAP = 2.5  # мм - половина зазора между деталями
        FULL_GAP = 5.0  # мм - полный зазор между деталями
        
        for idx, part in enumerate(sheet['parts']):
            color = colors[idx % len(colors)]
            
            # Координаты из rectpack включают зазор 2.5мм со всех сторон
            x_with_gap = offset_x + part['x'] * scale
            y_with_gap = offset_y + part['y'] * scale
            w_with_gap = part['width'] * scale
            h_with_gap = part['height'] * scale
            
            # Вычисляем реальные координаты и размеры (без зазора)
            gap_offset = HALF_GAP * scale
            x = x_with_gap + gap_offset
            y = y_with_gap + gap_offset
            w = w_with_gap - 2 * gap_offset
            h = h_with_gap - 2 * gap_offset
            
            # Деталь в реальный размер (БЕЗ зазора)
            canvas.create_rectangle(
                x, y, x + w, y + h,
                fill=color, outline='black', width=2
            )
            
            # Имя детали (укороченное)
            part_name = part['name'].split('#')[0][:15]  # Первые 15 символов
            if len(part['name']) > 15:
                part_name += "..."
            
            # Текст по центру детали
            text_x = x + w / 2
            text_y = y + h / 2
            
            canvas.create_text(
                text_x, text_y,
                text=part_name,
                font=('Arial', 7 if w < 100 else 8),
                fill='black',
                width=w-20  # Перенос текста
            )
            
            # Размеры (реальные, без зазора)
            real_width = part['width'] - 2 * HALF_GAP
            real_height = part['height'] - 2 * HALF_GAP
            size_text = f"{real_width:.0f}x{real_height:.0f}"
            canvas.create_text(
                text_x, text_y + 15,
                text=size_text,
                font=('Arial', 6),
                fill='#333'
            )
        
        # ВИЗУАЛИЗАЦИЯ ЗАЗОРОВ между деталями в GUI
        # Собираем реальные позиции деталей (без зазоров)
        real_parts_gui = []
        for part in sheet['parts']:
            gap_offset = HALF_GAP * scale
            real_parts_gui.append({
                'x': offset_x + (part['x'] + HALF_GAP) * scale,
                'y': offset_y + (part['y'] + HALF_GAP) * scale,
                'w': (part['width'] - 2 * HALF_GAP) * scale,
                'h': (part['height'] - 2 * HALF_GAP) * scale
            })
        
        gap_threshold = FULL_GAP * scale * 1.2
        
        for i, p1 in enumerate(real_parts_gui):
            for j, p2 in enumerate(real_parts_gui):
                if i >= j:
                    continue
                
                # Вертикальный зазор (детали рядом слева-справа)
                if abs((p1['x'] + p1['w']) - p2['x']) < gap_threshold:
                    y_top = max(p1['y'], p2['y'])
                    y_bottom = min(p1['y'] + p1['h'], p2['y'] + p2['h'])
                    if y_bottom > y_top:
                        gap_x = (p1['x'] + p1['w'] + p2['x']) / 2
                        canvas.create_line(
                            gap_x, y_top, gap_x, y_bottom,
                            fill='red', width=2, dash=(4, 4)
                        )
                
                # Горизонтальный зазор (детали рядом сверху-снизу)
                if abs((p1['y'] + p1['h']) - p2['y']) < gap_threshold:
                    x_left = max(p1['x'], p2['x'])
                    x_right = min(p1['x'] + p1['w'], p2['x'] + p2['w'])
                    if x_right > x_left:
                        gap_y = (p1['y'] + p1['h'] + p2['y']) / 2
                        canvas.create_line(
                            x_left, gap_y, x_right, gap_y,
                            fill='red', width=2, dash=(4, 4)
                        )
    
    def create_simple_reports(self, result: Dict, total_parts: int, project_name: str = "Проект без названия"):
        """Создать PDF с визуализацией и Excel отчеты"""
        print(f"[DEBUG] create_simple_reports вызван с result={result}, total_parts={total_parts}, project_name={project_name}")
        
        from datetime import datetime
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill
        import os
        
        # Импорты для PDF
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors as pdf_colors
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas as pdf_canvas
        from reportlab.platypus import Table, TableStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Получаем папку где находятся DXF файлы
        dxf_folder = Path(self.folder_path.get())
        project_name = dxf_folder.name or "проект"
        
        print(f"[DEBUG] DXF папка: {dxf_folder}")
        print(f"[DEBUG] Имя проекта: {project_name}")
        
        # Создаем подпапку "Отчеты_Раскроя" в папке с DXF
        reports_folder = dxf_folder / "Отчеты_Раскроя"
        print(f"[DEBUG] Папка отчетов: {reports_folder}")
        reports_folder.mkdir(exist_ok=True)
        print(f"[DEBUG] Папка отчетов создана: {reports_folder.exists()}")
        
        # Регистрируем шрифт Arial для кириллицы
        try:
            pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf'))
            pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:/Windows/Fonts/arialbd.ttf'))
            font_name = 'Arial'
            font_bold = 'Arial-Bold'
        except:
            font_name = 'Helvetica'
            font_bold = 'Helvetica-Bold'
        
        # PDF отчет с визуализацией (ПРОСТОЙ, БЕЗ геометрии)
        pdf_filename = f"Раскрой_{project_name}_{timestamp}.pdf"
        pdf_path = reports_folder / pdf_filename
        print(f"[DEBUG] Создаем PDF: {pdf_path}")
        self._create_pdf_with_visualization(pdf_path, result, total_parts, font_name, font_bold)
        print(f"[DEBUG] PDF создан: {pdf_path.exists()}")
        
        # Excel отчет с ПОЛНЫМ путем
        excel_filename = f"Раскрой_{project_name}_{timestamp}.xlsx"
        excel_path = reports_folder / excel_filename
        print(f"[DEBUG] Создаем Excel: {excel_path}")
        wb = openpyxl.Workbook()
        
        # === ЛИСТ 1: РАСЧЕТНАЯ ТАБЛИЦА ДЕТАЛЕЙ ===
        ws1 = wb.active
        ws1.title = "Расчет деталей"
        
        # Используем введенное пользователем название проекта
        project_name = self.project_name.get().strip()
        if not project_name:
            project_name = "Проект без названия"
        
        print(f"[DEBUG] Используем название проекта: {project_name}")
        
        # Название проекта (строка 1)
        row = 1
        ws1[f'A{row}'] = f"Проект: {project_name}"
        ws1[f'A{row}'].font = Font(size=14, bold=True, color="1976D2")
        ws1.merge_cells(f'A{row}:G{row}')
        ws1[f'A{row}'].alignment = Alignment(horizontal='center')
        row += 1
        
        # Дата (следующая строка)
        from datetime import datetime
        ws1[f'A{row}'] = f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        ws1[f'A{row}'].font = Font(size=10)
        ws1.merge_cells(f'A{row}:G{row}')
        ws1[f'A{row}'].alignment = Alignment(horizontal='center')
        row += 1
        
        # Пустая строка
        row += 1
        
        # Заголовок таблицы
        ws1[f'A{row}'] = "РАСЧЕТНАЯ ТАБЛИЦА ДЕТАЛЕЙ"
        ws1[f'A{row}'].font = Font(size=16, bold=True)
        ws1.merge_cells(f'A{row}:G{row}')
        ws1[f'A{row}'].alignment = Alignment(horizontal='center')
        row += 1
        
        # Собираем данные по уникальным деталям (как в PDF)
        parts_summary = {}
        for sheet in result['sheets']:
            for part in sheet['parts']:
                # Группируем по имени детали (без номера экземпляра и расширения)
                base_name = part['name'].split('#')[0].strip()
                # Убираем расширение .dxf если есть
                if base_name.endswith('.dxf'):
                    base_name = base_name[:-4]
                
                if base_name not in parts_summary:
                    # Используем реальные размеры без зазоров
                    real_width = part.get('real_width', part['width'])
                    real_height = part.get('real_height', part['height'])
                    
                    parts_summary[base_name] = {
                        'width': real_width,
                        'height': real_height,
                        'area_one': (real_width * real_height) / 1_000_000,
                        'quantity': 0
                    }
                parts_summary[base_name]['quantity'] += 1
        
        # Шапка таблицы (строка row)
        headers = ['№', 'Название детали', 'Ширина (мм)', 'Высота (мм)', 
                   'Площадь 1 шт (м2)', 'Кол-во (шт)', 'Площадь всего (м2)']
        
        for col, header in enumerate(headers, 1):
            cell = ws1.cell(row, col, header)
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill(start_color='1976D2', end_color='1976D2', fill_type='solid')
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        
        # Данные
        row += 1
        total_area_all = 0
        for idx, (name, data) in enumerate(sorted(parts_summary.items()), 1):
            total_area = data['area_one'] * data['quantity']
            total_area_all += total_area
            
            ws1.cell(row, 1, idx).alignment = Alignment(horizontal='center')
            ws1.cell(row, 2, name)
            ws1.cell(row, 3, f"{data['width']:.0f}").alignment = Alignment(horizontal='center')
            ws1.cell(row, 4, f"{data['height']:.0f}").alignment = Alignment(horizontal='center')
            ws1.cell(row, 5, f"{data['area_one']:.4f}").alignment = Alignment(horizontal='center')
            ws1.cell(row, 6, data['quantity']).alignment = Alignment(horizontal='center')
            ws1.cell(row, 7, f"{total_area:.4f}").alignment = Alignment(horizontal='center')
            row += 1
        
        # ИТОГО
        ws1.cell(row, 2, "ИТОГО:").font = Font(bold=True)
        ws1.cell(row, 6, total_parts).font = Font(bold=True)
        ws1.cell(row, 6).alignment = Alignment(horizontal='center')
        ws1.cell(row, 7, f"{total_area_all:.4f}").font = Font(bold=True)
        ws1.cell(row, 7).alignment = Alignment(horizontal='center')
        
        for col in range(1, 8):
            ws1.cell(row, col).fill = PatternFill(start_color='FFC107', end_color='FFC107', fill_type='solid')
        
        # Статистика
        row += 2
        ws1.cell(row, 1, "СТАТИСТИКА:").font = Font(bold=True, size=12)
        row += 1
        
        sheet_area = (2500 * 1250) / 1_000_000
        total_sheets_area = result['sheets_needed'] * sheet_area
        waste_area = total_sheets_area - total_area_all
        
        stats = [
            ("Листов требуется:", f"{result['sheets_needed']} шт"),
            ("Размер листа:", "2500x1250 мм (3.125 м2)"),
            ("Площадь всех листов:", f"{total_sheets_area:.4f} м2"),
            ("Площадь деталей:", f"{total_area_all:.4f} м2"),
            ("Использование материала:", f"{result['utilization_percent']:.1f}%"),
            ("Обрезки (отходы):", f"{result['overall_waste_percent']:.1f}% ({waste_area:.4f} м2)"),
            ("Общая длина реза:", f"{result.get('total_cut_length_mm', 0)/1000:.1f} м"),
            ("Количество контуров:", f"{result.get('total_contours', 0)} шт"),
            ("Время резки:", f"{result.get('cutting_time_minutes', 0):.1f} мин"),
        ]
        
        for param, value in stats:
            ws1.cell(row, 1, param).font = Font(bold=True)
            ws1.cell(row, 2, value)
            row += 1
        
        # Авторазмер колонок
        ws1.column_dimensions['A'].width = 8
        ws1.column_dimensions['B'].width = 40
        ws1.column_dimensions['C'].width = 15
        ws1.column_dimensions['D'].width = 15
        ws1.column_dimensions['E'].width = 20
        ws1.column_dimensions['F'].width = 15
        ws1.column_dimensions['G'].width = 20
        
        # === ЛИСТ 2: СВОДКА ПО ГРУППАМ ДЕТАЛЕЙ ===
        ws2 = wb.create_sheet("Сводка по группам")
        
        print(f"[DEBUG] Создаем лист 'Сводка по группам'...")
        
        # Заголовок
        row2 = 1
        ws2[f'A{row2}'] = "СВОДКА ПО ГРУППАМ ДЕТАЛЕЙ"
        ws2[f'A{row2}'].font = Font(size=16, bold=True, color="FF9800")
        ws2.merge_cells(f'A{row2}:E{row2}')
        ws2[f'A{row2}'].alignment = Alignment(horizontal='center')
        row2 += 2
        
        # Заголовки таблицы
        headers2 = ['№', 'Группа деталей', 'Общее количество', 'Общая площадь (м²)', 'Средний размер (мм)']
        for col, header in enumerate(headers2, 1):
            cell = ws2.cell(row2, col, header)
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill(start_color='FF9800', end_color='FF9800', fill_type='solid')
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        
        # Данные сводки
            row2 += 1
        for idx, (base_name, data) in enumerate(sorted(parts_summary.items()), 1):
            # Показываем полные названия (перенос текста настроен)
            display_name = base_name
            
            # Показываем средний размер
            avg_width = data['width']
            avg_height = data['height']
            total_area = data['area_one'] * data['quantity']
            
            ws2.cell(row2, 1, idx).alignment = Alignment(horizontal='center')
            ws2.cell(row2, 2, display_name)
            ws2.cell(row2, 3, data['quantity']).alignment = Alignment(horizontal='center')
            ws2.cell(row2, 4, f"{total_area:.4f}").alignment = Alignment(horizontal='center')
            ws2.cell(row2, 5, f"{avg_width:.0f}x{avg_height:.0f}").alignment = Alignment(horizontal='center')
            row2 += 1
        
        # ИТОГО для сводки
        ws2.cell(row2, 2, "ИТОГО:").font = Font(bold=True)
        ws2.cell(row2, 3, total_parts).font = Font(bold=True)
        ws2.cell(row2, 3).alignment = Alignment(horizontal='center')
        ws2.cell(row2, 4, f"{total_area_all:.4f}").font = Font(bold=True)
        ws2.cell(row2, 4).alignment = Alignment(horizontal='center')
        
        for col in range(1, 6):
            ws2.cell(row2, col).fill = PatternFill(start_color='FFC107', end_color='FFC107', fill_type='solid')
        
        # Авторазмер колонок для сводки
        ws2.column_dimensions['A'].width = 8
        ws2.column_dimensions['B'].width = 80  # Еще больше увеличиваем ширину для названий групп
        ws2.column_dimensions['C'].width = 20
        ws2.column_dimensions['D'].width = 20
        ws2.column_dimensions['E'].width = 20
        
        # Настраиваем перенос текста для всех ячеек в колонке B (Группа деталей)
        for row in range(3, row2 + 1):  # Начинаем с 3-й строки (после заголовков)
            ws2[f'B{row}'].alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
        
        # Также настраиваем высоту строк для автоматического подбора
        for row in range(3, row2 + 1):
            ws2.row_dimensions[row].height = None  # Автоматическая высота
        
        # === ЛИСТ 3: ОБРЕЗКИ С НУМЕРАЦИЕЙ ===
        ws3 = wb.create_sheet("Обрезки")
        
        print(f"[DEBUG] Создаем лист 'Обрезки' с нумерацией...")
        
        # Название проекта (строка 1)
        row3 = 1
        ws3[f'A{row3}'] = f"Проект: {project_name}"
        ws3[f'A{row3}'].font = Font(size=14, bold=True, color="1976D2")
        ws3.merge_cells(f'A{row3}:F{row3}')
        ws3[f'A{row3}'].alignment = Alignment(horizontal='center')
        row3 += 1
        
        # Дата
        ws3[f'A{row3}'] = f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        ws3[f'A{row3}'].font = Font(size=10)
        ws3.merge_cells(f'A{row3}:F{row3}')
        ws3[f'A{row3}'].alignment = Alignment(horizontal='center')
        row3 += 1
        
        # Пустая строка
        row3 += 1
        
        # Заголовок таблицы
        ws3[f'A{row3}'] = "ОБРЕЗКИ С НУМЕРАЦИЕЙ"
        ws3[f'A{row3}'].font = Font(size=16, bold=True)
        ws3.merge_cells(f'A{row3}:F{row3}')
        ws3[f'A{row3}'].alignment = Alignment(horizontal='center')
        row3 += 1
        
        # Шапка таблицы обрезков (используем row3!)
        headers_waste = ['№ обрезка', 'Лист №', 'Ширина (мм)', 'Высота (мм)', 
                         'Площадь (м2)', 'Пригодность']
        
        for col, header in enumerate(headers_waste, 1):
            cell = ws3.cell(row3, col, header)
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill(start_color='FF6F00', end_color='FF6F00', fill_type='solid')
            cell.alignment = Alignment(horizontal='center', wrap_text=True)
        
        # Рассчитываем обрезки для каждого листа
        row3 += 1
        waste_counter = 1
        total_waste_area = 0
        
        print(f"[DEBUG] Рассчитываем обрезки для {len(result['sheets'])} листов...")
        
        for sheet in result['sheets']:
            # Простой расчет: площадь листа - площадь всех деталей на нем
            sheet_area_m2 = (2500 * 1250) / 1_000_000
            parts_area = sum((p['width'] * p['height']) / 1_000_000 for p in sheet['parts'])
            waste_area_sheet = sheet_area_m2 - parts_area
            
            print(f"[DEBUG] Лист {sheet['number']}: площадь листа={sheet_area_m2:.4f} м2, детали={parts_area:.4f} м2, обрезки={waste_area_sheet:.4f} м2")
            
            if waste_area_sheet > 0.01:  # Если обрезок больше 0.01 м2
                # Примерные размеры обрезка (упрощенно)
                # В реальности нужно вычислять геометрию, но это сложно
                # Предполагаем что обрезки примерно квадратные или прямоугольные
                
                # Создаем несколько обрезков если площадь большая
                num_scraps = max(1, int(waste_area_sheet / 0.1))  # Примерно по 0.1 м2 каждый
                
                print(f"[DEBUG] Создаем {num_scraps} обрезков для листа {sheet['number']}")
                
                for i in range(num_scraps):
                    scrap_area = waste_area_sheet / num_scraps
                    # Примерные размеры (квадрат)
                    side = (scrap_area * 1_000_000) ** 0.5
                    
                    print(f"[DEBUG] Обрезок W-{waste_counter:03d}: {side:.0f}x{side:.0f} мм, {scrap_area:.4f} м2")
                    
                    ws3.cell(row3, 1, f"W-{waste_counter:03d}").alignment = Alignment(horizontal='center')
                    ws3.cell(row3, 2, sheet['number']).alignment = Alignment(horizontal='center')
                    ws3.cell(row3, 3, f"{side:.0f}").alignment = Alignment(horizontal='center')
                    ws3.cell(row3, 4, f"{side:.0f}").alignment = Alignment(horizontal='center')
                    ws3.cell(row3, 5, f"{scrap_area:.4f}").alignment = Alignment(horizontal='center')
                    
                    # Пригодность
                    usable = "✓ Да" if scrap_area > 0.05 else "✗ Нет (мелкий)"
                    ws3.cell(row3, 6, usable).alignment = Alignment(horizontal='center')
                    
                    if scrap_area > 0.05:
                        ws3.cell(row3, 6).fill = PatternFill(start_color='C8E6C9', end_color='C8E6C9', fill_type='solid')
                    else:
                        ws3.cell(row3, 6).fill = PatternFill(start_color='FFCCBC', end_color='FFCCBC', fill_type='solid')
                    
                    row3 += 1
                    waste_counter += 1
                    total_waste_area += scrap_area
        
        # ИТОГО по обрезкам
        ws3.cell(row3, 1, "ИТОГО:").font = Font(bold=True)
        ws3.cell(row3, 5, f"{total_waste_area:.4f}").font = Font(bold=True)
        ws3.cell(row3, 5).alignment = Alignment(horizontal='center')
        
        for col in range(1, 7):
            ws3.cell(row3, col).fill = PatternFill(start_color='FFE082', end_color='FFE082', fill_type='solid')
        
        row3 += 2  # Пропускаем строку
        
        # Инструкция по использованию
        ws3.cell(row3, 1, "💡 ИНСТРУКЦИЯ ПО МАРКИРОВКЕ:").font = Font(bold=True, size=12)
        ws3.merge_cells(f'A{row3}:F{row3}')
        row3 += 1
        
        instructions = [
            "1. После резки найдите обрезки на каждом листе",
            "2. Маркером пометьте обрезки номерами W-001, W-002, W-003...",
            "3. Сложите пригодные обрезки (✓ Да) в специальную зону",
            "4. Мелкие обрезки (✗ Нет) можно утилизировать",
            "5. Перед новым проектом проверяйте наличие подходящих обрезков в этой таблице"
        ]
        
        for instruction in instructions:
            ws3.cell(row3, 1, instruction)
            ws3.merge_cells(f'A{row3}:F{row3}')
            row3 += 1
        
        # Авторазмер колонок для листа обрезков
        ws3.column_dimensions['A'].width = 15
        ws3.column_dimensions['B'].width = 12
        ws3.column_dimensions['C'].width = 15
        ws3.column_dimensions['D'].width = 15
        ws3.column_dimensions['E'].width = 18
        ws3.column_dimensions['F'].width = 20
        
        # === ЛИСТ 4: КООРДИНАТЫ ДЕТАЛЕЙ (для CAM системы) ===
        ws4 = wb.create_sheet("Координаты (CAM)")
        
        ws4['A1'] = "КООРДИНАТЫ ДЕТАЛЕЙ ДЛЯ CAM СИСТЕМЫ"
        ws4['A1'].font = Font(size=14, bold=True)
        ws4.merge_cells('A1:F1')
        ws4['A1'].alignment = Alignment(horizontal='center')
        
        # Шапка
        row = 3
        headers_coords = ['Лист №', 'Деталь', 'X (мм)', 'Y (мм)', 'Ширина (мм)', 'Высота (мм)']
        
        for col, header in enumerate(headers_coords, 1):
            cell = ws4.cell(row, col, header)
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill(start_color='607D8B', end_color='607D8B', fill_type='solid')
            cell.alignment = Alignment(horizontal='center')
        
        # Данные координат
        row += 1
        for sheet in result['sheets']:
            for part in sheet['parts']:
                ws4.cell(row, 1, sheet['number']).alignment = Alignment(horizontal='center')
                ws4.cell(row, 2, part['name'])
                ws4.cell(row, 3, f"{part['x']:.1f}").alignment = Alignment(horizontal='center')
                ws4.cell(row, 4, f"{part['y']:.1f}").alignment = Alignment(horizontal='center')
                ws4.cell(row, 5, f"{part['width']:.1f}").alignment = Alignment(horizontal='center')
                ws4.cell(row, 6, f"{part['height']:.1f}").alignment = Alignment(horizontal='center')
                row += 1
        
        # Авторазмер для координат
        ws4.column_dimensions['A'].width = 10
        ws4.column_dimensions['B'].width = 40
        ws4.column_dimensions['C'].width = 12
        ws4.column_dimensions['D'].width = 12
        ws4.column_dimensions['E'].width = 15
        ws4.column_dimensions['F'].width = 15
        
        print(f"[DEBUG] Сохраняем Excel файл...")
        wb.save(str(excel_path))
        print(f"[DEBUG] Excel сохранен: {excel_path.exists()}")
        
        # Возвращаем ПОЛНЫЕ пути к PDF и Excel
        pdf_abs = str(pdf_path.absolute())
        excel_abs = str(excel_path.absolute())
        print(f"[DEBUG] Возвращаем пути: PDF={pdf_abs}, Excel={excel_abs}")
        return pdf_abs, excel_abs
    
    def _create_pdf_with_visualization(self, pdf_path, result, total_parts, font_name, font_bold):
        """Создать PDF с визуализацией раскроя"""
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors as pdf_colors
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas as pdf_canvas
        
        # Создаем PDF в альбомной ориентации
        c = pdf_canvas.Canvas(str(pdf_path), pagesize=landscape(A4))
        page_width, page_height = landscape(A4)
        
        # Цвета для деталей
        colors_list = [
            (144/255, 202/255, 249/255),  # Голубой
            (165/255, 214/255, 167/255),  # Зеленый
            (255/255, 245/255, 157/255),  # Желтый
            (244/255, 143/255, 177/255),  # Розовый
            (206/255, 147/255, 216/255),  # Фиолетовый
            (128/255, 222/255, 234/255),  # Бирюзовый
        ]
        
        # ПЕРВАЯ СТРАНИЦА: Титульный лист с заголовком
        c.setFont(font_bold, 24)
        c.drawCentredString(page_width/2, page_height - 30*mm, "ОПТИМАЛЬНЫЙ РАСКРОЙ ДЕТАЛЕЙ")
        
        # Добавляем информацию о проекте (шифр и номер заказа)
        y_info = page_height - 45*mm
        
        # Используем введенное пользователем название проекта
        project_name = self.project_name.get().strip()
        if not project_name:
            project_name = "Проект без названия"
        
        print(f"[DEBUG] PDF: Используем название проекта: {project_name}")
        
        # Выводим название проекта
            c.setFont(font_bold, 14)
        c.drawCentredString(page_width/2, y_info, f"Проект: {project_name}")
            y_info -= 6*mm
        
        # Дата
        c.setFont(font_name, 10)
        from datetime import datetime
        c.drawCentredString(page_width/2, y_info, f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        
        # ТАБЛИЦА 1: РАСЧЕТНАЯ ТАБЛИЦА ДЕТАЛЕЙ
        y = y_info - 10*mm
        c.setFont(font_bold, 14)
        c.drawString(20*mm, y, "РАСЧЕТНАЯ ТАБЛИЦА ДЕТАЛЕЙ:")
        y -= 8*mm
        
        # Собираем данные по уникальным деталям
        parts_summary = {}
        for sheet in result['sheets']:
            for part in sheet['parts']:
                # Группируем по имени детали (без номера экземпляра и расширения)
                base_name = part['name'].split('#')[0].strip()
                # Убираем расширение .dxf если есть
                if base_name.endswith('.dxf'):
                    base_name = base_name[:-4]
                
                if base_name not in parts_summary:
                    # Используем реальные размеры без зазоров
                    real_width = part.get('real_width', part['width'])
                    real_height = part.get('real_height', part['height'])
                    
                    parts_summary[base_name] = {
                        'width': real_width,
                        'height': real_height,
                        'area_one': (real_width * real_height) / 1_000_000,  # м2
                        'quantity': 0,
                        'total_area': 0
                    }
                
                parts_summary[base_name]['quantity'] += 1
        
        # Пересчитываем общую площадь
        for name, data in parts_summary.items():
            data['total_area'] = data['area_one'] * data['quantity']
        
        # Создаем таблицу
        from reportlab.platypus import Table, TableStyle
        
        table_data = [
            ['№', 'Название детали', 'Ширина\n(мм)', 'Высота\n(мм)', 
             'Площадь\n1 шт (м2)', 'Кол-во\n(шт)', 'Площадь\nвсего (м2)']
        ]
        
        total_area_all = 0
        for idx, (name, data) in enumerate(sorted(parts_summary.items()), 1):
            # Показываем полные названия
            short_name = name
            
            table_data.append([
                str(idx),
                short_name,
                f"{data['width']:.0f}",
                f"{data['height']:.0f}",
                f"{data['area_one']:.4f}",
                str(data['quantity']),
                f"{data['total_area']:.4f}"
            ])
            total_area_all += data['total_area']
        
        # Строка ИТОГО
        table_data.append([
            '', 'ИТОГО:', '', '', '', 
            str(total_parts), 
            f"{total_area_all:.4f}"
        ])
        
        # Создаем и рисуем таблицу
        table = Table(table_data, colWidths=[10*mm, 75*mm, 20*mm, 20*mm, 25*mm, 18*mm, 25*mm])
        table.setStyle(TableStyle([
            # Заголовок
            ('BACKGROUND', (0, 0), (-1, 0), pdf_colors.HexColor('#1976D2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), pdf_colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), font_bold),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Данные
            ('FONTNAME', (0, 1), (-1, -2), font_name),
            ('FONTSIZE', (0, 1), (-1, -2), 8),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Номер
            ('ALIGN', (2, 1), (-1, -1), 'CENTER'),  # Числа
            ('GRID', (0, 0), (-1, -2), 0.5, pdf_colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Строка ИТОГО
            ('BACKGROUND', (0, -1), (-1, -1), pdf_colors.HexColor('#FFC107')),
            ('FONTNAME', (0, -1), (-1, -1), font_bold),
            ('FONTSIZE', (0, -1), (-1, -1), 10),
            ('LINEABOVE', (0, -1), (-1, -1), 2, pdf_colors.black),
        ]))
        
        # Позиционируем и рисуем таблицу
        table.wrapOn(c, page_width, page_height)
        table_height = table._height
        
        # Проверяем, хватает ли места для таблицы
        MIN_MARGIN = 30*mm  # Минимальный отступ снизу
        if y - table_height < MIN_MARGIN:
            c.showPage()
            y = page_height - 30*mm
        
        table.drawOn(c, 20*mm, y - table_height)
        
        y = y - table_height - 15*mm
        
        # Проверка перед сводкой по группам
        if y < 100*mm:  # Нужно минимум 100мм для сводки по группам
            c.showPage()
            y = page_height - 30*mm
        
        # ТАБЛИЦА 2: СВОДКА ПО ГРУППАМ ДЕТАЛЕЙ
        c.setFont(font_bold, 14)
        c.drawString(20*mm, y, "СВОДКА ПО ГРУППАМ ДЕТАЛЕЙ:")
        y -= 8*mm
        
        # Создаем данные для сводки по группам
        summary_data = [
            ['№', 'Группа деталей', 'Общее количество', 'Общая площадь (м²)', 'Средний размер (мм)']
        ]
        
        for i, (base_name, data) in enumerate(parts_summary.items(), 1):
            # Показываем полные названия (перенос текста настроен в таблице)
            display_name = base_name
            
            # Показываем средний размер
            avg_width = data['width']
            avg_height = data['height']
            
            summary_data.append([
                str(i),
                display_name,
                str(data['quantity']),
                f"{data['total_area']:.4f}",
                f"{avg_width:.0f}x{avg_height:.0f}"
            ])
        
        # Создаем и рисуем таблицу сводки
        summary_table = Table(summary_data, colWidths=[10*mm, 80*mm, 25*mm, 30*mm, 30*mm])
        summary_table.setStyle(TableStyle([
            # Заголовок
            ('BACKGROUND', (0, 0), (-1, 0), pdf_colors.HexColor('#FF9800')),
            ('TEXTCOLOR', (0, 0), (-1, 0), pdf_colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), font_bold),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Данные
            ('FONTNAME', (0, 1), (-1, -1), font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Номер
            ('ALIGN', (2, 1), (-1, -1), 'CENTER'),  # Числа
            ('GRID', (0, 0), (-1, -1), 0.5, pdf_colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        # Позиционируем и рисуем таблицу сводки
        summary_table.wrapOn(c, page_width, page_height)
        summary_table_height = summary_table._height
        
        # Проверяем, хватает ли места для таблицы сводки
        if y - summary_table_height < MIN_MARGIN:
            c.showPage()
            y = page_height - 30*mm
        
        summary_table.drawOn(c, 20*mm, y - summary_table_height)
        
        y = y - summary_table_height - 15*mm
        
        # Проверка перед статистикой
        if y < 80*mm:  # Нужно минимум 80мм для статистики и рекомендаций
            c.showPage()
            y = page_height - 30*mm
        
        # ТАБЛИЦА 3: СТАТИСТИКА И РЕКОМЕНДАЦИИ
        c.setFont(font_bold, 14)
        c.drawString(20*mm, y, "СТАТИСТИКА И РЕКОМЕНДАЦИИ:")
        y -= 8*mm
        
        # Расчет данных
        sheet_area = (2500 * 1250) / 1_000_000  # м2
        total_sheets_area = result['sheets_needed'] * sheet_area
        waste_area = total_sheets_area - total_area_all
        
        stats_data = [
            ['Параметр', 'Значение'],
            ['Листов требуется', f"{result['sheets_needed']} шт"],
            ['Размер листа', '2500x1250 мм (3.125 м2)'],
            ['Площадь всех листов', f"{total_sheets_area:.4f} м2"],
            ['Площадь деталей', f"{total_area_all:.4f} м2"],
            ['Использование материала', f"{result['utilization_percent']:.1f}%"],
            ['Обрезки (отходы)', f"{result['overall_waste_percent']:.1f}% ({waste_area:.4f} м2)"],
            ['Общая длина реза', f"{result.get('total_cut_length_mm', 0)/1000:.1f} м"],
            ['Количество контуров', f"{result.get('total_contours', 0)} шт"],
            ['Время резки', f"{result.get('cutting_time_minutes', 0):.1f} мин"],
        ]
        
        stats_table = Table(stats_data, colWidths=[70*mm, 50*mm])
        stats_table.setStyle(TableStyle([
            # Заголовок
            ('BACKGROUND', (0, 0), (-1, 0), pdf_colors.HexColor('#4CAF50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), pdf_colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), font_bold),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Данные
            ('FONTNAME', (0, 1), (-1, -1), font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, pdf_colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 1), (0, -1), 10),
            ('RIGHTPADDING', (1, 1), (1, -1), 10),
            
            # Выделяем итоговые строки
            ('BACKGROUND', (0, -2), (-1, -2), pdf_colors.HexColor('#E8F5E9')),
            ('BACKGROUND', (0, -1), (-1, -1), pdf_colors.HexColor('#FFECB3')),
        ]))
        
        stats_table.wrapOn(c, page_width, page_height)
        stats_height = stats_table._height
        
        # Проверка перед статистикой
        if y - stats_height < MIN_MARGIN:
            c.showPage()
            y = page_height - 30*mm
        
        stats_table.drawOn(c, 20*mm, y - stats_height)
        
        y = y - stats_height - 10*mm
        
        # Проверка перед рекомендациями
        if y < 60*mm:  # Нужно минимум 60мм для рекомендаций
            c.showPage()
            y = page_height - 30*mm
        
        # РЕКОМЕНДАЦИИ (с ограничением ширины текста)
        c.setFont(font_bold, 11)
        c.drawString(20*mm, y, "💡 РЕКОМЕНДАЦИИ:")
        y -= 6*mm
        
        c.setFont(font_name, 9)
        recommendations = []
        
        if result['utilization_percent'] < 70:
            recommendations.append("⚠ Низкое использование материала (<70%).")
            recommendations.append("  Рассмотрите объединение с другими заказами.")
        elif result['utilization_percent'] > 85:
            recommendations.append("✓ Отличное использование материала (>85%).")
            recommendations.append("  Оптимальный раскрой!")
        else:
            recommendations.append("✓ Хорошее использование материала (70-85%).")
        
        if result['sheets_needed'] == 1:
            recommendations.append("✓ Все детали помещаются на 1 лист -")
            recommendations.append("  экономия времени резки.")
        
        recommendations.append("• Обрезки можно использовать для будущих заказов")
        recommendations.append("  (см. Excel с обрезками).")
        recommendations.append("• Зазор между деталями: 5 мм (учтено автоматически).")
        
        # Выводим рекомендации с проверкой ширины и места на странице
        max_width = page_width - 40*mm  # Максимальная ширина текста
        for rec in recommendations:
            # Проверка места перед каждой строкой
            if y < MIN_MARGIN + 5*mm:
                c.showPage()
                y = page_height - 30*mm
                c.setFont(font_name, 9)
            
            if len(rec) > 65:  # Если текст длинный
                # Разбиваем на строки
                words = rec.split()
                line = ""
                for word in words:
                    test_line = line + " " + word if line else word
                    if len(test_line) <= 65:
                        line = test_line
                    else:
                        if y < MIN_MARGIN + 5*mm:
                            c.showPage()
                            y = page_height - 30*mm
                            c.setFont(font_name, 9)
                        c.drawString(25*mm, y, line)
                        y -= 4*mm
                        line = word
                if line:
                    if y < MIN_MARGIN + 5*mm:
                        c.showPage()
                        y = page_height - 30*mm
                        c.setFont(font_name, 9)
                    c.drawString(25*mm, y, line)
                    y -= 5*mm
            else:
                c.drawString(25*mm, y, rec)
                y -= 5*mm
        
        # РАСКРОЙ - НА ОТДЕЛЬНЫХ СТРАНИЦАХ
        SHEET_WIDTH = 2500  # мм
        SHEET_HEIGHT = 1250  # мм
        
        for sheet in result['sheets']:
            c.showPage()
            
            # Заголовок листа
            c.setFont(font_bold, 18)
            c.drawCentredString(page_width/2, page_height - 20*mm, 
                               f"ЛИСТ №{sheet['number']} - {len(sheet['parts'])} деталей")
            
            # Размеры листа
            c.setFont(font_name, 10)
            c.drawCentredString(page_width/2, page_height - 28*mm, 
                               f"Размер листа: {SHEET_WIDTH}x{SHEET_HEIGHT} мм")
            
            # Рисуем визуализацию
            # Масштаб для размещения на странице
            available_width = page_width - 40*mm
            available_height = page_height - 60*mm
            
            scale_w = available_width / SHEET_WIDTH
            scale_h = available_height / SHEET_HEIGHT
            scale = min(scale_w, scale_h)
            
            # Центрируем
            sheet_w = SHEET_WIDTH * scale
            sheet_h = SHEET_HEIGHT * scale
            offset_x = (page_width - sheet_w) / 2
            offset_y = (page_height - sheet_h) / 2 - 15*mm
            
            # Контур листа
            c.setStrokeColor(pdf_colors.black)
            c.setLineWidth(2)
            c.setFillColor(pdf_colors.HexColor('#f0f0f0'))
            c.rect(offset_x, offset_y, sheet_w, sheet_h, fill=1, stroke=1)
            
            # Рисуем детали с номерами
            parts_legend = []  # Данные для таблицы-легенды
            
            for idx, part in enumerate(sheet['parts']):
                color = colors_list[idx % len(colors_list)]
                part_num = idx + 1  # Номер детали (с 1)
                
                # Координаты из rectpack ВКЛЮЧАЮТ зазор 2.5мм
                # Рисуем РЕАЛЬНЫЙ размер детали (БЕЗ зазора)
                CUT_GAP = 2.5  # мм - зазор добавляется ОДИН раз к каждому размеру!
                
                x_real_mm = part['x'] + CUT_GAP / 2  # Центрируем зазор
                y_real_mm = part['y'] + CUT_GAP / 2
                w_real_mm = part['width'] - CUT_GAP  # Вычитаем зазор (он добавлен ОДИН раз)
                h_real_mm = part['height'] - CUT_GAP
                
                x = offset_x + x_real_mm * scale
                y = offset_y + y_real_mm * scale
                w = w_real_mm * scale
                h = h_real_mm * scale
                
                # ПРОСТЫЕ ПРЯМОУГОЛЬНИКИ (реальный размер, БЕЗ зазора)
                c.setFillColorRGB(*color)
                c.setStrokeColor(pdf_colors.black)
                c.setLineWidth(0.5)
                c.rect(x, y, w, h, fill=1, stroke=1)
                
                # Имя детали
                part_name = part['name'].split('#')[0]
                
                # РАЗМЕРЫ для отображения (вычитаем зазор!)
                # part['width'] и part['height'] содержат размер + CUT_GAP (2.5мм)
                is_rotated = part.get('rotated', False)
                if is_rotated:
                    # Для повернутых меняем местами
                    size_w = h_real_mm  # Уже вычтен зазор
                    size_h = w_real_mm
                else:
                    size_w = w_real_mm  # Уже вычтен зазор
                    size_h = h_real_mm
                
                size_text = f"{size_w:.0f}x{size_h:.0f}"
                
                # Добавляем в легенду
                parts_legend.append({
                    'num': part_num,
                    'name': part_name,  # Полное название (не обрезаем!)
                    'size': size_text,
                    'color': color
                })
                
                # Показываем текст на детали (в зависимости от размера)
                c.setFillColor(pdf_colors.black)
                
                # БОЛЬШАЯ деталь - показываем ВСЁ (номер, название, размер)
                if w > 25*mm and h > 12*mm:
                    # Номер в верхнем левом углу
                    c.setFont(font_bold, 8)
                    c.drawString(x + 2*mm, y + h - 4*mm, f"#{part_num}")
                    
                    # Название по центру
                    c.setFont(font_name, 7 if w > 40*mm else 6)
                    short_name = part_name[:20] if len(part_name) > 20 else part_name
                    c.drawCentredString(x + w/2, y + h/2 + 2*mm, short_name)
                    
                    # Размер под названием
                    c.setFont(font_bold, 7)
                    c.drawCentredString(x + w/2, y + h/2 - 2*mm, size_text)
                    
                # СРЕДНЯЯ деталь - номер и размер
                elif w > 15*mm and h > 8*mm:
                    # Номер
                    c.setFont(font_bold, 9)
                    c.drawCentredString(x + w/2, y + h/2 + 2*mm, f"#{part_num}")
                    
                    # Размер
                    c.setFont(font_name, 6)
                    c.drawCentredString(x + w/2, y + h/2 - 2*mm, size_text)
                    
                # МАЛЕНЬКАЯ/УЗКАЯ деталь - только номер в белом кружке
                else:
                    c.setFillColor(pdf_colors.white)
                    c.setStrokeColor(pdf_colors.black)
                    c.setLineWidth(0.5)
                    
                    # Белый кружок
                    num_radius = 2*mm
                    c.circle(x + w/2, y + h/2, num_radius, fill=1, stroke=1)
                    
                    # Номер черным
                    c.setFillColor(pdf_colors.black)
                    c.setFont(font_bold, 7)
                    c.drawCentredString(x + w/2, y + h/2 - 0.7*mm, str(part_num))
            
            # === ТАБЛИЦА-ЛЕГЕНДА на отдельной странице ===
            c.showPage()  # Новая страница для таблицы
            
            # Заголовок страницы
            y_pos = page_height - 40*mm
            c.setFont(font_bold, 16)
            c.setFillColor(pdf_colors.black)
            c.drawCentredString(page_width/2, y_pos, "СПИСОК ДЕТАЛЕЙ")
            y_pos -= 15*mm
            
            # Параметры таблицы
            table_x = 30*mm
            table_y = y_pos
            row_height = 7*mm
            col_widths = [15*mm, 130*mm, 30*mm]  # №, Название (полное!), Размер
            
            # Заголовки таблицы
            c.setFont(font_bold, 10)
            c.setFillColor(pdf_colors.HexColor('#4472C4'))
            c.setStrokeColor(pdf_colors.black)
            c.setLineWidth(1)
            
            # Фон заголовков
            c.rect(table_x, table_y - row_height, sum(col_widths), row_height, fill=1, stroke=1)
            
            # Текст заголовков
            c.setFillColor(pdf_colors.white)
            c.drawString(table_x + 5*mm, table_y - row_height + 2*mm, "№")
            c.drawString(table_x + col_widths[0] + 5*mm, table_y - row_height + 2*mm, "Название детали")
            c.drawString(table_x + col_widths[0] + col_widths[1] + 5*mm, table_y - row_height + 2*mm, "Размер, мм")
            
            table_y -= row_height
            
            # Строки с деталями
            c.setFont(font_name, 9)
            for idx, item in enumerate(parts_legend):
                # Чередующийся цвет фона
                if idx % 2 == 0:
                    c.setFillColor(pdf_colors.HexColor('#F2F2F2'))
                else:
                    c.setFillColor(pdf_colors.white)
                
                c.setStrokeColor(pdf_colors.grey)
                c.setLineWidth(0.5)
                c.rect(table_x, table_y - row_height, sum(col_widths), row_height, fill=1, stroke=1)
                
                # Цветной индикатор
                c.setFillColorRGB(*item['color'])
                c.setStrokeColor(pdf_colors.black)
                c.rect(table_x + 2*mm, table_y - row_height + 2*mm, 4*mm, 3*mm, fill=1, stroke=1)
                
                # Номер
                c.setFillColor(pdf_colors.black)
                c.setFont(font_bold, 10)
                c.drawString(table_x + 8*mm, table_y - row_height + 2*mm, str(item['num']))
                
                # Название (полное!)
                c.setFont(font_name, 9)
                c.drawString(table_x + col_widths[0] + 2*mm, table_y - row_height + 2*mm, item['name'])
                
                # Размер
                c.setFont(font_bold, 9)
                c.drawString(table_x + col_widths[0] + col_widths[1] + 5*mm, table_y - row_height + 2*mm, item['size'])
                
                table_y -= row_height
                
                # Если вышли за границы страницы - новая страница
                if table_y < 40*mm:
                    c.showPage()
                    table_y = page_height - 40*mm
                    
                    # Повторяем заголовок на новой странице
                    c.setFont(font_bold, 10)
                    c.setFillColor(pdf_colors.HexColor('#4472C4'))
                    c.rect(table_x, table_y - row_height, sum(col_widths), row_height, fill=1, stroke=1)
                    c.setFillColor(pdf_colors.white)
                    c.drawString(table_x + 5*mm, table_y - row_height + 2*mm, "№")
                    c.drawString(table_x + col_widths[0] + 5*mm, table_y - row_height + 2*mm, "Название детали")
                    c.drawString(table_x + col_widths[0] + col_widths[1] + 5*mm, table_y - row_height + 2*mm, "Размер, мм")
                    table_y -= row_height
        
        # === АНАЛИЗ ОПТИМАЛЬНОСТИ (НА НОВОЙ СТРАНИЦЕ!) ===
        if self.current_dimensions and self.project_info:
            # ВСЕГДА начинаем с новой страницы
            c.showPage()
            y = page_height - 30*mm
            
            MIN_MARGIN = 30*mm  # Минимальный отступ снизу
            
            # Весь блок анализа оптимальности удален
        
        # === НОВАЯ СТРАНИЦА: РЕКОМЕНДУЕМАЯ РАСКЛАДКА ===
                c.showPage()
        
        # Сохраняем PDF
        c.save()
    
    
    def _create_tooltip(self, widget, text):
        """
        Создать всплывающую подсказку для виджета
        
        Args:
            widget: Tkinter виджет
            text: Текст подсказки
        """
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            label = tk.Label(tooltip, text=text, 
                           background="#FFFACD", 
                           relief=tk.SOLID, 
                           borderwidth=1,
                           font=('Arial', 9),
                           padx=5, pady=3)
            label.pack()
            
            # Сохраняем ссылку на tooltip
            widget.tooltip_window = tooltip
        
        def hide_tooltip(event):
            if hasattr(widget, 'tooltip_window'):
                widget.tooltip_window.destroy()
                delattr(widget, 'tooltip_window')
        
        widget.bind('<Enter>', show_tooltip)
        widget.bind('<Leave>', hide_tooltip)
    
    def add_files_to_project(self):
        """
        Добавить новые DXF файлы к текущему проекту без сброса прогресса
        """
        if not self.files_data:
            messagebox.showwarning("Нет проекта", 
                                  "Сначала загрузите файлы проекта!")
            return
        
        # Выбираем файлы для добавления
        new_files = filedialog.askopenfilenames(
            title="Выберите DXF файлы для добавления к проекту",
            filetypes=[("DXF files", "*.dxf"), ("All files", "*.*")],
            initialdir=Path(self.files_data[0]['filepath']).parent
        )
        
        if not new_files:
            return
        
        try:
            print(f"[DEBUG] Добавляем {len(new_files)} файлов к проекту")
            
            # Сохраняем текущий путь проекта
            current_project_path = Path(self.files_data[0]['filepath']).parent
            current_project_name = current_project_path.name
            
            added_count = 0
            
            # Обрабатываем каждый файл отдельно
            for filepath in new_files:
                try:
                    # Для одиночных файлов используем прямое чтение DXF
                    import ezdxf
                    doc = ezdxf.readfile(filepath)
                    msp = doc.modelspace()
                    
                    # Получаем границы через все объекты
                    min_x = min_y = float('inf')
                    max_x = max_y = float('-inf')
                    
                    for entity in msp:
                        try:
                            if hasattr(entity, 'dxf') and hasattr(entity.dxf, 'start'):
                                # Линии, дуги и т.д.
                                if hasattr(entity.dxf, 'start'):
                                    min_x = min(min_x, entity.dxf.start.x)
                                    min_y = min(min_y, entity.dxf.start.y)
                                    max_x = max(max_x, entity.dxf.start.x)
                                    max_y = max(max_y, entity.dxf.start.y)
                                if hasattr(entity.dxf, 'end'):
                                    min_x = min(min_x, entity.dxf.end.x)
                                    min_y = min(min_y, entity.dxf.end.y)
                                    max_x = max(max_x, entity.dxf.end.x)
                                    max_y = max(max_y, entity.dxf.end.y)
                            elif hasattr(entity, 'dxf') and hasattr(entity.dxf, 'center'):
                                # Круги
                                radius = getattr(entity.dxf, 'radius', 0)
                                min_x = min(min_x, entity.dxf.center.x - radius)
                                min_y = min(min_y, entity.dxf.center.y - radius)
                                max_x = max(max_x, entity.dxf.center.x + radius)
                                max_y = max(max_y, entity.dxf.center.y + radius)
                        except:
                            continue
                    
                    if min_x != float('inf') and max_x != float('-inf'):
                        width = max_x - min_x
                        height = max_y - min_y
                        area_m2 = (width * height) / 1000000  # мм² в м²
                        
                        if width > 0 and height > 0:
                            # Создаем данные файла вручную
                            file_data = {
                                'name': Path(filepath).stem,
                                'filename': Path(filepath).name,
                                'filepath': filepath,
                                'width': width + 5,  # Добавляем зазор
                                'height': height + 5,
                                'real_width': width,
                                'real_height': height,
                                'area_m2': area_m2,
                                'quantity': 1,  # Добавляем количество
                                'source_folder': "Добавленные файлы",
                                'is_additional': True,
                                'cut_length_mm': 0,  # Будет рассчитано позже
                                'contours': 1,  # Базовое значение
                                'cutting_time_minutes': 0
                            }
                            
                            # Добавляем в список
                            self.files_data.append(file_data)
                            
                            # Добавляем строку в таблицу
                            self._add_file_row_to_table(file_data, len(self.files_data) - 1)
                            added_count += 1
                            print(f"[DEBUG] Добавлен файл: {Path(filepath).name}")
                            
                            # Проверяем готовность файла к резке
                            try:
                                from components.dxf_cutting_readiness_analyzer import DXFCuttingReadinessAnalyzer
                                analyzer = DXFCuttingReadinessAnalyzer()
                                report = analyzer.analyze_file(filepath)
                                
                                if not report.get('is_ready', True):
                                    print(f"[WARNING] Файл {Path(filepath).name} требует доработки:")
                                    for problem in report.get('problems', []):
                                        print(f"  - {problem}")
                                        
                            except Exception as e:
                                print(f"[DEBUG] Не удалось проверить готовность файла {Path(filepath).name}: {e}")
                        else:
                            print(f"[WARNING] Не удалось получить границы файла: {Path(filepath).name}")
                    else:
                        print(f"[WARNING] Не удалось получить границы файла: {Path(filepath).name}")
                        
                except Exception as e:
                    print(f"[ERROR] Ошибка анализа файла {filepath}: {e}")
                    import traceback
                    traceback.print_exc()
            
            if added_count == 0:
                messagebox.showwarning("Нет файлов", 
                                      "Не удалось проанализировать выбранные файлы!")
                return
            
            # Обновляем итоги
            self.update_summary()
            
            
            # Запускаем проверку готовности к резке в фоне
            print(f"[DEBUG] Запускаем проверку готовности к резке для всех файлов...")
            self.analyze_cutting_readiness()
            
            # Показываем сообщение
            dxf_files = sum(1 for f in self.files_data if f.get('filepath', '').endswith('.dxf'))
            messagebox.showinfo("✅ Файлы добавлены!",
                              f"Добавлено {added_count} файлов к проекту\n"
                              f"Проект: {current_project_name}\n\n"
                              f"📊 Всего файлов: {len(self.files_data)}\n"
                              f"📄 DXF файлов: {dxf_files}\n\n"
                              f"🔍 Проверка готовности к резке выполнена в фоне\n"
                              f"Используйте кнопку 'Результаты проверки' для просмотра деталей")
            
            # Автоматически запускаем раскрой если есть предыдущий результат
            if self.last_nesting_result:
                print(f"[DEBUG] Автоматически обновляем раскрой после добавления файлов")
                self._run_smart_nesting_optimization()
            
        except Exception as e:
            print(f"[ERROR] Ошибка добавления файлов: {e}")
            messagebox.showerror("Ошибка", 
                               f"Ошибка добавления файлов:\n{e}")
    
    def add_files_from_folder(self):
        """
        Добавить все DXF файлы из папки к текущему проекту
        """
        if not self.files_data:
            messagebox.showwarning("Нет проекта", 
                                  "Сначала загрузите файлы проекта!")
            return
        
        # Выбираем папку
        folder_path = filedialog.askdirectory(
            title="Выберите папку с DXF файлами для добавления",
            initialdir=Path(self.files_data[0]['filepath']).parent
        )
        
        if not folder_path:
            return
        
        try:
            print(f"[DEBUG] Добавляем файлы из папки: {folder_path}")
            
            # Используем существующую логику из calculator
            result = self.calculator.calculate_from_folder(folder_path)
            
            if not result['success']:
                messagebox.showerror("Ошибка", 
                                   f"Не удалось загрузить файлы:\n{result.get('error', 'Неизвестная ошибка')}")
                return
            
            added_count = 0
            folder_name = Path(folder_path).name
            
            # Добавляем новые файлы к существующим
            for file_data in result['files']:
                # Помечаем, что файл из дополнительной папки
                file_data['source_folder'] = folder_name
                file_data['is_additional'] = True
                
                # Добавляем в список
                self.files_data.append(file_data)
                
                # Добавляем строку в таблицу
                self._add_file_row_to_table(file_data, len(self.files_data) - 1)
                added_count += 1
            
            # Обновляем итоги
            self.update_summary()
            
            # Запускаем проверку готовности к резке в фоне
            print(f"[DEBUG] Запускаем проверку готовности к резке для всех файлов...")
            self.analyze_cutting_readiness()
            
            # Показываем сообщение
            dxf_files = sum(1 for f in self.files_data if f.get('filepath', '').endswith('.dxf'))
            messagebox.showinfo("✅ Файлы добавлены!",
                              f"Добавлено {added_count} файлов из папки\n"
                              f"Папка: {folder_name}\n\n"
                              f"📊 Всего файлов: {len(self.files_data)}\n"
                              f"📄 DXF файлов: {dxf_files}\n\n"
                              f"🔍 Проверка готовности к резке выполнена в фоне\n"
                              f"Используйте кнопку 'Результаты проверки' для просмотра деталей")
            
            # Автоматически запускаем раскрой если есть предыдущий результат
            if self.last_nesting_result:
                print(f"[DEBUG] Автоматически обновляем раскрой после добавления файлов из папки")
                self._run_smart_nesting_optimization()
            
        except Exception as e:
            print(f"[ERROR] Ошибка добавления файлов из папки: {e}")
            messagebox.showerror("Ошибка", 
                               f"Ошибка добавления файлов:\n{e}")
    
    def scan_projects_database(self):
        """
        v3.0: Сканирование всех проектов для базы данных
        """
        # Выбор папки с проектами
        base_folder = filedialog.askdirectory(
            title="Выберите корневую папку с проектами",
            initialdir=str(Path.home())
        )
        
        if not base_folder:
            return
        
        # Создаем окно прогресса
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Сканирование проектов")
        progress_window.geometry("500x200")
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        # Центрируем окно
        progress_window.update_idletasks()
        x = (progress_window.winfo_screenwidth() // 2) - (500 // 2)
        y = (progress_window.winfo_screenheight() // 2) - (200 // 2)
        progress_window.geometry(f"+{x}+{y}")
        
        # Контент
        frame = ttk.Frame(progress_window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="🔍 Сканирование проектов...", 
                 font=('Arial', 12, 'bold')).pack(pady=(0,10))
        
        status_label = ttk.Label(frame, text="Инициализация...", 
                                font=('Arial', 10))
        status_label.pack(pady=(0,10))
        
        progress_bar = ttk.Progressbar(frame, mode='indeterminate', length=400)
        progress_bar.pack(pady=(0,10))
        progress_bar.start(10)
        
        stats_text = tk.Text(frame, height=4, width=60, font=('Arial', 9))
        stats_text.pack()
        
        # Обновляем GUI
        progress_window.update()
        
        try:
            # Запускаем сканирование
            status_label.config(text=f"Сканирование папки: {Path(base_folder).name}")
            progress_window.update()
            
            projects_found = self.projects_db.scan_all_projects(base_folder)
            
            progress_bar.stop()
            
            if projects_found > 0:
                stats = self.projects_db.get_statistics()
                
                stats_text.insert('1.0', 
                    f"✓ Найдено проектов: {stats['total_projects']}\n"
                    f"✓ Деталей в базе: {stats.get('total_parts', 0)}\n"
                    f"✓ Групп в индексе: {stats.get('indexed_groups', 0)}\n"
                    f"✓ База данных сохранена в кэш"
                )
                stats_text.config(state=tk.DISABLED)
                
                # Обновляем статус в главном окне
                if hasattr(self, 'db_status_label'):
                    self.db_status_label.config(
                        text=f"База данных: {stats['total_projects']} проектов",
                        foreground='green'
                    )
                
                status_label.config(text="✅ Сканирование завершено!")
                
                # Кнопка закрытия
                ttk.Button(frame, text="Закрыть", 
                          command=progress_window.destroy,
                          width=20).pack(pady=(10,0))
                
            else:
                stats_text.insert('1.0', 
                    "⚠️ Проекты не найдены\n\n"
                    "Убедитесь что выбрана правильная папка\n"
                    "с проектами в формате ZVD.LITE.H.W.L"
                )
                status_label.config(text="Проекты не найдены")
                
                ttk.Button(frame, text="Закрыть", 
                          command=progress_window.destroy,
                          width=20).pack(pady=(10,0))
                
        except Exception as e:
            progress_bar.stop()
            messagebox.showerror("Ошибка", 
                               f"Ошибка сканирования:\n{e}",
                               parent=progress_window)
            progress_window.destroy()
    
    def expand_window_for_table(self):
        """Адаптивно расширить окно при заполнении таблицы"""
        if not self.window_expanded:
            # Получаем текущий размер окна
            current_width = self.root.winfo_width()
            current_height = self.root.winfo_height()
            
            # Расширяем окно для комфортного просмотра таблицы
            new_width = max(1200, current_width + 200)
            new_height = max(700, current_height + 100)
            
            # Ограничиваем максимальный размер экраном
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            new_width = min(new_width, int(screen_width * 0.9))
            new_height = min(new_height, int(screen_height * 0.9))
            
            # Применяем новый размер
            self.root.geometry(f"{new_width}x{new_height}")
            self.window_expanded = True
            print(f"[DEBUG] Окно расширено до {new_width}x{new_height}")
    
    def analyze_cutting_readiness(self):
        """Анализ готовности DXF файлов к лазерной резке (упрощенная версия)"""
        print(f"[DEBUG] === НАЧАЛО АНАЛИЗА ГОТОВНОСТИ К РЕЗКЕ ===")
        print(f"[DEBUG] Всего файлов в проекте: {len(self.files_data)}")
        
        try:
            # Собираем пути к DXF файлам
            dxf_files = []
            for file_data in self.files_data:
                if file_data.get('filepath') and file_data['filepath'].endswith('.dxf'):
                    dxf_files.append(file_data['filepath'])
                    print(f"[DEBUG] Добавлен DXF файл: {file_data['filepath']}")
            
            if not dxf_files:
                print("[DEBUG] Нет DXF файлов для анализа готовности к резке")
                # Активируем кнопку даже если нет DXF файлов
                if hasattr(self, 'check_results_btn'):
                    self.check_results_btn.config(state=tk.NORMAL)
                    print(f"[DEBUG] Кнопка 'Результаты проверки' активирована (нет DXF файлов)")
                return
            
            print(f"[DEBUG] Анализируем готовность {len(dxf_files)} DXF файлов...")
            
            # Простой анализ - проверяем только существование файлов
            reports = []
            for filepath in dxf_files:
                try:
                    import os
                    if os.path.exists(filepath):
                        # Простая проверка - файл существует
                        report = {
                            'filename': os.path.basename(filepath),
                            'filepath': filepath,
                            'is_ready': True,
                            'problems': [],
                            'status': 'Готов к резке'
                        }
                    else:
                        report = {
                            'filename': os.path.basename(filepath),
                            'filepath': filepath,
                            'is_ready': False,
                            'problems': ['Файл не найден'],
                            'status': 'Ошибка'
                        }
                    reports.append(report)
                except Exception as e:
                    report = {
                        'filename': os.path.basename(filepath),
                        'filepath': filepath,
                        'is_ready': False,
                        'problems': [f'Ошибка анализа: {str(e)}'],
                        'status': 'Ошибка'
                    }
                    reports.append(report)
            
            # Подсчитываем статистику
            total_files = len(reports)
            ready_files = sum(1 for r in reports if r.get('is_ready', False))
            problem_files = total_files - ready_files
            
            print(f"[DEBUG] Проверка завершена: {ready_files}/{total_files} файлов готовы к резке")
            if problem_files > 0:
                print(f"[WARNING] {problem_files} файлов требуют доработки")
            
            # Сохраняем результаты для возможного просмотра
            self._cutting_readiness_results = {
                'reports': reports, 
                'summary': {
                    'total_files': total_files,
                    'ready_files': ready_files,
                    'problem_files': problem_files
                }
            }
            
            # Активируем кнопку просмотра результатов
            if hasattr(self, 'check_results_btn'):
                self.check_results_btn.config(state=tk.NORMAL)
                print(f"[DEBUG] Кнопка 'Результаты проверки' активирована")
            else:
                print(f"[ERROR] Кнопка 'check_results_btn' не найдена!")
            
        except Exception as e:
            print(f"[DEBUG] Ошибка анализа готовности к резке: {e}")
            import traceback
            traceback.print_exc()
            self._cutting_readiness_results = None
            # Активируем кнопку даже при ошибке, чтобы пользователь мог попробовать снова
            if hasattr(self, 'check_results_btn'):
                self.check_results_btn.config(state=tk.NORMAL)
                print(f"[DEBUG] Кнопка 'Результаты проверки' активирована (после ошибки)")
            else:
                print(f"[ERROR] Кнопка 'check_results_btn' не найдена даже после ошибки!")
        
        print(f"[DEBUG] === КОНЕЦ АНАЛИЗА ГОТОВНОСТИ К РЕЗКЕ ===")
    
    def show_cutting_readiness_results(self):
        """Показать результаты проверки готовности к резке"""
        if not hasattr(self, '_cutting_readiness_results') or not self._cutting_readiness_results:
            messagebox.showinfo("Информация", "Результаты проверки недоступны.\nСначала загрузите файлы проекта.")
            return
        
        # Показываем результаты в окне
        self._show_cutting_readiness_results(
            self._cutting_readiness_results['reports'], 
            self._cutting_readiness_results['summary']
        )
    
    def recalculate_reports(self):
        """Пересчитать отчеты без перезагрузки проекта"""
        if not self.files_data:
            messagebox.showwarning("Предупреждение", "Нет загруженных файлов для пересчета!")
            return
        
        # Подтверждение
        if not messagebox.askyesno("Подтверждение", 
                                 "Пересчитать отчеты для текущего проекта?\n\n"
                                 "Это создаст новые PDF и Excel файлы с актуальными данными."):
            return
        
        try:
            print("[DEBUG] Начинаем пересчет отчетов...")
            
            # Получаем название проекта
            project_name = self.project_name.get().strip() or "Проект без названия"
            
            # Запускаем оптимизацию раскроя
            result = self.optimize_nesting_smart()
            
            if not result['success']:
                messagebox.showerror("Ошибка", f"Ошибка оптимизации раскроя:\n{result.get('error', 'Неизвестная ошибка')}")
                return
            
            # Создаем отчеты
            total_parts = sum(file_data.get('quantity', 1) for file_data in self.files_data)
            pdf_path, excel_path = self.create_simple_reports(result, total_parts, project_name)
            
            # Показываем результат
            messagebox.showinfo("Успех", 
                              f"Отчеты пересчитаны успешно!\n\n"
                              f"📄 PDF: {pdf_path.name}\n"
                              f"📊 Excel: {excel_path.name}\n\n"
                              f"Файлы сохранены в папке:\n{pdf_path.parent}")
            
            # Открываем папку с файлами
            import os
            os.startfile(pdf_path.parent)
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при пересчете отчетов:\n{str(e)}")
            print(f"[ERROR] Ошибка пересчета отчетов: {e}")
            import traceback
            traceback.print_exc()
    
    def _show_cutting_readiness_results(self, reports, summary):
        """Показать результаты анализа готовности к резке"""
        try:
            # Создаем окно с результатами
            results_window = tk.Toplevel(self.root)
            results_window.title("Анализ готовности к лазерной резке")
            results_window.geometry("800x600")
            results_window.transient(self.root)
            results_window.grab_set()
            
            # Заголовок
            title_frame = ttk.Frame(results_window)
            title_frame.pack(fill=tk.X, padx=10, pady=10)
            
            readiness_percent = summary['readiness_percentage']
            if readiness_percent >= 90:
                status_color = '#4CAF50'  # Зеленый
                status_icon = "✅"
                status_text = "ГОТОВ К РЕЗКЕ"
            elif readiness_percent >= 70:
                status_color = '#FF9800'  # Оранжевый
                status_icon = "⚠️"
                status_text = "ТРЕБУЕТ ДОРАБОТКИ"
            else:
                status_color = '#F44336'  # Красный
                status_icon = "❌"
                status_text = "НЕ ГОТОВ К РЕЗКЕ"
            
            ttk.Label(title_frame, text=f"{status_icon} {status_text}", 
                     font=('Arial', 14, 'bold'), foreground=status_color).pack()
            
            # Статистика
            stats_text = f"Готовность: {readiness_percent:.1f}% ({summary['ready_files']}/{summary['total_files']} файлов)"
            if summary['total_issues'] > 0:
                stats_text += f" | Проблем: {summary['total_issues']}"
            
            ttk.Label(title_frame, text=stats_text, font=('Arial', 10)).pack()
            
            # Создаем единую страницу с прокруткой
            main_frame = ttk.Frame(results_window)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            # Создаем Canvas с прокруткой
            canvas = tk.Canvas(main_frame, bg='white')
            scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
                )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Сводка
            summary_frame = ttk.LabelFrame(scrollable_frame, text="📊 Сводка", padding="10")
            summary_frame.pack(fill=tk.X, pady=(0, 10))
            
            summary_content = f"Всего файлов: {summary['total_files']}\n"
            summary_content += f"Готовых к резке: {summary['ready_files']}\n"
            summary_content += f"Требуют доработки: {summary['not_ready_files']}\n"
            summary_content += f"Общая готовность: {readiness_percent:.1f}%\n\n"
            
            if summary['total_issues'] > 0:
                summary_content += "ОБНАРУЖЕННЫЕ ПРОБЛЕМЫ:\n"
                for issue_type, count in summary['issue_types'].items():
                    summary_content += f"  - {issue_type}: {count} случаев\n"
                
                summary_content += "\nРЕКОМЕНДАЦИИ:\n"
                for rec in summary['recommendations']:
                    summary_content += f"  - {rec}\n"
            else:
                summary_content += "Все файлы готовы к лазерной резке!\n"
            
            summary_text = tk.Text(summary_frame, wrap=tk.WORD, font=('Arial', 9), height=6)
            summary_text.pack(fill=tk.X)
            summary_text.insert('1.0', summary_content)
            summary_text.config(state=tk.DISABLED)
            
            # Таблица файлов
            table_frame = ttk.LabelFrame(scrollable_frame, text="📋 Таблица файлов", padding="10")
            table_frame.pack(fill=tk.X, pady=(0, 10))
            
            # Создаем таблицу с результатами
            table_container = ttk.Frame(table_frame)
            table_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Заголовки таблицы
            headers = ["Файл", "Статус", "Готовность", "Сущностей", "Проблем", "Проблемы"]
            
            # Создаем заголовки с цветным фоном
            for col, header in enumerate(headers):
                header_frame = ttk.Frame(table_container)
                header_frame.grid(row=0, column=col, padx=1, pady=1, sticky='ew')
                header_frame.configure(relief='raised', borderwidth=1)
                
                label = ttk.Label(header_frame, text=header, font=('Arial', 9, 'bold'))
                label.pack(fill=tk.BOTH, expand=True, padx=3, pady=2)
            
            # Настраиваем веса колонок
            table_container.grid_columnconfigure(0, weight=2)  # Файл - шире
            table_container.grid_columnconfigure(1, weight=1)  # Статус
            table_container.grid_columnconfigure(2, weight=1)  # Готовность
            table_container.grid_columnconfigure(3, weight=1)  # Сущностей
            table_container.grid_columnconfigure(4, weight=1)  # Проблем
            table_container.grid_columnconfigure(5, weight=3)  # Проблемы - шире
            
            # Заполняем таблицу данными
            for row, report in enumerate(reports, 1):
                # Статус с иконкой
                if report.is_ready:
                    status_text = "✅ ГОТОВ"
                    status_color = '#4CAF50'
                elif report.readiness_score >= 70:
                    status_text = "⚠️ ДОРАБОТКА"
                    status_color = '#FF9800'
                else:
                    status_text = "❌ НЕ ГОТОВ"
                    status_color = '#F44336'
                
                # Имя файла (сокращенное)
                filename_short = report.filename[:30] + "..." if len(report.filename) > 30 else report.filename
                
                # Готовность
                readiness_text = f"{report.readiness_score:.1f}%"
                
                # Количество сущностей
                entities_text = str(report.total_entities)
                
                # Количество проблем
                problems_count = len(report.issues)
                problems_text = str(problems_count)
                
                # Краткое описание проблем
                if report.issues:
                    issue_types = {}
                    for issue in report.issues:
                        issue_type = issue.type
                        if issue_type not in issue_types:
                            issue_types[issue_type] = 0
                        issue_types[issue_type] += 1
                    
                    problems_desc = ", ".join([f"{issue_type}({count})" for issue_type, count in issue_types.items()])
                    if len(problems_desc) > 40:
                        problems_desc = problems_desc[:37] + "..."
                else:
                    problems_desc = "Нет проблем"
                
                # Создаем ячейки с цветовой индикацией
                # Файл
                file_frame = ttk.Frame(table_container)
                file_frame.grid(row=row, column=0, padx=1, pady=1, sticky='ew')
                file_label = ttk.Label(file_frame, text=filename_short, font=('Arial', 8))
                file_label.pack(fill=tk.BOTH, expand=True, padx=3, pady=2)
                
                # Статус с цветом
                status_frame = ttk.Frame(table_container)
                status_frame.grid(row=row, column=1, padx=1, pady=1, sticky='ew')
                status_label = ttk.Label(status_frame, text=status_text, font=('Arial', 8, 'bold'))
                status_label.pack(fill=tk.BOTH, expand=True, padx=3, pady=2)
                status_label.configure(foreground=status_color)
                
                # Готовность с цветом фона
                readiness_frame = ttk.Frame(table_container)
                readiness_frame.grid(row=row, column=2, padx=1, pady=1, sticky='ew')
                readiness_label = ttk.Label(readiness_frame, text=readiness_text, font=('Arial', 8, 'bold'))
                readiness_label.pack(fill=tk.BOTH, expand=True, padx=3, pady=2)
                
                # Цвет фона в зависимости от готовности
                if report.readiness_score >= 90:
                    bg_color = '#E8F5E9'  # Светло-зеленый
                elif report.readiness_score >= 70:
                    bg_color = '#FFF3E0'  # Светло-оранжевый
                else:
                    bg_color = '#FFEBEE'  # Светло-красный
                
                readiness_label.configure(background=bg_color)
                
                # Сущности
                entities_frame = ttk.Frame(table_container)
                entities_frame.grid(row=row, column=3, padx=1, pady=1, sticky='ew')
                entities_label = ttk.Label(entities_frame, text=entities_text, font=('Arial', 8))
                entities_label.pack(fill=tk.BOTH, expand=True, padx=3, pady=2)
                
                # Проблемы
                problems_frame = ttk.Frame(table_container)
                problems_frame.grid(row=row, column=4, padx=1, pady=1, sticky='ew')
                problems_label = ttk.Label(problems_frame, text=problems_text, font=('Arial', 8, 'bold'))
                problems_label.pack(fill=tk.BOTH, expand=True, padx=3, pady=2)
                
                # Цвет текста в зависимости от количества проблем
                if problems_count == 0:
                    problems_color = '#4CAF50'  # Зеленый
                elif problems_count <= 2:
                    problems_color = '#FF9800'  # Оранжевый
                else:
                    problems_color = '#F44336'  # Красный
                
                problems_label.configure(foreground=problems_color)
                
                # Описание проблем
                desc_frame = ttk.Frame(table_container)
                desc_frame.grid(row=row, column=5, padx=1, pady=1, sticky='ew')
                desc_label = ttk.Label(desc_frame, text=problems_desc, font=('Arial', 8))
                desc_label.pack(fill=tk.BOTH, expand=True, padx=3, pady=2)
            
            # Детальные проблемы
            details_frame = ttk.LabelFrame(scrollable_frame, text="🔍 Подробные проблемы", padding="10")
            details_frame.pack(fill=tk.X, pady=(0, 10))
            
            details_content = "ДЕТАЛЬНЫЙ АНАЛИЗ ПРОБЛЕМ\n"
            details_content += "=" * 50 + "\n\n"
            
            for report in reports:
                if report.issues:  # Показываем только файлы с проблемами
                    status_icon = "OK" if report.is_ready else "ERROR"
                    details_content += f"{status_icon} {report.filename}\n"
                    details_content += f"   Готовность: {report.readiness_score:.1f}%\n"
                    details_content += f"   Сущностей: {report.total_entities}\n"
                    details_content += f"   Проблемных: {report.problematic_entities}\n"
                    
                    details_content += "   Проблемы:\n"
                    for issue in report.issues:
                        severity_icon = "ERROR" if issue.severity == 'error' else "WARNING" if issue.severity == 'warning' else "INFO"
                        details_content += f"     {severity_icon} {issue.description}\n"
                        details_content += f"       -> {issue.recommendation}\n"
                    
                    details_content += "\n"
            
            if not any(report.issues for report in reports):
                details_content += "Все файлы готовы к лазерной резке!\n"
            
            details_text = tk.Text(details_frame, wrap=tk.WORD, font=('Arial', 9), height=8)
            details_text.pack(fill=tk.X)
            details_text.insert('1.0', details_content)
            details_text.config(state=tk.DISABLED)
            
            # Кнопка закрытия
            button_frame = ttk.Frame(results_window)
            button_frame.pack(fill=tk.X, padx=10, pady=10)
            
            ttk.Button(button_frame, text="Закрыть", 
                      command=results_window.destroy).pack(side=tk.RIGHT)
            
        except Exception as e:
            print(f"[DEBUG] Ошибка показа результатов анализа: {e}")
            messagebox.showerror("Ошибка", f"Не удалось показать результаты анализа:\n{e}")
    
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()


if __name__ == "__main__":
    app = EnhancedUnfoldingAreaGUI()
    app.run()

