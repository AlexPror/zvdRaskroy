#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Система мониторинга папки с DXF файлами и автоматической обработки обрезков
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import logging
from pathlib import Path
from datetime import datetime
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from components.dxf_nesting_analyzer import DXFNestingAnalyzer
from components.cypcut_parser import WasteDatabaseManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class DXFFileHandler(FileSystemEventHandler):
    """
    Обработчик событий файловой системы
    Автоматически обрабатывает новые DXF файлы
    """
    
    def __init__(self, watch_folder: Path, db_manager: WasteDatabaseManager, analyzer: DXFNestingAnalyzer):
        self.watch_folder = watch_folder
        self.db_manager = db_manager
        self.analyzer = analyzer
        self.processed_files = set()
        self.logger = logging.getLogger(__name__)
    
    def on_created(self, event):
        """Вызывается при создании нового файла"""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Проверяем расширение
        if file_path.suffix.lower() not in ['.dxf', '.DXF']:
            return
        
        # Проверяем, не обработан ли уже
        if str(file_path) in self.processed_files:
            return
        
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"🔔 НОВЫЙ ФАЙЛ ОБНАРУЖЕН: {file_path.name}")
        self.logger.info(f"{'='*80}")
        
        # Даем время на завершение копирования (если файл большой)
        time.sleep(1)
        
        # Обрабатываем
        self.process_dxf_file(file_path)
        
        # Помечаем как обработанный
        self.processed_files.add(str(file_path))
    
    def process_dxf_file(self, dxf_path: Path):
        """Обрабатывает DXF файл раскроя"""
        try:
            self.logger.info(f"📂 Обработка файла: {dxf_path.name}")
            
            # Анализируем DXF
            result = self.analyzer.analyze_nesting_dxf(dxf_path)
            
            if not result['success']:
                self.logger.error(f"❌ Ошибка анализа: {result.get('error')}")
                return
            
            metadata = result['metadata']
            sheets = result['sheets']
            
            self.logger.info(f"✅ Файл проанализирован!")
            self.logger.info(f"   Листов: {len(sheets)}")
            
            # Извлекаем метаданные
            project_name = metadata.get('project', 'Unknown')
            order_number = metadata.get('order', 'N/A')
            
            if not metadata.get('project'):
                # Пытаемся получить из пути
                path_parts = str(dxf_path).split('\\')
                for part in path_parts:
                    if 'LITE' in part or 'TURBO' in part:
                        project_name = part
                        break
            
            self.logger.info(f"   Проект: {project_name}")
            self.logger.info(f"   Заказ: {order_number}")
            
            # Собираем все обрезки
            all_wastes = []
            total_usable = 0
            
            for sheet in sheets:
                waste_regions = sheet['waste_regions']
                
                self.logger.info(f"\n   Лист №{sheet['sheet_number']}:")
                self.logger.info(f"      Деталей: {len(sheet['parts'])}")
                self.logger.info(f"      Обрезков: {len(waste_regions)}")
                
                for waste in waste_regions:
                    if waste['usable']:
                        total_usable += 1
                        all_wastes.append(waste)
                        
                        self.logger.info(f"         ✓ {waste['width']:.0f}×{waste['height']:.0f} мм "
                                       f"({waste['area_m2']:.4f} м²)")
            
            if not all_wastes:
                self.logger.warning("   ⚠️  Пригодных обрезков не найдено")
                return
            
            self.logger.info(f"\n   📊 ИТОГО пригодных обрезков: {total_usable}")
            
            # Добавляем в базу данных
            self.logger.info(f"\n💾 Сохранение в базу данных...")
            
            waste_records = self.db_manager.add_waste_records(
                waste_regions=all_wastes,
                project_name=project_name,
                order_number=order_number,
                material="Оцинковка 1.5мм"  # TODO: можно извлекать из файла
            )
            
            self.logger.info(f"✅ Сохранено {len(waste_records)} обрезков!")
            self.logger.info(f"\n📋 ПРИСВОЕНЫ НОМЕРА:")
            
            for record in waste_records:
                self.logger.info(f"   {record['id']}: {record['width']:.0f}×{record['height']:.0f} мм "
                               f"(Лист {record.get('sheet_number', '?')})")
            
            self.logger.info(f"\n{'='*80}")
            self.logger.info(f"✅ ОБРАБОТКА ЗАВЕРШЕНА")
            self.logger.info(f"{'='*80}\n")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки файла: {e}", exc_info=True)


