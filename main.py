# -*- coding: utf-8 -*-
# Telegram-бот для выкупа б/у техники Apple
# Python 3.8+, pyTelegramBotAPI
# Установка: pip install pyTelegramBotAPI Flask

import os
import telebot
from telebot import types
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InputMediaPhoto
from flask import Flask, request

# ======================== НАСТРОЙКИ ========================
TOKEN = os.getenv("TG_TOKEN", "7618321225:AAGSxJVnjX1snonDMQNeK3lPJsB1AI5q9gg")
ADMIN_ID = int(os.getenv("ADMIN_ID", "119780466"))
WEBHOOK_HOST = os.getenv("WEBHOOK_URL", "")
BOT_NAME = "Apple Buyout Bot"
# ===========================================================

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
app = Flask(__name__)

# ======================== ДАННЫЕ ========================
DEVICE_TYPES = [
    "📱 iPhone", "💻 Mac", "📲 iPad",
    "⌚ Apple Watch", "🎧 AirPods", "🕶️ Vision Pro",
    "🔌Аксессуары", "📦 Другая техника",
]

CONDITIONS = [
    "✨ Новый", "💎 Идеальное (без царапин)",
    "🙂 Хорошее (есть незначительные следы использования)",
    "😕 Есть царапины/сколы", "💥 Есть повреждения или битые элементы корпуса",
]

CONTACT_METHODS = [
    "Поделиться номером ☎️",
    "WhatsApp 📲",
    "Telegram @username"
]

BTN_SKIP = "Пропустить ⏭️"
BTN_DONE = "Готово ➡️"
BTN_CANCEL = "Отмена ❌"
MAX_PHOTOS = 3

STATES = {
    "DEVICE": "DEVICE", "CONDITION": "CONDITION", "SPECS": "SPECS",
    "KIT": "KIT", "FAULTS": "FAULTS", "PHOTOS": "PHOTOS",
    "CONTACT_METHOD": "CONTACT_METHOD", "CONTACT": "CONTACT", "DONE": "DONE",
}

users = {}

# ======================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ========================

def get_kb(options, row_width=2, add_cancel=True, extra_buttons=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=row_width)
    buttons = [KeyboardButton(o) for o in options]
    if extra_buttons:
        buttons += [KeyboardButton(o) for o in extra_buttons]
    if add_cancel:
        buttons.append(KeyboardButton(BTN_CANCEL))
    kb.add(*buttons)
    return kb

def reset_user(chat_id):
    users[chat_id] = {
        "state": STATES["DEVICE"],
        "device": None, "condition": None, "specs": None,
        "kit": None, "faults": None, "photos": [],
        "contact_method": None, "contact": None,
        "username": None, "name": None, "phone": None,
    }

def summary_text(chat_id):
    d = users[chat_id]
    photos_info = f"{len(d['photos'])} шт." if d["photos"] else "нет"
    username_info = f"@{d['username']}" if d.get("username") else "—"
    contact_block = d["contact"] or (f"{d['name'] or ''} {d['phone'] or ''}".strip() or username_info)
    text = (
        f"<b>📝 Новая заявка на выкуп</b>\n"
        f"────────────────────────\n"
        f"📦 <b>Тип устройства:</b> {d['device'] or '—'}\n"
        f"🧿 <b>Состояние:</b> {d['condition'] or '—'}\n"
        f"🧾 <b>Характеристики:</b>\n{d['specs'] or '—'}\n"
        f"📚 <b>Комплект:</b>\n{d['kit'] or '—'}\n"
        f"⚠️ <b>Неисправности:</b>\n{d['faults'] or '—'}\n"
        f"🖼️ <b>Фото:</b> {photos_info}\n"
        f"👤 <b>Контакты:</b>\n{contact_block}"
    )
    return text

# ======================== ВОПРОСЫ ========================

def ask_device(chat_id):
    bot.send_message(chat_id,
        "Я бот, который поможет вам продать вашу технику Apple быстро и по выгодной цене.\n"
        "Пожалуйста, выберите, что вы хотите продать 📦:",
        reply_markup=get_kb(DEVICE_TYPES, row_width=2))
    users[chat_id]["state"] = STATES["DEVICE"]

