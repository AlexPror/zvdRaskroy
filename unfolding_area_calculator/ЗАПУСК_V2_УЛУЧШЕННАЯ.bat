@echo off
chcp 65001 >nul
echo ╔═══════════════════════════════════════════════════════╗
echo ║  ZVD - Расчет площадей v2.0 (УЛУЧШЕННАЯ)            ║
echo ║  С оптимизацией раскроя и учетом обрезков           ║
echo ╚═══════════════════════════════════════════════════════╝
echo.

echo [1/2] Запуск программы...
python gui_calculator_enhanced.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Ошибка запуска!
    echo.
    echo Возможные причины:
    echo   - Python не установлен
    echo   - Не установлены зависимости
    echo.
    echo Решение:
    echo   pip install rectpack openpyxl reportlab ezdxf
    echo.
    pause
)

