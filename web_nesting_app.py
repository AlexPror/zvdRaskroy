from flask import Flask, render_template, request, jsonify, send_file
import os
import json
import ezdxf
import rectpack
from datetime import datetime
import tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import threading
import time

# Константы
CUT_GAP = 2.5  # мм - зазор для резки

# Глобальные переменные для материала
material_type = "stainless_304"  # По умолчанию нержавейка
material_thickness = 1.0  # мм

WEASYPRINT_AVAILABLE = False

app = Flask(__name__)

# Глобальные переменные для хранения данных
files_data = []
optimization_result = None
project_name = ""

def register_russian_fonts():
    """Регистрация русских шрифтов"""
    try:
        # Список возможных путей к шрифтам
        font_paths = [
            ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
            ("C:/Windows/Fonts/calibri.ttf", "C:/Windows/Fonts/calibrib.ttf"),
            ("C:/Windows/Fonts/tahoma.ttf", "C:/Windows/Fonts/tahomabd.ttf"),
            ("C:/Windows/Fonts/verdana.ttf", "C:/Windows/Fonts/verdanab.ttf")
        ]
        
        font_registered = False
        
        for regular_path, bold_path in font_paths:
            if os.path.exists(regular_path) and os.path.exists(bold_path):
                try:
                    pdfmetrics.registerFont(TTFont('RussianFont', regular_path))
                    pdfmetrics.registerFont(TTFont('RussianFont-Bold', bold_path))
                    print(f"Зарегистрированы шрифты: {regular_path}, {bold_path}")
                    font_registered = True
                    break
                except Exception as e:
                    print(f"Ошибка регистрации шрифтов {regular_path}: {e}")
                    continue
        
        if not font_registered:
            print("Не удалось найти подходящие шрифты, используются стандартные")
            
    except Exception as e:
        print(f"Ошибка регистрации шрифтов: {e}")

def parse_dxf_file(file_path, folder_name=""):
    """Парсинг DXF файла"""
    try:
        doc = ezdxf.readfile(file_path)
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
                    # Круг
                    center = entity.dxf.center
                    radius = entity.dxf.radius
                    min_x = min(min_x, center.x - radius)
                    max_x = max(max_x, center.x + radius)
                    min_y = min(min_y, center.y - radius)
                    max_y = max(max_y, center.y + radius)
                    contours += 1
                elif hasattr(entity.dxf, 'points'):
                    # Полилиния
                    for point in entity.dxf.points:
                        min_x = min(min_x, point[0])
                        max_x = max(max_x, point[0])
                        min_y = min(min_y, point[1])
                        max_y = max(max_y, point[1])
                    contours += 1
        
        if min_x == float('inf'):
            return None
            
        width = max_x - min_x
        height = max_y - min_y
        
        # Добавляем зазор для резки
        width += CUT_GAP
        height += CUT_GAP
        
        area_m2 = (width * height) / 1_000_000
        
        # Извлекаем количество из имени файла
        filename = os.path.basename(file_path)
        quantity = 1
        if '2шт' in filename:
            quantity = 2
        elif '3шт' in filename:
            quantity = 3
        elif '4шт' in filename:
            quantity = 4
        elif '5шт' in filename:
            quantity = 5
        
        # Создаем уникальное имя файла
        unique_name = folder_name + filename
        
        return {
            'name': unique_name,
            'original_name': filename,
            'folder_name': folder_name,
            'width': round(width),
            'height': round(height),
            'area_m2': area_m2,
            'quantity': quantity,
            'contours': contours
        }
        
    except Exception as e:
        print(f"Ошибка чтения файла {file_path}: {e}")
        return None