def ask_condition(chat_id):
    bot.send_message(chat_id,
        "Уточните состояние устройства:",
        reply_markup=get_kb(CONDITIONS, row_width=1, extra_buttons=[BTN_SKIP]))
    users[chat_id]["state"] = STATES["CONDITION"]

def ask_specs(chat_id):
    bot.send_message(chat_id,
        "Опишите характеристики устройства, которые знаете. Менеджер уточнит детали при необходимости:\n"
        "(год выпуска модели, память, аккумулятор (циклы и проценты), цвет и т.д.)",
        reply_markup=get_kb([BTN_SKIP], row_width=1))
    users[chat_id]["state"] = STATES["SPECS"]

def ask_kit(chat_id):
    bot.send_message(chat_id,
        "Укажите, что входит в комплект 📦\nНапример: коробка, зарядное устройство, чек",
        reply_markup=get_kb([BTN_SKIP], row_width=1))
    users[chat_id]["state"] = STATES["KIT"]

def ask_faults(chat_id):
    bot.send_message(chat_id,
        "Есть ли неисправности? ⚠️\nОпишите их в свободной форме, если они имеются.",
        reply_markup=get_kb([BTN_SKIP], row_width=1))
    users[chat_id]["state"] = STATES["FAULTS"]

def ask_photos(chat_id):
    bot.send_message(chat_id,
        "Прикрепите 1–3 фото устройства 🖼️. После загрузки нажмите «Готово ➡️».",
        reply_markup=get_kb([BTN_DONE, BTN_SKIP], row_width=2))
    users[chat_id]["state"] = STATES["PHOTOS"]

def ask_contact_method(chat_id):
    bot.send_message(chat_id,
        "Как с вами удобнее связаться? 📱",
        reply_markup=get_kb(CONTACT_METHODS + [BTN_SKIP], row_width=1))
    users[chat_id]["state"] = STATES["CONTACT_METHOD"]

def ask_contact(chat_id):
    method = users[chat_id]["contact_method"]
    if method == "Поделиться номером ☎️":
        kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        kb.add(KeyboardButton("Поделиться номером ☎️", request_contact=True))
        kb.add(KeyboardButton(BTN_SKIP), KeyboardButton(BTN_CANCEL))
        bot.send_message(chat_id, "Пожалуйста, отправьте ваш номер через кнопку ниже:", reply_markup=kb)
        users[chat_id]["state"] = STATES["CONTACT"]
    elif method == "WhatsApp 📲":
        kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        kb.add(KeyboardButton(BTN_SKIP), KeyboardButton(BTN_CANCEL))
        bot.send_message(chat_id, "Пожалуйста, напишите ваш номер для связи через WhatsApp (например: +79123456789)",
                         reply_markup=kb)
        users[chat_id]["state"] = STATES["CONTACT"]
    elif method == "Telegram @username":
        username = users[chat_id].get("username")
        if username:
            users[chat_id]["contact"] = f"https://t.me/{username} (Telegram)"
            finish_and_send(chat_id)
        else:
            bot.send_message(chat_id, "Не удалось определить ваш username. Пожалуйста, выберите другой способ связи.")
            ask_contact_method(chat_id)

def finish_and_send(chat_id):
    text = summary_text(chat_id)
    bot.send_message(ADMIN_ID, text)
    photos = users[chat_id]["photos"]
    if photos:
        media = [InputMediaPhoto(pid) for pid in photos[:MAX_PHOTOS]]
        try:
            bot.send_media_group(ADMIN_ID, media)
        except:
            for pid in photos[:MAX_PHOTOS]:
                bot.send_photo(ADMIN_ID, pid)
    bot.send_message(chat_id, "Спасибо! 🎉 Заявка отправлена менеджеру.",
                     reply_markup=ReplyKeyboardRemove())
    users[chat_id]["state"] = STATES["DONE"]

# ======================== ХЭНДЛЕРЫ ========================

@bot.message_handler(commands=["start", "help"])
def cmd_start(message):
    chat_id = message.chat.id
    users.setdefault(chat_id, {})
    reset_user(chat_id)
    users[chat_id]["username"] = message.from_user.username
    ask_device(chat_id)

