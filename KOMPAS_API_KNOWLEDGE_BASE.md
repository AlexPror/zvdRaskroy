# 🎓 БАЗА ЗНАНИЙ: KOMPAS-3D API

## Для AI-ассистентов и разработчиков

**Версия:** 1.0  
**Дата:** 2025-10-09  
**Протестировано на:** KOMPAS-3D V23

---

## 📚 ОГЛАВЛЕНИЕ

1. [Основы подключения](#основы-подключения)
2. [Работа с документами](#работа-с-документами)
3. [Переменные и параметры](#переменные-и-параметры)
4. [Детали и сборки](#детали-и-сборки)
5. [Экспорт и сохранение](#экспорт-и-сохранение)
6. [Частые проблемы и решения](#частые-проблемы-и-решения)
7. [Ограничения API](#ограничения-api)
8. [Лучшие практики](#лучшие-практики)

---

## 1. Основы подключения

### Подключение к КОМПАС-3D

```python
import pythoncom
from win32com.client import Dispatch, gencache

# КРИТИЧНО: Всегда инициализируем COM
pythoncom.CoInitialize()

try:
    # API 5 - для работы с 3D
    api5 = Dispatch("Kompas.Application.5")
    api5.Visible = True  # Делаем видимым
    
    # API 7 - для работы с документами
    api7 = Dispatch("Kompas.Application.7")
    
    # Константы (ОБЯЗАТЕЛЬНО для работы с 3D)
    kompas6_constants_3d = gencache.EnsureModule(
        "{2CAF168C-7961-4B90-9DA2-701419BEEFE3}", 0, 1, 0
    ).constants
    
    # Ваш код здесь...
    
finally:
    # ВСЕГДА освобождаем ресурсы
    pythoncom.CoUninitialize()
```

**Важно:**
- `pythoncom.CoInitialize()` в НАЧАЛЕ
- `pythoncom.CoUninitialize()` в КОНЦЕ (в finally)
- Используйте `gencache.EnsureModule` для констант

---

## 2. Работа с документами

### Открытие документа

```python
# Метод 1: Через API7 (универсальный)
doc = api7.Documents.Open(file_path, False, True)
time.sleep(2)  # КРИТИЧНО: дать время на открытие!

# Метод 2: Через API5 (для 3D)
doc3D = api5.Document3D
doc3D.Open(file_path, False)
time.sleep(1)
```

**Важно:**
- Всегда добавляйте `time.sleep()` после открытия!
- Для `.a3d` (сборки) и `.m3d` (детали) - API5
- Для `.cdw` (чертежи) - API7

### Получение активного документа

```python
# 3D документ
iDocument3D = api5.ActiveDocument3D
if not iDocument3D:
    print("3D документ не открыт!")

# Любой документ
active_doc = api7.ActiveDocument
```

### Закрытие документа

```python
# БЕЗ сохранения
api7.ActiveDocument.Close(False)

# С СОХРАНЕНИЕМ
api7.ActiveDocument.Close(True)
```

---

## 3. Переменные и параметры

### Получение переменной

```python
# Получить TopPart (главная деталь сборки)
iPart = iDocument3D.GetPart(kompas6_constants_3d.pTop_Part)

# Получить коллекцию переменных
var_collection = iPart.VariableCollection()

# Получить переменную по имени
variable = var_collection.GetByName('H')

if variable:
    # Чтение
    value = variable.value
    expression = variable.Expression
    
    # Запись
    variable.value = 150.0
    variable.Expression = "150.0"
```

**⚠️ ОГРАНИЧЕНИЯ API:**
- ✅ Можно: читать `value` и `Expression`
- ✅ Можно: менять `value` и `Expression` (для простых переменных)
- ❌ НЕЛЬЗЯ: менять `linkDocName` / `linkVarName` (гиперссылки защищены!)
- ❌ НЕЛЬЗЯ: создавать переменные через `Add()` (метод недоступен в некоторых версиях)

### Синтаксис Expression в КОМПАС-3D

```python
# Простое значение
variable.Expression = "150.0"

# Формула
variable.Expression = "H - 18.5"

# Условие (if)
variable.Expression = "if(L1<1500; 2; 3)"

# Вложенные условия
variable.Expression = "if(L1<1500; 2; if(L1<2000; 3; 4))"
```

**Синтаксис условий:**
- `if(условие; значение_если_да; значение_если_нет)`
- Разделитель: `;` (точка с запятой) или `,` (запятая) - зависит от версии
- Операторы: `<`, `>`, `<=`, `>=`, `=`, `<>`

---

## 4. Детали и сборки

### Работа со сборкой

```python
# Открыть сборку
doc3D = api5.Document3D
doc3D.Open(assembly_path, False)
time.sleep(2)

# Получить TopPart сборки
iDocument3D = api5.ActiveDocument3D
iPart_assembly = iDocument3D.GetPart(kompas6_constants_3d.pTop_Part)

# Получить количество деталей
parts_count = 0
for i in range(100):  # Максимум 100 деталей
    try:
        part = iPart_assembly.GetPart(i)
        if part:
            parts_count = i + 1
        else:
            break
    except:
        break

# Перебрать все детали
for i in range(parts_count):
    part = iPart_assembly.GetPart(i)
    if part:
        marking = part.marking  # Обозначение
        name = part.name        # Имя
        fileName = part.fileName # Путь к файлу
```

### Изменение marking (обозначения)

```python
# КРИТИЧНАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ для сохранения!
part.marking = "ZVD.LITE.150.145.001"

# 1. Update
part.Update()

# 2. RebuildModel
part.RebuildModel()

# 3. RebuildDocument (для сборки)
iDocument3D.RebuildDocument()
time.sleep(1)

# 4. Save
active_doc = api7.ActiveDocument
active_doc.Save()
time.sleep(1)

# 5. Close с сохранением
active_doc.Close(True)
time.sleep(1)
```

**⚠️ КРИТИЧНО:**
- Без `Update()` → изменения не применятся
- Без `RebuildModel()` → не сохранится
- Без `Save()` → потеряется при закрытии
- Нужна вся последовательность!

---

## 5. Экспорт и сохранение

### Экспорт чертежа в BMP/PNG

```python
# КРИТИЧНО: Сначала обновить чертеж!
from win32com.client import Dispatch

api5 = Dispatch("Kompas.Application.5")
doc2d = api5.ActiveDocument2D

# Rebuild чертежа
doc2d.ksRebuildDocument()
time.sleep(2)

# Сохранение
active_doc.Save()
time.sleep(1)

# Экспорт в растр
document_2d = api7.ActiveDocument

# Параметры
raster_params = document_2d.RasterFormatParam()
raster_params.Init()

try:
    raster_params.ColorBPP = 8  # 24 бита (цветной)
    raster_params.DPI = 300     # Разрешение
except:
    # Format может быть недоступен в некоторых версиях
    pass

# Экспорт (формат передается третьим параметром!)
format_code = 1  # 1=BMP, 2=PNG, 3=JPEG, 4=TIFF
success = document_2d.SaveAsToRasterFormat(output_path, raster_params, format_code)
```

**Важно:**
- `ksRebuildDocument()` ПЕРЕД экспортом!
- `format_code` передается ТРЕТЬИМ параметром
- Без Rebuild → пустой файл!

### Экспорт в DXF

```python
# ТОЛЬКО для 2D документов!
api5 = Dispatch("Kompas.Application.5")
doc2d = api5.ActiveDocument2D

# КРИТИЧНО: Rebuild + Save перед экспортом!
doc2d.ksRebuildDocument()
time.sleep(2)

active_doc.Save()
time.sleep(1)

# Экспорт (правильный метод!)
saved = doc2d.ksSaveToDXF(output_path)
```

**⚠️ НЕ ИСПОЛЬЗУЙТЕ:**
- `SaveAs(путь_с_dxf)` → создает ZIP, а не DXF!
- Правильно: `ksSaveToDXF()`

---

## 6. Частые проблемы и решения

### Проблема 1: "Marking не сохраняется"

```python
# ❌ НЕ РАБОТАЕТ:
part.marking = "новое"
active_doc.Save()

# ✅ РАБОТАЕТ:
part.marking = "новое"
part.Update()
part.RebuildModel()
iDocument3D.RebuildDocument()
active_doc.Save()
active_doc.Close(True)
```

### Проблема 2: "Экспорт PDF создает ZIP файлы"

```python
# ❌ НЕ РАБОТАЕТ:
active_doc.SaveAs(file_path + ".pdf")  # Создает ZIP!

# ✅ РАБОТАЕТ:
# Используйте SaveAsToRasterFormat для изображений
# Для PDF используйте внешний конвертер
```

### Проблема 3: "Детали не открываются программно"

```python
# ❌ ПРОБЛЕМА: .m3d файлы не всегда открываются через API

# ✅ РЕШЕНИЕ: Работайте через сборку
assembly = api5.Document3D
assembly.Open(assembly_path, False)
iPart = iDocument3D.GetPart(kompas6_constants_3d.pTop_Part)

# Получаем детали через сборку
for i in range(100):
    part = iPart.GetPart(i)  # Это работает!
```

### Проблема 4: "Изменения Expression откатываются"

```python
# ❌ ПРОБЛЕМА: Если переменная имеет гиперссылку

# ✅ РЕШЕНИЕ:
# Гиперссылки защищены API - нельзя изменить программно
# Варианты:
# 1. Удалить гиперссылки вручную в исходном проекте
# 2. Использовать PyWinAuto для автоматизации GUI
# 3. Работать БЕЗ гиперссылок (приложение само вычисляет)
```

### Проблема 5: "Дублирующиеся детали не обновляются"

```python
# Если деталь используется несколько раз в сборке:
# - Изменение файла детали обновит только первый экземпляр
# - Другие экземпляры берут данные из кэша

# ✅ РЕШЕНИЕ: Обновлять через сборку!
for i in range(parts_count):
    part = iPart.GetPart(i)
    part.marking = new_marking
    part.Update()
    part.RebuildModel()

# Затем сохранить сборку
iDocument3D.RebuildDocument()
active_doc.Save()
```

### Проблема: "Переменные с формулами не пересчитываются"

**Симптомы:**
- Обновили H в сборке на 150
- Переменная A1 имеет формулу `Expression = "H-A2"`
- Но A1.value остается старым (не пересчитывается)

**Причина:**
КОМПАС-3D **НЕ пересчитывает формулы автоматически** после `Update()`, `RebuildModel()`, `RebuildDocument()`!

**Решение:**
Рассчитывайте зависимые переменные **вручную в Python**:

```python
# Читаем все переменные из сборки
all_vars = {}
for i in range(200):
    var = var_collection.GetByIndex(i)
    if var:
        all_vars[var.name] = var.value

# КРИТИЧНО: Рассчитываем зависимые переменные ВРУЧНУЮ!
if 'A2' in all_vars:
    all_vars['A1'] = h - all_vars['A2']  # Не полагаемся на формулу!
    
if 'A1' in all_vars:
    all_vars['A4'] = all_vars['A1'] - 5
```

### Проблема: "Формулы в переменных стираются при обновлении"

**Симптомы:**
- Переменная A3 имела формулу `Expression = "A1-10.5"`
- После обновления через API: `Expression = "99"` (формула стерлась!)

**Причина:**
Установка `var.Expression = str(value)` **перезаписывает** формулу числом!

**Решение:**
Проверяйте наличие формулы **ПЕРЕД** обновлением:

```python
current_expr = var.Expression
has_formula = any(op in str(current_expr) for op in ['-', '+', '*', '/', 'if', '?'])
has_hyperlink = ':\\' in str(current_expr) or '|' in str(current_expr)

if has_hyperlink:
    # Удаляем гиперссылку
    var.Expression = str(new_value)
    var.value = new_value
elif has_formula:
    # НЕ ТРОГАЕМ формулу! Она пересчитается автоматически
    # после обновления базовых переменных (H, B1, L1)
    pass
else:
    # Простое число - обновляем
    var.Expression = str(new_value)
    var.value = new_value
```

### Проблема: "Переменные экземпляров (v1398_B3) перезаписывают значения"

**Симптомы:**
- В сборке есть переменные типа `v1398_B3 = 377.1`
- После копирования этих переменных в детали, они перезаписывают правильные значения

**Причина:**
КОМПАС-3D создает переменные вида `v[цифры]_[имя]` для **каждого экземпляра** детали в сборке. Они хранят **индивидуальные** значения и **не должны** копироваться в файлы деталей!

**Решение:**
Пропускайте эти переменные при копировании:

```python
for var_name, var_value in all_calculated_vars.items():
    # Пропускаем переменные экземпляров (v1398_B3, v2456_A1, и т.д.)
    if var_name.startswith('v') and '_' in var_name:
        prefix = var_name.split('_')[0]
        if prefix[1:].isdigit():  # v1398, v2456
            continue  # Пропускаем!
    
    # Обновляем переменную...
```

### Проблема: "Формулы в эскизах используют старые значения переменных"

**Симптомы:**
- В эскизе размер = `A1-20`
- Обновили A1 с 71.5 на 129.5
- Размер в эскизе = 51.5 (71.5-20), а не 109.5 (129.5-20)!

**Причина:**
Формула в эскизе **вычисляется при ОТКРЫТИИ файла** и использует значения переменных **на тот момент**!

**Решение:**
- **Переменную** (например, A3) установить в **0** или удалить
- **В эскизе** использовать формулу `A1-20` напрямую
- **НЕ создавать** переменную A3 с формулой - это конфликтует с эскизом!
- Формула в эскизе **автоматически пересчитается** при обновлении A1

---

## 7. Ограничения API

### ❌ ЧТО НЕ РАБОТАЕТ (проверено!):

1. **Гиперссылки**
   - Нельзя создать программно
   - Нельзя изменить `linkDocName` / `linkVarName`
   - Можно только читать (и то не во всех версиях)

2. **Создание переменных**
   - `var_collection.Add()` недоступен в некоторых версиях
   - Переменные нужно создавать вручную или через GUI

3. **Прямой PDF экспорт**
   - `SaveAs("файл.pdf")` создает ZIP архив
   - Нет прямого метода экспорта в PDF через API

4. **Файлы-источники в чертежах**
   - Путь к файлу-источнику вида хранится в `.cdw` (ZIP архив)
   - Программно изменить сложно
   - Лучше полуавтоматический режим (открыть + юзер нажимает кнопку)

5. **Открытие .m3d файлов**
   - Иногда API блокирует прямое открытие деталей
   - Лучше работать через сборку

6. **Контекстные связи (проецирование, совпадение и т.д.)**
   - API НЕ предоставляет методов для создания
   - Создаются ТОЛЬКО через GUI КОМПАС-3D
   - Решение: подготовить варианты деталей с разными связями
   - Приложение подменяет нужный вариант детали

### ✅ ЧТО РАБОТАЕТ НАДЕЖНО:

1. **Чтение и запись переменных**
   - `variable.value` и `variable.Expression` работают отлично

2. **Изменение marking**
   - С правильной последовательностью Update → Rebuild → Save

3. **Экспорт в растр**
   - BMP, PNG, JPEG, TIFF через `SaveAsToRasterFormat`

4. **Экспорт в DXF**
   - Через `ksSaveToDXF()` для 2D документов

5. **Работа со сборками**
   - `GetPart(index)` надежно работает
   - Изменение marking через сборку

---

## 8. Лучшие практики

### Архитектура приложения

```python
class BaseKompasComponent:
    """Базовый класс для всех компонентов"""
    
    def connect_to_kompas(self):
        """Подключение к КОМПАС"""
        pass
    
    def open_document(self, path):
        """Открытие документа"""
        pass
    
    def close_document(self, save=False):
        """Закрытие с опциональным сохранением"""
        pass

class VariablesUpdater(BaseKompasComponent):
    """Обновление переменных"""
    pass

class DesignationUpdater(BaseKompasComponent):
    """Переименование деталей"""
    pass
```

### Обработка ошибок

```python
try:
    # Работа с КОМПАС
    if not self.connect_to_kompas():
        return {'success': False, 'error': 'Подключение не удалось'}
    
    # Операции
    
    return {'success': True, 'data': результат}
    
except Exception as e:
    self.logger.error(f"Ошибка: {e}")
    return {'success': False, 'error': str(e)}
finally:
    # Закрываем документы
    try:
        api7.ActiveDocument.Close(False)
    except:
        pass
```

### Логирование

```python
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# В критичных местах:
logger.info(f"Открытие файла: {file_name}")
logger.warning(f"Деталь пропущена: {marking}")
logger.error(f"Ошибка: {e}")
```

---

## 9. Типичные задачи и решения

### Задача: Обновить переменные H, B1, L1 в сборке

```python
def update_assembly_variables(assembly_path, variables):
    """
    variables = {'H': 150, 'B1': 145, 'L1': 1400}
    """
    pythoncom.CoInitialize()
    try:
        api5 = Dispatch("Kompas.Application.5")
        api7 = Dispatch("Kompas.Application.7")
        
        # Открыть сборку
        api7.Documents.Open(assembly_path, False, True)
        time.sleep(2)
        
        # Получить переменные
        iDocument3D = api5.ActiveDocument3D
        iPart = iDocument3D.GetPart(kompas6_constants_3d.pTop_Part)
        var_collection = iPart.VariableCollection()
        
        # Обновить
        for var_name, var_value in variables.items():
            var = var_collection.GetByName(var_name)
            if var:
                var.value = float(var_value)
                var.Expression = str(var_value)
        
        # Сохранить (КРИТИЧНО!)
        iPart.Update()
        iPart.RebuildModel()
        iDocument3D.RebuildDocument()
        time.sleep(1)
        
        api7.ActiveDocument.Save()
        time.sleep(1)
        
        api7.ActiveDocument.Close(True)
        
        return {'success': True}
        
    finally:
        pythoncom.CoUninitialize()
```

### Задача: Переименовать все детали в сборке

```python
def rename_parts(assembly_path, base_name):
    """
    base_name = "ZVD.LITE.150.145"
    """
    # Открыть сборку
    # ...
    
    # Группировка по именам (одинаковые имена → один номер!)
    parts_by_name = {}
    
    for i in range(parts_count):
        part = iPart.GetPart(i)
        name = part.name.strip()
        marking = part.marking.strip()
        
        # Пропустить служебные
        if not marking or marking.startswith('-'):
            continue
        
        if name not in parts_by_name:
            parts_by_name[name] = []
        parts_by_name[name].append((i, part))
    
    # Переименовать с группировкой
    part_number = 1
    
    for name in sorted(parts_by_name.keys()):
        instances = parts_by_name[name]
        new_marking = f"{base_name}.{part_number:03d}"
        
        # ВСЕ экземпляры получают ОДИН номер!
        for idx, part_obj in instances:
            part_obj.marking = new_marking
            part_obj.Update()
            part_obj.RebuildModel()
        
        part_number += 1
    
    # Сохранить
    iDocument3D.RebuildDocument()
    active_doc.Save()
    active_doc.Close(True)
```

### Задача: Экспортировать все чертежи в BMP

```python
def export_drawings_to_bmp(project_path, output_folder):
    """Экспорт всех .cdw файлов"""
    
    drawing_files = list(Path(project_path).glob("*.cdw"))
    
    # Фильтр: пропускаем развертки
    regular_drawings = [f for f in drawing_files 
                       if "развертка" not in f.name.lower()]
    
    for drawing_file in regular_drawings:
        # Открыть
        api7.Documents.Open(str(drawing_file), False, True)
        time.sleep(2)
        
        # REBUILD обязательно!
        api5_doc2d = Dispatch("Kompas.Application.5").ActiveDocument2D
        if api5_doc2d:
            api5_doc2d.ksRebuildDocument()
            time.sleep(2)
        
        active_doc.Save()
        time.sleep(1)
        
        # Экспорт
        doc = api7.ActiveDocument
        raster_params = doc.RasterFormatParam()
        raster_params.Init()
        
        output_path = Path(output_folder) / (drawing_file.stem + ".bmp")
        
        # Формат передается третьим параметром!
        format_code = 1  # BMP
        success = doc.SaveAsToRasterFormat(str(output_path), raster_params, format_code)
        
        # Закрыть
        api7.ActiveDocument.Close(False)
        time.sleep(0.5)
```

---

## 10. Продвинутые техники

### Вычисление зависимых переменных

```python
# Если у вас формулы с зависимостями:
# A1 = H - A2
# A3 = A1 - 20

# Нужно вычислять в правильном порядке!

def calculate_all_variables(h, b1, l1):
    values = {}
    
    # 1. Входные
    values['H'] = h
    values['B1'] = b1
    values['L1'] = l1
    
    # 2. Константы
    values['A2'] = 18.5
    values['B2'] = 18
    
    # 3. Зависимые (порядок важен!)
    values['A1'] = values['H'] - values['A2']
    values['A'] = values['A1']
    values['A3'] = values['A1'] - 20
    values['A4'] = values['A1'] - 5
    
    values['B'] = values['B1']
    values['B3'] = values['B1'] - values['B2']*2 - 6.9
    
    values['L'] = values['L1']
    
    return values
```

### Условные переменные

```python
# В Python:
def calculate_conditional(l1):
    if l1 < 1500:
        return 2
    elif l1 < 2000:
        return 3
    elif l1 <= 2400:
        return 4
    else:
        return 5

# В КОМПАС Expression:
# "if(L1<1500; 2; if(L1<2000; 3; if(L1<=2400; 4; 5)))"
```

### Работа с файловой системой

```python
from pathlib import Path
import shutil

# Копирование проекта
source = Path("путь/к/источнику")
target = Path("путь/к/цели")

# Копировать все файлы
for file in source.iterdir():
    if file.is_file():
        shutil.copy2(file, target / file.name)

# Переименование файла сборки
old_file = target / "старое_имя.a3d"
new_file = target / "новое_имя.a3d"

if old_file.exists():
    old_file.rename(new_file)
```

---

## 11. Структура ZIP-архивов КОМПАС

### .m3d и .a3d файлы - это ZIP!

```python
import zipfile

# Проверка
with open(file_path, 'rb') as f:
    header = f.read(4)
    is_zip = header[:2] == b'PK'

# Чтение
with zipfile.ZipFile(file_path, 'r') as zf:
    contents = zf.read('Contents')  # Основные данные
    fileinfo = zf.read('FileInfo')
    metainfo = zf.read('MetaInfo')
```

**Файлы внутри:**
- `Contents` - основные данные модели (бинарные!)
- `FileInfo` - информация о файле
- `MetaInfo` - метаданные
- `Preview` - превью
- `SysInfo` - системная информация

**⚠️ ВНИМАНИЕ:**
- Данные в **бинарном формате**
- Прямое редактирование **ОПАСНО**
- Может повредить файл!

### .cdw файлы - тоже ZIP!

Структура похожа на .m3d, но с данными чертежа.

---

## 12. API версии и совместимость

### API 5 vs API 7

```python
# API 5 - низкоуровневый, для 3D
api5 = Dispatch("Kompas.Application.5")
doc3D = api5.Document3D
activeDoc3D = api5.ActiveDocument3D
doc2D = api5.ActiveDocument2D

# API 7 - высокоуровневый, для документов
api7 = Dispatch("Kompas.Application.7")
documents = api7.Documents
activeDoc = api7.ActiveDocument
```

**Когда использовать:**
- API 5: работа с переменными, 3D объектами, rebuild
- API 7: открытие/закрытие документов, параметры экспорта

**Часто нужны ОБА!**

---

## 13. Чек-лист для типичных задач

### ✅ Обновление переменных:
- [ ] CoInitialize()
- [ ] Подключиться к API
- [ ] Открыть документ
- [ ] Получить var_collection
- [ ] Обновить value и Expression
- [ ] Update() → RebuildModel() → RebuildDocument()
- [ ] Save()
- [ ] Close(True)
- [ ] CoUninitialize()

### ✅ Экспорт чертежа:
- [ ] Открыть чертеж
- [ ] ksRebuildDocument()
- [ ] Sleep(2)
- [ ] Save()
- [ ] SaveAsToRasterFormat() с format_code
- [ ] Проверить размер файла (не 0!)
- [ ] Close()

### ✅ Переименование деталей:
- [ ] Открыть сборку
- [ ] Получить все детали через GetPart(i)
- [ ] Группировать по именам
- [ ] Обновить marking для ВСЕХ экземпляров
- [ ] Update() для каждой
- [ ] RebuildDocument() для сборки
- [ ] Save() и Close(True)

---

## 14. Примеры готовых компонентов

### Базовый компонент

```python
import logging
import pythoncom
from win32com.client import Dispatch, gencache

class BaseKompasComponent:
    def __init__(self):
        self.application = None
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def connect_to_kompas(self):
        try:
            self.application = Dispatch("Kompas.Application.7")
            self.application.Visible = True
            return True
        except Exception as e:
            self.logger.error(f"Подключение: {e}")
            return False
    
    def open_document(self, path):
        try:
            doc = self.application.Documents.Open(path, False, True)
            time.sleep(2)
            return doc is not None
        except Exception as e:
            self.logger.error(f"Открытие: {e}")
            return False
```

---

## 15. Отладка и диагностика

### Просмотр всех свойств объекта

```python
# Для исследования объектов API
for attr in dir(объект):
    if not attr.startswith('_'):
        try:
            value = getattr(объект, attr)
            if not callable(value):
                print(f"{attr} = {value}")
        except:
            pass
```

### Проверка типа документа

```python
# Активный документ
active = api7.ActiveDocument

# Тип документа
doc_type = active.DocumentType
# 1 = фрагмент, 3 = спецификация, 4 = сборка, 5 = деталь, 6 = чертеж
```

---

## 16. Частые паттерны кода

### Закрытие всех открытых документов

```python
try:
    while True:
        doc = api7.ActiveDocument
        if doc:
            doc.Close(False)
            time.sleep(0.3)
        else:
            break
except:
    pass
```

### Поиск файлов проекта

```python
from pathlib import Path

project_path = Path("путь/к/проекту")

# Сборки
assemblies = list(project_path.glob("*.a3d"))

# Детали (без разверток)
parts = [f for f in project_path.glob("*.m3d") 
         if "развертка" not in f.name.lower()]

# Чертежи (без разверток)
drawings = [f for f in project_path.glob("*.cdw")
           if "развертка" not in f.name.lower()]

# Развертки
unfoldings = [f for f in project_path.glob("*.cdw")
             if "развертка" in f.name.lower()]
```

---

## 17. Форматы гиперссылок (только для чтения!)

### Формат Expression с гиперссылкой:

```
C:\путь\к\файлу.a3d|Имя документа|Имя переменной
```

Пример:
```
C:\Projects\ZVD.LITE.80\сборка.a3d|ZVD LITE 80|H
```

**Относительная гиперссылка:**
```
Expression = "H"  # Просто имя переменной
```
КОМПАС автоматически ищет H в родительской сборке!

---

## 18. Обходные пути для ограничений

### Гиперссылки → Вычисление в приложении

```python
# Вместо создания гиперссылок:
# 1. Приложение вычисляет все переменные
# 2. Обновляет их в сборке
# 3. Обновляет их в каждой детали

values = calculate_all_variables(h, b1, l1)

# Обновить сборку
update_assembly_variables(assembly_path, values)

# Обновить каждую деталь
for part_file in part_files:
    update_part_variables(part_file, values_for_part)
```

### PDF экспорт → Через растр + конвертер

```python
# 1. Экспорт в BMP/PNG
export_to_bmp(drawing, output)

# 2. Внешний конвертер
from PIL import Image
img = Image.open("output.bmp")
img.save("output.pdf")

# Или используйте img2pdf, reportlab и т.д.
```

---

## 19. Timing и delays

### Рекомендуемые задержки:

```python
# После открытия документа
time.sleep(2)

# После Rebuild
time.sleep(1)

# После Save
time.sleep(1)

# После Close
time.sleep(1)

# Между операциями с разными документами
time.sleep(0.5)
```

**Почему это важно:**
- КОМПАС-3D работает асинхронно
- API возвращает управление ДО завершения операции
- Без задержек → данные не успевают обновиться

---

## 20. Краткая шпаргалка (Quick Reference)

```python
# === ПОДКЛЮЧЕНИЕ ===
pythoncom.CoInitialize()
api5 = Dispatch("Kompas.Application.5")
api7 = Dispatch("Kompas.Application.7")
const3d = gencache.EnsureModule("{2CAF168C-7961-4B90-9DA2-701419BEEFE3}", 0, 1, 0).constants

# === ОТКРЫТИЕ ===
api7.Documents.Open(path, False, True)
time.sleep(2)

# === ПЕРЕМЕННЫЕ ===
iDoc3D = api5.ActiveDocument3D
iPart = iDoc3D.GetPart(const3d.pTop_Part)
var_coll = iPart.VariableCollection()
var = var_coll.GetByName('H')
var.value = 150
var.Expression = "150"

# === СОХРАНЕНИЕ ===
iPart.Update()
iPart.RebuildModel()
iDoc3D.RebuildDocument()
api7.ActiveDocument.Save()
api7.ActiveDocument.Close(True)

# === ЭКСПОРТ BMP ===
doc2d = api5.ActiveDocument2D
doc2d.ksRebuildDocument()
active_doc.Save()
raster = active_doc.RasterFormatParam()
raster.Init()
active_doc.SaveAsToRasterFormat(path, raster, 1)  # 1=BMP

# === ЭКСПОРТ DXF ===
doc2d.ksSaveToDXF(path)

# === ЗАВЕРШЕНИЕ ===
pythoncom.CoUninitialize()
```

---

## 21. Функция "Копировать объекты" (для гиперссылок)

### Проблема:
Гиперссылки нельзя переназначить программно через API.

### Решение через GUI:

```
1. Открыть сборку в КОМПАС-3D
2. Ctrl+A (выбрать все объекты)
3. ПКМ → "Копировать объекты"
4. Включить опцию "Переназначить ссылки"
5. Вставить в новую сборку
6. Сохранить с новым именем
```

**Преимущества:**
- ✅ Автоматически обновляет ВСЕ гиперссылки
- ✅ Сохраняет связи между объектами
- ✅ Работает с любыми типами ссылок
- ✅ Не требует программирования

**Применение:**
- Копирование параметрических сборок с гиперссылками
- Создание вариантов проектов
- Переназначение ссылок после переименования файлов

**Ограничение:**
- Полуавтоматический процесс (требует действий в GUI)
- Можно автоматизировать через PyWinAuto

---

## 22. Экспорт разверток листового металла

### Что НЕ работает через API:

```python
# ❌ Автоматическое создание развертки из 3D модели
# API КОМПАС-3D НЕ предоставляет методов для:
# - Автоматического расчета развертки
# - Программного создания чертежа развертки
# - Развертывания листового металла
```

### Что РАБОТАЕТ:

```python
# ✅ Экспорт ГОТОВЫХ чертежей разверток

# 1. Чертеж развертки уже создан вручную в КОМПАС
# 2. Экспортируем программно:

api5 = Dispatch("Kompas.Application.5")
doc2d = api5.ActiveDocument2D

# Обновляем чертеж
doc2d.ksRebuildDocument()
time.sleep(2)

active_doc.Save()
time.sleep(1)

# Экспорт в DXF
doc2d.ksSaveToDXF(output_path)
```

**Рекомендация:**
1. Создавайте чертежи разверток в КОМПАС вручную (один раз)
2. Сохраняйте их в образцовом проекте
3. При копировании проекта они копируются автоматически
4. Программно обновляйте и экспортируйте в DXF

**НЕ пытайтесь:**
- Генерировать развертки программно
- Создавать чертежи разверток через API
- Автоматически разворачивать листовой металл

---

## 9. Экспорт чертежей в PDF

### ❌ Проблема: Прямой экспорт в PDF НЕ РАБОТАЕТ

```python
# ❌ НЕ РАБОТАЕТ!
active_doc.SaveAs("файл.pdf")  
# Результат: создается ZIP файл, а не PDF!

# ❌ ТОЖЕ НЕ РАБОТАЕТ!
# SaveAsToRasterFormat не поддерживает PDF
```

### ✅ Работающее решение: PNG/BMP → PDF

```python
from PIL import Image

# 1. Экспорт в PNG высокого качества
raster_params = active_doc.RasterFormatParam()
raster_params.Init()
raster_params.DPI = 300

active_doc.SaveAsToRasterFormat("чертеж.png", raster_params, 2)  # 2=PNG

# 2. Конвертация PNG → PDF
img = Image.open("чертеж.png")
img.save("чертеж.pdf", "PDF", resolution=300.0)
```

### Альтернатива: img2pdf (быстрее)

```python
import img2pdf

with open("чертеж.pdf", "wb") as f:
    f.write(img2pdf.convert("чертеж.png"))
```

---

## 10. Расчет площадей разверток

### Задача: Автоматический расчет площадей листового металла

```python
from components.advanced_area_calculator import AdvancedAreaCalculator
from components.advanced_pdf_generator import AdvancedPDFGenerator

# 1. Расчет площадей с учетом количества деталей
calc = AdvancedAreaCalculator()
result = calc.calculate_total_areas("C:\\Projects\\ZVD.LITE.140.145.1400")

print(f"Общая площадь: {result['total_area_with_quantity']:.4f} м²")

# 2. Генерация PDF отчета
gen = AdvancedPDFGenerator()
pdf = gen.generate_detailed_report(
    project_name="ZVD.LITE.140.145.1400",
    area_data=result,
    output_path="Расчет_площадей.pdf"
)
```

### Как это работает:

1. **Анализ сборки** → подсчет количества деталей
2. **Экспорт чертежей во временный DXF** → точные габариты
3. **Чтение DXF через ezdxf** → ширина и высота
4. **Интеллектуальное сопоставление** развертка ↔ деталь (с учетом падежей!)
5. **Расчет площадей** → ширина × высота / 1_000_000 (мм² → м²)
6. **Генерация PDF** → профессиональный отчет с таблицей

### Пример извлечения габаритов из DXF:

```python
import ezdxf

doc = ezdxf.readfile("развертка.dxf")
msp = doc.modelspace()

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

width = abs(max_x - min_x)
height = abs(max_y - min_y)
area_m2 = width * height / 1_000_000
```

### Интеллектуальное сопоставление деталей:

Проблема: названия в разных падежах
- Сборка: "Крышка декоративная" (именительный)
- Чертеж: "Развертка крышки декоративной" (родительный)

Решение: используем корни слов
```python
# "крышк" → "крышка", "крышки", "крышку" и тд
if "крышк" in clean_name and "крышк" in detail_name:
    return quantity
```

---

## 📝 ОБНОВЛЕНИЯ

### v1.3 (2025-10-12)
- Добавлено: Каскадная пересборка (3 цикла для контекстных связей)
- Добавлено: Автообновление чертежей (открыть → пересобрать → сохранить)
- Добавлено: Тернарный оператор `?:` в формулах (альтернатива `if()`)
- Добавлено: Автоматическое чтение переменных массивов

### v1.2 (2025-10-10)
- Добавлено: Экспорт чертежей в PDF через PNG/BMP
- Добавлено: Расчет площадей разверток с учетом количества
- Добавлено: Интеллектуальное сопоставление деталей (с падежами)
- Добавлено: Генерация PDF отчетов с таблицами

### v1.1 (2025-10-10)
- Добавлено: Функция "Копировать объекты" для гиперссылок
- Добавлено: Работа с развертками листового металла
- Уточнено: Что можно и что нельзя с развертками

### v1.0 (2025-10-09)
- Базовые знания по API 5/7
- Работа с переменными
- Экспорт в растр и DXF
- Переименование деталей с группировкой
- Ограничения гиперссылок
- Условные переменные
- Работа с массивами

---

## 🎯 Для AI-ассистентов

При работе с КОМПАС-3D:
1. ВСЕГДА используйте `pythoncom.CoInitialize/Uninitialize`
2. Добавляйте `time.sleep()` после операций
3. Используйте правильную последовательность Update → Rebuild → Save
4. Не пытайтесь создавать гиперссылки программно
5. Группируйте одинаковые детали при переименовании
6. Используйте `ksSaveToDXF()` для DXF экспорта
7. Делайте `ksRebuildDocument()` перед экспортом чертежей
8. Для PDF используйте PNG/BMP + конвертацию (прямой экспорт НЕ РАБОТАЕТ!)
9. Для расчета площадей используйте DXF + ezdxf
10. Учитывайте падежи при сопоставлении названий (используйте корни слов)
11. **КРИТИЧНО:** После обновления переменных делайте **КАСКАДНУЮ пересборку** (2-3 раза):
    - 1-я пересборка → геометрия
    - 2-я пересборка → контекстные связи (отверстия)
    - 3-я пересборка → финальная стабилизация
12. **КРИТИЧНО:** При обновлении переменных ОБЯЗАТЕЛЬНО устанавливайте флаг `External=True`:
    ```python
    var.value = new_value
    var.Expression = str(new_value)
    var.External = True  # БЕЗ ЭТОГО переменная НЕ ВИДНА из других деталей!
    ```
13. Для обновления чертежей достаточно открыть → `ksRebuildDocument()` → сохранить

---

## ✅ БАЗА ЗНАНИЙ ГОТОВА!

Этот документ содержит **весь опыт** работы с КОМПАС-3D API.

**Используйте как справочник** для любых задач автоматизации КОМПАС-3D!