def optimize_nesting():
    """Оптимизация раскроя"""
    global optimization_result
    
    if not files_data:
        optimization_result = {'success': False, 'error': 'Нет загруженных файлов'}
        return
    
    try:
        # Создаем прямоугольники для rectpack
        rectangles = []
        for file_data in files_data:
            for _ in range(file_data['quantity']):
                rectangles.append((
                    file_data['width'] + 5,  # +5мм зазор
                    file_data['height'] + 5,
                    file_data['name']
                ))
        
        # Размеры листа 2500x1250 мм
        sheet_width = 2500
        sheet_height = 1250
        
        # Создаем упаковщик
        packer = rectpack.newPacker()
        
        # Добавляем прямоугольники
        for i, (w, h, name) in enumerate(rectangles):
            packer.add_rect(w, h, i)
        
        # Добавляем листы - начинаем с одного, добавляем по мере необходимости
        packer.add_bin(sheet_width, sheet_height)
        
        # Упаковываем
        packer.pack()
        
        # Получаем результат
        bins = list(packer)
        
        # Если не все детали поместились, добавляем дополнительные листы
        placed_rects = set()
        for bin_data in bins:
            for rect in bin_data:
                placed_rects.add(rect.rid)
        
        # Проверяем, все ли детали размещены
        if len(placed_rects) < len(rectangles):
            # Добавляем дополнительные листы
            additional_bins_needed = (len(rectangles) - len(placed_rects)) // 20 + 1  # Примерно 20 деталей на лист
            
            for _ in range(additional_bins_needed):
                packer.add_bin(sheet_width, sheet_height)
            
            # Упаковываем снова
            packer.pack()
            bins = list(packer)
        
        if not bins:
            optimization_result = {'success': False, 'error': 'Не удалось разместить детали'}
            return
        
        # Создаем листы
        sheets = []
        for bin_idx, bin_data in enumerate(bins):
            sheet = {
                'sheet_number': bin_idx + 1,
                'width': sheet_width,
                'height': sheet_height,
                'parts': []
            }
            
            for rect in bin_data:
                x, y, w, h = rect.x, rect.y, rect.width, rect.height
                part_name = rectangles[rect.rid][2]
                
                part = {
                    'name': part_name,
                    'x': x,
                    'y': y,
                    'width': w - 5,  # Убираем зазор
                    'height': h - 5,
                    'area': (w - 5) * (h - 5) / 1_000_000
                }
                sheet['parts'].append(part)
            
            sheets.append(sheet)
        
        # Расчет дополнительных параметров
        total_parts = len(rectangles)
        total_area_all = sum(f['area_m2'] * f['quantity'] for f in files_data)
        total_sheets_area = len(bins) * 3.125  # 2500x1250 мм = 3.125 м²
        
        # Правильный расчет использования материала по фактическому размещению
        total_used_area = 0
        for sheet in sheets:
            sheet_area = 0
            for part in sheet['parts']:
                sheet_area += part['area']
            total_used_area += sheet_area
        
        if total_sheets_area > 0:
            utilization_percent = min((total_used_area / total_sheets_area) * 100, 100.0)
            waste_area = max(total_sheets_area - total_used_area, 0)
            overall_waste_percent = (waste_area / total_sheets_area) * 100
        else:
            utilization_percent = 0
            waste_area = 0
            overall_waste_percent = 0
        
        # Отладочная информация
        print(f"DEBUG: Площадь деталей: {total_area_all:.4f} м2")
        print(f"DEBUG: Площадь листов: {total_sheets_area:.4f} м2")
        print(f"DEBUG: Использование: {utilization_percent:.1f}%")
        
        # Расчет длины реза и времени
        total_cut_length_mm = sum(f['contours'] * f['quantity'] for f in files_data) * 50  # Примерно 50мм на контур
        total_contours = sum(f['contours'] * f['quantity'] for f in files_data)
        # Реалистичный расчет времени резки с учетом материала
        if material_type == "stainless_304":
            # Нержавейка AISI 304 - более медленная резка
            cutting_speed_m_per_min = 1.5  # Скорость резки 1.5 м/мин
            positioning_time_per_part = 0.15  # 9 сек на позиционирование (сложнее)
        else:  # galvanized
            # Оцинковка - быстрее режется
            cutting_speed_m_per_min = 2.5  # Скорость резки 2.5 м/мин
            positioning_time_per_part = 0.1  # 6 сек на позиционирование
        
        # Корректировка скорости в зависимости от толщины
        thickness_factor = 1.0 + (material_thickness - 1.0) * 0.2  # +20% за каждый мм сверх 1мм
        cutting_speed_m_per_min = cutting_speed_m_per_min / thickness_factor
        
        cutting_time_minutes = (total_cut_length_mm / 1000 / cutting_speed_m_per_min) + (total_parts * positioning_time_per_part)
        
        optimization_result = {
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
        
    except Exception as e:
        optimization_result = {'success': False, 'error': str(e)}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    global files_data, project_name, material_type, material_thickness
    
    if 'files' not in request.files:
        return jsonify({'error': 'Нет файлов'}), 400
    
    files = request.files.getlist('files')
    project_name = request.form.get('project_name', 'Проект без названия')
    material_type = request.form.get('material_type', 'stainless_304')
    material_thickness = float(request.form.get('material_thickness', '1.0'))
    
    files_data = []
    
    for file in files:
        if file.filename.endswith('.dxf'):
            # Создаем временный файл с оригинальным именем
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, file.filename)
            
            try:
                file.save(temp_path)
                
                # Определяем папку из пути файла
                folder_name = ""
                if hasattr(file, 'name') and '/' in file.name:
                    folder_name = file.name.split('/')[0] + "_"
                elif hasattr(file, 'name') and '\\' in file.name:
                    folder_name = file.name.split('\\')[0] + "_"
                
                # Парсим DXF
                file_data = parse_dxf_file(temp_path, folder_name)
                if file_data:
                    files_data.append(file_data)
                
            finally:
                # Удаляем временный файл
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass  # Игнорируем ошибки удаления
    
    return jsonify({
        'success': True,
        'count': len(files_data),
        'files': files_data
    })

