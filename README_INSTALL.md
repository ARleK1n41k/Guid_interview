# 📦 Установка зависимостей

## 🪟 Windows - Быстрое решение

### Вариант 1: Автоматическая установка (Самый простой)

1. **Запустите `install_requirements.bat`**
   - Дважды кликните на файл
   - Скрипт установит все зависимости автоматически

### Вариант 2: Ручная установка

Откройте **Command Prompt** (cmd) и выполните:

```cmd
python.exe -m pip install --upgrade pip
python.exe -m pip install python-dotenv pandas openpyxl python-telegram-bot
```

### Вариант 3: Если возникает ошибка про Visual C++

Установите более новую версию pandas:

```cmd
python.exe -m pip install --upgrade pip
python.exe -m pip install python-dotenv
python.exe -m pip install "pandas>=2.1.0"
python.exe -m pip install openpyxl python-telegram-bot
```

## ✅ Проверка

После установки проверьте:

```cmd
python.exe -c "import telegram; import pandas; import openpyxl; from dotenv import load_dotenv; print('OK')"
```

Если выводится "OK" - все готово!

## 🚀 Запуск

1. Создайте файл `.env`:
   ```
   BOT_TOKEN=8534429029:AAFhc4gNNTco5hu3jB9xa3zfSm_hUWtevR4
   ```

2. Запустите бота:
   ```cmd
   python bot.py
   ```

## 📚 Подробные инструкции

- **Простая установка:** См. `INSTALL_SIMPLE.md`
- **Решение проблем:** См. `INSTALL_WINDOWS.md`

---

**Рекомендация:** Запустите `install_requirements.bat` - это самый простой способ!

