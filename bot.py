import logging
import pandas as pd
import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telegram.error import BadRequest
import re
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния разговора
(START, RESPONDENT_INFO, DAY_MAP, PAIN_POINTS, PAIN_POINTS_OTHER, REGULAR_PROBLEMS, 
 PAIN_NAME, PAIN_CASE, PAIN_REASON, PAIN_EMOTION, PAIN_SCORE,
 MAGIC_WAND, INSIGHTS_SURPRISE, INSIGHTS_NEEDS, INSIGHTS_FOOD, INSIGHTS_PAY) = range(16)

# Хранилище данных
interviews = {}
all_interviews = []  # Глобальная база всех интервью

# Константы для кнопок
PAIN_POINT_OPTIONS = [
    ["Спешка между парами", "Длинные очереди"],
    ["Нехватка времени на обед", "Проблемы с расписанием"],
    ["Пропустить"]
]

EMOTION_OPTIONS = [
    ["Раздражение", "Злость", "Бессилие"],
    ["Усталость", "Тревога", "Другое"]
]

class InterviewData:
    """Класс для хранения данных интервью"""
    def __init__(self):
        self.respondent_id = None
        self.date = None
        self.duration = None
        self.day_description = ""
        self.pain_points = []
        self.main_pains = ""
        self.most_annoying = ""
        self.pain_analysis = []
        self.magic_wand = ""
        self.insights = {
            "surprise": "",
            "hidden_needs": "",
            "food_signals": "",
            "willingness_to_pay": ""
        }

