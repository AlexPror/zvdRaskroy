#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
import ezdxf
import openpyxl
from openpyxl.styles import Font, Alignment
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors
import rectpack
from datetime import datetime
import re
import threading
import subprocess
import platform

# Добавляем путь к модулям
sys.path.append(os.path.join(os.path.dirname(__file__), 'components'))

class EnhancedWorkingGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Раскрой Деталей v2.0 - Улучшенная версия")
        self.root.geometry("1400x900")
        
        # Переменные
        self.project_name = tk.StringVar()
        self.folder_path = tk.StringVar()
        self.files_data = []
        self.optimization_result = None
        
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
        ttk.Button(button_frame, text="Оптимизировать раскрой", command=self.optimize_nesting).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(button_frame, text="Создать отчеты", command=self.create_reports).grid(row=0, column=2, padx=(0, 10))
        ttk.Button(button_frame, text="Проверить DXF", command=self.check_dxf_files).grid(row=0, column=3, padx=(0, 10))
        ttk.Button(button_frame, text="Открыть папку отчетов", command=self.open_reports_folder).grid(row=0, column=4)
        
        # Таблица файлов с возможностью редактирования
        ttk.Label(main_frame, text="Загруженные файлы (двойной клик для редактирования):").grid(row=3, column=0, sticky=tk.W, pady=(20, 5))
        
        # Создаем фрейм для таблицы и кнопок
        table_frame = ttk.Frame(main_frame)
        table_frame.grid(row=4, column=0, columnspan=2, pady=(0, 20), sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Таблица
        self.tree = ttk.Treeview(table_frame, columns=('name', 'size', 'area', 'quantity', 'contours'), show='headings', height=12)
        self.tree.heading('name', text='Название файла')
        self.tree.heading('size', text='Размер (мм)')
        self.tree.heading('area', text='Площадь (м²)')
        self.tree.heading('quantity', text='Количество')
        self.tree.heading('contours', text='Контуры')
        
        # Настройка ширины колонок
        self.tree.column('name', width=300)
        self.tree.column('size', width=120)
        self.tree.column('area', width=100)
        self.tree.column('quantity', width=80)
        self.tree.column('contours', width=80)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Скроллбар для таблицы
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Кнопки для работы с таблицей
        table_buttons_frame = ttk.Frame(table_frame)
        table_buttons_frame.grid(row=0, column=2, padx=(10, 0), sticky=(tk.N, tk.S))
        
        ttk.Button(table_buttons_frame, text="Удалить выбранный", command=self.delete_selected_file).grid(row=0, column=0, pady=(0, 5), sticky=(tk.W, tk.E))
        ttk.Button(table_buttons_frame, text="Изменить количество", command=self.edit_quantity).grid(row=1, column=0, pady=(0, 5), sticky=(tk.W, tk.E))
        ttk.Button(table_buttons_frame, text="Обновить статистику", command=self.update_statistics).grid(row=2, column=0, pady=(0, 5), sticky=(tk.W, tk.E))
        
        # Привязываем события
        self.tree.bind('<Double-1>', self.on_double_click)
        self.tree.bind('<Button-1>', self.on_single_click)
        
        # Статистика
        stats_frame = ttk.LabelFrame(main_frame, text="Статистика", padding="10")
        stats_frame.grid(row=5, column=0, columnspan=2, pady=(0, 20), sticky=(tk.W, tk.E))
        
        self.stats_label = ttk.Label(stats_frame, text="Файлы не загружены")
        self.stats_label.grid(row=0, column=0, sticky=tk.W)
        
        # Настройка растягивания
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        folder_frame.columnconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        table_buttons_frame.columnconfigure(0, weight=1)
        
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
        
        self.files_data = []
        
        for file in dxf_files:
            try:
                # Парсим количество из названия файла
                quantity = 1
                qty_match = re.search(r'(\d+)шт', file)
                if qty_match:
                    quantity = int(qty_match.group(1))
                
                # Читаем DXF файл
                filepath = os.path.join(folder, file)
                doc = ezdxf.readfile(filepath)
                msp = doc.modelspace()
                
                # Вычисляем размеры
                min_x = min_y = float('inf')
                max_x = max_y = float('-inf')
                
                # Подсчитываем контуры
                contours = 0
                for entity in msp:
                    if hasattr(entity, 'dxf'):
                        if hasattr(entity.dxf, 'start') and hasattr(entity.dxf, 'end'):
                            # Линия
                            min_x = min(min_x, entity.dxf.start.x, entity.dxf.end.x)
                            max_x = max(max_x, entity.dxf.start.x, entity.dxf.end.x)
                            min_y = min(min_y, entity.dxf.start.y, entity.dxf.end.y)
                            max_y = max(max_y, entity.dxf.start.y, entity.dxf.end.y)
                            contours += 1
                        elif hasattr(entity.dxf, 'center'):
                            # Круг или дуга
                            radius = getattr(entity.dxf, 'radius', 0)
                            min_x = min(min_x, entity.dxf.center.x - radius)
                            max_x = max(max_x, entity.dxf.center.x + radius)
                            min_y = min(min_y, entity.dxf.center.y - radius)
                            max_y = max(max_y, entity.dxf.center.y + radius)
                            contours += 1
                
                if min_x != float('inf') and max_x != float('-inf'):
                    width = max_x - min_x
                    height = max_y - min_y
                    area_m2 = (width * height) / 1_000_000
                    
                    file_data = {
                        'name': file,
                        'filename': file,
                        'filepath': filepath,
                        'width': width,
                        'height': height,
                        'area_m2': area_m2,
                        'quantity': quantity,
                        'contours': contours
                    }
                    
                    self.files_data.append(file_data)
                    
                    # Добавляем в таблицу
                    self.tree.insert('', 'end', values=(
                        file,
                        f"{width:.1f}x{height:.1f}",
                        f"{area_m2:.4f}",
                        quantity,
                        contours
                    ))
                    
            except Exception as e:
                print(f"Ошибка чтения файла {file}: {e}")
                
        self.update_statistics()
        messagebox.showinfo("Информация", f"Загружено {len(self.files_data)} DXF файлов")
        
    def on_double_click(self, event):
        """Обработка двойного клика для редактирования"""
        item = self.tree.selection()[0]
        column = self.tree.identify_column(event.x)
        
        if column == '#5':  # Колонка количества
            self.edit_quantity()
        elif column == '#2':  # Колонка размера
            self.edit_size()
            
    def on_single_click(self, event):
        """Обработка одинарного клика для выбора"""
        pass
        
    def edit_quantity(self):
        """Редактирование количества"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите файл для редактирования")
            return
            
        item = selection[0]
        values = self.tree.item(item, 'values')
        current_quantity = int(values[3])
        
        # Диалог ввода нового количества
        new_quantity = tk.simpledialog.askinteger(
            "Изменить количество",
            f"Текущее количество: {current_quantity}\nВведите новое количество:",
            initialvalue=current_quantity,
            minvalue=1,
            maxvalue=1000
        )
        
        if new_quantity is not None and new_quantity != current_quantity:
            # Обновляем данные
            file_name = values[0]
            for file_data in self.files_data:
                if file_data['name'] == file_name:
                    file_data['quantity'] = new_quantity
                    break
            
            # Обновляем таблицу
            self.tree.item(item, values=(
                values[0], values[1], values[2], new_quantity, values[4]
            ))
            
            self.update_statistics()
            
    def edit_size(self):
        """Редактирование размера (для демонстрации)"""
        messagebox.showinfo("Информация", "Редактирование размеров пока не реализовано")
        
    def delete_selected_file(self):
        """Удаление выбранного файла"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите файл для удаления")
            return
            
        item = selection[0]
        values = self.tree.item(item, 'values')
        file_name = values[0]
        
        # Подтверждение удаления
        if messagebox.askyesno("Подтверждение", f"Удалить файл '{file_name}' из списка?"):
            # Удаляем из данных
            self.files_data = [f for f in self.files_data if f['name'] != file_name]
            
            # Удаляем из таблицы
            self.tree.delete(item)
            
            self.update_statistics()
            
    def update_statistics(self):
        """Обновление статистики"""
        if not self.files_data:
            self.stats_label.config(text="Файлы не загружены")
            return
            
        total_area = sum(f['area_m2'] * f['quantity'] for f in self.files_data)
        total_parts = sum(f['quantity'] for f in self.files_data)
        total_contours = sum(f['contours'] * f['quantity'] for f in self.files_data)
        
        self.stats_label.config(text=f"Файлов: {len(self.files_data)} | Площадь: {total_area:.4f} м² | Деталей: {total_parts} шт | Контуров: {total_contours} шт")
        
    def optimize_nesting(self):
        if not self.files_data:
            messagebox.showwarning("Предупреждение", "Сначала загрузите файлы")
            return
            
        # Показываем прогресс
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Оптимизация раскроя")
        progress_window.geometry("400x150")
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        ttk.Label(progress_window, text="Выполняется оптимизация раскроя...").pack(pady=20)
        progress_bar = ttk.Progressbar(progress_window, mode='indeterminate')
        progress_bar.pack(pady=10, padx=20, fill='x')
        progress_bar.start()
        
        def optimization_thread():
            try:
                # Подготавливаем данные для rectpack
                rectangles = []
                for file_data in self.files_data:
                    for _ in range(file_data['quantity']):
                        rectangles.append((
                            int(file_data['width'] + 5),  # Добавляем зазор для резки
                            int(file_data['height'] + 5),
                            file_data['name']
                        ))
                
                # Создаем упаковщик
                packer = rectpack.newPacker()
                
                # Добавляем листы 2500x1250 мм
                for i in range(10):  # Максимум 10 листов
                    packer.add_bin(2500, 1250)
                
                # Добавляем прямоугольники
                for rect in rectangles:
                    packer.add_rect(*rect)
                
                # Выполняем упаковку
                packer.pack()
                
                # Получаем результаты
                bins = packer[0]
                if bins:
                    self.optimization_result = {
                        'success': True,
                        'sheets_needed': len(bins),
                        'bins': bins,
                        'total_parts': len(rectangles),
                        'utilization': self.calculate_utilization(bins)
                    }
                else:
                    self.optimization_result = {'success': False, 'error': 'Не удалось разместить детали'}
                    
            except Exception as e:
                self.optimization_result = {'success': False, 'error': str(e)}
            
            # Закрываем окно прогресса
            progress_window.after(0, progress_window.destroy)
            
            # Показываем результат
            if self.optimization_result['success']:
                messagebox.showinfo("Результат оптимизации", 
                    f"Оптимизация завершена!\n\n"
                    f"Использовано листов: {self.optimization_result['sheets_needed']}\n"
                    f"Деталей размещено: {self.optimization_result['total_parts']}\n"
                    f"Использование материала: {self.optimization_result['utilization']:.1f}%")
            else:
                messagebox.showerror("Ошибка оптимизации", self.optimization_result['error'])
        
        # Запускаем оптимизацию в отдельном потоке
        thread = threading.Thread(target=optimization_thread)
        thread.daemon = True
        thread.start()
        
    def calculate_utilization(self, bins):
        total_sheet_area = 2500 * 1250 * len(bins)  # мм²
        used_area = 0
        for bin in bins:
            for rect in bin:
                used_area += rect[0] * rect[1]
        return (used_area / total_sheet_area) * 100
        
    def check_dxf_files(self):
        if not self.files_data:
            messagebox.showwarning("Предупреждение", "Сначала загрузите файлы")
            return
            
        # Анализ DXF файлов
        ready_files = 0
        problem_files = []
        
        for file_data in self.files_data:
            try:
                doc = ezdxf.readfile(file_data['filepath'])
                msp = doc.modelspace()
                
                # Проверяем на проблемы
                problems = []
                for entity in msp:
                    if entity.dxftype() == 'TEXT':
                        problems.append('Содержит текст')
                    elif entity.dxftype() == 'MTEXT':
                        problems.append('Содержит многострочный текст')
                    elif hasattr(entity.dxf, 'thickness') and entity.dxf.thickness > 0.1:
                        problems.append('Толстые линии')
                
                if not problems:
                    ready_files += 1
                else:
                    problem_files.append((file_data['name'], problems))
                    
            except Exception as e:
                problem_files.append((file_data['name'], [f'Ошибка чтения: {e}']))
        
        # Показываем результаты
        result_text = f"Проверка завершена!\n\nГотовы к резке: {ready_files}/{len(self.files_data)} файлов\n\n"
        
        if problem_files:
            result_text += "Файлы с проблемами:\n"
            for filename, problems in problem_files:
                result_text += f"• {filename}: {', '.join(problems)}\n"
        
        messagebox.showinfo("Результаты проверки DXF", result_text)
        
    def open_reports_folder(self):
        """Открыть папку с отчетами"""
        try:
            current_dir = os.getcwd()
            if platform.system() == "Windows":
                os.startfile(current_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", current_dir])
            else:  # Linux
                subprocess.run(["xdg-open", current_dir])
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть папку: {e}")
        
    def create_reports(self):
        if not self.files_data:
            messagebox.showwarning("Предупреждение", "Сначала загрузите файлы")
            return
            
        project_name = self.project_name.get() or "Проект без названия"
        
        try:
            # Создаем Excel отчет
            wb = openpyxl.Workbook()
            
            # Лист 1: Основные данные
            ws1 = wb.active
            ws1.title = "Раскрой деталей"
            
            # Заголовок
            ws1['A1'] = f"Проект: {project_name}"
            ws1['A1'].font = Font(size=14, bold=True, color="1976D2")
            ws1.merge_cells('A1:F1')
            ws1['A1'].alignment = Alignment(horizontal='center')
            
            # Дата
            ws1['A2'] = f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            ws1['A2'].font = Font(size=10)
            
            # Заголовки таблицы
            headers = ['№', 'Название файла', 'Размер (мм)', 'Площадь (м²)', 'Количество', 'Контуры']
            for col, header in enumerate(headers, 1):
                cell = ws1.cell(row=4, column=col, value=header)
                cell.font = Font(bold=True)
                cell.alignment = Alignment(horizontal='center')
            
            # Данные
            total_area = 0
            total_parts = 0
            total_contours = 0
            for i, file_data in enumerate(self.files_data, 1):
                row = i + 4
                ws1.cell(row=row, column=1, value=i)
                ws1.cell(row=row, column=2, value=file_data['name'])
                ws1.cell(row=row, column=3, value=f"{file_data['width']:.1f}x{file_data['height']:.1f}")
                ws1.cell(row=row, column=4, value=f"{file_data['area_m2']:.4f}")
                ws1.cell(row=row, column=5, value=file_data['quantity'])
                ws1.cell(row=row, column=6, value=file_data['contours'])
                
                # Форматирование числовых колонок по центру
                for col in [1, 3, 4, 5, 6]:
                    ws1.cell(row=row, column=col).alignment = Alignment(horizontal='center')
                
                total_area += file_data['area_m2'] * file_data['quantity']
                total_parts += file_data['quantity']
                total_contours += file_data['contours'] * file_data['quantity']
            
            # Итого
            total_row = len(self.files_data) + 5
            ws1.cell(row=total_row, column=2, value="ИТОГО:")
            ws1.cell(row=total_row, column=4, value=f"{total_area:.4f}")
            ws1.cell(row=total_row, column=5, value=total_parts)
            ws1.cell(row=total_row, column=6, value=total_contours)
            
            for col in range(2, 7):
                cell = ws1.cell(row=total_row, column=col)
                cell.font = Font(bold=True)
                cell.alignment = Alignment(horizontal='center')
            
            # Лист 2: Сводка по группам
            ws2 = wb.create_sheet("Сводка по группам")
            ws2['A1'] = f"Проект: {project_name}"
            ws2['A1'].font = Font(size=14, bold=True)
            
            # Группируем по базовому имени
            groups = {}
            for file_data in self.files_data:
                base_name = file_data['name'].split('#')[0].strip()
                if base_name.endswith('.dxf'):
                    base_name = base_name[:-4]
                
                if base_name not in groups:
                    groups[base_name] = {
                        'count': 0,
                        'total_area': 0,
                        'total_contours': 0
                    }
                
                groups[base_name]['count'] += file_data['quantity']
                groups[base_name]['total_area'] += file_data['area_m2'] * file_data['quantity']
                groups[base_name]['total_contours'] += file_data['contours'] * file_data['quantity']
            
            # Заголовки
            ws2['A3'] = 'Группа деталей'
            ws2['B3'] = 'Количество'
            ws2['C3'] = 'Площадь (м²)'
            ws2['D3'] = 'Контуры'
            
            for col in range(1, 5):
                cell = ws2.cell(row=3, column=col)
                cell.font = Font(bold=True)
                cell.alignment = Alignment(horizontal='center')
            
            # Данные групп
            row = 4
            for group_name, data in groups.items():
                ws2.cell(row=row, column=1, value=group_name)
                ws2.cell(row=row, column=2, value=data['count'])
                ws2.cell(row=row, column=3, value=f"{data['total_area']:.4f}")
                ws2.cell(row=row, column=4, value=data['total_contours'])
                
                # Форматирование числовых колонок по центру
                for col in [2, 3, 4]:
                    ws2.cell(row=row, column=col).alignment = Alignment(horizontal='center')
                row += 1
            
            # Настройка ширины колонок
            ws1.column_dimensions['A'].width = 5
            ws1.column_dimensions['B'].width = 50
            ws1.column_dimensions['C'].width = 15
            ws1.column_dimensions['D'].width = 15
            ws1.column_dimensions['E'].width = 12
            ws1.column_dimensions['F'].width = 10
            
            ws2.column_dimensions['A'].width = 50
            ws2.column_dimensions['B'].width = 15
            ws2.column_dimensions['C'].width = 15
            ws2.column_dimensions['D'].width = 15
            
            # Сохраняем Excel
            excel_path = f"Отчет_раскроя_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            wb.save(excel_path)
            
            # Создаем PDF отчет
            pdf_path = f"Отчет_раскроя_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            c = canvas.Canvas(pdf_path, pagesize=A4)
            width, height = A4
            
            # Заголовок
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(width/2, height - 50, "ОТЧЕТ РАСКРОЯ ДЕТАЛЕЙ")
            c.setFont("Helvetica", 12)
            c.drawCentredString(width/2, height - 80, f"Проект: {project_name}")
            c.drawCentredString(width/2, height - 100, f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
            
            # Статистика
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, height - 140, "СТАТИСТИКА:")
            c.setFont("Helvetica", 10)
            c.drawString(50, height - 160, f"Общая площадь: {total_area:.4f} м²")
            c.drawString(50, height - 180, f"Общее количество деталей: {total_parts} шт")
            c.drawString(50, height - 200, f"Общее количество контуров: {total_contours} шт")
            
            # Таблица
            y = height - 240
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, y, "№")
            c.drawString(100, y, "Название файла")
            c.drawString(300, y, "Размер (мм)")
            c.drawString(400, y, "Площадь (м²)")
            c.drawString(500, y, "Кол-во")
            c.drawString(550, y, "Контуры")
            
            y -= 20
            c.setFont("Helvetica", 9)
            for i, file_data in enumerate(self.files_data, 1):
                if y < 100:  # Новая страница
                    c.showPage()
                    y = height - 50
                
                c.drawString(50, y, str(i))
                c.drawString(100, y, file_data['name'][:25])  # Обрезаем длинные имена
                c.drawString(300, y, f"{file_data['width']:.1f}x{file_data['height']:.1f}")
                c.drawString(400, y, f"{file_data['area_m2']:.4f}")
                c.drawString(500, y, str(file_data['quantity']))
                c.drawString(550, y, str(file_data['contours']))
                y -= 15
            
            # Итого
            y -= 10
            c.setFont("Helvetica-Bold", 10)
            c.drawString(100, y, "ИТОГО:")
            c.drawString(400, y, f"{total_area:.4f} м²")
            c.drawString(500, y, f"{total_parts} шт")
            c.drawString(550, y, f"{total_contours} шт")
            
            c.save()
            
            messagebox.showinfo("Успех", 
                f"Отчеты созданы!\n\n"
                f"Excel: {excel_path}\n"
                f"PDF: {pdf_path}\n\n"
                f"Общая площадь: {total_area:.4f} м²\n"
                f"Общее количество деталей: {total_parts} шт\n"
                f"Общее количество контуров: {total_contours} шт")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка создания отчетов: {e}")
        
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    # Добавляем импорт для диалога
    import tkinter.simpledialog
    app = EnhancedWorkingGUI()
    app.run()