@app.route('/optimize', methods=['POST'])
def optimize():
    global optimization_result
    
    # Запускаем оптимизацию в отдельном потоке
    thread = threading.Thread(target=optimize_nesting)
    thread.start()
    thread.join()  # Ждем завершения
    
    return jsonify(optimization_result)

@app.route('/html_report', methods=['GET'])
def generate_html_report():
    """Генерация HTML отчета"""
    global optimization_result, project_name
    
    if not optimization_result or not optimization_result['success']:
        return jsonify({'error': 'Нет результатов оптимизации'}), 400
    
    try:
        # Подготавливаем данные для шаблона
        result = optimization_result
        total_area_all = sum(f['area_m2'] * f['quantity'] for f in files_data)
        
        # Цвета для деталей
        colors_list = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', 
            '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F'
        ]
        
        # Обрабатываем листы
        processed_sheets = []
        for sheet in result['sheets']:
            # Группируем детали по названию
            parts_by_name = {}
            for part in sheet['parts']:
                name = part['name']
                if name not in parts_by_name:
                    parts_by_name[name] = {
                        'count': 0,
                        'width': float(part['width']),
                        'height': float(part['height']),
                        'area': float(part['area'])
                    }
                parts_by_name[name]['count'] += 1
            
            # Добавляем цвета к деталям
            colored_parts = []
            for i, part in enumerate(sheet['parts']):
                part['color'] = colors_list[i % len(colors_list)]
                colored_parts.append(part)
            
            total_parts = sum(data['count'] for data in parts_by_name.values())
            total_area = round(sum(data['area'] * data['count'] for data in parts_by_name.values()), 5)
            
            processed_sheet = {
                'sheet_number': sheet['sheet_number'],
                'width': float(sheet['width']),
                'height': float(sheet['height']),
                'parts': colored_parts,
                'parts_by_name': parts_by_name,
                'total_parts': total_parts,
                'total_area': total_area
            }
            processed_sheets.append(processed_sheet)
        
        # Обрабатываем данные деталей для шаблона
        processed_parts_data = []
        for f in files_data:
            processed_part = {
                'name': f['name'],
                'width': float(f['width']),
                'height': float(f['height']),
                'area_m2': float(f['area_m2']),
                'quantity': int(f['quantity'])
            }
            processed_parts_data.append(processed_part)
        
        # Объединяем одинаковые детали для итоговой таблицы
        merged_parts = {}
        for part in processed_parts_data:
            # Создаем ключ для объединения: название + размер + площадь
            key = f"{part['name']}_{part['width']}x{part['height']}_{part['area_m2']}"
            
            if key not in merged_parts:
                merged_parts[key] = {
                    'name': part['name'],
                    'width': part['width'],
                    'height': part['height'],
                    'area_m2': part['area_m2'],
                    'total_quantity': 0,
                    'total_area': 0
                }
            
            merged_parts[key]['total_quantity'] += part['quantity']
            merged_parts[key]['total_area'] += part['area_m2'] * part['quantity']
        
        # Вычисляем общие итоги для объединенных деталей
        total_quantity_merged = sum(data['total_quantity'] for data in merged_parts.values())
        total_area_merged = round(sum(data['total_area'] for data in merged_parts.values()), 5)
        
        # Данные для шаблона
        material_names = {
            'stainless_304': 'Нержавейка AISI 304',
            'galvanized': 'Оцинковка'
        }
        
        template_data = {
            'project_name': project_name,
            'report_date': datetime.now().strftime('%d.%m.%Y %H:%M'),
            'material_name': material_names.get(material_type, 'Неизвестный материал'),
            'material_thickness': material_thickness,
            'sheets_needed': int(result.get('sheets_needed', 1)),
            'utilization_percent': f"{float(result.get('utilization_percent', 0)):.1f}",
            'total_parts': int(result.get('total_parts', 0)),
            'total_area_m2': f"{total_area_all:.5f}",
            'total_cut_length': f"{float(result.get('total_cut_length_mm', 0))/1000:.1f}",
            'cutting_time': f"{float(result.get('cutting_time_minutes', 0)):.1f}",
            'cut_gap': CUT_GAP,
            'parts_data': list(merged_parts.values()),
            'total_quantity': sum(f['quantity'] for f in files_data),
            'sheets': processed_sheets,
            'merged_parts': merged_parts,
            'total_quantity_merged': total_quantity_merged,
            'total_area_merged': f"{total_area_merged:.5f}"
        }
        
        return render_template('report.html', **template_data)
        
    except Exception as e:
        print(f"DEBUG: Ошибка в HTML отчете: {str(e)}")
        print(f"DEBUG: Тип optimization_result: {type(optimization_result)}")
        if optimization_result:
            print(f"DEBUG: Ключи result: {list(optimization_result.keys())}")
            print(f"DEBUG: result['sheets_needed']: {optimization_result.get('sheets_needed')} (тип: {type(optimization_result.get('sheets_needed'))}")
            print(f"DEBUG: result['total_parts']: {optimization_result.get('total_parts')} (тип: {type(optimization_result.get('total_parts'))})")
        return jsonify({'error': str(e)}), 500