def escape_markdown(text):
    """Экранирует специальные символы Markdown"""
    if not text:
        return ""
    # Экранируем символы, которые могут сломать Markdown
    special_chars = ['*', '_', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = str(text).replace(char, f'\\{char}')
    return text

def safe_markdown_text(text, parse_mode='Markdown'):
    """Безопасная отправка текста с Markdown"""
    try:
        # Пытаемся отправить с Markdown
        return text, parse_mode
    except:
        # Если не получается, убираем форматирование
        return text, None

def save_to_global_database(interview):
    """Сохраняем интервью в общую базу"""
    global all_interviews
    
    try:
        # Преобразуем данные в удобный формат
        interview_data = {
            'Респондент': interview.respondent_id or '',
            'Дата': interview.date or '',
            'Описание_дня': interview.day_description or '',
            'Точки_напряжения': ', '.join(interview.pain_points) if interview.pain_points else '',
            'Основные_проблемы': interview.main_pains or '',
            'Самая_раздражающая': interview.most_annoying or '',
            'Волшебная_палочка': interview.magic_wand or '',
            'Что_удивило': interview.insights.get('surprise', '') or '',
            'Скрытые_потребности': interview.insights.get('hidden_needs', '') or '',
            'Сигналы_о_еде': interview.insights.get('food_signals', '') or '',
            'Готовность_платить': interview.insights.get('willingness_to_pay', '') or '',
            'Время_записи': datetime.now()
        }
        
        # Добавляем анализ болей (до 10 болей для удобства)
        max_pains = 10
        for i, pain in enumerate(interview.pain_analysis[:max_pains], 1):
            interview_data[f'Боль_{i}_Название'] = pain.get('name', '') or ''
            interview_data[f'Боль_{i}_Оценка'] = pain.get('score', 0) or 0
            interview_data[f'Боль_{i}_Эмоция'] = pain.get('emotion', '') or ''
            interview_data[f'Боль_{i}_Случай'] = pain.get('last_case', '') or ''
            interview_data[f'Боль_{i}_Причина'] = pain.get('reason', '') or ''
        
        all_interviews.append(interview_data)
        logger.info(f"Интервью респондента {interview.respondent_id} сохранено в базу")
        
        # Автосохранение в файл
        save_all_to_excel()
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении интервью в базу: {e}", exc_info=True)
        raise

def save_all_to_excel():
    """Сохраняем все данные в Excel"""
    global all_interviews
    
    if not all_interviews:
        logger.warning("Нет данных для сохранения в Excel")
        return None
    
    try:
        df = pd.DataFrame(all_interviews)
        
        # Сортируем по времени записи
        if 'Время_записи' in df.columns:
            df = df.sort_values('Время_записи', ascending=True)
        
        # Сохраняем в файл
        filename = "все_интервью.xlsx"
        df.to_excel(filename, index=False, engine='openpyxl')
        
        logger.info(f"Данные сохранены в {filename}, всего записей: {len(all_interviews)}")
        return filename
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении в Excel: {e}", exc_info=True)
        return None

def get_user_interview(user_id):
    """Получает интервью пользователя или создает новое"""
    if user_id not in interviews:
        interviews[user_id] = InterviewData()
    return interviews[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало интервью"""
    user_id = update.message.from_user.id
    
    # Если уже есть активное интервью, предупреждаем
    if user_id in interviews:
        await update.message.reply_text(
            "⚠️ У вас уже есть активное интервью.\n"
            "Начинаю новое интервью. Старые данные будут потеряны.\n\n"
            "Введи номер респондента:",
            reply_markup=ReplyKeyboardRemove()
        )
    
    # Создаем новое интервью
    interviews[user_id] = InterviewData()
    
    try:
        await update.message.reply_text(
            "🎓 Исследование студенческого дня\n\n"
            "Привет! Я помогу провести интервью о студенческом дне.\n"
            "Давай начнем!\n\n"
            "Введи номер респондента:",
            reply_markup=ReplyKeyboardRemove()
        )
    except Exception as e:
        logger.error(f"Ошибка в start: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз.")
        return ConversationHandler.END
    
    return RESPONDENT_INFO

async def respondent_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение номера респондента"""
    user_id = update.message.from_user.id
    
    try:
        interview = get_user_interview(user_id)
        interview.respondent_id = update.message.text.strip()
        interview.date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        await update.message.reply_text(
            "📝 Карта дня\n\n"
            "Опиши подробно вчерашний учебный день респондента:"
        )
        
        return DAY_MAP
        
    except Exception as e:
        logger.error(f"Ошибка в respondent_info: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз или используйте /cancel")
        return ConversationHandler.END

async def day_map(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Описание дня"""
    user_id = update.message.from_user.id
    
    try:
        interview = get_user_interview(user_id)
        interview.day_description = update.message.text.strip()
        
        keyboard = PAIN_POINT_OPTIONS.copy()
        keyboard.insert(-1, ["Другое"])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "⚡ Точки напряжения\n\n"
            "Какие проблемы выявились в описании дня?\n"
            "Можно выбрать несколько.",
            reply_markup=reply_markup
        )
        
        return PAIN_POINTS
        
    except Exception as e:
        logger.error(f"Ошибка в day_map: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз или используйте /cancel")
        return ConversationHandler.END

async def pain_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка точек напряжения"""
    user_id = update.message.from_user.id
    choice = update.message.text.strip()
    
    try:
        interview = get_user_interview(user_id)
        
        # Обработка специальных команд
        if choice == "Продолжить":
            return await regular_problems_start(update, context)
        elif choice == "Выбрать еще":
            keyboard = PAIN_POINT_OPTIONS.copy()
            keyboard.insert(-1, ["Другое"])
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text("Выбери еще проблемы:", reply_markup=reply_markup)
            return PAIN_POINTS
        elif choice == "Другое":
            await update.message.reply_text(
                "Опиши другие проблемы:",
                reply_markup=ReplyKeyboardRemove()
            )
            return PAIN_POINTS_OTHER
        elif choice == "Пропустить":
            return await regular_problems_start(update, context)
        else:
            # Добавляем выбранную проблему
            if choice not in interview.pain_points:
                interview.pain_points.append(choice)
            
            # Показываем текущий список и предлагаем продолжить
            current_points = "\n".join([f"• {p}" for p in interview.pain_points])
            
            keyboard = [["Выбрать еще", "Продолжить"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            
            await update.message.reply_text(
                f"✅ Добавлено: {choice}\n\n"
                f"Текущие проблемы:\n{current_points}\n\n"
                f"Выбери действие:",
                reply_markup=reply_markup
            )
            return PAIN_POINTS
            
    except Exception as e:
        logger.error(f"Ошибка в pain_points: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз или используйте /cancel")
        return ConversationHandler.END

async def pain_points_other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода других проблем"""
    user_id = update.message.from_user.id
    
    try:
        interview = get_user_interview(user_id)
        other_text = update.message.text.strip()
        
        if other_text and other_text not in interview.pain_points:
            interview.pain_points.append(f"Другое: {other_text}")
        
        # Показываем список и предлагаем продолжить
        current_points = "\n".join([f"• {p}" for p in interview.pain_points])
        
        keyboard = [["Выбрать еще", "Продолжить"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            f"✅ Добавлено: {other_text}\n\n"
            f"Текущие проблемы:\n{current_points}\n\n"
            f"Выбери действие:",
            reply_markup=reply_markup
        )
        
        return PAIN_POINTS
        
    except Exception as e:
        logger.error(f"Ошибка в pain_points_other: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз или используйте /cancel")
        return ConversationHandler.END

async def regular_problems_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало раздела регулярных проблем"""
    try:
        await update.message.reply_text(
            "😫 Регулярные проблемы\n\n"
            "Какие основные 'боли' бывают в учебные дни?",
            reply_markup=ReplyKeyboardRemove()
        )
        return REGULAR_PROBLEMS
    except Exception as e:
        logger.error(f"Ошибка в regular_problems_start: {e}", exc_info=True)
        return ConversationHandler.END

async def regular_problems(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Основные боли"""
    user_id = update.message.from_user.id
    
    try:
        interview = get_user_interview(user_id)
        interview.main_pains = update.message.text.strip()
        
        await update.message.reply_text(
            "💢 Самая раздражающая проблема\n\n"
            "Какая проблема раздражает больше всего?"
        )
        
        return PAIN_NAME
        
    except Exception as e:
        logger.error(f"Ошибка в regular_problems: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз или используйте /cancel")
        return ConversationHandler.END

async def pain_analysis_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода названия боли или команды"""
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    text_lower = text.lower()
    
    try:
        interview = get_user_interview(user_id)
        
        # Проверяем команды для перехода дальше
        if text_lower in ['дальше', 'продолжить', 'next', '➡️', 'пропустить', 'skip']:
            # Если еще не было добавлено ни одной боли, сохраняем most_annoying как первую
            if not interview.pain_analysis and interview.most_annoying:
                # Создаем простую запись о боли
                interview.pain_analysis.append({
                    'name': interview.most_annoying,
                    'last_case': '',
                    'reason': '',
                    'emotion': '',
                    'score': 0
                })
            return await magic_wand_start(update, context)
        
        # Если не команда, то это название новой боли
        pain_name = text
        if not interview.most_annoying:
            interview.most_annoying = pain_name
        
        # Инициализируем текущую боль
        context.user_data['current_pain'] = {
            'name': pain_name,
            'last_case': '',
            'reason': '',
            'emotion': '',
            'score': 0
        }
        
        await update.message.reply_text(
            f"📝 Боль: {pain_name}\n\n"
            "Опиши последний случай (когда и где):"
        )
        
        return PAIN_CASE
        
    except Exception as e:
        logger.error(f"Ошибка в pain_analysis_name: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз или используйте /cancel")
        return ConversationHandler.END

async def pain_analysis_case(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем описание случая"""
    try:
        if 'current_pain' not in context.user_data:
            context.user_data['current_pain'] = {}
        
        context.user_data['current_pain']['last_case'] = update.message.text.strip()
        
        await update.message.reply_text(
            "❓ Почему было тяжело?\n\n"
            "Что именно вызывало сложности?"
        )
        
        return PAIN_REASON
        
    except Exception as e:
        logger.error(f"Ошибка в pain_analysis_case: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз или используйте /cancel")
        return ConversationHandler.END

async def pain_analysis_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем причину сложностей"""
    try:
        if 'current_pain' not in context.user_data:
            context.user_data['current_pain'] = {}
        
        context.user_data['current_pain']['reason'] = update.message.text.strip()
        
        keyboard = [row[:] for row in EMOTION_OPTIONS]  # Копируем список
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "😔 Какая это была эмоция?",
            reply_markup=reply_markup
        )
        
        return PAIN_EMOTION
        
    except Exception as e:
        logger.error(f"Ошибка в pain_analysis_reason: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз или используйте /cancel")
        return ConversationHandler.END

async def pain_analysis_emotion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем эмоцию"""
    try:
        if 'current_pain' not in context.user_data:
            context.user_data['current_pain'] = {}
        
        emotion_text = update.message.text.strip()
        
        # Если выбрано "Другое", просим описать
        if emotion_text == "Другое":
            await update.message.reply_text(
                "Опиши эмоцию своими словами:",
                reply_markup=ReplyKeyboardRemove()
            )
            return PAIN_EMOTION
        
        context.user_data['current_pain']['emotion'] = emotion_text
        
        keyboard = [
            [str(i) for i in range(1, 6)],
            [str(i) for i in range(6, 11)]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "📊 Оценка боли\n\n"
            "Оцени боль от 1 до 10:",
            reply_markup=reply_markup
        )
        
        return PAIN_SCORE
        
    except Exception as e:
        logger.error(f"Ошибка в pain_analysis_emotion: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз или используйте /cancel")
        return ConversationHandler.END

async def pain_analysis_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем оценку и завершаем анализ одной боли"""
    user_id = update.message.from_user.id
    
    try:
        interview = get_user_interview(user_id)
        
        # Обработка эмоции, если это текстовый ввод
        if 'current_pain' in context.user_data and not context.user_data['current_pain'].get('emotion'):
            context.user_data['current_pain']['emotion'] = update.message.text.strip()
            await update.message.reply_text(
                "📊 Оценка боли\n\n"
                "Оцени боль от 1 до 10 (введи число):"
            )
            return PAIN_SCORE
        
        # Обработка оценки
        try:
            score = int(update.message.text.strip())
            if score < 1 or score > 10:
                raise ValueError
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите число от 1 до 10:")
            return PAIN_SCORE
        
        if 'current_pain' not in context.user_data:
            logger.warning("current_pain не найден в user_data")
            context.user_data['current_pain'] = {
                'name': interview.most_annoying or 'Не указано',
                'last_case': '',
                'reason': '',
                'emotion': '',
                'score': score
            }
        else:
            context.user_data['current_pain']['score'] = score
        
        # Сохраняем боль
        interview.pain_analysis.append(context.user_data['current_pain'].copy())
        
        pain_name = context.user_data['current_pain']['name']
        pain_count = len(interview.pain_analysis)
        
        await update.message.reply_text(
            f"✅ Боль '{pain_name}' сохранена!\n"
            f"Всего проанализировано болей: {pain_count}\n\n"
            "Что дальше?\n"
            "• Напиши название новой боли - чтобы добавить еще\n"
            "• Напиши 'дальше' - чтобы перейти к волшебной палочке",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Очищаем текущую боль из user_data
        if 'current_pain' in context.user_data:
            del context.user_data['current_pain']
        
        return PAIN_NAME
        
    except Exception as e:
        logger.error(f"Ошибка в pain_analysis_score: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз или используйте /cancel")
        return ConversationHandler.END

async def magic_wand_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Волшебная палочка"""
    try:
        await update.message.reply_text(
            "✨ Волшебная палочка\n\n"
            "Если бы у тебя была волшебная палочка и ты мог бы решить "
            "одну проблему твоего учебного дня, что бы это было?",
            reply_markup=ReplyKeyboardRemove()
        )
        return MAGIC_WAND
    except Exception as e:
        logger.error(f"Ошибка в magic_wand_start: {e}", exc_info=True)
        return ConversationHandler.END

async def magic_wand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ответ волшебной палочки"""
    user_id = update.message.from_user.id
    
    try:
        interview = get_user_interview(user_id)
        interview.magic_wand = update.message.text.strip()
        
        await update.message.reply_text(
            "💡 Ключевые инсайты\n\n"
            "Что удивило в ходе разговора?"
        )
        
        return INSIGHTS_SURPRISE
        
    except Exception as e:
        logger.error(f"Ошибка в magic_wand: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз или используйте /cancel")
        return ConversationHandler.END

async def insights_surprise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Что удивило"""
    user_id = update.message.from_user.id
    
    try:
        interview = get_user_interview(user_id)
        interview.insights['surprise'] = update.message.text.strip()
        
        await update.message.reply_text(
            "🎯 Скрытые потребности\n\n"
            "Какие скрытые потребности удалось выявить?"
        )
        return INSIGHTS_NEEDS
        
    except Exception as e:
        logger.error(f"Ошибка в insights_surprise: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз или используйте /cancel")
        return ConversationHandler.END

async def insights_needs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Скрытые потребности"""
    user_id = update.message.from_user.id
    
    try:
        interview = get_user_interview(user_id)
        interview.insights['hidden_needs'] = update.message.text.strip()
        
        await update.message.reply_text(
            "🍔 Сигналы о еде/столовой\n\n"
            "Что говорили про питание?"
        )
        return INSIGHTS_FOOD
        
    except Exception as e:
        logger.error(f"Ошибка в insights_needs: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз или используйте /cancel")
        return ConversationHandler.END

async def insights_food(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сигналы о еде"""
    user_id = update.message.from_user.id
    
    try:
        interview = get_user_interview(user_id)
        interview.insights['food_signals'] = update.message.text.strip()
        
        await update.message.reply_text(
            "💰 Готовность платить\n\n"
            "Готовность платить временем/деньгами за решение проблем?"
        )
        return INSIGHTS_PAY
        
    except Exception as e:
        logger.error(f"Ошибка в insights_food: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз или используйте /cancel")
        return ConversationHandler.END

async def insights_complete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершение инсайтов и интервью"""
    user_id = update.message.from_user.id
    
    try:
        interview = get_user_interview(user_id)
        interview.insights['willingness_to_pay'] = update.message.text.strip()
        
        # Сохраняем в общую базу
        try:
            save_to_global_database(interview)
            save_success = True
        except Exception as e:
            logger.error(f"Ошибка при сохранении интервью: {e}", exc_info=True)
            save_success = False
        
        # Генерируем и отправляем отчет
        report = generate_report(interview)
        
        # Разбиваем отчет на части, если он слишком длинный (лимит Telegram ~4096 символов)
        max_length = 4000
        if len(report) > max_length:
            parts = [report[i:i+max_length] for i in range(0, len(report), max_length)]
            for part in parts:
                await update.message.reply_text(part)
        else:
            await update.message.reply_text(report)
        
        # Сообщение о завершении
        status_msg = "✅ Данные сохранены" if save_success else "⚠️ Данные сохранены с ошибками"
        await update.message.reply_text(
            f"🎉 Интервью завершено!\n\n"
            f"{status_msg}\n"
            f"Респондент №{interview.respondent_id}\n\n"
            f"Команды:\n"
            f"/export_all - скачать таблицу Excel со всеми респондентами\n"
            f"/stats - посмотреть статистику\n"
            f"/start - начать новое интервью"
        )
        
        # Очищаем сессию
        if user_id in interviews:
            del interviews[user_id]
        if 'current_pain' in context.user_data:
            del context.user_data['current_pain']
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Ошибка в insights_complete: {e}", exc_info=True)
        await update.message.reply_text(
            "Произошла ошибка при завершении интервью. "
            "Попробуйте использовать /export_all для проверки данных."
        )
        return ConversationHandler.END

def generate_report(interview):
    """Генерация отчета"""
    try:
        report_lines = [
            "📊 ОТЧЕТ ОБ ИНТЕРВЬЮ",
            f"Респондент №: {interview.respondent_id or 'Не указано'}",
            f"Дата: {interview.date or 'Не указано'}",
            "",
            "⚡ Точки напряжения:",
        ]
        
        if interview.pain_points:
            for point in interview.pain_points:
                report_lines.append(f"  • {point}")
        else:
            report_lines.append("  • Нет")
        
        report_lines.extend([
            "",
            "😫 Основные боли:",
            f"  {interview.main_pains or 'Не указано'}",
            "",
            "💢 Самая раздражающая:",
            f"  {interview.most_annoying or 'Не указано'}",
            "",
            "🔍 Анализ болей:"
        ])
        
        if interview.pain_analysis:
            for i, pain in enumerate(interview.pain_analysis, 1):
                score = pain.get('score', 0)
                score_icon = "❗" if score >= 7 else "⚠️" if score >= 4 else "✓"
                report_lines.extend([
                    f"  Боль #{i}: {pain.get('name', 'Не указано')}",
                    f"    Оценка: {score}/10 {score_icon}",
                    f"    Эмоция: {pain.get('emotion', 'Не указано')}",
                    f"    Случай: {pain.get('last_case', 'Не указано')}",
                    f"    Причина: {pain.get('reason', 'Не указано')}",
                    ""
                ])
        else:
            report_lines.append("  • Нет проанализированных болей")
        
        report_lines.extend([
            "",
            "✨ Волшебная палочка:",
            f"  {interview.magic_wand or 'Не указано'}",
            "",
            "💡 Инсайты:",
            f"  Удивило: {interview.insights.get('surprise', 'Не указано')}",
            f"  Скрытые потребности: {interview.insights.get('hidden_needs', 'Не указано')}",
            f"  Еда: {interview.insights.get('food_signals', 'Не указано')}",
            f"  Готовность платить: {interview.insights.get('willingness_to_pay', 'Не указано')}"
        ])
        
        return "\n".join(report_lines)
        
    except Exception as e:
        logger.error(f"Ошибка при генерации отчета: {e}", exc_info=True)
        return "Ошибка при генерации отчета"

async def export_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Экспорт ВСЕХ данных в Excel"""
    global all_interviews
    
    try:
        if not all_interviews:
            await update.message.reply_text(
                "❌ Нет данных для экспорта.\n"
                "Сначала проведи несколько интервью через /start"
            )
            return
        
        filename = save_all_to_excel()
        
        if not filename or not os.path.exists(filename):
            await update.message.reply_text(
                "❌ Ошибка при создании файла Excel.\n"
                "Проверьте логи для подробностей."
            )
            return
        
        total = len(all_interviews)
        
        # Отправляем файл
        try:
            with open(filename, 'rb') as file:
                await update.message.reply_document(
                    document=file,
                    filename=f"все_интервью_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    caption=(
                        f"📊 ОБЩАЯ ТАБЛИЦА\n\n"
                        f"Всего респондентов: {total}\n"
                        f"Файл обновляется автоматически"
                    )
                )
        except BadRequest as e:
            logger.error(f"Ошибка Telegram API при отправке файла: {e}")
            await update.message.reply_text(
                f"❌ Ошибка при отправке файла.\n"
                f"Проверьте, что файл не слишком большой.\n"
                f"Всего записей: {total}"
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке файла: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ Ошибка при отправке файла: {str(e)}"
            )
            
    except Exception as e:
        logger.error(f"Ошибка в export_all: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Произошла ошибка при экспорте данных.\n"
            "Проверьте логи для подробностей."
        )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику"""
    global all_interviews
    
    try:
        if not all_interviews:
            await update.message.reply_text("📊 Пока нет данных для статистики")
            return
        
        total = len(all_interviews)
        
        # Безопасно получаем даты
        first_date = "Не указано"
        last_date = "Не указано"
        
        try:
            if all_interviews:
                first_interview = all_interviews[0]
                last_interview = all_interviews[-1]
                first_date = first_interview.get('Дата', 'Не указано')
                last_date = last_interview.get('Дата', 'Не указано')
        except Exception as e:
            logger.warning(f"Ошибка при получении дат: {e}")
        
        # Подсчитываем статистику по болям
        total_pains = 0
        high_pain_count = 0  # Боли с оценкой >= 7
        
        for interview in all_interviews:
            for i in range(1, 11):  # Проверяем до 10 болей
                pain_score_key = f'Боль_{i}_Оценка'
                if pain_score_key in interview:
                    score = interview[pain_score_key]
                    if isinstance(score, (int, float)) and score > 0:
                        total_pains += 1
                        if score >= 7:
                            high_pain_count += 1
        
        stats_text = (
            f"📈 СТАТИСТИКА ПО ВСЕМ ИНТЕРВЬЮ\n\n"
            f"Всего респондентов: {total}\n"
            f"Первое интервью: {first_date}\n"
            f"Последнее интервью: {last_date}\n"
            f"Всего проанализировано болей: {total_pains}\n"
            f"Высокая интенсивность (≥7): {high_pain_count}\n\n"
            f"Команды:\n"
            f"/export_all - скачать общую таблицу Excel\n"
            f"/stats - показать эту статистику\n"
            f"/start - начать новое интервью"
        )
        
        await update.message.reply_text(stats_text)
        
    except Exception as e:
        logger.error(f"Ошибка в stats: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Произошла ошибка при получении статистики.\n"
            "Проверьте логи для подробностей."
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена интервью"""
    user_id = update.message.from_user.id
    
    try:
        if user_id in interviews:
            del interviews[user_id]
        if 'current_pain' in context.user_data:
            del context.user_data['current_pain']
        
        await update.message.reply_text(
            'Интервью отменено.',
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Ошибка в cancel: {e}", exc_info=True)
        return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Update {update} caused error {context.error}", exc_info=context.error)
    
    if update and update.message:
        try:
            await update.message.reply_text(
                "⚠️ Произошла непредвиденная ошибка.\n"
                "Попробуйте использовать /start для начала нового интервью "
                "или /cancel для отмены текущего."
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения об ошибке: {e}")

def main():
    """Запуск бота"""
    # Получаем токен из переменной окружения
    TOKEN = os.getenv('BOT_TOKEN')
    
    if not TOKEN:
        logger.error("BOT_TOKEN не найден в переменных окружения!")
        print("❌ Ошибка: BOT_TOKEN не найден в переменных окружения!")
        print("Создайте файл .env и добавьте туда: BOT_TOKEN=your_token_here")
        print("Или установите переменную окружения BOT_TOKEN")
        return
    
    try:
        application = Application.builder().token(TOKEN).build()
        
        # Обработчик ошибок
        application.add_error_handler(error_handler)
        
        # ConversationHandler для интервью
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                RESPONDENT_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, respondent_info)],
                DAY_MAP: [MessageHandler(filters.TEXT & ~filters.COMMAND, day_map)],
                PAIN_POINTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, pain_points)],
                PAIN_POINTS_OTHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, pain_points_other)],
                REGULAR_PROBLEMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, regular_problems)],
                PAIN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, pain_analysis_name)],
                PAIN_CASE: [MessageHandler(filters.TEXT & ~filters.COMMAND, pain_analysis_case)],
                PAIN_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, pain_analysis_reason)],
                PAIN_EMOTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, pain_analysis_emotion)],
                PAIN_SCORE: [MessageHandler(filters.TEXT & ~filters.COMMAND, pain_analysis_score)],
                MAGIC_WAND: [MessageHandler(filters.TEXT & ~filters.COMMAND, magic_wand)],
                INSIGHTS_SURPRISE: [MessageHandler(filters.TEXT & ~filters.COMMAND, insights_surprise)],
                INSIGHTS_NEEDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, insights_needs)],
                INSIGHTS_FOOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, insights_food)],
                INSIGHTS_PAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, insights_complete)],
            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )
        
        application.add_handler(conv_handler)
        application.add_handler(CommandHandler("export_all", export_all))
        application.add_handler(CommandHandler("stats", stats))
        
        logger.info("🚀 Бот запущен! Команды: /start, /export_all, /stats, /cancel")
        print("🚀 Бот запущен! Команды: /start, /export_all, /stats, /cancel")
        
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}", exc_info=True)
        print(f"❌ Критическая ошибка: {e}")

if __name__ == '__main__':
    main()
