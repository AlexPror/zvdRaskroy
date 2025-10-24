#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import os
import sys
import ezdxf
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import rectpack
from datetime import datetime
import re
import threading
import subprocess
import platform
import math

class CorrectPDFStructureGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Раскрой Деталей v2.0 - ПРАВИЛЬНАЯ СТРУКТУРА PDF")
        self.root.geometry("1400x900")
        
        # Регистрируем русский шрифт для PDF
        self.register_russian_fonts()
        
        # Переменные
        self.project_name = tk.StringVar()
        self.folder_path = tk.StringVar()
        self.files_data = []
        self.optimization_result = None
        self.editing_item = None  # Для редактирования в таблице
        
        self.create_widgets()
        
    def register_russian_fonts(self):
        """Регистрируем русские шрифты для PDF"""
        try:
            # Пытаемся найти системные шрифты
            font_paths = [
                ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),  # Arial + Arial Bold
                ("C:/Windows/Fonts/calibri.ttf", "C:/Windows/Fonts/calibrib.ttf"),  # Calibri + Calibri Bold
                ("C:/Windows/Fonts/tahoma.ttf", "C:/Windows/Fonts/tahomabd.ttf"),  # Tahoma + Tahoma Bold
                ("/System/Library/Fonts/Arial.ttf", "/System/Library/Fonts/Arial Bold.ttf"),  # macOS
                ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),  # Linux
            ]
            
            for regular_path, bold_path in font_paths:
                if os.path.exists(regular_path):
                    try:
                        # Регистрируем обычный шрифт
                        pdfmetrics.registerFont(TTFont('RussianFont', regular_path))
                        print(f"Зарегистрирован обычный шрифт: {regular_path}")
                        
                        # Регистрируем жирный шрифт если есть
                        if os.path.exists(bold_path):
                            pdfmetrics.registerFont(TTFont('RussianFont-Bold', bold_path))
                            print(f"Зарегистрирован жирный шрифт: {bold_path}")
                        else:
                            # Если нет отдельного жирного шрифта, используем обычный
                            pdfmetrics.registerFont(TTFont('RussianFont-Bold', regular_path))
                            print(f"Используем обычный шрифт как жирный: {regular_path}")
                        
                        break
                    except Exception as e:
                        print(f"Ошибка регистрации шрифта {regular_path}: {e}")
                        continue
        except Exception as e:
            print(f"Не удалось зарегистрировать русский шрифт: {e}")
            # Используем встроенные шрифты как fallback
            try:
                pdfmetrics.registerFont(TTFont('RussianFont', 'Helvetica'))
                pdfmetrics.registerFont(TTFont('RussianFont-Bold', 'Helvetica-Bold'))
            except:
                pass
        
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
        ttk.Button(button_frame, text="🚀 ОПТИМИЗИРОВАТЬ РАСКРОЙ", command=self.optimize_nesting).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(button_frame, text="📊 Создать PDF отчет", command=self.create_pdf_report).grid(row=0, column=2, padx=(0, 10))
        ttk.Button(button_frame, text="📋 Создать Excel отчет", command=self.create_excel_report).grid(row=0, column=3, padx=(0, 10))
        ttk.Button(button_frame, text="Открыть папку отчетов", command=self.open_reports_folder).grid(row=0, column=4)
        
        # Таблица файлов
        ttk.Label(main_frame, text="Загруженные файлы:").grid(row=3, column=0, sticky=tk.W, pady=(20, 5))
        
        table_frame = ttk.Frame(main_frame)
        table_frame.grid(row=4, column=0, columnspan=2, pady=(0, 20), sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Таблица
        self.tree = ttk.Treeview(table_frame, columns=('name', 'size', 'area', 'quantity', 'contours'), show='headings', height=12)
        self.tree.heading('name', text='Название файла')
        self.tree.heading('size', text='Размер (мм)')
        self.tree.heading('area', text='Площадь (м²)')
        self.tree.heading('quantity', text='Количество')
        self.tree.heading('contours', text='Контуры')
        
        self.tree.column('name', width=300)
        self.tree.column('size', width=120)
        self.tree.column('area', width=100)
        self.tree.column('quantity', width=80)
        self.tree.column('contours', width=80)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Скроллбар
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Кнопки для работы с таблицей
        table_buttons_frame = ttk.Frame(table_frame)
        table_buttons_frame.grid(row=0, column=2, padx=(10, 0), sticky=(tk.N, tk.S))
        
        ttk.Button(table_buttons_frame, text="Удалить выбранный", command=self.delete_selected_file).grid(row=0, column=0, pady=(0, 5), sticky=(tk.W, tk.E))
        ttk.Button(table_buttons_frame, text="Изменить количество", command=self.edit_quantity).grid(row=1, column=0, pady=(0, 5), sticky=(tk.W, tk.E))
        ttk.Button(table_buttons_frame, text="Обновить статистику", command=self.update_statistics).grid(row=2, column=0, pady=(0, 5), sticky=(tk.W, tk.E))
        ttk.Button(table_buttons_frame, text="🗑️ Очистить таблицу", command=self.clear_table).grid(row=3, column=0, pady=(0, 5), sticky=(tk.W, tk.E))
        
        # Привязываем события
        self.tree.bind('<Double-1>', self.on_double_click)
        self.tree.bind('<Button-1>', self.on_single_click)
        self.tree.bind('<KeyPress>', self.on_key_press)
        
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
                # Ищем паттерны: "2шт", "3шт", "1шт" в названии файла
                qty_match = re.search(r'(\d+)шт', file)
                if qty_match:
                    quantity = int(qty_match.group(1))
                    print(f"Найдено количество {quantity} в файле: {file}")
                else:
                    print(f"Количество не найдено в файле: {file}, используем 1")
                
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
                    
                    print(f"Добавлен файл: {file}, количество: {quantity}, площадь: {area_m2:.4f}")
                    
            except Exception as e:
                print(f"Ошибка чтения файла {file}: {e}")
                
        self.update_statistics()
        messagebox.showinfo("Информация", f"Загружено {len(self.files_data)} DXF файлов")
        
    def on_single_click(self, event):
        """Обработка одинарного клика для выбора колонки"""
        item = self.tree.selection()
        if item:
            column = self.tree.identify_column(event.x)
            if column == '#5':  # Колонка количества
                self.start_edit_quantity(item[0])
    
    def on_double_click(self, event):
        """Обработка двойного клика для редактирования"""
        item = self.tree.selection()[0]
        column = self.tree.identify_column(event.x)
        
        if column == '#5':  # Колонка количества
            self.start_edit_quantity(item)
    
    def on_key_press(self, event):
        """Обработка нажатия клавиш"""
        if self.editing_item:
            if event.keysym == 'Return':
                self.finish_edit_quantity()
            elif event.keysym == 'Escape':
                self.cancel_edit_quantity()
    
    def start_edit_quantity(self, item):
        """Начать редактирование количества"""
        self.editing_item = item
        values = self.tree.item(item, 'values')
        current_quantity = int(values[3])
        
        # Создаем Entry для редактирования
        bbox = self.tree.bbox(item, '#5')
        if bbox:
            x, y, width, height = bbox
            self.edit_entry = tk.Entry(self.tree, width=8)
            self.edit_entry.place(x=x, y=y, width=width, height=height)
            self.edit_entry.insert(0, str(current_quantity))
            self.edit_entry.select_range(0, tk.END)
            self.edit_entry.focus()
            
            # Привязываем события
            self.edit_entry.bind('<Return>', lambda e: self.finish_edit_quantity())
            self.edit_entry.bind('<Escape>', lambda e: self.cancel_edit_quantity())
            self.edit_entry.bind('<FocusOut>', lambda e: self.finish_edit_quantity())
    
    def finish_edit_quantity(self):
        """Завершить редактирование количества"""
        if not self.editing_item:
            return
            
        try:
            new_quantity = int(self.edit_entry.get())
            if new_quantity < 1:
                raise ValueError("Количество должно быть больше 0")
                
            # Обновляем данные
            values = self.tree.item(self.editing_item, 'values')
            file_name = values[0]
            
            for file_data in self.files_data:
                if file_data['name'] == file_name:
                    file_data['quantity'] = new_quantity
                    break
            
            # Обновляем таблицу
            self.tree.item(self.editing_item, values=(
                values[0], values[1], values[2], new_quantity, values[4]
            ))
            
            self.update_statistics()
            
        except ValueError as e:
            messagebox.showerror("Ошибка", f"Некорректное количество: {e}")
        
        self.cancel_edit_quantity()
    
    def cancel_edit_quantity(self):
        """Отменить редактирование"""
        if hasattr(self, 'edit_entry'):
            self.edit_entry.destroy()
        self.editing_item = None
            
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
    
    def clear_table(self):
        """Очистить всю таблицу"""
        if not self.files_data:
            messagebox.showinfo("Информация", "Таблица уже пуста")
            return
            
        # Подтверждение очистки
        result = messagebox.askyesno("Подтверждение", 
                                   "Вы уверены, что хотите очистить всю таблицу?\nВсе загруженные файлы будут удалены.")
        
        if result:
            # Очищаем данные
            self.files_data.clear()
            self.optimization_result = None
            
            # Очищаем таблицу
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Обновляем статистику
            self.update_statistics()
            
            # Очищаем поле названия проекта
            self.project_name.set("")
            
            messagebox.showinfo("Успех", "Таблица очищена")
        
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
                # ИСПРАВЛЯЕМ ТИПЫ ДАННЫХ ДЛЯ RECTPACK
                rectangles = []
                for file_data in self.files_data:
                    for _ in range(file_data['quantity']):
                        # ИСПРАВЛЯЕМ: используем int для rectpack и правильный формат
                        width_int = int(round(file_data['width'] + 5))  # Добавляем зазор для резки
                        height_int = int(round(file_data['height'] + 5))
                        
                        # Rectpack ожидает (width, height, rid) где rid - идентификатор
                        rectangles.append((width_int, height_int, file_data['name']))
                
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
                
                # Получаем результаты - ИСПРАВЛЯЕМ НЕИТЕРАБЕЛЬНЫЙ ОБЪЕКТ
                bins = []
                for bin in packer:
                    bins.append(bin)
                
                if bins:
                    # Создаем структуру результата как в оригинале
                    sheets = []
                    for bin_idx, bin_data in enumerate(bins):
                        sheet = {
                            'sheet_number': bin_idx + 1,
                            'width': 2500,
                            'height': 1250,
                            'parts': []
                        }
                        
                        # ИСПРАВЛЯЕМ: rectpack возвращает объекты Rectangle
                        for rect in bin_data:
                            # Получаем атрибуты объекта Rectangle
                            x = rect.x
                            y = rect.y
                            w = rect.width
                            h = rect.height
                            rid = rect.rid  # Идентификатор
                            
                            # Преобразуем rid в строку для имени
                            name = str(rid) if rid else f"Деталь_{w}x{h}"
                            
                            part = {
                                'name': name,
                                'x': x,
                                'y': y,
                                'width': w,
                                'height': h,
                                'real_width': w - 5,  # Убираем зазор
                                'real_height': h - 5
                            }
                            sheet['parts'].append(part)
                        
                        sheets.append(sheet)
                    
                    # РАСЧЕТ ДОПОЛНИТЕЛЬНЫХ ПАРАМЕТРОВ КАК В ОРИГИНАЛЕ
                    total_parts = len(rectangles)
                    total_area_all = sum(f['area_m2'] * f['quantity'] for f in self.files_data)
                    total_sheets_area = len(bins) * 3.125  # 2500x1250 мм = 3.125 м²
                    utilization_percent = (total_area_all / total_sheets_area) * 100 if total_sheets_area > 0 else 0
                    waste_area = total_sheets_area - total_area_all
                    overall_waste_percent = (waste_area / total_sheets_area) * 100 if total_sheets_area > 0 else 0
                    
                    # Расчет длины реза и времени
                    total_cut_length_mm = self.calculate_cut_length()
                    total_contours = sum(f['contours'] * f['quantity'] for f in self.files_data)
                    cutting_time_minutes = total_cut_length_mm / 1000 * 0.5  # Примерно 0.5 мин на метр
                    
                    self.optimization_result = {
                        'success': True,
                        'sheets_needed': len(bins),
                        'sheets': sheets,
                        'total_parts': total_parts,
                        'utilization_percent': utilization_percent,
                        'overall_waste_percent': overall_waste_percent,
                        'total_cut_length_mm': total_cut_length_mm,
                        'total_contours': total_contours,
                        'cutting_time_minutes': cutting_time_minutes
                    }
                else:
                    self.optimization_result = {'success': False, 'error': 'Не удалось разместить детали'}
                    
            except Exception as e:
                self.optimization_result = {'success': False, 'error': str(e)}
                print(f"Ошибка оптимизации: {e}")
                import traceback
                traceback.print_exc()
            
            # Закрываем окно прогресса
            progress_window.after(0, progress_window.destroy)
            
            # Показываем результат
            if self.optimization_result['success']:
                messagebox.showinfo("Оптимизация завершена!", 
                    f"✅ Раскрой оптимизирован!\n\n"
                    f"📊 Использовано листов: {self.optimization_result['sheets_needed']}\n"
                    f"🔢 Деталей размещено: {self.optimization_result['total_parts']}\n"
                    f"📈 Использование материала: {self.optimization_result['utilization_percent']:.1f}%\n"
                    f"✂️ Длина реза: {self.optimization_result['total_cut_length_mm']/1000:.1f} м\n"
                    f"⏱️ Время резки: {self.optimization_result['cutting_time_minutes']:.1f} мин\n\n"
                    f"Теперь можно создать PDF и Excel отчеты!")
            else:
                messagebox.showerror("Ошибка оптимизации", self.optimization_result['error'])
        
        # Запускаем оптимизацию в отдельном потоке
        thread = threading.Thread(target=optimization_thread)
        thread.daemon = True
        thread.start()
        
    def calculate_cut_length(self):
        """Расчет общей длины реза"""
        total_length = 0
        for file_data in self.files_data:
            # Примерный расчет: периметр детали * количество
            perimeter = 2 * (file_data['width'] + file_data['height'])
            total_length += perimeter * file_data['quantity']
        return total_length
    
    def create_pdf_report(self):
        """Создать PDF отчет с визуализацией раскроя"""
        if not self.files_data:
            messagebox.showwarning("Предупреждение", "Сначала загрузите файлы")
            return
            
        # Если нет результата оптимизации, выполняем её автоматически
        if not self.optimization_result or not self.optimization_result['success']:
            messagebox.showinfo("Информация", "Выполняется оптимизация раскроя...")
            self.optimize_nesting()
            # Ждем завершения оптимизации
            import time
            time.sleep(2)
            
            if not self.optimization_result or not self.optimization_result['success']:
                messagebox.showerror("Ошибка", "Не удалось выполнить оптимизацию")
                return
            
        project_name = self.project_name.get() or "Проект без названия"
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_path = f"Раскрой_{project_name}_{timestamp}.pdf"
        
        # Удаляем старый файл если существует
        import os
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        
        try:
            # Создаем PDF с визуализацией
            self._create_pdf_with_visualization(pdf_path, self.optimization_result)
            
            messagebox.showinfo("Успех", f"PDF отчет создан!\n\nФайл: {pdf_path}\n\nОткройте папку отчетов для просмотра.")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка создания PDF: {e}")
            import traceback
            traceback.print_exc()
    
    def _create_pdf_with_visualization(self, pdf_path, result):
        """Создать PDF с правильной структурой"""
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors as pdf_colors
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas as pdf_canvas
        
        # Создаем PDF в альбомной ориентации
        c = pdf_canvas.Canvas(pdf_path, pagesize=landscape(A4))
        page_width, page_height = landscape(A4)
        
        # Цвета для деталей (одинаковые группы - одинаковый цвет)
        colors_list = [
            (144/255, 202/255, 249/255),  # Голубой
            (165/255, 214/255, 167/255),  # Зеленый
            (255/255, 245/255, 157/255),  # Желтый
            (244/255, 143/255, 177/255),  # Розовый
            (206/255, 147/255, 216/255),  # Фиолетовый
            (128/255, 222/255, 234/255),  # Бирюзовый
        ]
        
        # ПЕРВАЯ СТРАНИЦА: Титульный лист с заголовком
        try:
            c.setFont("RussianFont-Bold", 24)
        except:
            c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(page_width/2, page_height - 30*mm, "ОПТИМАЛЬНЫЙ РАСКРОЙ ДЕТАЛЕЙ")
        
        # Информация о проекте
        y_info = page_height - 45*mm
        project_name = self.project_name.get().strip() or "Проект без названия"
        
        try:
            c.setFont("RussianFont-Bold", 14)
        except:
            c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(page_width/2, y_info, f"Проект: {project_name}")
        y_info -= 6*mm
        
        # Дата
        try:
            c.setFont("RussianFont", 10)
        except:
            c.setFont("Helvetica", 10)
        c.drawCentredString(page_width/2, y_info, f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        
        # СТАТИСТИКА И РЕКОМЕНДАЦИИ В ТАБЛИЦЕ
        y = y_info - 20*mm
        
        # Заголовок таблицы
        try:
            c.setFont("RussianFont-Bold", 14)
        except:
            c.setFont("Helvetica-Bold", 14)
        c.drawString(20*mm, y, "СТАТИСТИКА И РЕКОМЕНДАЦИИ:")
        y -= 20*mm
        
        # Расчет параметров
        total_sheets_area = result['sheets_needed'] * 3.125
        total_area_all = sum(f['area_m2'] * f['quantity'] for f in self.files_data)
        waste_area = total_sheets_area - total_area_all
        
        # Создаем таблицу статистики с 3 колонками
        stats_data = [
            ['№', 'Параметр', 'Значение'],
            ['1', 'Листов требуется', f"{result['sheets_needed']} шт"],
            ['2', 'Размер листа', "2500x1250 мм"],
            ['3', 'Площадь листа', "3.125 м2"],
            ['4', 'Площадь всех листов', f"{total_sheets_area:.4f} м2"],
            ['5', 'Площадь деталей', f"{total_area_all:.4f} м2"],
            ['6', 'Использование материала', f"{result['utilization_percent']:.1f}%"],
            ['7', 'Обрезки (отходы)', f"{result['overall_waste_percent']:.1f}%"],
            ['8', 'Общая длина реза', f"{result.get('total_cut_length_mm', 0)/1000:.1f} м"],
            ['9', 'Количество контуров', f"{result.get('total_contours', 0)} шт"],
            ['10', 'Время резки', f"{result.get('cutting_time_minutes', 0):.1f} мин"],
            ['11', 'Зазор между деталями', "5 мм (2.5 мм с каждой стороны)"]
        ]
        
        # Создаем таблицу статистики с 3 колонками
        stats_table = Table(stats_data, colWidths=[15*mm, 80*mm, 60*mm])
        
        # Проверяем доступность шрифтов для статистики
        try:
            pdfmetrics.getFont('RussianFont-Bold')
            stats_bold_font = 'RussianFont-Bold'
        except:
            stats_bold_font = 'Helvetica-Bold'
            
        try:
            pdfmetrics.getFont('RussianFont')
            stats_regular_font = 'RussianFont'
        except:
            stats_regular_font = 'Helvetica'
        
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E86AB')),  # Синий заголовок
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), stats_bold_font),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F0F8FF')),  # Очень светло-голубой
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#B0C4DE')),  # Светло-серый
            ('FONTNAME', (0, 1), (-1, -1), stats_regular_font),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        # Размещаем таблицу статистики на первой странице (правильное позиционирование)
        stats_table.wrapOn(c, page_width - 40*mm, page_height - 200*mm)
        stats_table.drawOn(c, 20*mm, y - 90*mm)
        
        # НОВАЯ СТРАНИЦА: РАСЧЕТНАЯ ТАБЛИЦА ДЕТАЛЕЙ
        c.showPage()
        
        # Заголовок страницы
        try:
            c.setFont("RussianFont-Bold", 16)
        except:
            c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(page_width/2, page_height - 30*mm, "РАСЧЕТНАЯ ТАБЛИЦА ДЕТАЛЕЙ")
        
        y = page_height - 50*mm
        
        # Создаем данные для таблицы как в оригинале
        table_data = [
            ['№', 'Название детали', 'Ширина\n(мм)', 'Высота\n(мм)', 
             'Площадь\n1 шт (м2)', 'Кол-во\n(шт)', 'Площадь\nвсего (м2)']
        ]
        
        total_area_all = 0
        total_parts = 0
        
        for i, file_data in enumerate(self.files_data, 1):
            # Получаем количество из названия файла
            quantity = file_data['quantity']
            area_total = file_data['area_m2'] * quantity
            total_area_all += area_total
            total_parts += quantity
            
            table_data.append([
                str(i),
                file_data['name'],
                f"{file_data['width']:.0f}",
                f"{file_data['height']:.0f}",
                f"{file_data['area_m2']:.4f}",
                str(quantity),
                f"{area_total:.4f}"
            ])
        
        # Итого
        table_data.append([
            '', 'ИТОГО:', '', '', '', 
            str(total_parts),
            f"{total_area_all:.4f}"
        ])
        
        # Создаем таблицу с адаптивными колонками и переносом текста
        table = Table(table_data, colWidths=[15*mm, 100*mm, 20*mm, 20*mm, 25*mm, 15*mm, 30*mm])
        
        # Проверяем доступность шрифтов
        try:
            pdfmetrics.getFont('RussianFont-Bold')
            bold_font = 'RussianFont-Bold'
        except:
            bold_font = 'Helvetica-Bold'
            
        try:
            pdfmetrics.getFont('RussianFont')
            regular_font = 'RussianFont'
        except:
            regular_font = 'Helvetica'
        
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4A90E2')),  # Синий заголовок
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), bold_font),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#F5F5F5')),  # Светло-серый
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#D3D3D3')),  # Светло-серый
            ('FONTNAME', (0, -1), (-1, -1), bold_font),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E8F4FD')),  # Очень светло-голубой
            ('FONTNAME', (0, 1), (-1, -2), regular_font),
            ('FONTSIZE', (0, 1), (-1, -2), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            # Перенос текста для всех колонок
            ('WORDWRAP', (0, 1), (-1, -2), 'CJK'),
        ]))
        
        # Размещаем таблицу с правильным отступом от заголовка
        table.wrapOn(c, page_width - 40*mm, page_height - 100*mm)
        table.drawOn(c, 20*mm, page_height - 100*mm)
        
        
        # НОВАЯ СТРАНИЦА: Визуализация раскроя
        c.showPage()
        
        # Заголовок страницы
        try:
            c.setFont("RussianFont-Bold", 16)
        except:
            c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(page_width/2, page_height - 30*mm, "ВИЗУАЛИЗАЦИЯ РАСКРОЯ")
        
        # Параметры для рисования (НА ВСЮ СТРАНИЦУ)
        sheet_width = 2500  # мм
        sheet_height = 1250  # мм
        # Рассчитываем масштаб для размещения на всю страницу
        available_width = page_width - 40*mm  # Минимальные отступы
        available_height = page_height - 60*mm  # Только для заголовка
        scale_x = available_width / sheet_width
        scale_y = available_height / sheet_height
        scale = min(scale_x, scale_y)  # Используем меньший масштаб
        margin_x = 20*mm
        margin_y = page_height - 40*mm  # Верхняя граница
        
        # Создаем карту цветов для одинаковых деталей
        part_colors = {}
        color_index = 0
        
        # Рисуем каждый лист
        if 'sheets' in result and result['sheets']:
            for sheet_idx, sheet in enumerate(result['sheets']):
                if sheet_idx > 0:
                    c.showPage()
                
                # Заголовок листа
                try:
                    c.setFont("RussianFont-Bold", 14)
                except:
                    c.setFont("Helvetica-Bold", 14)
                c.drawString(margin_x, margin_y, f"ЛИСТ №{sheet['sheet_number']} - {len(sheet['parts'])} деталей")
                c.drawString(margin_x, margin_y - 6*mm, f"Размер листа: {sheet['width']}x{sheet['height']} мм")
                
                # Рамка листа
                c.setStrokeColor(colors.black)
                c.setLineWidth(2)
                c.rect(margin_x, margin_y - 20*mm - sheet_height*scale, 
                       sheet_width*scale, sheet_height*scale)
                
                # Размещаем детали
                if 'parts' in sheet and sheet['parts']:
                    for part_idx, part in enumerate(sheet['parts']):
                        x = margin_x + part['x'] * scale
                        y = margin_y - 20*mm - (part['y'] + part['height']) * scale
                        w = part['width'] * scale
                        h = part['height'] * scale
                        
                        # Определяем цвет для одинаковых деталей
                        part_name = part['name']
                        if part_name not in part_colors:
                            part_colors[part_name] = colors_list[color_index % len(colors_list)]
                            color_index += 1
                        
                        color = part_colors[part_name]
                        
                        # Рисуем прямоугольник
                        c.setFillColor(color)
                        c.setStrokeColor(colors.black)
                        c.setLineWidth(1)
                        c.rect(x, y, w, h, fill=1, stroke=1)
                        
                        # Номер детали (всегда показываем)
                        try:
                            c.setFont("RussianFont-Bold", 10)
                        except:
                            c.setFont("Helvetica-Bold", 10)
                        c.setFillColor(colors.black)
                        c.drawCentredString(x + w/2, y + h/2 - 2*mm, f"#{part_idx + 1}")
                        
                        # Название и габариты (если помещается)
                        if w > 30 and h > 20:
                            try:
                                c.setFont("RussianFont", 6)
                            except:
                                c.setFont("Helvetica", 6)
                            c.setFillColor(colors.black)
                            # Название детали
                            name_text = part_name[:15] if len(part_name) > 15 else part_name
                            c.drawCentredString(x + w/2, y + h/2 + 3*mm, name_text)
                            # Габариты
                            size_text = f"{part['real_width']:.0f}x{part['real_height']:.0f}"
                            c.drawCentredString(x + w/2, y + h/2 + 8*mm, size_text)
                
                # НОВАЯ СТРАНИЦА: Список деталей для этого листа
                c.showPage()
                
                # Заголовок страницы
                try:
                    c.setFont("RussianFont-Bold", 16)
                except:
                    c.setFont("Helvetica-Bold", 16)
                c.drawCentredString(page_width/2, page_height - 30*mm, f"СПИСОК ДЕТАЛЕЙ ЛИСТА №{sheet['sheet_number']}")
                
                # Группируем детали по одинаковым названиям
                parts_groups = {}
                for part in sheet['parts']:
                    name = part['name']
                    if name not in parts_groups:
                        parts_groups[name] = {
                            'count': 0,
                            'width': part['real_width'],
                            'height': part['real_height'],
                            'area': (part['real_width'] * part['real_height']) / 1_000_000
                        }
                    parts_groups[name]['count'] += 1
                
                # Создаем таблицу списка деталей для этого листа
                list_data = [
                    ['№', 'Название детали', 'Габариты', 'Кол-во', 'Площадь 1 шт', 'Общая площадь']
                ]
                
                total_sheet_area = 0
                for idx, (name, data) in enumerate(parts_groups.items(), 1):
                    total_area = data['area'] * data['count']
                    total_sheet_area += total_area
                    
                    list_data.append([
                        str(idx),
                        name,
                        f"{data['width']:.0f}x{data['height']:.0f}",
                        str(data['count']),
                        f"{data['area']:.4f}",
                        f"{total_area:.4f}"
                    ])
                
                # Итого для листа
                list_data.append([
                    '', 'ИТОГО:', '', str(sum(d['count'] for d in parts_groups.values())),
                    '', f"{total_sheet_area:.4f}"
                ])
                
                # Создаем таблицу списка с адаптивными колонками и переносом текста
                list_table = Table(list_data, colWidths=[15*mm, 100*mm, 25*mm, 15*mm, 20*mm, 30*mm])
                
                # Проверяем доступность шрифтов для списка
                try:
                    pdfmetrics.getFont('RussianFont-Bold')
                    list_bold_font = 'RussianFont-Bold'
                except:
                    list_bold_font = 'Helvetica-Bold'
                    
                try:
                    pdfmetrics.getFont('RussianFont')
                    list_regular_font = 'RussianFont'
                except:
                    list_regular_font = 'Helvetica'
                
                list_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6B73FF')),  # Фиолетово-синий заголовок
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), list_bold_font),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('TOPPADDING', (0, 0), (-1, 0), 8),
                    ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#F8F9FF')),  # Очень светло-фиолетовый
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E0E0E0')),  # Светло-серый
                    ('FONTNAME', (0, -1), (-1, -1), list_bold_font),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E8F0FF')),  # Светло-голубой
                    ('FONTNAME', (0, 1), (-1, -2), list_regular_font),
                    ('FONTSIZE', (0, 1), (-1, -2), 8),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    # Перенос текста для всех колонок
                    ('WORDWRAP', (0, 1), (-1, -2), 'CJK'),
                ]))
                
                # Размещаем таблицу списка с правильным отступом от заголовка
                list_table.wrapOn(c, page_width - 40*mm, page_height - 100*mm)
                list_table.drawOn(c, 20*mm, page_height - 90*mm)
        
        c.save()
        
    def create_excel_report(self):
        """Создать Excel отчет с оригинальными таблицами"""
        if not self.optimization_result or not self.optimization_result['success']:
            messagebox.showwarning("Предупреждение", "Сначала выполните оптимизацию раскроя")
            return
            
        project_name = self.project_name.get() or "Проект без названия"
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        excel_path = f"Раскрой_{project_name}_{timestamp}.xlsx"
        
        try:
            # Создаем Excel отчет как в оригинале
            wb = openpyxl.Workbook()
            
            # === ЛИСТ 1: РАСЧЕТНАЯ ТАБЛИЦА ДЕТАЛЕЙ ===
            ws1 = wb.active
            ws1.title = "Раскрой деталей"
            
            # Заголовок
            ws1['A1'] = f"Проект: {project_name}"
            ws1['A1'].font = Font(size=14, bold=True, color="1976D2")
            ws1.merge_cells('A1:G1')
            ws1['A1'].alignment = Alignment(horizontal='center')
            
            # Дата
            ws1['A2'] = f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            ws1['A2'].font = Font(size=10)
            
            # Заголовки таблицы
            headers = ['№', 'Название детали', 'Ширина (мм)', 'Высота (мм)', 'Площадь 1 шт (м²)', 'Количество (шт)', 'Площадь всего (м²)']
            for col, header in enumerate(headers, 1):
                cell = ws1.cell(row=4, column=col, value=header)
                cell.font = Font(bold=True)
                cell.alignment = Alignment(horizontal='center')
            
            # Данные
            total_area_all = 0
            total_parts = 0
            for i, file_data in enumerate(self.files_data, 1):
                row = i + 4
                ws1.cell(row=row, column=1, value=i)
                ws1.cell(row=row, column=2, value=file_data['name'])
                ws1.cell(row=row, column=3, value=f"{file_data['width']:.0f}")
                ws1.cell(row=row, column=4, value=f"{file_data['height']:.0f}")
                ws1.cell(row=row, column=5, value=f"{file_data['area_m2']:.4f}")
                ws1.cell(row=row, column=6, value=file_data['quantity'])
                ws1.cell(row=row, column=7, value=f"{file_data['area_m2'] * file_data['quantity']:.4f}")
                
                # Форматирование числовых колонок по центру
                for col in [1, 3, 4, 5, 6, 7]:
                    ws1.cell(row=row, column=col).alignment = Alignment(horizontal='center')
                
                total_area_all += file_data['area_m2'] * file_data['quantity']
                total_parts += file_data['quantity']
            
            # Итого
            total_row = len(self.files_data) + 5
            ws1.cell(row=total_row, column=2, value="ИТОГО:")
            ws1.cell(row=total_row, column=6, value=total_parts)
            ws1.cell(row=total_row, column=7, value=f"{total_area_all:.4f}")
            
            for col in range(2, 8):
                cell = ws1.cell(row=total_row, column=col)
                cell.font = Font(bold=True)
                cell.alignment = Alignment(horizontal='center')
            
            # СТАТИСТИКА КАК В ОРИГИНАЛЕ
            row = total_row + 3
            ws1.cell(row, 1, "СТАТИСТИКА И РЕКОМЕНДАЦИИ:").font = Font(bold=True, size=14)
            row += 2
            
            # Расчет параметров
            total_sheets_area = self.optimization_result['sheets_needed'] * 3.125
            waste_area = total_sheets_area - total_area_all
            
            stats = [
                ("Листов требуется:", f"{self.optimization_result['sheets_needed']} шт"),
                ("Размер листа:", "2500x1250 мм (3.125 м2)"),
                ("Площадь всех листов:", f"{total_sheets_area:.4f} м2"),
                ("Площадь деталей:", f"{total_area_all:.4f} м2"),
                ("Использование материала:", f"{self.optimization_result['utilization_percent']:.1f}%"),
                ("Обрезки (отходы):", f"{self.optimization_result['overall_waste_percent']:.1f}% ({waste_area:.4f} м2)"),
                ("Общая длина реза:", f"{self.optimization_result.get('total_cut_length_mm', 0)/1000:.1f} м"),
                ("Количество контуров:", f"{self.optimization_result.get('total_contours', 0)} шт"),
                ("Время резки:", f"{self.optimization_result.get('cutting_time_minutes', 0):.1f} мин"),
            ]
            
            for param, value in stats:
                ws1.cell(row, 1, param).font = Font(bold=True)
                ws1.cell(row, 2, value)
                row += 1
            
            # === ЛИСТ 2: СВОДКА ПО ГРУППАМ ДЕТАЛЕЙ ===
            ws2 = wb.create_sheet("Сводка по группам")
            
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
                        'total_width': 0,
                        'total_height': 0
                    }
                
                groups[base_name]['count'] += file_data['quantity']
                groups[base_name]['total_area'] += file_data['area_m2'] * file_data['quantity']
                groups[base_name]['total_width'] += file_data['width'] * file_data['quantity']
                groups[base_name]['total_height'] += file_data['height'] * file_data['quantity']
            
            # Заполняем таблицу
            for i, (group_name, data) in enumerate(groups.items(), 1):
                avg_width = data['total_width'] / data['count'] if data['count'] > 0 else 0
                avg_height = data['total_height'] / data['count'] if data['count'] > 0 else 0
                
                ws2.cell(row2, 1, i)
                ws2.cell(row2, 2, group_name)
                ws2.cell(row2, 3, data['count'])
                ws2.cell(row2, 4, f"{data['total_area']:.4f}")
                ws2.cell(row2, 5, f"{avg_width:.0f}x{avg_height:.0f}")
                
                # Форматирование
                for col in range(1, 6):
                    ws2.cell(row2, col).alignment = Alignment(horizontal='center')
                row2 += 1
            
            # Настройка ширины колонок
            ws1.column_dimensions['A'].width = 8
            ws1.column_dimensions['B'].width = 40
            ws1.column_dimensions['C'].width = 15
            ws1.column_dimensions['D'].width = 15
            ws1.column_dimensions['E'].width = 20
            ws1.column_dimensions['F'].width = 15
            ws1.column_dimensions['G'].width = 20
            
            ws2.column_dimensions['A'].width = 8
            ws2.column_dimensions['B'].width = 50
            ws2.column_dimensions['C'].width = 20
            ws2.column_dimensions['D'].width = 20
            ws2.column_dimensions['E'].width = 25
            
            # Сохраняем Excel
            wb.save(excel_path)
            
            messagebox.showinfo("Успех", f"Excel отчет создан!\n\nФайл: {excel_path}\n\nОткройте папку отчетов для просмотра.")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка создания Excel: {e}")
            import traceback
            traceback.print_exc()
        
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
        
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    # Добавляем импорт для диалога
    import tkinter.simpledialog
    app = CorrectPDFStructureGUI()
    app.run()
