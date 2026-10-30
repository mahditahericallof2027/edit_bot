import json
import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.errors import UserNotParticipant

CONFIG_FILE = "config.json"
DB_FILE = "remixes_db.json"

def load_json(filepath):
    if not os.path.exists(filepath):
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}

def save_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

config = load_json(CONFIG_FILE)
BOT_TOKEN = config.get("bot_token")
ADMIN_ID = config.get("admin_id")
REQUIRED_CHANNELS = config.get("required_channels", ["@ms_ediit"])

app = Client("ms_ediit_bot", bot_token=BOT_TOKEN)

async def check_membership(client: Client, user_id: int):
    not_joined = []
    for ch in REQUIRED_CHANNELS:
        try:
            member = await client.get_chat_member(ch, user_id)
            if member.status in ["kicked", "left"]:
                not_joined.append(ch)
        except Exception:
            not_joined.append(ch)
    return not_joined

def get_join_keyboard(channels, start_param=None):
    buttons = []
    for ch in channels:
        ch_clean = ch.replace("@", "")
        buttons.append([InlineKeyboardButton(f"عضویت در کانال {ch}", url=f"https://t.me/{ch_clean}")])
    callback_data = f"check_{start_param}" if start_param else "check_none"
    buttons.append([InlineKeyboardButton("تایید عضویت ✅", callback_data=callback_data)])
    return InlineKeyboardMarkup(buttons)

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user_id = message.from_user.id
    text_parts = message.text.split(maxsplit=1)
    start_param = text_parts[1] if len(text_parts) > 1 else None

    not_joined = await check_membership(client, user_id)
    if not_joined:
        await message.reply(
            "سلام دوست عزیز! برای دریافت فایل ابتدا باید در کانال‌های زیر عضو شوید:",
            reply_markup=get_join_keyboard(not_joined, start_param)
        )
        return

    await send_content_or_welcome(client, message, start_param)

@app.on_callback_query(filters.regex(r"^check_"))
async def callback_handler(client: Client, callback_query):
    user_id = callback_query.from_user.id
    data = callback_query.data.split("_", 1)[1]
    start_param = data if data != "none" else None

    not_joined = await check_membership(client, user_id)
    if not_joined:
        await callback_query.answer("هنوز در تمام کانال‌ها عضو نشده‌اید!", show_alert=True)
        return

    await callback_query.message.delete()
    await send_content_or_welcome(client, callback_query.message, start_param)

async def send_content_or_welcome(client: Client, message: Message, start_param: str = None):
    if not start_param:
        await message.reply(
            "به ربات ادیت و ریمیکس خوش آمدید!\nفایل مورد نظر خود را از طریق لینک‌های اختصاصی کانال دریافت کنید."
        )
        return

    db = load_json(DB_FILE)
    if start_param in db:
        file_info = db[start_param]
        file_id = file_info.get("file_id")
        file_type = file_info.get("type", "audio")
        caption = file_info.get("caption", "")

        if file_type == "audio":
            await client.send_audio(chat_id=message.chat.id, audio=file_id, caption=caption)
        elif file_type == "video":
            await client.send_video(chat_id=message.chat.id, video=file_id, caption=caption)
        elif file_type == "document":
            await client.send_document(chat_id=message.chat.id, document=file_id, caption=caption)
        elif file_type == "voice":
            await client.send_voice(chat_id=message.chat.id, voice=file_id, caption=caption)
        else:
            await client.send_message(chat_id=message.chat.id, text="نوع فایل پشتیبانی نمی‌شود.")
    else:
        await message.reply("فایل مورد نظر پیدا نشد یا حذف شده است.")

@app.on_message(filters.command("add") & filters.private)
async def add_remix_handler(client: Client, message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    if not message.reply_to_message:
        await message.reply("لطفاً این دستور را در پاسخ (ریپلای) به یک فایل صوتی، ویدیویی یا آهنگ بفرستید.\nمثال: `/add remix_80`")
        return

    text_parts = message.text.split(maxsplit=1)
    if len(text_parts) < 2:
        await message.reply("لطفاً کد ریمیکس را مشخص کنید.\nمثال: `/add remix_80`")
        return

    remix_code = text_parts[1].strip()
    target_msg = message.reply_to_message
    file_id = None
    file_type = "audio"
    caption = target_msg.caption or ""

    if target_msg.audio:
        file_id = target_msg.audio.file_id
        file_type = "audio"
    elif target_msg.video:
        file_id = target_msg.video.file_id
        file_type = "video"
    elif target_msg.voice:
        file_id = target_msg.voice.file_id
        file_type = "voice"
    elif target_msg.document:
        file_id = target_msg.document.file_id
        file_type = "document"

    if not file_id:
        await message.reply("پیام ریپلای شده یک فایل معتبر نیست.")
        return

    db = load_json(DB_FILE)
    db[remix_code] = {
        "file_id": file_id,
        "type": file_type,
        "caption": caption
    }
    save_json(DB_FILE, db)

    bot_info = await client.get_me()
    deep_link = f"https://t.me/{bot_info.username}?start={remix_code}"
    await message.reply(
        f"✅ ریمیکس با کد `{remix_code}` با موفقیت ذخیره شد!\n\nلینک اختصاصی برای گذاشتن در چنل:\n{deep_link}"
    )

print("Bot is starting...")
app.run()
