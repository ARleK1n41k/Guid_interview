# 🚀 Простая установка на Windows

## Быстрое решение проблемы с pandas

Если вы видите ошибку про Microsoft Visual C++ 14.0, выполните следующие команды **по порядку**:

### Способ 1: Автоматическая установка (Рекомендуется)

1. **Запустите файл `install_requirements.bat`**
   - Просто дважды кликните на файл
   - Скрипт автоматически установит все зависимости

### Способ 2: Ручная установка через Command Prompt

Откройте **Command Prompt** (cmd, не PowerShell!) и выполните:

```cmd
python.exe -m pip install --upgrade pip
python.exe -m pip install python-dotenv
python.exe -m pip install pandas
python.exe -m pip install openpyxl python-telegram-bot
```

### Способ 3: Если pandas все еще не устанавливается

Попробуйте установить более новую версию pandas:

```cmd
python.exe -m pip install --upgrade pip
python.exe -m pip install python-dotenv
python.exe -m pip install "pandas>=2.1.0"
python.exe -m pip install openpyxl python-telegram-bot
```

## ✅ Проверка установки

После установки проверьте:

```cmd
python.exe -c "import telegram; import pandas; import openpyxl; from dotenv import load_dotenv; print('OK')"
```

Если выводится "OK" - все установлено правильно!

## 🚀 Запуск бота

1. Создайте файл `.env` в папке проекта:
   ```
   BOT_TOKEN=8534429029:AAFhc4gNNTco5hu3jB9xa3zfSm_hUWtevR4
   ```

2. Запустите бота:
   ```cmd
   python bot.py
   ```

## ❓ Проблемы?

### "ModuleNotFoundError: No module named 'dotenv'"

Установите отдельно:
```cmd
python.exe -m pip install python-dotenv
```

### "error: Microsoft Visual C++ 14.0 or greater is required"

**Решение 1:** Используйте более новую версию pandas:
```cmd
python.exe -m pip install "pandas>=2.1.0"
```

**Решение 2:** Установите предкомпилированную версию:
```cmd
python.exe -m pip install --only-binary :all: pandas
```

**Решение 3:** Установите Microsoft C++ Build Tools:
- Скачайте: https://visualstudio.microsoft.com/visual-cpp-build-tools/
- Установите "C++ build tools"
- Перезагрузите компьютер
- Попробуйте снова: `python.exe -m pip install pandas`

### Другие проблемы

Если ничего не помогает:
1. Обновите pip: `python.exe -m pip install --upgrade pip`
2. Установите зависимости по одной
3. Убедитесь, что используете Python 3.11+

---

**Самый простой способ:** Запустите `install_requirements.bat` и следуйте инструкциям!

