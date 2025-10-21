@echo off
chcp 65001 > nul
title Build EXE for v2.0

echo ═══════════════════════════════════════════════════
echo   📦 СОЗДАНИЕ EXE ДЛЯ ЦЕХА (v2.0)
echo ═══════════════════════════════════════════════════
echo.

echo 📋 Проверка PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo ❌ PyInstaller не установлен
    echo 📥 Устанавливаю PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo ✗ Ошибка установки PyInstaller
        pause
        exit /b 1
    )
    echo ✓ PyInstaller установлен
) else (
    echo ✓ PyInstaller найден
)
echo.

echo 🔧 Создание .exe файла...
echo    Это может занять 2-3 минуты...
echo.

pyinstaller ^
    --onefile ^
    --windowed ^
    --name="Раскрой_Деталей_v2.0" ^
    --icon=NONE ^
    --add-data "components;components" ^
    --hidden-import=tkinter ^
    --hidden-import=tkinter.ttk ^
    --hidden-import=tkinter.messagebox ^
    --hidden-import=tkinter.filedialog ^
    --hidden-import=ezdxf ^
    --hidden-import=rectpack ^
    --hidden-import=reportlab ^
    --hidden-import=openpyxl ^
    --hidden-import=PIL ^
    --hidden-import=win32com ^
    --hidden-import=pathlib ^
    --exclude-module=PyQt5 ^
    --exclude-module=PyQt6 ^
    --exclude-module=matplotlib ^
    --exclude-module=pandas ^
    --exclude-module=scipy ^
    --exclude-module=IPython ^
    --exclude-module=jupyter ^
    --collect-all reportlab ^
    --collect-all ezdxf ^
    unfolding_area_calculator/gui_calculator_enhanced.py

if errorlevel 1 (
    echo.
    echo ✗ Ошибка создания EXE
    pause
    exit /b 1
)

echo.
echo ═══════════════════════════════════════════════════
echo   ✅ EXE ФАЙЛ СОЗДАН!
echo ═══════════════════════════════════════════════════
echo.
echo 📁 Файл находится в: dist\Раскрой_Деталей_v2.0.exe
echo 💾 Размер: ~50-100 MB
echo.
echo 📋 ЧТО ДЕЛАТЬ ДАЛЬШЕ:
echo    1. Скопируйте dist\Раскрой_Деталей_v2.0.exe на компьютер в цеху
echo    2. Запустите двойным кликом (Python не нужен!)
echo    3. Готово!
echo.
echo ⚠️ ВАЖНО:
echo    • Сохраните исходники Python для дальнейшей разработки
echo    • EXE нельзя редактировать - только пересобирать
echo    • Для v3.0 будет новый EXE
echo.

pause

echo.
echo 🚀 Открыть папку dist?
pause
explorer dist