@app.route('/pdf', methods=['GET'])
def generate_pdf():
    global optimization_result, project_name
    
    if not optimization_result or not optimization_result['success']:
        return jsonify({'error': 'Нет результатов оптимизации'}), 400
    
    # Создаем PDF
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    temp_pdf.close()
    
    try:
        register_russian_fonts()
        
        # Создаем PDF в альбомной ориентации A3
        c = canvas.Canvas(temp_pdf.name, pagesize=landscape(A3))
        page_width, page_height = landscape(A3)
        
        # ФИКСИРОВАННЫЙ БЛОК ЗАГОЛОВКА - ПЕРВАЯ СТРАНИЦА
        header_y_start = page_height - 40*mm
        header_y_end = page_height - 20*mm
        
        # Заголовок
        try:
            c.setFont("RussianFont-Bold", 24)
        except:
            c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(page_width/2, header_y_start, "ОПТИМАЛЬНЫЙ РАСКРОЙ ДЕТАЛЕЙ")
        
        # Информация о проекте
        try:
            c.setFont("RussianFont-Bold", 14)
        except:
            c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(page_width/2, header_y_start - 15*mm, f"Проект: {project_name}")
        
        try:
            c.setFont("RussianFont", 10)
        except:
            c.setFont("Helvetica", 10)
        c.drawCentredString(page_width/2, header_y_start - 25*mm, f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        
        # СТАТИСТИКА В ТАБЛИЦЕ
        result = optimization_result
        total_area_all = sum(f['area_m2'] * f['quantity'] for f in files_data)
        total_sheets_area = result['sheets_needed'] * 3.125
        
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
        
        stats_table = Table(stats_data, colWidths=[15*mm, 80*mm, 60*mm])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E86AB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'RussianFont-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F0F8FF')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#B0C4DE')),
            ('FONTNAME', (0, 1), (-1, -1), 'RussianFont'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        # ФИКСИРОВАННЫЙ БЛОК ТАБЛИЦЫ СТАТИСТИКИ
        stats_table_y_start = header_y_start - 40*mm
        stats_table_y_end = stats_table_y_start - 80*mm
        
        stats_table.wrapOn(c, page_width - 40*mm, 80*mm)
        stats_table.drawOn(c, 20*mm, stats_table_y_end)
        
        # НОВАЯ СТРАНИЦА: РАСЧЕТНАЯ ТАБЛИЦА ДЕТАЛЕЙ
        c.showPage()
        
        # ФИКСИРОВАННЫЙ БЛОК ЗАГОЛОВКА ДЛЯ ТАБЛИЦ
        table_header_y_start = page_height - 30*mm
        table_header_y_end = page_height - 10*mm
        
        try:
            c.setFont("RussianFont-Bold", 16)
        except:
            c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(page_width/2, table_header_y_start, "РАСЧЕТНАЯ ТАБЛИЦА ДЕТАЛЕЙ")
        
        # Создаем данные для таблицы
        table_data = [
            ['№', 'Название детали', 'Ширина\n(мм)', 'Высота\n(мм)', 
             'Площадь\n1 шт (м2)', 'Кол-во\n(шт)', 'Площадь\nвсего (м2)']
        ]
        
        total_area_all = 0
        for i, file_data in enumerate(files_data, 1):
            area_total = file_data['area_m2'] * file_data['quantity']
            total_area_all += area_total
            
            table_data.append([
                str(i),
                file_data['name'],
                f"{file_data['width']:.1f}",
                f"{file_data['height']:.1f}",
                f"{file_data['area_m2']:.4f}",
                str(file_data['quantity']),
                f"{area_total:.4f}"
            ])
        
        # Итоговая строка
        table_data.append([
            '', 'ИТОГО:', '', '', '', 
            str(sum(f['quantity'] for f in files_data)),
            f"{total_area_all:.4f}"
        ])
        
        # Создаем таблицу с адаптивными столбцами
        table = Table(table_data, colWidths=[15*mm, 150*mm, 25*mm, 25*mm, 30*mm, 25*mm, 35*mm])
        
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
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4A90E2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), bold_font),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#F5F5F5')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#D3D3D3')),
            ('FONTNAME', (0, -1), (-1, -1), bold_font),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E8F4FD')),
            ('FONTNAME', (0, 1), (-1, -2), regular_font),
            ('FONTSIZE', (0, 1), (-1, -2), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('WORDWRAP', (0, 1), (-1, -2), 'CJK'),
        ]))
        
        # ФИКСИРОВАННЫЙ БЛОК ТАБЛИЦЫ - РАСЧЕТНАЯ ТАБЛИЦА
        table_y_start = table_header_y_end - 20*mm
        table_y_end = 50*mm  # Фиксированная нижняя граница
        available_table_height = table_y_start - table_y_end
        
        table.wrapOn(c, page_width - 60*mm, available_table_height)
        
        if table._height > available_table_height:
            # Разбиваем таблицу на части
            rows_per_page = max(1, len(table_data) // 2)  # Половина строк на страницу
            
            for page_start in range(0, len(table_data), rows_per_page):
                if page_start > 0:
                    c.showPage()
                    # ФИКСИРОВАННЫЙ БЛОК ЗАГОЛОВКА для продолжения
                    try:
                        c.setFont("RussianFont-Bold", 16)
                    except:
                        c.setFont("Helvetica-Bold", 16)
                    c.drawCentredString(page_width/2, table_header_y_start, "РАСЧЕТНАЯ ТАБЛИЦА ДЕТАЛЕЙ (продолжение)")
                
                page_data = table_data[page_start:page_start + rows_per_page]
                
                # На последней странице добавляем итоговую строку
                if page_start + rows_per_page >= len(table_data) - 1 and len(table_data) > 1:
                    page_data.append(table_data[-1])
                
                page_table = Table(page_data, colWidths=[15*mm, 150*mm, 25*mm, 25*mm, 30*mm, 25*mm, 35*mm])
                page_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4A90E2')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), bold_font),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#F5F5F5')),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#D3D3D3')),
                    ('FONTNAME', (0, 1), (-1, -2), regular_font),
                    ('FONTSIZE', (0, 1), (-1, -2), 8),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('WORDWRAP', (0, 1), (-1, -2), 'CJK'),
                ]))
                
                page_table.wrapOn(c, page_width - 60*mm, available_table_height)
                page_table.drawOn(c, 30*mm, table_y_end)
        else:
            table.drawOn(c, 30*mm, table_y_end)
        
        # НОВАЯ СТРАНИЦА: Визуализация раскроя
        c.showPage()
        
        # ФИКСИРОВАННЫЙ БЛОК ЗАГОЛОВКА для визуализации
        viz_header_y_start = page_height - 30*mm
        viz_header_y_end = page_height - 10*mm
        
        try:
            c.setFont("RussianFont-Bold", 16)
        except:
            c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(page_width/2, viz_header_y_start, "ВИЗУАЛИЗАЦИЯ РАСКРОЯ")
        
        # Цвета для деталей
        colors_list = [
            (1, 0, 0),      # Красный
            (0, 1, 0),      # Зеленый
            (0, 0, 1),      # Синий
            (1, 1, 0),      # Желтый
            (1, 0, 1),      # Пурпурный
            (0, 1, 1),      # Голубой
            (0.5, 0.5, 0.5), # Серый
            (1, 0.5, 0),    # Оранжевый
        ]
        
        # Рисуем листы
        for sheet_idx, sheet in enumerate(result['sheets']):
            if sheet_idx > 0:
                c.showPage()
            
            # ФИКСИРОВАННЫЙ БЛОК ЗАГОЛОВКА листа
            sheet_header_y_start = page_height - 30*mm
            sheet_header_y_end = page_height - 10*mm
            
            # Заголовок листа
            try:
                c.setFont("RussianFont-Bold", 14)
            except:
                c.setFont("Helvetica-Bold", 14)
            c.drawCentredString(page_width/2, sheet_header_y_start, f"ЛИСТ №{sheet['sheet_number']} - {len(sheet['parts'])} деталей")
            
            # ФИКСИРОВАННЫЙ БЛОК для визуализации листа
            viz_y_start = sheet_header_y_end - 20*mm
            viz_y_end = 100*mm  # Фиксированная нижняя граница для визуализации
            available_viz_height = viz_y_start - viz_y_end
            
            # Масштаб для размещения на странице
            scale = min((page_width - 100*mm) / sheet['width'], available_viz_height / sheet['height'])
            start_x = (page_width - sheet['width'] * scale) / 2
            start_y = viz_y_start - sheet['height'] * scale
            
            # Рисуем контур листа
            c.setStrokeColor(colors.black)
            c.setLineWidth(2)
            c.rect(start_x, start_y, sheet['width'] * scale, sheet['height'] * scale)
            
            # Рисуем детали
            for part_idx, part in enumerate(sheet['parts']):
                color = colors_list[part_idx % len(colors_list)]
                c.setFillColor(colors.Color(*color))
                c.setStrokeColor(colors.black)
                c.setLineWidth(1)
                
                x = start_x + part['x'] * scale
                y = start_y + part['y'] * scale
                width = part['width'] * scale
                height = part['height'] * scale
                
                c.rect(x, y, width, height, fill=1, stroke=1)
                
                # Номер детали
                try:
                    c.setFont("RussianFont", 8)
                except:
                    c.setFont("Helvetica", 8)
                c.setFillColor(colors.black)
                c.drawCentredString(x + width/2, y + height/2, str(part_idx + 1))
            
            # НОВАЯ СТРАНИЦА: СПИСОК ДЕТАЛЕЙ ДЛЯ ЭТОГО ЛИСТА
            c.showPage()
            
            # ФИКСИРОВАННЫЙ БЛОК ЗАГОЛОВКА для списка деталей
            list_header_y_start = page_height - 30*mm
            list_header_y_end = page_height - 10*mm
            
            try:
                c.setFont("RussianFont-Bold", 16)
            except:
                c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(page_width/2, list_header_y_start, f"СПИСОК ДЕТАЛЕЙ ЛИСТА №{sheet['sheet_number']}")
            
            # Создаем таблицу деталей для этого листа
            sheet_parts_data = [
                ['№', 'Название детали', 'Габариты', 'Кол-во', 'Площадь 1 шт', 'Общая площадь']
            ]
            
            # Группируем детали по названию
            parts_by_name = {}
            for part in sheet['parts']:
                name = part['name']
                if name not in parts_by_name:
                    parts_by_name[name] = {
                        'count': 0,
                        'width': part['width'],
                        'height': part['height'],
                        'area': part['area']
                    }
                parts_by_name[name]['count'] += 1
            
            # Добавляем в таблицу
            for i, (name, data) in enumerate(parts_by_name.items(), 1):
                sheet_parts_data.append([
                    str(i),
                    name,
                    f"{data['width']:.0f}x{data['height']:.0f}",
                    str(data['count']),
                    f"{data['area']:.4f}",
                    f"{data['area'] * data['count']:.4f}"
                ])
            
            # Итоговая строка
            total_parts = sum(data['count'] for data in parts_by_name.values())
            total_area = sum(data['area'] * data['count'] for data in parts_by_name.values())
            sheet_parts_data.append([
                '', 'ИТОГО:', '', str(total_parts), '', f"{total_area:.5f}"
            ])
            
            # ФИКСИРОВАННЫЙ БЛОК ТАБЛИЦЫ для списка деталей
            list_table_y_start = list_header_y_end - 20*mm
            list_table_y_end = 50*mm  # Фиксированная нижняя граница
            available_list_height = list_table_y_start - list_table_y_end
            
            # Создаем таблицу с адаптивными столбцами
            sheet_table = Table(sheet_parts_data, colWidths=[15*mm, 150*mm, 30*mm, 20*mm, 25*mm, 35*mm])
            sheet_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6B73FF')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), bold_font),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#F8F9FF')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E0E0E0')),
                ('FONTNAME', (0, 1), (-1, -2), regular_font),
                ('FONTSIZE', (0, 1), (-1, -2), 8),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('WORDWRAP', (0, 1), (-1, -2), 'CJK'),
            ]))
            
            sheet_table.wrapOn(c, page_width - 60*mm, available_list_height)
            sheet_table.drawOn(c, 30*mm, list_table_y_end)
        
        c.save()
        
        # Создаем безопасное имя файла без русских символов
        safe_project_name = project_name.replace(' ', '_').replace(':', '').replace('/', '_')
        safe_filename = f'Nesting_Report_{safe_project_name}_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf'
        
        return send_file(temp_pdf.name, as_attachment=True, download_name=safe_filename)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/pdf_from_html', methods=['GET'])
