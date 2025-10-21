# 🔨 Сборка EXE - Портативная версия

## Дата: 17.10.2025

---

## 🎯 Зачем нужно?

**Проблема:** На компьютере цеха может не быть Python

**Решение:** Собираем EXE файл - работает БЕЗ установки!

**Результат:**
- ✅ Один файл `ZVD_Площади.exe`
- ✅ Не требует Python
- ✅ Двойной клик → программа запускается
- ✅ Можно скопировать на любой компьютер

---

## 🚀 Быстрая сборка

### Автоматическая сборка:

```bash
Двойной клик: build_exe.bat
```

Скрипт автоматически:
1. Проверит PyInstaller (установит если нужно)
2. Соберет EXE файл
3. Положит в папку `dist/`

---

## 📦 Ручная сборка

### Шаг 1: Установите PyInstaller

```bash
pip install pyinstaller
```

### Шаг 2: Соберите EXE

```bash
pyinstaller --onefile --windowed --name "ZVD_Площади" gui_calculator.py
```

### Шаг 3: Найдите результат

```
dist\ZVD_Площади.exe  ← Готовый файл!
```

---

## ⚙️ Параметры сборки

```bash
pyinstaller ^
    --onefile           # Один файл (не папка)
    --windowed          # Без консоли
    --name "ZVD_Площади" # Имя EXE
    --icon=NONE         # Без иконки (или укажите .ico)
    --add-data "README.md;."  # Включить документацию
    --hidden-import=ezdxf     # Библиотеки
    --hidden-import=reportlab
    --hidden-import=openpyxl
    gui_calculator.py
```

---

## 📁 Результат сборки

```
unfolding_area_calculator/
├── build/              ← Временные файлы (можно удалить)
├── dist/               ← РЕЗУЛЬТАТ!
│   └── ZVD_Площади.exe ← Этот файл копируем в цех!
├── ZVD_Площади.spec   ← Конфигурация (можно редактировать)
└── ...
```

---

## 📦 Что делать с EXE

### Для цеха:

```
1. Скопируйте: dist\ZVD_Площади.exe
2. Положите на: \\Server\Производство\Утилиты\
3. Создайте ярлык на рабочем столе мастера
4. Готово!
```

### Запуск:

```
Двойной клик: ZVD_Площади.exe

→ Программа запускается
→ Python НЕ ТРЕБУЕТСЯ!
→ Работает на любом Windows
```

---

## 📊 Размер файла

**Обычно:** 25-40 МБ

**Почему большой:**
- Включен Python runtime
- Библиотеки: ezdxf, reportlab, openpyxl
- Все зависимости упакованы

**Но:** Это нормально для портативной программы!

---

## 🔧 Настройка сборки

### Добавить иконку:

1. Создайте файл `icon.ico` (256×256 пикселей)
2. Измените в `build_exe.bat`:
   ```
   --icon=icon.ico
   ```

### Уменьшить размер:

```bash
# Без Excel экспорта (если не нужен)
pyinstaller --onefile --windowed ^
    --exclude-module=openpyxl ^
    gui_calculator.py
```

### Добавить версию:

```bash
--version-file=version.txt
```

---

## 📝 Файл version.txt (опционально)

```
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'ZVD GROUP'),
        StringStruct(u'FileDescription', u'Расчет площадей разверток'),
        StringStruct(u'FileVersion', u'1.0.0.0'),
        StringStruct(u'ProductName', u'ZVD Площади'),
        StringStruct(u'ProductVersion', u'1.0.0.0')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1049, 1200])])
  ]
)
```

---

## ✅ Готовый EXE

### После сборки:

```
dist\ZVD_Площади.exe  (25-40 МБ)
```

### Передача в цех:

1. **Скопируйте EXE** на сетевой диск или USB
2. **Создайте ярлык** на рабочем столе мастера
3. **Инструкция:** См. `ИНСТРУКЦИЯ_ДЛЯ_ЦЕХА.md`

### Запуск:

```
Двойной клик → Программа работает!
```

**Преимущества:**
- ✅ Не нужен Python
- ✅ Не нужны библиотеки
- ✅ Портативный (один файл)
- ✅ Быстрый запуск

---

## 🔄 Обновление

### Если изменили код:

1. Исправьте `gui_calculator.py` или `area_calculator.py`
2. Запустите `build_exe.bat` снова
3. Скопируйте новый EXE в цех

---

## 🎉 Готово!

**Команда для сборки:**
```bash
build_exe.bat
```

**Результат:**
```
dist\ZVD_Площади.exe
```

**Использование:**
```
Двойной клик → Работает без Python!
```

---

**Версия:** 1.0  
**Дата:** 17.10.2025  
**Инструмент:** PyInstaller