@bot.message_handler(content_types=["contact"])
def handle_contact(message):
    chat_id = message.chat.id
    if chat_id not in users: reset_user(chat_id)
    if users[chat_id].get("state") != STATES["CONTACT"]: 
        bot.send_message(chat_id, "Нажмите /start, чтобы начать заново."); return
    c = message.contact
    users[chat_id]["name"] = f"{c.first_name or ''} {c.last_name or ''}".strip()
    users[chat_id]["phone"] = c.phone_number
    users[chat_id]["contact"] = f"{users[chat_id]['name']} | {users[chat_id]['phone']}"
    finish_and_send(chat_id)

@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    chat_id = message.chat.id
    users.setdefault(chat_id, {"photos": []})
    if users[chat_id].get("state") != STATES["PHOTOS"]:
        bot.send_message(chat_id, "Фото сохранено, но анкета не запущена. Нажмите /start.")
        return
    fid = message.photo[-1].file_id
    if len(users[chat_id]["photos"]) < MAX_PHOTOS:
        users[chat_id]["photos"].append(fid)
        left = MAX_PHOTOS - len(users[chat_id]["photos"])
        bot.send_message(chat_id, f"Фото сохранено ✅ Осталось: {left}" if left > 0 else f"Максимум {MAX_PHOTOS} фото.")
    else:
        bot.send_message(chat_id, f"Достигнут лимит {MAX_PHOTOS} фото.")

@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_text(message):
    chat_id, text = message.chat.id, message.text.strip()
    if chat_id not in users: reset_user(chat_id)

    if text == BTN_CANCEL or text.lower() in ("/cancel", "cancel"):
        bot.send_message(chat_id, "Окей, отменил. Нажмите /start, чтобы начать заново.",
                         reply_markup=ReplyKeyboardRemove())
        reset_user(chat_id)
        return

    state = users[chat_id].get("state")

    # ======= Логика шагов =======
    if state == STATES["DEVICE"]:
        if text in DEVICE_TYPES:
            users[chat_id]["device"] = text
            ask_condition(chat_id)
        else: ask_device(chat_id)

    elif state == STATES["CONDITION"]:
        users[chat_id]["condition"] = None if text == BTN_SKIP else text
        ask_specs(chat_id)

    elif state == STATES["SPECS"]:
        users[chat_id]["specs"] = None if text == BTN_SKIP else text
        ask_kit(chat_id)

    elif state == STATES["KIT"]:
        users[chat_id]["kit"] = None if text == BTN_SKIP else text
        ask_faults(chat_id)

    elif state == STATES["FAULTS"]:
        users[chat_id]["faults"] = None if text == BTN_SKIP else text
        ask_photos(chat_id)

    elif state == STATES["PHOTOS"]:
        if text in (BTN_DONE, BTN_SKIP):
            ask_contact_method(chat_id)
        else:
            bot.send_message(chat_id, f"Прикрепите фото или нажмите «{BTN_DONE}» / «{BTN_SKIP}».")

    elif state == STATES["CONTACT_METHOD"]:
        if text in CONTACT_METHODS:
            users[chat_id]["contact_method"] = text
            ask_contact(chat_id)
        elif text == BTN_SKIP:
            finish_and_send(chat_id)
        else:
            ask_contact_method(chat_id)

    elif state == STATES["CONTACT"]:
        method = users[chat_id]["contact_method"]
        if method == "WhatsApp 📲":
            users[chat_id]["contact"] = f"{text} (WhatsApp)"
            finish_and_send(chat_id)
        elif method == "Поделиться номером ☎️":
            users[chat_id]["contact"] = text
            finish_and_send(chat_id)
        else:
            finish_and_send(chat_id)
    else:
        bot.send_message(chat_id, "Давайте начнём заново. Нажмите /start.", reply_markup=ReplyKeyboardRemove())
        reset_user(chat_id)

# ======================== WEBHOOK ========================

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_data().decode("utf-8")
    bot.process_new_updates([telebot.types.Update.de_json(update)])
    return "ok", 200

@app.route("/", methods=["GET"])
def index():
    return "Бот работает через webhook!", 200

if __name__ == "__main__":
    if not WEBHOOK_HOST:
        raise RuntimeError("❌ Укажи переменную окружения WEBHOOK_URL (адрес Render/Railway)!")
    WEBHOOK_URL = f"{WEBHOOK_HOST}/{TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