def generate_pdf_from_html():
    """Генерация PDF из HTML отчета"""
    global optimization_result, project_name
    
    if not optimization_result or not optimization_result['success']:
        return jsonify({'error': 'Нет результатов оптимизации'}), 400
    
    if not WEASYPRINT_AVAILABLE:
        return jsonify({'error': 'WeasyPrint недоступен. Используйте HTML отчет или старый PDF.'}), 400
    
    try:
        # Получаем HTML отчет
        html_response = generate_html_report()
        if hasattr(html_response, 'data'):
            html_content = html_response.data.decode('utf-8')
        else:
            html_content = str(html_response)
        
        # Создаем временный PDF файл
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_pdf.close()
        
        # Конвертируем HTML в PDF с помощью WeasyPrint
        html_doc = weasyprint.HTML(string=html_content)
        html_doc.write_pdf(temp_pdf.name)
        
        # Создаем безопасное имя файла
        safe_project_name = project_name.replace(' ', '_').replace(':', '').replace('/', '_')
        safe_filename = f'Nesting_Report_{safe_project_name}_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf'
        
        return send_file(temp_pdf.name, as_attachment=True, download_name=safe_filename)
        
    except Exception as e:
        return jsonify({'error': f'Ошибка генерации PDF: {str(e)}'}), 500

