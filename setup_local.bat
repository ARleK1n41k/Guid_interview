@echo off
echo ========================================
echo Настройка Telegram бота для локального запуска
echo ========================================
echo.

if exist .env (
    echo Файл .env уже существует!
    echo.
    pause
    exit /b
)

echo Создаю файл .env...
echo BOT_TOKEN=8534429029:AAFhc4gNNTco5hu3jB9xa3zfSm_hUWtevR4 > .env

if exist .env (
    echo ✓ Файл .env успешно создан!
    echo.
    echo Теперь вы можете запустить бота: python bot.py
) else (
    echo ✗ Ошибка при создании файла .env
    echo.
    echo Создайте файл .env вручную и добавьте:
    echo BOT_TOKEN=8534429029:AAFhc4gNNTco5hu3jB9xa3zfSm_hUWtevR4
)

echo.
pause

