#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Финальная версия GUI v2 - с обновлением всех переменных без гиперссылок
"""

import sys
import io
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import logging
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class QTextEditHandler(logging.Handler):
    """Обработчик логов для вывода в Text widget"""
    
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
    
    def emit(self, record):
        msg = self.format(record)
        
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.configure(state='disabled')
            self.text_widget.see(tk.END)
        
        self.text_widget.after(0, append)

class FinalProjectGUI:
    """Финальная версия GUI для создания проектов КОМПАС-3D"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ZVD Auto - Создание проектов КОМПАС-3D v2.6")
        
        # Получаем размер экрана
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Адаптивный размер окна (80% от экрана, но не меньше минимума)
        window_width = min(1200, int(screen_width * 0.8))
        window_height = min(850, int(screen_height * 0.85))
        
        # Центрируем окно
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.minsize(900, 650)  # Минимальный размер
        
        # Переменные (пути по умолчанию для удобства)
        self.source_path = tk.StringVar(value=r"C:\Users\Vorob\Documents\ZVD GROUP\Заказы\Прадекс Инжиниринг 300925-1451\02_КД\ZVD.LITE.90.420.2100")
        self.dest_folder = tk.StringVar(value=r"C:\Users\Vorob\Documents\ZVD GROUP\Заказы\Прадекс Инжиниринг 300925-1451\02_КД")
        self.existing_project = tk.StringVar()  # НОВОЕ: Путь к существующему проекту
        self.h_var = tk.StringVar(value="140")
        self.b1_var = tk.StringVar(value="145")
        self.l1_var = tk.StringVar(value="1400")
        
        self.created_project_path = None
        self.is_processing = False
        
        # Настройка логирования
        self.setup_logging()
        
        # Создание интерфейса
        self.create_widgets()
        
        self.log("="*70)
        self.log("GUI v2.0 запущен")
        self.log("="*70)
        self.log("Новые возможности:")
        self.log("  ✓ Обновление всех переменных (БЕЗ гиперссылок!)")
        self.log("  ✓ Каскадная пересборка (3 цикла)")
        self.log("  ✓ Автообновление чертежей")
        self.log("  ✓ Расчет площадей → PDF")
        self.log("  ✓ Параметры отверстий")
        self.log("="*70)
    
    def setup_logging(self):
        """Настройка системы логирования"""
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        
        # Удаляем старые обработчики
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Добавляем файловый обработчик
        file_handler = logging.FileHandler('gui_v2_log.txt', mode='w', encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(file_handler)
    
    def create_widgets(self):
        """Создание виджетов интерфейса"""
        
        # Создаем Canvas для скроллинга
        canvas = tk.Canvas(self.root, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        
        # Скроллируемый фрейм
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        # Центрируем контент в canvas
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="n")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Функция для центрирования при изменении размера
        def center_window(event=None):
            canvas_width = canvas.winfo_width()
            frame_width = scrollable_frame.winfo_reqwidth()
            x_position = max(0, (canvas_width - frame_width) // 2)
            canvas.coords(canvas_window, x_position, 0)
        
        canvas.bind('<Configure>', center_window)
        
        # Размещаем canvas и scrollbar
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Настраиваем веса для адаптивности
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Основной контейнер с ограниченной шириной
        main_frame = ttk.Frame(scrollable_frame, padding="10")
        main_frame.pack(anchor="center")
        main_frame.columnconfigure(0, weight=1)
        
        # === СЕКЦИЯ 1: Пути ===
        paths_frame = ttk.LabelFrame(main_frame, text="Пути к проектам", padding="10")
        paths_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        paths_frame.columnconfigure(1, weight=1)
        
        # Исходный проект
        ttk.Label(paths_frame, text="Шаблон:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(paths_frame, textvariable=self.source_path, width=60).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(paths_frame, text="...", command=self.browse_source, width=3).grid(row=0, column=2)
        
        # Папка назначения
        ttk.Label(paths_frame, text="Сохранить в:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(paths_frame, textvariable=self.dest_folder, width=60).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Button(paths_frame, text="...", command=self.browse_dest, width=3).grid(row=1, column=2, pady=5)
        
        # НОВОЕ: Работа с существующим проектом
        ttk.Separator(paths_frame, orient='horizontal').grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Label(paths_frame, text="Существующий:", font=('Arial', 9, 'bold')).grid(row=3, column=0, sticky=tk.W)
        ttk.Entry(paths_frame, textvariable=self.existing_project, width=60).grid(row=3, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(paths_frame, text="...", command=self.browse_existing, width=3).grid(row=3, column=2)
        
        ttk.Button(paths_frame, text="Открыть проект", command=self.use_existing_project, width=15).grid(row=4, column=1, sticky=tk.E, pady=5)
        
        # === СЕКЦИЯ 2: Параметры ===
        params_frame = ttk.LabelFrame(main_frame, text="Параметры конвектора", padding="10")
        params_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        params_frame.columnconfigure(1, weight=1)
        params_frame.columnconfigure(3, weight=1)
        params_frame.columnconfigure(5, weight=1)
        
        ttk.Label(params_frame, text="H (высота):").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(params_frame, textvariable=self.h_var, width=10).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        ttk.Label(params_frame, text="B1 (ширина):").grid(row=0, column=2, sticky=tk.W, padx=(10,0))
        ttk.Entry(params_frame, textvariable=self.b1_var, width=10).grid(row=0, column=3, sticky=(tk.W, tk.E), padx=5)
        
        ttk.Label(params_frame, text="L1 (длина):").grid(row=0, column=4, sticky=tk.W, padx=(10,0))
        ttk.Entry(params_frame, textvariable=self.l1_var, width=10).grid(row=0, column=5, sticky=(tk.W, tk.E), padx=5)
        
        # Рекомендации по формату
        self.format_label = ttk.Label(params_frame, text="ℹ️ Формат чертежей: --", 
                                     font=('Arial', 9), foreground='blue')
        self.format_label.grid(row=1, column=0, columnspan=6, sticky=tk.W, pady=(10,0))
        
        # Привязываем обновление рекомендаций к изменению параметров
        self.h_var.trace_add('write', lambda *args: self.update_format_recommendation())
        self.b1_var.trace_add('write', lambda *args: self.update_format_recommendation())
        self.l1_var.trace_add('write', lambda *args: self.update_format_recommendation())
        
        # === СЕКЦИЯ 2.5: Коэффициенты и номер заказа (компактно) ===
        extra_frame = ttk.LabelFrame(main_frame, text="Дополнительные параметры", padding="10")
        extra_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        extra_frame.columnconfigure(1, weight=1)
        extra_frame.columnconfigure(3, weight=1)
        
        self.a2_var = tk.StringVar(value="18.5")
        self.b2_var = tk.StringVar(value="18")
        
        # Коэффициенты
        ttk.Label(extra_frame, text="A2 (толщ.):").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(extra_frame, textvariable=self.a2_var, width=8).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(extra_frame, text="B2 (зазор):").grid(row=0, column=2, sticky=tk.W, padx=(10,0))
        ttk.Entry(extra_frame, textvariable=self.b2_var, width=8).grid(row=0, column=3, sticky=tk.W, padx=5)
        
        # Номер заказа (адаптивно растягивается)
        ttk.Label(extra_frame, text="Номер заказа:").grid(row=1, column=0, sticky=tk.W, pady=(10,0))
        self.order_number_var = tk.StringVar(value="")
        order_entry = ttk.Entry(extra_frame, textvariable=self.order_number_var)
        order_entry.grid(row=1, column=1, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=(10,0))
        
        ttk.Label(extra_frame, text="ℹ️ Примеры: А-180925-1801, ЗВД-2025-001", 
                 font=('Arial', 8), foreground='gray').grid(row=2, column=0, columnspan=4, sticky=tk.W, pady=(2,0))
        
        # === СЕКЦИЯ 3: Кнопки действий (в строку по группам) ===
        actions_frame = ttk.LabelFrame(main_frame, text="Действия", padding="10")
        actions_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # Настраиваем веса колонок для адаптивности
        actions_frame.columnconfigure(0, weight=1)
        actions_frame.columnconfigure(1, weight=1)
        actions_frame.columnconfigure(2, weight=1)
        
        # ГРУППА 1: Создание проекта
        group1_frame = ttk.LabelFrame(actions_frame, text="📦 Создание", padding="5")
        group1_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), padx=3, pady=3)
        
        self.btn_create = ttk.Button(group1_frame, text="🚀 Создать проект", 
                                     command=self.create_full_project)
        self.btn_create.pack(fill=tk.X, pady=2)
        
        # ГРУППА 2: Обновление
        group2_frame = ttk.LabelFrame(actions_frame, text="🔄 Обновление", padding="5")
        group2_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N), padx=3, pady=3)
        
        self.btn_update_drawings = ttk.Button(group2_frame, text="🔄 Чертежи + BMP/DXF", 
                                              command=self.update_drawings)
        self.btn_update_drawings.pack(fill=tk.X, pady=2)
        
        self.btn_update_project = ttk.Button(group2_frame, text="🔁 Параметры проекта", 
                                            command=self.update_existing_project)
        self.btn_update_project.pack(fill=tk.X, pady=2)
        
        self.btn_update_stamps = ttk.Button(group2_frame, text="📝 Обозначения", 
                                           command=self.update_drawing_stamps)
        self.btn_update_stamps.pack(fill=tk.X, pady=2)
        
        # ГРУППА 3: Расчеты
        group3_frame = ttk.LabelFrame(actions_frame, text="📊 Расчеты", padding="5")
        group3_frame.grid(row=0, column=2, sticky=(tk.W, tk.E, tk.N), padx=3, pady=3)
        
        self.btn_recalc_areas = ttk.Button(group3_frame, text="📊 Площади разверток", 
                                          command=self.recalculate_areas)
        self.btn_recalc_areas.pack(fill=tk.X, pady=2)
        
        self.btn_optimize_nesting = ttk.Button(group3_frame, text="📐 Раскрой на листы", 
                                              command=self.optimize_sheet_nesting)
        self.btn_optimize_nesting.pack(fill=tk.X, pady=2)
        
        self.btn_show_nesting = ttk.Button(group3_frame, text="👁 Показать раскрой", 
                                          command=self.show_nesting_canvas)
        self.btn_show_nesting.pack(fill=tk.X, pady=2)
        
        self.btn_edit_nesting = ttk.Button(group3_frame, text="✏️ Редактировать раскрой", 
                                          command=self.edit_nesting_interactive)
        self.btn_edit_nesting.pack(fill=tk.X, pady=2)
        
        # Кнопка СТОП отдельно (на всю ширину)
        self.btn_stop = ttk.Button(actions_frame, text="⛔ СТОП (прервать операцию)", 
                                   command=self.stop_processing,
                                   state='disabled')
        self.btn_stop.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10,5), padx=3)
        
        # === СЕКЦИЯ 4: Прогресс ===
        progress_frame = ttk.LabelFrame(main_frame, text="⏳ Прогресс", padding="10")
        progress_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # Текущий этап
        self.progress_label = ttk.Label(progress_frame, text="Ожидание...", 
                                       font=('Arial', 10))
        self.progress_label.pack(pady=(0,5))
        
        # Прогресс-бар
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=600)
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        # Общее время
        self.total_time_label = ttk.Label(progress_frame, text="⏱ Время: --:--", 
                                          font=('Arial', 11, 'bold'), foreground='blue')
        self.total_time_label.pack(pady=5)
        
        # === СЕКЦИЯ 5: Лог ===
        log_frame = ttk.LabelFrame(main_frame, text="Журнал", padding="10")
        log_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=5)
        log_frame.columnconfigure(0, weight=1)
        
        # Текстовое поле для логов (компактнее)
        self.log_text = tk.Text(log_frame, height=12, state='disabled',
                               bg='#1e1e1e', fg='#ffffff', font=('Consolas', 9), wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Скроллбар
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text['yscrollcommand'] = log_scrollbar.set
        
        # Добавляем обработчик логов
        text_handler = QTextEditHandler(self.log_text)
        text_handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(text_handler)
        
        # Статусбар
        self.status_var = tk.StringVar(value="Готов к работе")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        # Привязываем скроллинг колесиком мыши
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    def browse_source(self):
        """Выбор папки шаблона"""
        folder = filedialog.askdirectory(title="Выберите папку шаблона")
        if folder:
            self.source_path.set(folder)
    
    def browse_dest(self):
        """Выбор папки назначения"""
        folder = filedialog.askdirectory(title="Выберите папку для сохранения")
        if folder:
            self.dest_folder.set(folder)
    
    def browse_existing(self):
        """Выбор существующего проекта"""
        folder = filedialog.askdirectory(title="Выберите существующий проект")
        if folder:
            self.existing_project.set(folder)
    
    def use_existing_project(self):
        """Использовать существующий проект"""
        existing = self.existing_project.get()
        if not existing:
            messagebox.showwarning("Ошибка", "Выберите папку существующего проекта!")
            return
        
        if not Path(existing).exists():
            messagebox.showerror("Ошибка", f"Папка не существует: {existing}")
            return
        
        # Устанавливаем как текущий проект
        self.created_project_path = existing
        
        # Пытаемся извлечь параметры из имени проекта
        try:
            project_name = Path(existing).name
            # Формат: ZVD.LITE.H.B1.L1
            if "ZVD.LITE" in project_name:
                parts = project_name.split(".")
                if len(parts) >= 5:
                    self.h_var.set(parts[2])
                    self.b1_var.set(parts[3])
                    self.l1_var.set(parts[4])
        except:
            pass
        
        self.log(f"\n✓ Открыт существующий проект: {Path(existing).name}")
        self.log(f"  Путь: {existing}")
        self.log(f"  Параметры: H={self.h_var.get()}, B1={self.b1_var.get()}, L1={self.l1_var.get()}\n")
        self.log("Теперь можете использовать кнопки обновления!")
        
        messagebox.showinfo("Успех", f"Проект открыт!\n\nТеперь вы можете:\n• Обновить чертежи\n• Обновить параметры\n• Рассчитать раскрой")
    
    def log(self, message):
        """Добавить сообщение в лог"""
        self.logger.info(message)
    
    def set_status(self, message, color=None):
        """Установить статус"""
        self.status_var.set(message)
    
    def update_progress(self, step_name: str, percent: int):
        """Обновление прогресс-бара"""
        def _update():
            self.progress_label.config(text=f"{step_name}...")
            self.progress_bar['value'] = percent
        
        self.root.after(0, _update)
    
    def update_total_time(self, total_seconds: float):
        """Обновление общего времени"""
        def _update():
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)
            self.total_time_label.config(text=f"⏱ Время: {minutes:02d}:{seconds:02d}")
        
        self.root.after(0, _update)
    
    def update_format_recommendation(self):
        """Обновление рекомендации по формату чертежей"""
        try:
            h = int(self.h_var.get()) if self.h_var.get() else 0
            b1 = int(self.b1_var.get()) if self.b1_var.get() else 0
            l1 = int(self.l1_var.get()) if self.l1_var.get() else 0
            
            max_dim = max(h, b1, l1)
            
            if max_dim == 0:
                self.format_label.config(text="ℹ️ Формат чертежей: --")
                return
            
            # Определяем формат
            if max_dim < 300:
                format_name = "A4"
                scale = "1:1"
            elif max_dim < 600:
                format_name = "A3"
                scale = "1:1"
            elif max_dim < 1200:
                format_name = "A2"
                scale = "1:2"
            elif max_dim < 2000:
                format_name = "A1"
                scale = "1:2"
            else:
                format_name = "A0"
                scale = "1:5"
            
            self.format_label.config(
                text=f"ℹ️ Рекомендуемый формат: {format_name}, масштаб: {scale} (макс. габарит: {max_dim} мм)"
            )
        except:
            pass
    
    def set_buttons_enabled(self, enabled):
        """Включить/отключить кнопки"""
        state = 'normal' if enabled else 'disabled'
        self.btn_create['state'] = state
        self.btn_update_drawings['state'] = state
        self.btn_update_project['state'] = state
        self.btn_update_stamps['state'] = state
        self.btn_optimize_nesting['state'] = state
        self.btn_show_nesting['state'] = state
        self.btn_edit_nesting['state'] = state
        
        # Кнопка СТОП - наоборот (активна когда идет процесс)
        self.btn_stop['state'] = 'disabled' if enabled else 'normal'
    
    def create_full_project(self):
        """Создание проекта (полный цикл)"""
        if self.is_processing:
            return
        
        # ПРОВЕРКА: пути не должны быть пустыми!
        if not self.source_path.get():
            messagebox.showerror("Ошибка", "Выберите папку шаблона!")
            return
        
        if not self.dest_folder.get():
            messagebox.showerror("Ошибка", "Выберите папку для сохранения!")
            return
        
        self.is_processing = True
        self.set_buttons_enabled(False)
        self.set_status("Создание проекта...", "orange")
        self.progress_bar['value'] = 0
        self.progress_label.config(text="Инициализация...")
        
        thread = threading.Thread(target=self.create_project_thread, daemon=True)
        thread.start()
    
    def create_project_thread(self):
        """Поток создания проекта"""
        import time
        import threading as th
        
        # Засекаем общее время
        total_start = time.time()
        step_times = {}
        
        # Запускаем фоновый поток для обновления таймера
        stop_timer = th.Event()
        def update_timer():
            while not stop_timer.is_set():
                elapsed = time.time() - total_start
                self.update_total_time(elapsed)
                time.sleep(1)
        
        timer_thread = th.Thread(target=update_timer, daemon=True)
        timer_thread.start()
        
        try:
            from components.project_copier import ProjectCopier
            
            h = int(self.h_var.get())
            b1 = int(self.b1_var.get())
            l1 = int(self.l1_var.get())
            
            project_name = f"ZVD.LITE.{h}.{b1}.{l1}"
            dest_path = Path(self.dest_folder.get()) / project_name
            
            self.log(f"\n{'='*70}")
            self.log(f"СОЗДАНИЕ ПРОЕКТА: {project_name}")
            self.log(f"⏱ Старт: {time.strftime('%H:%M:%S')}")
            self.log(f"{'='*70}\n")
            
            # 1. Копирование
            step_start = time.time()
            self.log("ШАГ 1: Копирование файлов...")
            self.update_progress("Шаг 1/7: Копирование файлов", 10)
            
            copier = ProjectCopier()
            copy_result = copier.copy_project(
                self.source_path.get(), 
                str(dest_path.parent),
                project_name
            )
            
            step_times['copy'] = time.time() - step_start
            self.update_progress("Шаг 1/7: Копирование завершено", 15)
            
            if not copy_result['success']:
                self.log(f"❌ Ошибка копирования: {copy_result.get('error')}")
                self.root.after(0, lambda: self.on_finished(False))
                return
            
            self.log(f"✓ Проект скопирован: {copy_result.get('copied_path', dest_path)}\n")
            self.created_project_path = str(dest_path)
            
            # 2. Каскадное обновление переменных (сборка → детали)
            self.log("ШАГ 2: Каскадное обновление переменных (сборка → детали)...")
            self.update_progress("Шаг 2/7: Обновление переменных", 20)
            
            from components.cascading_variables_updater import CascadingVariablesUpdater
            
            try:
                cascading_updater = CascadingVariablesUpdater()
                self.log("Запуск каскадного обновления...")
                cascade_result = cascading_updater.update_project_variables(str(dest_path), h, b1, l1)
                
                self.log(f"Результат: {cascade_result}")
                
                if cascade_result.get('success'):
                    self.log(f"✓ Сборка: {cascade_result.get('assembly_vars_updated', 0)} переменных")
                    self.log(f"✓ Деталей: {cascade_result.get('parts_updated', 0)} шт, {cascade_result.get('total_vars_in_parts', 0)} переменных\n")
                    self.update_progress("Шаг 2/7: Переменные обновлены", 35)
                else:
                    self.log(f"⚠️ Ошибка каскадного обновления: {cascade_result.get('error', 'Неизвестная ошибка')}\n")
                    for error in cascade_result.get('errors', []):
                        self.log(f"   {error}")
            except Exception as e:
                self.log(f"❌ КРИТИЧЕСКАЯ ОШИБКА каскадного обновления: {e}\n")
                import traceback
                self.log(traceback.format_exc())
            
            # 3. Переименование файлов деталей
            self.log("ШАГ 3: Переименование файлов деталей...")
            self.update_progress("Шаг 3/7: Переименование деталей", 40)
            
            from components.designation_updater_fixed import DesignationUpdaterFixed
            des_updater = DesignationUpdaterFixed()
            
            # Получаем номер заказа из GUI
            order_number = self.order_number_var.get().strip() if self.order_number_var.get() else None
            
            des_result = des_updater.update_all_designations(str(dest_path), h, b1, l1, order_number)
            
            if des_result['success']:
                self.log(f"✓ Переименовано деталей: {des_result.get('parts_renamed', 0)}\n")
                self.update_progress("Шаг 3/7: Детали переименованы", 50)
            else:
                self.log(f"⚠️ Ошибка переименования\n")
            
            # 4. Обновление чертежей
            self.log("ШАГ 4: Автообновление всех чертежей...")
            self.update_progress("Шаг 4/7: Обновление чертежей", 55)
            
            from components.drawing_auto_updater import DrawingAutoUpdater
            drw_updater = DrawingAutoUpdater()
            drw_result = drw_updater.update_all_drawings(str(dest_path))
            
            if drw_result['success']:
                self.log(f"✓ Обновлено чертежей: {drw_result.get('drawings_updated', 0)}\n")
                self.update_progress("Шаг 4/7: Чертежи обновлены", 65)
            else:
                self.log(f"⚠️ Ошибка обновления чертежей\n")
            
            # 5. Экспорт BMP
            self.log("ШАГ 5: Экспорт чертежей в BMP...")
            self.update_progress("Шаг 5/7: Экспорт BMP", 70)
            
            bmp_folder = dest_path / "BMP"
            bmp_folder.mkdir(exist_ok=True)
            
            from components.drawing_exporter import DrawingExporter
            exporter = DrawingExporter()
            bmp_result = exporter.export_all_drawings(
                str(dest_path),
                str(bmp_folder),
                format_type='BMP'
            )
            
            if bmp_result['success']:
                self.log(f"✓ Экспортировано BMP: {bmp_result.get('exported_count', 0)}\n")
                self.update_progress("Шаг 5/7: BMP экспортированы", 80)
            
            # 6. Экспорт DXF
            self.log("ШАГ 6: Экспорт разверток в DXF...")
            self.update_progress("Шаг 6/7: Экспорт DXF", 85)
            
            dxf_folder = dest_path / "DXF"
            dxf_folder.mkdir(exist_ok=True)
            
            from components.unfolding_dxf_exporter import UnfoldingDxfExporter
            dxf_exporter = UnfoldingDxfExporter()
            dxf_result = dxf_exporter.export_all_unfoldings(str(dest_path), str(dxf_folder))
            
            if dxf_result['success']:
                self.log(f"✓ Экспортировано DXF: {dxf_result.get('exported_count', 0)}\n")
                self.update_progress("Шаг 6/8: DXF экспортированы", 80)
            
            # 7. Переименование DXF (количество + номер заказа)
            self.log("ШАГ 7: Переименование DXF (добавление количества и номера заказа)...")
            self.update_progress("Шаг 7/8: Переименование DXF", 85)
            
            from components.dxf_renamer import DxfRenamer
            
            dxf_renamer = DxfRenamer()
            order_number = self.order_number_var.get().strip() if self.order_number_var.get() else None
            
            rename_result = dxf_renamer.rename_dxf_files(str(dest_path), order_number)
            
            if rename_result['success']:
                self.log(f"✓ Переименовано DXF: {rename_result['renamed_count']}\n")
                self.update_progress("Шаг 7/8: DXF переименованы", 90)
            
            # 8. Расчет площадей разверток
            self.log("ШАГ 8: Расчет площадей разверток...")
            self.update_progress("Шаг 8/8: Расчет площадей", 92)
            
            from components.unfolding_area_calculator import UnfoldingAreaCalculator
            from components.unfolding_pdf_generator import UnfoldingPDFGenerator
            
            area_calc = UnfoldingAreaCalculator()
            area_data = area_calc.calculate_all_unfoldings(str(dest_path))
            
            if area_data['success']:
                pdf_path = dest_path / "Площади_разверток.pdf"
                pdf_gen = UnfoldingPDFGenerator()
                pdf_result = pdf_gen.generate_report(project_name, area_data, str(pdf_path), order_number)
                
                if pdf_result['success']:
                    self.log(f"✓ PDF отчет создан: {pdf_path.name}")
                    self.log(f"✓ Общая площадь: {area_data['total_area_with_quantity']:.6f} м²")
                    if order_number:
                        self.log(f"✓ Номер заказа в PDF: {order_number}\n")
            
            self.update_progress("Шаг 8/8: PDF создан", 95)
            
            # ИТОГО
            total_time = time.time() - total_start
            stop_timer.set()  # Останавливаем таймер
            
            self.update_progress("✅ ПРОЕКТ СОЗДАН!", 100)
            self.update_total_time(total_time)
            
            self.log("="*70)
            self.log("✅ ПРОЕКТ СОЗДАН УСПЕШНО!")
            self.log("="*70)
            self.log(f"Путь: {dest_path}")
            self.log(f"Параметры: H={h}, B1={b1}, L1={l1}")
            self.log(f"⏱ Время: {int(total_time//60):02d}:{int(total_time%60):02d}")
            self.log("="*70)
            
            self.root.after(0, lambda: self.on_finished(True))
        
        except Exception as e:
            stop_timer.set()  # Останавливаем таймер при ошибке
            self.log(f"\n❌ ОШИБКА: {e}")
            import traceback
            self.log(traceback.format_exc())
            self.root.after(0, lambda: self.on_finished(False))
    
    def update_existing_project(self):
        """Обновление существующего проекта с новыми параметрами"""
        if not self.created_project_path:
            messagebox.showwarning("Ошибка", "Сначала создайте проект или выберите существующий!")
            return
        
        if self.is_processing:
            return
        
        self.is_processing = True
        self.set_buttons_enabled(False)
        self.set_status("Обновление проекта...")
        
        thread = threading.Thread(target=self.update_project_thread, daemon=True)
        thread.start()
    
    def update_project_thread(self):
        """Поток обновления проекта"""
        try:
            from components.cascading_variables_updater import CascadingVariablesUpdater
            
            h = int(self.h_var.get())
            b1 = int(self.b1_var.get())
            l1 = int(self.l1_var.get())
            
            self.log(f"\n{'='*70}")
            self.log(f"ОБНОВЛЕНИЕ ПРОЕКТА С НОВЫМИ ПАРАМЕТРАМИ")
            self.log(f"{'='*70}")
            self.log(f"Путь: {self.created_project_path}")
            self.log(f"H={h}, B1={b1}, L1={l1}\n")
            
            # Обновляем переменные
            updater = CascadingVariablesUpdater()
            result = updater.update_project_variables(self.created_project_path, h, b1, l1)
            
            if result.get('success'):
                self.log(f"✓ Переменные обновлены:")
                self.log(f"  Сборка: {result.get('assembly_vars_updated')} переменных")
                self.log(f"  Детали: {result.get('parts_updated')} шт, {result.get('total_vars_in_parts')} переменных\n")
            else:
                self.log(f"❌ Ошибка обновления переменных\n")
                return
            
            # Переименование файлов
            self.log("Переименование сборки и деталей...")
            from components.designation_updater_fixed import DesignationUpdaterFixed
            des_updater = DesignationUpdaterFixed()
            
            # Получаем номер заказа
            order_number = self.order_number_var.get().strip() if self.order_number_var.get() else None
            
            des_result = des_updater.update_all_designations(self.created_project_path, h, b1, l1, order_number)
            
            if des_result.get('success'):
                self.log(f"✓ Переименовано:")
                self.log(f"  Сборка: {des_result.get('assembly_renamed', False)}")
                self.log(f"  Детали: {des_result.get('parts_renamed', 0)} шт\n")
                self.log("✓ Проект полностью обновлен!")
            else:
                self.log(f"⚠️ Ошибка переименования\n")
            
        except Exception as e:
            self.log(f"❌ Ошибка: {e}\n")
            import traceback
            self.log(traceback.format_exc())
        
        finally:
            self.root.after(0, lambda: self.on_finished(True))
    
    def update_drawings(self):
        """Обновление чертежей"""
        if not self.created_project_path:
            messagebox.showwarning("Ошибка", "Сначала создайте проект!")
            return
        
        if self.is_processing:
            return
        
        self.is_processing = True
        self.set_buttons_enabled(False)
        self.set_status("Обновление чертежей...", "orange")
        self.progress_bar['value'] = 0
        self.progress_label.config(text="Обновление чертежей...")
        
        thread = threading.Thread(target=self.update_drawings_thread, daemon=True)
        thread.start()
    
    def update_drawings_thread(self):
        """Поток обновления чертежей + экспорт BMP/DXF"""
        from pathlib import Path
        import time
        import threading as th
        
        # Запускаем таймер
        start_time = time.time()
        stop_timer = th.Event()
        
        def update_timer():
            while not stop_timer.is_set():
                elapsed = time.time() - start_time
                self.update_total_time(elapsed)
                time.sleep(1)
        
        timer_thread = th.Thread(target=update_timer, daemon=True)
        timer_thread.start()
        
        try:
            project_path = Path(self.created_project_path)
            
            self.log("\n" + "="*70)
            self.log("ПОЛНОЕ ОБНОВЛЕНИЕ ЧЕРТЕЖЕЙ И РАЗВЕРТОК")
            self.log("="*70)
            
            # 1. Обновление чертежей
            self.log("\n1. Обновление чертежей...")
            self.update_progress("Шаг 1/5: Обновление чертежей", 10)
            from components.drawing_auto_updater import DrawingAutoUpdater
            
            updater = DrawingAutoUpdater()
            result = updater.update_all_drawings(str(project_path))
            
            if result['success']:
                self.log(f"✓ Обновлено чертежей: {result['drawings_updated']}\n")
                self.update_progress("Шаг 1/5: Чертежи обновлены", 30)
            
            # 2. Экспорт BMP
            self.log("2. Экспорт чертежей в BMP...")
            self.update_progress("Шаг 2/5: Экспорт BMP", 35)
            
            bmp_folder = project_path / "BMP"
            bmp_folder.mkdir(exist_ok=True)
            
            from components.drawing_exporter import DrawingExporter
            exporter = DrawingExporter()
            bmp_result = exporter.export_all_drawings(
                str(project_path),
                str(bmp_folder),
                format_type='BMP'
            )
            
            if bmp_result['success']:
                self.log(f"✓ Экспортировано BMP: {bmp_result.get('exported_count', 0)}\n")
                self.update_progress("Шаг 2/5: BMP готовы", 55)
            
            # 3. Экспорт DXF
            self.log("3. Экспорт разверток в DXF...")
            self.update_progress("Шаг 3/5: Экспорт DXF", 60)
            
            dxf_folder = project_path / "DXF"
            dxf_folder.mkdir(exist_ok=True)
            
            from components.unfolding_dxf_exporter import UnfoldingDxfExporter
            dxf_exporter = UnfoldingDxfExporter()
            dxf_result = dxf_exporter.export_all_unfoldings(str(project_path), str(dxf_folder))
            
            if dxf_result['success']:
                self.log(f"✓ Экспортировано DXF: {dxf_result.get('exported_count', 0)}\n")
                self.update_progress("Шаг 3/5: DXF готовы", 75)
            
            # 4. Переименование DXF (добавление количества и номера заказа)
            self.log("4. Переименование DXF файлов...")
            self.update_progress("Шаг 4/5: Переименование DXF", 80)
            
            from components.dxf_renamer import DxfRenamer
            
            dxf_renamer = DxfRenamer()
            order_number = self.order_number_var.get().strip() if self.order_number_var.get() else None
            
            rename_result = dxf_renamer.rename_dxf_files(str(project_path), order_number)
            
            if rename_result['success']:
                self.log(f"✓ Переименовано DXF: {rename_result['renamed_count']}\n")
                self.update_progress("Шаг 4/5: DXF переименованы", 85)
            
            # 5. Расчет площадей → PDF
            self.log("5. Расчет площадей → PDF...")
            self.update_progress("Шаг 5/5: Расчет площадей", 90)
            
            from components.unfolding_area_calculator import UnfoldingAreaCalculator
            from components.unfolding_pdf_generator import UnfoldingPDFGenerator
            
            area_calc = UnfoldingAreaCalculator()
            area_data = area_calc.calculate_all_unfoldings(str(project_path))
            
            if area_data['success']:
                pdf_path = project_path / "Площади_разверток.pdf"
                pdf_gen = UnfoldingPDFGenerator()
                pdf_result = pdf_gen.generate_report(project_path.name, area_data, str(pdf_path), order_number)
                
                if pdf_result['success']:
                    self.log(f"✓ PDF отчет: {pdf_path.name}")
                    self.log(f"✓ Общая площадь: {area_data['total_area_with_quantity']:.6f} м²")
                    if order_number:
                        self.log(f"✓ Номер заказа в PDF: {order_number}\n")
            
            # ИТОГО
            total_time = time.time() - start_time
            stop_timer.set()
            self.update_progress("✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО!", 100)
            self.update_total_time(total_time)
            
            self.log("="*70)
            self.log("✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО")
            self.log(f"⏱ Время: {int(total_time//60):02d}:{int(total_time%60):02d}")
            self.log("="*70)
            
            self.root.after(0, lambda: self.on_finished(True))
        
        except Exception as e:
            stop_timer.set()  # Останавливаем таймер
            self.log(f"❌ Ошибка: {e}")
            import traceback
            self.log(traceback.format_exc())
            self.root.after(0, lambda: self.on_finished(False))
    
    def calculate_areas(self):
        """Расчет площадей"""
        if not self.created_project_path:
            messagebox.showwarning("Ошибка", "Сначала создайте проект!")
            return
        
        if self.is_processing:
            return
        
        self.is_processing = True
        self.set_buttons_enabled(False)
        
        thread = threading.Thread(target=self.calculate_areas_thread, daemon=True)
        thread.start()
    
    def calculate_unfolding_areas(self):
        """Расчет площадей разверток"""
        if not self.created_project_path:
            messagebox.showwarning("Ошибка", "Сначала создайте проект!")
            return
        
        if self.is_processing:
            return
        
        self.is_processing = True
        self.set_buttons_enabled(False)
        self.set_status("Расчет площадей...", "orange")
        
        thread = threading.Thread(target=self.calculate_unfolding_areas_thread, daemon=True)
        thread.start()
    
    def calculate_unfolding_areas_thread(self):
        """Поток расчета площадей разверток"""
        try:
            from components.unfolding_area_calculator import UnfoldingAreaCalculator
            from components.unfolding_pdf_generator import UnfoldingPDFGenerator
            
            self.log("\n" + "="*70)
            self.log("РАСЧЕТ ПЛОЩАДЕЙ РАЗВЕРТОК")
            self.log("="*70)
            
            # Расчет площадей
            calc = UnfoldingAreaCalculator()
            area_data = calc.calculate_all_unfoldings(self.created_project_path)
            
            if area_data['success']:
                project_name = Path(self.created_project_path).name
                pdf_path = Path(self.created_project_path) / "Площади_разверток.pdf"
                
                # Генерация PDF
                gen = UnfoldingPDFGenerator()
                pdf_result = gen.generate_report(project_name, area_data, str(pdf_path))
                
                if pdf_result['success']:
                    self.log(f"\n✓ PDF отчет: {pdf_path.name}")
                    self.log(f"✓ Общая площадь: {area_data['total_area_with_quantity']:.6f} м²")
                    self.log(f"✓ Деталей: {len(area_data['parts'])}")
                else:
                    self.log(f"⚠️ Ошибка создания PDF: {pdf_result['error']}")
            else:
                self.log(f"⚠️ Ошибка расчета: {area_data.get('error', 'Неизвестная ошибка')}")
            
            self.root.after(0, lambda: self.on_finished(True))
        
        except Exception as e:
            self.log(f"❌ Ошибка: {e}")
            import traceback
            self.log(traceback.format_exc())
            self.root.after(0, lambda: self.on_finished(False))
    
    def update_drawing_stamps(self):
        """Обновление штампов чертежей"""
        if not self.created_project_path:
            messagebox.showwarning("Ошибка", "Сначала создайте проект!")
            return
        
        if self.is_processing:
            return
        
        # Проверка параметров
        try:
            h = int(self.h_var.get())
            b1 = int(self.b1_var.get())
            l1 = int(self.l1_var.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректные значения H, B1, L1!")
            return
        
        self.is_processing = True
        self.set_buttons_enabled(False)
        self.set_status("Обновление штампов...", "orange")
        
        thread = threading.Thread(target=self.update_drawing_stamps_thread, args=(h, b1, l1), daemon=True)
        thread.start()
    
    def update_drawing_stamps_thread(self, h, b1, l1):
        """Поток обновления штампов И обозначений в деталях"""
        try:
            self.log("\n" + "="*70)
            self.log("ОБНОВЛЕНИЕ ОБОЗНАЧЕНИЙ И ШТАМПОВ")
            self.log("="*70)
            
            # 1. ОБНОВЛЯЕМ ОБОЗНАЧЕНИЯ В ДЕТАЛЯХ (.m3d файлы)
            self.log("\n1. Обновление обозначений в деталях...")
            from components.designation_updater_fixed import DesignationUpdaterFixed
            
            des_updater = DesignationUpdaterFixed()
            
            # Получаем номер заказа
            order_number = self.order_number_var.get().strip() if self.order_number_var.get() else None
            
            des_result = des_updater.update_all_designations(self.created_project_path, h, b1, l1, order_number)
            
            if des_result['success']:
                self.log(f"✓ Обновлено деталей: {des_result.get('parts_renamed', 0)}")
                self.log(f"✓ Обновлена сборка: {des_result.get('assembly_marking', 'N/A')}")
            else:
                self.log(f"⚠️ Ошибка обновления деталей")
            
            # 2. ОБНОВЛЯЕМ ШТАМПЫ ЧЕРТЕЖЕЙ (.cdw файлы)
            self.log("\n2. Обновление штампов чертежей...")
            from components.drawing_stamp_updater import DrawingStampUpdater
            
            stamp_updater = DrawingStampUpdater()
            
            # Обновляем обозначения в штампах (без номера заказа - он уже в наименовании!)
            stamp_result = stamp_updater.update_all_drawings_in_project(
                self.created_project_path,
                h, b1, l1,
                order_number=None  # НЕ обновляем номер заказа в штампе!
            )
            
            if stamp_result['success']:
                self.log(f"✓ Обновлено штампов: {stamp_result['updated_count']}")
                if order_number:
                    self.log(f"✓ Номер заказа добавлен в наименования деталей: ({order_number})")
                
                if stamp_result['errors']:
                    self.log(f"\n⚠️ Ошибки ({len(stamp_result['errors'])}):")
                    for error in stamp_result['errors']:
                        self.log(f"  • {error}")
            else:
                self.log("⚠️ Ошибка обновления штампов")
            
            self.log("\n" + "="*70)
            self.log("✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО")
            self.log("="*70)
            
            self.root.after(0, lambda: self.on_finished(True))
        
        except Exception as e:
            self.log(f"❌ Ошибка: {e}")
            import traceback
            self.log(traceback.format_exc())
            self.root.after(0, lambda: self.on_finished(False))
    
    def recalculate_areas(self):
        """Обновление расчета площадей разверток"""
        if not self.created_project_path:
            messagebox.showwarning("Ошибка", "Сначала создайте проект или откройте существующий!")
            return
        
        if self.is_processing:
            return
        
        self.is_processing = True
        self.set_buttons_enabled(False)
        self.set_status("Расчет площадей...", "orange")
        
        thread = threading.Thread(target=self.recalculate_areas_thread, daemon=True)
        thread.start()
    
    def recalculate_areas_thread(self):
        """Поток пересчета площадей"""
        from pathlib import Path
        
        try:
            self.log("\n" + "="*70)
            self.log("ОБНОВЛЕНИЕ РАСЧЕТА ПЛОЩАДЕЙ РАЗВЕРТОК")
            self.log("="*70)
            
            # НОВАЯ ВЕРСИЯ: Улучшенный калькулятор с оптимизацией раскроя и учетом обрезков
            from components.enhanced_area_calculator_with_waste import EnhancedAreaCalculatorWithWaste
            from components.advanced_pdf_generator import AdvancedPDFGenerator
            
            # Получаем номер заказа из GUI
            order_number = self.order_number_var.get().strip() if self.order_number_var.get() else None
            
            self.log("\n🔄 Запуск оптимизации раскроя...")
            
            calculator = EnhancedAreaCalculatorWithWaste(use_array_manager=False)
            result = calculator.calculate_with_nesting(self.created_project_path, order_number=order_number)
            
            # Извлекаем данные площадей
            area_data = result.get('areas', {})
            
            if not area_data['success']:
                self.log("❌ Не удалось рассчитать площади")
                for error in area_data.get('errors', []):
                    self.log(f"  - {error}")
                self.root.after(0, lambda: self.on_finished(False))
                return
            
            # Генерация PDF
            project_name = Path(self.created_project_path).name
            order_number = self.order_number_var.get().strip() if self.order_number_var.get() else None
            
            # Формируем имя файла
            if order_number:
                pdf_filename = f"Расчет_площадей_{order_number}.pdf"
            else:
                pdf_filename = "Расчет_площадей.pdf"
            
            pdf_path = Path(self.created_project_path) / pdf_filename
            
            generator = AdvancedPDFGenerator()
            pdf_result = generator.generate_detailed_report(
                project_name=project_name,
                area_data=area_data,
                output_path=str(pdf_path)
            )
            
            if pdf_result['success']:
                self.log(f"\n✓ PDF создан: {pdf_path.name}")
                self.log(f"✓ Уникальных деталей: {len(area_data['unfoldings'])}")
                self.log(f"✓ Общая площадь: {area_data['total_area_with_quantity']:.4f} м²")
                self.log("\nДетализация:")
                for unf in area_data['unfoldings']:
                    self.log(f"  • {unf['name']}: {unf['quantity']} шт × {unf['area_m2']:.4f} м² = {unf['total_area_m2']:.4f} м²")
            else:
                self.log(f"❌ Ошибка создания PDF: {pdf_result.get('error', 'Неизвестная ошибка')}")
            
            # НОВОЕ: Обработка результатов оптимизации раскроя
            nesting = result.get('nesting', {})
            if nesting.get('success'):
                self.log("\n" + "="*70)
                self.log("ОПТИМИЗАЦИЯ РАСКРОЯ")
                self.log("="*70)
                self.log(f"\n✓ Листов требуется: {nesting['sheets_needed']}")
                self.log(f"✓ Использование материала: {nesting['utilization_percent']:.1f}%")
                self.log(f"✓ Обрезки: {nesting['overall_waste_percent']:.1f}%")
                
                # Обрезки с номерами
                waste_pieces = result.get('waste_pieces', [])
                if waste_pieces:
                    self.log(f"\n✓ Обрезков найдено: {len(waste_pieces)}")
                    usable = [w for w in waste_pieces if w['usable']]
                    if usable:
                        self.log(f"  • Можно использовать: {len(usable)} шт")
                        self.log(f"  • Площадь пригодных: {sum(w['area_m2'] for w in usable):.4f} м²")
                
                # Визуализация
                vis_pdf = result.get('visualization_pdf')
                if vis_pdf:
                    self.log(f"\n✓ Раскладка создана: {vis_pdf}")
                    self.log("  • Схема размещения деталей на листах")
                    self.log("  • Таблица обрезков с номерами для маркировки")
                
                # База обрезков
                waste_excel = result.get('waste_excel')
                if waste_excel:
                    self.log(f"\n✓ База обрезков обновлена: {waste_excel}")
                    self.log("  • Используйте для поиска подходящих обрезков")
                    self.log("  • Помечайте использованные обрезки в Excel")
                
                self.log("\n💡 Инструкция по работе с обрезками:")
                self.log("  1. Распечатайте PDF с раскладкой")
                self.log("  2. После резки маркером пометьте обрезки (номер W-XXX)")
                self.log("  3. Сложите обрезки в специальную зону")
                self.log("  4. Перед новым проектом ищите обрезки в Excel")
            else:
                self.log("\n⚠ Оптимизация раскроя недоступна (установите: pip install rectpack)")
            
            self.root.after(0, lambda: self.on_finished(True))
        
        except Exception as e:
            self.log(f"❌ Ошибка: {e}")
            import traceback
            self.log(traceback.format_exc())
            self.root.after(0, lambda: self.on_finished(False))
    
    def optimize_sheet_nesting(self):
        """Оптимизация раскроя на листы"""
        if not self.created_project_path:
            messagebox.showwarning("Ошибка", "Сначала создайте проект!")
            return
        
        if self.is_processing:
            return
        
        self.is_processing = True
        self.set_buttons_enabled(False)
        self.set_status("Расчет раскроя...", "orange")
        
        thread = threading.Thread(target=self.optimize_sheet_nesting_thread, daemon=True)
        thread.start()
    
    def optimize_sheet_nesting_thread(self):
        """Поток оптимизации раскроя"""
        from pathlib import Path
        
        try:
            self.log("\n" + "="*70)
            self.log("ОПТИМИЗАЦИЯ РАСКРОЯ НА ЛИСТЫ 2500×1250")
            self.log("="*70)
            
            # 1. Расчет площадей
            from components.unfolding_area_calculator import UnfoldingAreaCalculator
            
            calc = UnfoldingAreaCalculator()
            area_data = calc.calculate_all_unfoldings(self.created_project_path)
            
            if not area_data['success']:
                self.log("❌ Не удалось рассчитать площади")
                self.root.after(0, lambda: self.on_finished(False))
                return
            
            # 2. Оптимизация раскладки
            from components.sheet_nesting_optimizer import SheetNestingOptimizer
            
            optimizer = SheetNestingOptimizer()
            nesting_data = optimizer.optimize_layout(area_data)
            
            if nesting_data['success']:
                self.log(f"\n✓ Листов требуется: {nesting_data['sheets_needed']}")
                self.log(f"✓ Использование: {nesting_data['utilization_percent']:.1f}%")
                self.log(f"✓ Обрезков пригодных: {len(nesting_data['reusable_scraps'])}")
                
                # 3. Генерация PDF с раскроем
                project_name = Path(self.created_project_path).name
                order_number = self.order_number_var.get().strip() if self.order_number_var.get() else None
                
                pdf_path = Path(self.created_project_path) / "Раскрой_на_листы.pdf"
                
                pdf_result = optimizer.generate_nesting_pdf(
                    project_name,
                    area_data,
                    nesting_data,
                    str(pdf_path),
                    order_number
                )
                
                if pdf_result['success']:
                    self.log(f"\n✓ PDF раскроя создан: {pdf_path.name}")
                    self.log(f"✓ Откройте файл для просмотра раскладки!")
            else:
                self.log("❌ Ошибка оптимизации раскроя")
            
            self.root.after(0, lambda: self.on_finished(True))
        
        except Exception as e:
            self.log(f"❌ Ошибка: {e}")
            import traceback
            self.log(traceback.format_exc())
            self.root.after(0, lambda: self.on_finished(False))
    
    def show_nesting_canvas(self):
        """Показать раскрой в интерактивном окне Canvas"""
        if not self.created_project_path:
            messagebox.showwarning("Ошибка", "Сначала создайте проект или откройте существующий!")
            return
        
        try:
            # Импортируем Canvas визуализатор
            from components.nesting_canvas_viewer import NestingCanvasViewer
            
            # Получаем данные раскроя
            from components.enhanced_area_calculator_with_waste import EnhancedAreaCalculatorWithWaste
            
            self.log("\n🔄 Загрузка данных раскроя...")
            
            calculator = EnhancedAreaCalculatorWithWaste(use_array_manager=False)
            order_number = self.order_number_var.get().strip() if self.order_number_var.get() else None
            result = calculator.calculate_with_nesting(self.created_project_path, order_number=order_number)
            
            nesting_result = result.get('nesting', {})
            if not nesting_result.get('success'):
                messagebox.showerror("Ошибка", "Не удалось загрузить данные раскроя!\n\nВозможные причины:\n• Не установлена библиотека rectpack\n• Ошибка в расчете площадей")
                return
            
            # Показываем Canvas окно
            project_name = Path(self.created_project_path).name
            viewer = NestingCanvasViewer(self.root)
            viewer.show_nesting(nesting_result, project_name)
            
            self.log(f"✓ Окно раскроя открыто: {project_name}")
            self.log(f"✓ Листов: {nesting_result['sheets_needed']}")
            self.log(f"✓ Использование: {nesting_result['utilization_percent']:.1f}%")
            self.log(f"✓ Обрезки: {nesting_result['overall_waste_percent']:.1f}%")
            
        except ImportError as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить модуль визуализации:\n{e}\n\nУстановите: pip install rectpack")
        except Exception as e:
            self.log(f"❌ Ошибка показа раскроя: {e}")
            messagebox.showerror("Ошибка", f"Не удалось показать раскрой:\n{e}")
    
    def edit_nesting_interactive(self):
        """Открыть интерактивный редактор раскроя"""
        if not self.created_project_path:
            messagebox.showwarning("Ошибка", "Сначала создайте проект или откройте существующий!")
            return
        
        try:
            # Импортируем интерактивный редактор
            from components.interactive_nesting_editor import InteractiveNestingEditor
            
            # Получаем данные деталей
            from components.enhanced_area_calculator_with_waste import EnhancedAreaCalculatorWithWaste
            
            self.log("\n🔄 Загрузка данных для редактирования...")
            
            calculator = EnhancedAreaCalculatorWithWaste(use_array_manager=False)
            order_number = self.order_number_var.get().strip() if self.order_number_var.get() else None
            result = calculator.calculate_with_nesting(self.created_project_path, order_number=order_number)
            
            # Извлекаем данные деталей
            area_data = result.get('areas', {})
            if not area_data.get('success'):
                messagebox.showerror("Ошибка", "Не удалось загрузить данные деталей!")
                return
            
            # Подготавливаем данные для редактора
            parts_data = []
            for unfolding in area_data.get('unfoldings', []):
                parts_data.append({
                    'name': unfolding['name'],
                    'width_mm': unfolding['width_mm'],
                    'height_mm': unfolding['height_mm'],
                    'area_m2': unfolding['area_m2'],
                    'quantity': unfolding['quantity']
                })
            
            if not parts_data:
                messagebox.showwarning("Предупреждение", "Нет деталей для редактирования!")
                return
            
            # Показываем редактор
            project_name = Path(self.created_project_path).name
            editor = InteractiveNestingEditor(self.root)
            editor.show_editor(parts_data, project_name)
            
            self.log(f"✓ Интерактивный редактор открыт: {project_name}")
            self.log(f"✓ Деталей для размещения: {len(parts_data)}")
            self.log("\n💡 Инструкция:")
            self.log("  1. Перетащите детали из списка на лист")
            self.log("  2. Перетаскивайте размещенные детали для оптимизации")
            self.log("  3. Используйте 'Авторазмещение' для быстрого старта")
            self.log("  4. Нажмите 'Сохранить раскрой' когда закончите")
            
        except ImportError as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить редактор:\n{e}")
        except Exception as e:
            self.log(f"❌ Ошибка открытия редактора: {e}")
            messagebox.showerror("Ошибка", f"Не удалось открыть редактор:\n{e}")
    
    def stop_processing(self):
        """Экстренная остановка процесса"""
        if not self.is_processing:
            return
        
        # Убиваем КОМПАС (чтобы освободить файлы)
        import subprocess
        try:
            subprocess.run(['taskkill', '/F', '/IM', 'KOMPAS.exe'], 
                          capture_output=True, timeout=5)
            self.log("\n⛔ ПРОЦЕСС ПРЕРВАН ПОЛЬЗОВАТЕЛЕМ!")
            self.log("КОМПАС-3D принудительно закрыт")
        except:
            pass
        
        # Сбрасываем состояние
        self.is_processing = False
        self.set_buttons_enabled(True)
        self.set_status("⛔ Остановлено", "red")
        self.progress_bar['value'] = 0
        self.progress_label.config(text="Прервано пользователем")
        
        messagebox.showinfo("Остановлено", 
                           "Процесс прерван!\n\nКОМПАС-3D закрыт.\nМожете начать заново.")
    
    def on_finished(self, success):
        """Обработчик завершения операции"""
        self.is_processing = False
        self.set_buttons_enabled(True)
        
        if success:
            self.set_status("✅ Операция завершена", "green")
        else:
            self.set_status("❌ Ошибка", "red")
    
    def run(self):
        """Запуск GUI"""
        self.root.mainloop()

if __name__ == "__main__":
    print("="*70)
    print("Запуск GUI v2.0...")
    print("="*70)
    
    app = FinalProjectGUI()
    app.run()