@app.route('/check_weasyprint', methods=['GET'])
def check_weasyprint():
    """Проверка доступности WeasyPrint"""
    return jsonify({'available': WEASYPRINT_AVAILABLE})

@app.route('/add_files', methods=['POST'])
def add_files():
    """Добавление новых файлов к существующему проекту"""
    global files_data, optimization_result
    
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'Нет файлов для загрузки'}), 400
        
        files = request.files.getlist('files')
        new_files_count = 0
        
        print(f"DEBUG: Получено файлов: {len(files)}")
        print(f"DEBUG: request.files: {list(request.files.keys())}")
        
        for i, file in enumerate(files):
            print(f"DEBUG: Файл {i}: {file.filename}, пустой: {file.filename == ''}, размер: {file.content_length if hasattr(file, 'content_length') else 'unknown'}")
            if file and file.filename:
                print(f"DEBUG: Проверяем файл: {file.filename}")
                if file.filename.endswith('.dxf'):
                    print(f"DEBUG: Файл {file.filename} прошел проверку .dxf")
                    # Создаем временный файл с оригинальным именем
                    temp_dir = tempfile.gettempdir()
                    temp_path = os.path.join(temp_dir, file.filename)
                
                    try:
                        file.save(temp_path)
                        
                        # Определяем папку из пути файла
                        folder_name = ""
                        if hasattr(file, 'name') and '/' in file.name:
                            folder_name = file.name.split('/')[0] + "_"
                        elif hasattr(file, 'name') and '\\' in file.name:
                            folder_name = file.name.split('\\')[0] + "_"
                        
                        # Парсим DXF используя существующую функцию
                        file_data = parse_dxf_file(temp_path, folder_name)
                        if file_data:
                            files_data.append(file_data)
                            new_files_count += 1
                            print(f"DEBUG: Файл {file.filename} добавлен. Всего файлов: {new_files_count}")
                        else:
                            print(f"DEBUG: Не удалось обработать файл {file.filename}")
                        
                    except Exception as e:
                        print(f"Ошибка обработки файла {file.filename}: {e}")
                        
                    finally:
                        # Удаляем временный файл
                        if os.path.exists(temp_path):
                            try:
                                os.remove(temp_path)
                            except OSError:
                                pass  # Игнорируем ошибки удаления
        
        # Сбрасываем результаты оптимизации для пересчета
        optimization_result = None
        
        return jsonify({
            'success': True,
            'message': f'Добавлено {new_files_count} новых файлов',
            'total_files': len(files_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/update_quantities', methods=['POST'])
def update_quantities():
    """Обновление количества деталей"""
    global files_data, optimization_result
    
    try:
        data = request.get_json()
        quantities = data.get('quantities', {})
        
        # Обновляем количества
        for i, quantity in quantities.items():
            if 0 <= int(i) < len(files_data):
                files_data[int(i)]['quantity'] = int(quantity)
        
        # Сбрасываем результаты оптимизации для пересчета
        optimization_result = None
        
        return jsonify({
            'success': True,
            'message': 'Количества обновлены'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/recalculate', methods=['POST'])
def recalculate():
    """Пересчет отчета с новыми данными"""
    global optimization_result
    
    try:
        # Запускаем оптимизацию заново
        thread = threading.Thread(target=optimize_nesting)
        thread.start()
        thread.join()  # Ждем завершения
        
        if optimization_result and optimization_result['success']:
            return jsonify({
                'success': True,
                'message': 'Отчет пересчитан',
                'result': optimization_result
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Ошибка пересчета'
            }), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_files_data', methods=['GET'])
def get_files_data():
    """Получение данных о загруженных файлах"""
    global files_data
    
    try:
        return jsonify({
            'success': True,
            'files': files_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
