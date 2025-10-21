@echo off
chcp 65001 >nul
echo ═══════════════════════════════════════════════════════════
echo   СБОРКА EXE - ZVD Расчет площадей разверток
echo ═══════════════════════════════════════════════════════════
echo.

echo Шаг 1: Проверка зависимостей...
python -c "import PyInstaller" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo PyInstaller не установлен. Устанавливаю...
    pip install pyinstaller
)

echo.
echo Шаг 2: Сборка EXE файла...
echo.

pyinstaller --noconfirm ^
    --onefile ^
    --windowed ^
    --name "ZVD_Площади" ^
    --icon=NONE ^
    --add-data "README.md;." ^
    --add-data "ИНСТРУКЦИЯ_ДЛЯ_ЦЕХА.md;." ^
    --hidden-import=ezdxf ^
    --hidden-import=reportlab ^
    --hidden-import=openpyxl ^
    --hidden-import=tkinter ^
    gui_calculator.py

echo.
echo ═══════════════════════════════════════════════════════════
if exist "dist\ZVD_Площади.exe" (
    echo ✓ УСПЕХ! EXE создан:
    echo   dist\ZVD_Площади.exe
    echo.
    echo Размер:
    dir dist\ZVD_Площади.exe | find "ZVD"
    echo.
    echo ═══════════════════════════════════════════════════════════
    echo.
    echo ГОТОВО К ИСПОЛЬЗОВАНИЮ!
    echo.
    echo Скопируйте файл dist\ZVD_Площади.exe на компьютер цеха
    echo Двойной клик для запуска - Python НЕ ТРЕБУЕТСЯ!
    echo.
) else (
    echo ✗ ОШИБКА: EXE не создан
    echo Проверьте лог выше
)

echo.
pause