def start_monitoring(watch_folder: str = None, check_existing: bool = True):
    """
    Запускает систему мониторинга папки с DXF файлами
    
    Args:
        watch_folder: путь к папке для мониторинга
        check_existing: проверять ли существующие файлы при запуске
    """
    
    # Папка по умолчанию
    if watch_folder is None:
        watch_folder = Path(r"C:\Users\Vorob\Documents\ZVD GROUP\Для_резки")
        
        # Создаем если не существует
        watch_folder.mkdir(parents=True, exist_ok=True)
    else:
        watch_folder = Path(watch_folder)
    
    if not watch_folder.exists():
        print(f"❌ Папка не найдена: {watch_folder}")
        print(f"Создаю папку...")
        watch_folder.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("🏭 СИСТЕМА МОНИТОРИНГА ОБРЕЗКОВ")
    print("=" * 80)
    print(f"\n📁 Папка мониторинга: {watch_folder}")
    print(f"\n💡 ИНСТРУКЦИЯ:")
    print(f"   1. Технолог создает раскрой в CypCut")
    print(f"   2. Сохраняет DXF файл в эту папку")
    print(f"   3. Программа АВТОМАТИЧЕСКИ:")
    print(f"      - Анализирует обрезки")
    print(f"      - Присваивает номера W-XXX")
    print(f"      - Сохраняет в базу")
    print(f"\n🔄 Мониторинг запущен. Ожидание новых файлов...")
    print("=" * 80 + "\n")
    
    # Инициализация
    analyzer = DXFNestingAnalyzer(sheet_width=2500, sheet_height=1250)
    db_manager = WasteDatabaseManager()
    
    # Обработчик файлов
    event_handler = DXFFileHandler(watch_folder, db_manager, analyzer)
    
    # Проверяем существующие файлы при запуске
    if check_existing:
        print("🔍 Проверка существующих файлов в папке...\n")
        
        dxf_files = list(watch_folder.glob("*.dxf")) + list(watch_folder.glob("*.DXF"))
        
        if dxf_files:
            print(f"Найдено {len(dxf_files)} DXF файлов")
            
            for dxf_file in dxf_files:
                print(f"\n{'='*80}")
                print(f"📄 Обработка: {dxf_file.name}")
                print(f"{'='*80}")
                
                event_handler.process_dxf_file(dxf_file)
                event_handler.processed_files.add(str(dxf_file))
        else:
            print("Существующих DXF файлов не найдено")
        
        print(f"\n{'='*80}")
        print("✅ Проверка завершена. Ожидание новых файлов...")
        print(f"{'='*80}\n")
    
    # Запускаем наблюдатель
    observer = Observer()
    observer.schedule(event_handler, str(watch_folder), recursive=False)
    observer.start()
    
    print("🚀 Система активна!")
    print("💡 Для остановки нажмите Ctrl+C\n")
    
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n\n🛑 Остановка системы...")
        observer.stop()
        observer.join()
        print("✅ Система остановлена")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Система мониторинга обрезков')
    parser.add_argument('--folder', type=str, help='Папка для мониторинга')
    parser.add_argument('--no-check-existing', action='store_true', 
                       help='Не проверять существующие файлы')
    
    args = parser.parse_args()
    
    start_monitoring(
        watch_folder=args.folder,
        check_existing=not args.no_check_existing
    )


