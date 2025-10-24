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
import rectpack
from datetime import datetime

# Добавляем путь к модулям
sys.path.append(os.path.join(os.path.dirname(__file__), 'components'))

class WorkingGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Раскрой Деталей v2.0 - Рабочая версия")
        self.root.geometry("1000x700")
        
        # Переменные
        self.project_name = tk.StringVar()
        self.folder_path = tk.StringVar()
        self.files_data = []
        
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
        self.tree = ttk.Treeview(main_frame, columns=('name', 'size', 'area', 'quantity'), show='headings', height=15)
        self.tree.heading('name', text='Название файла')
        self.tree.heading('size', text='Размер (мм)')
        self.tree.heading('area', text='Площадь (м²)')
        self.tree.heading('quantity', text='Количество')
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
        
        self.files_data = []
        
        for file in dxf_files:
            try:
                # Парсим количество из названия файла
                quantity = 1
                import re
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
                
                for entity in msp:
                    if hasattr(entity, 'dxf'):
                        if hasattr(entity.dxf, 'start') and hasattr(entity.dxf, 'end'):
                            # Линия
                            min_x = min(min_x, entity.dxf.start.x, entity.dxf.end.x)
                            max_x = max(max_x, entity.dxf.start.x, entity.dxf.end.x)
                            min_y = min(min_y, entity.dxf.start.y, entity.dxf.end.y)
                            max_y = max(max_y, entity.dxf.start.y, entity.dxf.end.y)
                        elif hasattr(entity.dxf, 'center'):
                            # Круг или дуга
                            radius = getattr(entity.dxf, 'radius', 0)
                            min_x = min(min_x, entity.dxf.center.x - radius)
                            max_x = max(max_x, entity.dxf.center.x + radius)
                            min_y = min(min_y, entity.dxf.center.y - radius)
                            max_y = max(max_y, entity.dxf.center.y + radius)
                
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
                        'quantity': quantity
                    }
                    
                    self.files_data.append(file_data)
                    
                    # Добавляем в таблицу
                    self.tree.insert('', 'end', values=(
                        file,
                        f"{width:.1f}x{height:.1f}",
                        f"{area_m2:.4f}",
                        quantity
                    ))
                    
            except Exception as e:
                print(f"Ошибка чтения файла {file}: {e}")
                
        messagebox.showinfo("Информация", f"Загружено {len(self.files_data)} DXF файлов")
        
    def optimize(self):
        if not self.files_data:
            messagebox.showwarning("Предупреждение", "Сначала загрузите файлы")
            return
            
        # Простая оптимизация с rectpack
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
            
            # Добавляем лист 2500x1250 мм
            packer.add_bin(2500, 1250)
            
            # Добавляем прямоугольники
            for rect in rectangles:
                packer.add_rect(*rect)
            
            # Выполняем упаковку
            packer.pack()
            
            # Получаем результаты
            bins = packer[0]
            if bins:
                messagebox.showinfo("Результат оптимизации", 
                    f"Оптимизация завершена!\n"
                    f"Использовано листов: {len(bins)}\n"
                    f"Деталей размещено: {sum(len(bin) for bin in bins)}")
            else:
                messagebox.showerror("Ошибка", "Не удалось разместить детали на листах")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка оптимизации: {e}")
        
    def create_reports(self):
        if not self.files_data:
            messagebox.showwarning("Предупреждение", "Сначала загрузите файлы")
            return
            
        project_name = self.project_name.get() or "Проект без названия"
        
        try:
            # Создаем Excel отчет
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Раскрой деталей"
            
            # Заголовок
            ws['A1'] = f"Проект: {project_name}"
            ws['A1'].font = Font(size=14, bold=True)
            ws.merge_cells('A1:D1')
            
            # Дата
            ws['A2'] = f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            ws['A2'].font = Font(size=10)
            
            # Заголовки таблицы
            headers = ['№', 'Название файла', 'Размер (мм)', 'Площадь (м²)', 'Количество']
            for col, header in enumerate(headers, 1):
                ws.cell(row=4, column=col, value=header).font = Font(bold=True)
            
            # Данные
            total_area = 0
            total_parts = 0
            for i, file_data in enumerate(self.files_data, 1):
                row = i + 4
                ws.cell(row=row, column=1, value=i)
                ws.cell(row=row, column=2, value=file_data['name'])
                ws.cell(row=row, column=3, value=f"{file_data['width']:.1f}x{file_data['height']:.1f}")
                ws.cell(row=row, column=4, value=f"{file_data['area_m2']:.4f}")
                ws.cell(row=row, column=5, value=file_data['quantity'])
                
                total_area += file_data['area_m2'] * file_data['quantity']
                total_parts += file_data['quantity']
            
            # Итого
            total_row = len(self.files_data) + 5
            ws.cell(row=total_row, column=2, value="ИТОГО:")
            ws.cell(row=total_row, column=4, value=f"{total_area:.4f}")
            ws.cell(row=total_row, column=5, value=total_parts)
            ws.cell(row=total_row, column=2).font = Font(bold=True)
            ws.cell(row=total_row, column=4).font = Font(bold=True)
            ws.cell(row=total_row, column=5).font = Font(bold=True)
            
            # Сохраняем Excel
            excel_path = f"Отчет_раскроя_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            wb.save(excel_path)
            
            # Создаем PDF отчет
            pdf_path = f"Отчет_раскроя_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            c = canvas.Canvas(pdf_path, pagesize=A4)
            width, height = A4
            
            # Заголовок
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(width/2, height - 50, f"ОТЧЕТ РАСКРОЯ ДЕТАЛЕЙ")
            c.setFont("Helvetica", 12)
            c.drawCentredString(width/2, height - 80, f"Проект: {project_name}")
            c.drawCentredString(width/2, height - 100, f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
            
            # Таблица
            y = height - 150
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, y, "№")
            c.drawString(100, y, "Название файла")
            c.drawString(300, y, "Размер (мм)")
            c.drawString(400, y, "Площадь (м²)")
            c.drawString(500, y, "Количество")
            
            y -= 20
            c.setFont("Helvetica", 9)
            for i, file_data in enumerate(self.files_data, 1):
                if y < 100:  # Новая страница
                    c.showPage()
                    y = height - 50
                
                c.drawString(50, y, str(i))
                c.drawString(100, y, file_data['name'][:30])  # Обрезаем длинные имена
                c.drawString(300, y, f"{file_data['width']:.1f}x{file_data['height']:.1f}")
                c.drawString(400, y, f"{file_data['area_m2']:.4f}")
                c.drawString(500, y, str(file_data['quantity']))
                y -= 15
            
            # Итого
            y -= 10
            c.setFont("Helvetica-Bold", 10)
            c.drawString(100, y, "ИТОГО:")
            c.drawString(400, y, f"{total_area:.4f} м²")
            c.drawString(500, y, f"{total_parts} шт")
            
            c.save()
            
            messagebox.showinfo("Успех", 
                f"Отчеты созданы!\n\n"
                f"Excel: {excel_path}\n"
                f"PDF: {pdf_path}\n\n"
                f"Общая площадь: {total_area:.4f} м²\n"
                f"Общее количество деталей: {total_parts} шт")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка создания отчетов: {e}")
        
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = WorkingGUI()
    app.run()
