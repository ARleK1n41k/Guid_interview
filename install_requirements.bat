@echo off
chcp 65001 >nul
echo ========================================
echo Установка зависимостей для Telegram бота
echo ========================================
echo.

echo [1/4] Обновляю pip...
python.exe -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo Ошибка при обновлении pip
    pause
    exit /b 1
)

echo [2/4] Устанавливаю python-dotenv...
python.exe -m pip install python-dotenv
if errorlevel 1 (
    echo Ошибка при установке python-dotenv
    pause
    exit /b 1
)

echo [3/4] Устанавливаю pandas (предкомпилированная версия)...
python.exe -m pip install pandas
if errorlevel 1 (
    echo Попытка установить pandas с предкомпилированными wheels...
    python.exe -m pip install --only-binary :all: pandas
    if errorlevel 1 (
        echo Ошибка при установке pandas
        echo Попробуйте установить Microsoft C++ Build Tools
        pause
        exit /b 1
    )
)

echo [4/4] Устанавливаю openpyxl и python-telegram-bot...
python.exe -m pip install openpyxl python-telegram-bot
if errorlevel 1 (
    echo Ошибка при установке openpyxl или python-telegram-bot
    pause
    exit /b 1
)

echo.
echo ========================================
echo Проверка установки...
echo ========================================
echo.

python.exe -c "import telegram; import pandas; import openpyxl; from dotenv import load_dotenv; print('Все модули установлены успешно!')"

if %errorlevel% equ 0 (
    echo.
    echo [OK] Все зависимости установлены успешно!
    echo.
    echo Теперь вы можете запустить бота: python bot.py
) else (
    echo.
    echo [ОШИБКА] Некоторые модули не установлены
    echo.
    echo Попробуйте установить вручную:
    echo   python.exe -m pip install python-dotenv pandas openpyxl python-telegram-bot
)

echo.
pause

