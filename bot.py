
import os
import time
import sqlite3
import logging
import telebot
from telebot import types

# ========== SOZLAMALAR ==========
TOKEN = os.getenv("BOT_TOKEN", "8490034289:AAEm_ysBOS0AV82abZsTXWYZsx0ZEkcXiRY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7465934934"))
PRICE = int(os.getenv("PREMIUM_PRICE", "5000"))
PREMIUM_DAYS = 7
DB = "axiy_movies.db"

if not TOKEN or not ADMIN_ID:
    raise ValueError("BOT_TOKEN yoki ADMIN_ID sozlanmagan!")

logging.basicConfig(level=logging.INFO)
bot = telebot.TeleBot(TOKEN)

# ========== BAZA ==========
def database():
    return sqlite3.connect(DB)

def init_db():
    con = database()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        premium_until INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS movies(
        code TEXT PRIMARY KEY,
        title TEXT,
        file_id TEXT,
        genre TEXT,
        quality TEXT,
        description TEXT,
        premium INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments(
        charge_id TEXT PRIMARY KEY,
        user_id INTEGER,
        amount INTEGER,
        paid_at INTEGER
    )
    """)

    con.commit()
    con.close()

init_db()

def is_admin(user_id):
    return user_id == ADMIN_ID

def save_user(user):
    con = database()
    con.execute(
        "INSERT OR IGNORE INTO users(user_id, username) VALUES (?,?)",
        (user.id, user.username or "")
    )
    con.commit()
    con.close()

def is_premium(user_id):
    con = database()
    row = con.execute(
        "SELECT premium_until FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()
    con.close()
    return bool(row and row[0] > int(time.time()))

# ========== MENYULAR ==========
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🎬 Kino kodi", "🔎 Kino qidirish")
    kb.row("📚 Katalog", "💎 Premium")
    kb.row("👤 Profil", "❓ Yordam")
    return kb

def admin_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("➕ Kino qo‘shish", "🗑 Kino o‘chirish")
    kb.row("📊 Statistika", "👥 Foydalanuvchilar")
    kb.row("🏠 Bosh menyu")
    return kb

# ========== START ==========
@bot.message_handler(commands=["start"])
def start(message):
    save_user(message.from_user)
    bot.send_message(
        message.chat.id,
        "🎬 AXIY KINO BOT PRO\n\n"
        "Xush kelibsiz!\n"
        "Kino olamiga marhamat 🍿",
        reply_markup=main_menu()
    )

# ========== ADMIN PANEL ==========
@bot.message_handler(commands=["admin"])
def admin_panel(message):
    if not is_admin(message.from_user.id):
        return

    bot.send_message(
        message.chat.id,
        "👑 AXIY PRO ADMIN PANEL",
        reply_markup=admin_menu()
    )

# ========== KINO YUBORISH ==========
def send_movie(chat_id, movie, user_id):
    code, title, file_id, genre, quality, description, premium = movie

    if premium and not is_premium(user_id):
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(
            "💎 PREMIUM OLISH",
            callback_data="buy"
        ))
        bot.send_message(
            chat_id,
            "🔒 Bu kino faqat Premium uchun!",
            reply_markup=kb
        )
        return

    caption = (
        f"🎬 {title}\n\n"
        f"🔢 Kod: {code}\n"
        f"🎭 Janr: {genre}\n"
        f"📺 Sifat: {quality}\n\n"
        f"📝 {description}"
    )

    bot.send_video(chat_id, file_id, caption=caption)

# ========== KINO KODI ==========
@bot.message_handler(func=lambda m: m.text == "🎬 Kino kodi")
def code_start(message):
    msg = bot.send_message(message.chat.id, "Kino kodini yuboring:")
    bot.register_next_step_handler(msg, code_search)

def code_search(message):
    con = database()
    movie = con.execute(
        "SELECT * FROM movies WHERE code=?",
        (message.text.strip(),)
    ).fetchone()
    con.close()

    if movie:
        send_movie(message.chat.id, movie, message.from_user.id)
    else:
        bot.send_message(message.chat.id, "❌ Kino topilmadi.")

# ========== KINO QIDIRISH ==========
@bot.message_handler(func=lambda m: m.text == "🔎 Kino qidirish")
def search_start(message):
    msg = bot.send_message(message.chat.id, "Kino nomini yozing:")
    bot.register_next_step_handler(msg, search_movie)

def search_movie(message):
    con = database()
    movies = con.execute(
        "SELECT * FROM movies WHERE title LIKE ? LIMIT 10",
        ("%" + message.text.strip() + "%",)
    ).fetchall()
    con.close()

    if not movies:
        bot.send_message(message.chat.id, "❌ Kino topilmadi.")
        return

    for movie in movies:
        send_movie(message.chat.id, movie, message.from_user.id)

# ========== KATALOG ==========
@bot.message_handler(func=lambda m: m.text == "📚 Katalog")
def catalog(message):
    con = database()
    movies = con.execute(
        "SELECT code,title,genre,premium FROM movies ORDER BY title"
    ).fetchall()
    con.close()

    if not movies:
        bot.send_message(message.chat.id, "Katalog bo‘sh.")
        return

    text = "📚 KINO KATALOGI\n\n"
    for code, title, genre, premium in movies:
        lock = " 🔒" if premium else ""
        text += f"🎬 {title}{lock}\n"
        text += f"🔢 Kod: {code} | {genre}\n\n"

    bot.send_message(message.chat.id, text)

# ========== PREMIUM ==========
def send_invoice(chat_id):
    bot.send_invoice(
        chat_id,
        title="AXIY KINO BOT PRO Premium",
        description=f"{PREMIUM_DAYS} kunlik Premium",
        invoice_payload="axiy_premium_7",
        provider_token="",
        currency="XTR",
        prices=[
            types.LabeledPrice(
                label="7 kun Premium",
                amount=PRICE
            )
        ]
    )

@bot.message_handler(func=lambda m: m.text == "💎 Premium")
def premium(message):
    if is_premium(message.from_user.id):
        bot.send_message(
            message.chat.id,
            "💎 Sizda Premium faol!"
        )
        return

    bot.send_message(
        message.chat.id,
        f"💎 AXIY PREMIUM\n\n"
        f"⏳ Muddat: {PREMIUM_DAYS} kun\n"
        f"⭐ Narx: {PRICE} Stars\n\n"
        "Premium kontentdan foydalaning!"
    )
    send_invoice(message.chat.id)

@bot.callback_query_handler(func=lambda c: c.data == "buy")
def buy_callback(call):
    bot.answer_callback_query(call.id)
    if is_premium(call.from_user.id):
        bot.send_message(call.message.chat.id, "Premium allaqachon faol!")
    else:
        send_invoice(call.message.chat.id)

# ========== TO‘LOV TEKSHIRISH ==========
@bot.pre_checkout_query_handler(func=lambda q: True)
def checkout(query):
    valid = (
        query.invoice_payload == "axiy_premium_7"
        and query.currency == "XTR"
        and query.total_amount == PRICE
    )

    bot.answer_pre_checkout_query(
        query.id,
        ok=valid,
        error_message=None if valid else "To‘lov ma’lumotlari noto‘g‘ri."
    )

# ========== TO‘LOV QABUL QILISH ==========
@bot.message_handler(content_types=["successful_payment"])
def payment_success(message):
    payment = message.successful_payment

    if (
        payment.invoice_payload != "axiy_premium_7"
        or payment.currency != "XTR"
        or payment.total_amount != PRICE
    ):
        return

    save_user(message.from_user)

    con = database()
    charge_id = payment.telegram_payment_charge_id

    try:
        con.execute(
            "INSERT INTO payments VALUES (?,?,?,?)",
            (charge_id, message.from_user.id,
             payment.total_amount, int(time.time()))
        )

        row = con.execute(
            "SELECT premium_until FROM users WHERE user_id=?",
            (message.from_user.id,)
        ).fetchone()

        old_until = row[0] if row else 0
        start_time = max(int(time.time()), old_until)
        until = start_time + PREMIUM_DAYS * 86400

        con.execute(
            "UPDATE users SET premium_until=? WHERE user_id=?",
            (until, message.from_user.id)
        )
        con.commit()

        bot.send_message(
            message.chat.id,
            "🎉 TO‘LOV MUVAFFAQIYATLI!\n\n"
            "💎 Premium faollashtirildi!\n"
            "⏳ 7 kunlik Premium berildi.",
            reply_markup=main_menu()
        )

    except sqlite3.IntegrityError:
        bot.send_message(message.chat.id, "Bu to‘lov avval qayd etilgan.")

    finally:
        con.close()

# ========== PROFIL ==========
@bot.message_handler(func=lambda m: m.text == "👤 Profil")
def profile(message):
    con = database()
    row = con.execute(
        "SELECT premium_until FROM users WHERE user_id=?",
        (message.from_user.id,)
    ).fetchone()
    con.close()

    until = row[0] if row else 0

    if until > int(time.time()):
        status = "💎 PREMIUM"
        date = time.strftime("%d.%m.%Y", time.localtime(until))
    else:
        status = "👤 Oddiy foydalanuvchi"
        date = "Premium faol emas"

    bot.send_message(
        message.chat.id,
        f"👤 PROFIL\n\n"
        f"🆔 ID: {message.from_user.id}\n"
        f"📌 Holat: {status}\n"
        f"⏳ Tugash sanasi: {date}"
    )

# ========== KINO QO‘SHISH ==========
@bot.message_handler(func=lambda m: m.text == "➕ Kino qo‘shish")
def add_start(message):
    if not is_admin(message.from_user.id):
        return

    bot.send_message(
        message.chat.id,
        "Videoni quyidagi izoh bilan yuboring:\n\n"
        "/add KOD | NOMI | JANR | SIFAT | TAVSIF | 0 yoki 1\n\n"
        "0 = Oddiy kino\n"
        "1 = Premium kino"
    )

@bot.message_handler(content_types=["video"])
def add_movie(message):
    if not is_admin(message.from_user.id):
        return

    caption = message.caption or ""
    if not caption.startswith("/add "):
        return

    try:
        data = [x.strip() for x in caption[5:].split("|", 5)]

        if len(data) != 6 or data[5] not in ("0", "1"):
            raise ValueError("Format noto‘g‘ri")

        code, title, genre, quality, description, premium_flag = data

        if not code or not title:
            raise ValueError("Kod va nom bo‘sh bo‘lmasin")

        con = database()
        con.execute(
            "INSERT OR REPLACE INTO movies VALUES (?,?,?,?,?,?,?)",
            (
                code, title, message.video.file_id,
                genre, quality, description, int(premium_flag)
            )
        )
        con.commit()
        con.close()

        bot.reply_to(message, "✅ Kino bazaga qo‘shildi!")

    except Exception:
        bot.reply_to(
            message,
            "❌ Format xato. Ma’lumotlarni tekshiring."
        )

# ========== KINO O‘CHIRISH ==========
@bot.message_handler(func=lambda m: m.text == "🗑 Kino o‘chirish")
def delete_start(message):
    if not is_admin(message.from_user.id):
        return

    msg = bot.send_message(message.chat.id, "Kino kodini yuboring:")
    bot.register_next_step_handler(msg, delete_movie)

def delete_movie(message):
    if not is_admin(message.from_user.id):
        return

    con = database()
    cur = con.execute(
        "DELETE FROM movies WHERE code=?",
        (message.text.strip(),)
    )
    con.commit()
    count = cur.rowcount
    con.close()

    bot.send_message(
        message.chat.id,
        "✅ Kino o‘chirildi!" if count else "❌ Kod topilmadi."
    )

# ========== ADMIN PREMIUM ==========
@bot.message_handler(commands=["grant"])
def grant_premium(message):
    if not is_admin(message.from_user.id):
        return

    try:
        parts = message.text.split()
        user_id = int(parts[1])
        days = int(parts[2]) if len(parts) > 2 else PREMIUM_DAYS

        if days < 1 or days > 365:
            raise ValueError()

        con = database()
        con.execute(
            "INSERT OR IGNORE INTO users(user_id,username) VALUES (?,?)",
            (user_id, "")
        )

        row = con.execute(
            "SELECT premium_until FROM users WHERE user_id=?",
            (user_id,)
        ).fetchone()

        until = max(int(time.time()), row[0]) + days * 86400

        con.execute(
            "UPDATE users SET premium_until=? WHERE user_id=?",
            (until, user_id)
        )
        con.commit()
        con.close()

        bot.send_message(
            message.chat.id,
            f"✅ {user_id} foydalanuvchiga {days} kun Premium berildi."
        )

    except Exception:
        bot.send_message(
            message.chat.id,
            "Format: /grant USER_ID [kun]"
        )

@bot.message_handler(commands=["revoke"])
def revoke_premium(message):
    if not is_admin(message.from_user.id):
        return

    try:
        user_id = int(message.text.split()[1])

        con = database()
        con.execute(
            "UPDATE users SET premium_until=0 WHERE user_id=?",
            (user_id,)
        )
        con.commit()
        con.close()

        bot.send_message(message.chat.id, "✅ Premium bekor qilindi.")

    except Exception:
        bot.send_message(message.chat.id, "Format: /revoke USER_ID")

# ========== STATISTIKA ==========
@bot.message_handler(func=lambda m: m.text == "📊 Statistika")
def stats(message):
    if not is_admin(message.from_user.id):
        return

    con = database()
    users = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    movies = con.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    premium = con.execute(
        "SELECT COUNT(*) FROM users WHERE premium_until>?",
        (int(time.time()),)
    ).fetchone()[0]
    payments = con.execute(
        "SELECT COUNT(*) FROM payments"
    ).fetchone()[0]
    con.close()

    bot.send_message(
        message.chat.id,
        f"📊 AXIY PRO STATISTIKA\n\n"
        f"👥 Foydalanuvchilar: {users}\n"
        f"🎬 Kinolar: {movies}\n"
        f"💎 Premium: {premium}\n"
        f"⭐ To‘lovlar: {payments}"
    )

# ========== FOYDALANUVCHILAR ==========
@bot.message_handler(func=lambda m: m.text == "👥 Foydalanuvchilar")
def users_list(message):
    if not is_admin(message.from_user.id):
        return

    con = database()
    users = con.execute(
        "SELECT user_id,username FROM users ORDER BY user_id DESC LIMIT 30"
    ).fetchall()
    con.close()

    if not users:
        bot.send_message(message.chat.id, "Foydalanuvchilar yo‘q.")
        return

    text = "👥 OXIRGI FOYDALANUVCHILAR\n\n"
    for user_id, username in users:
        text += f"🆔 {user_id} | @{username or 'username yo‘q'}\n"

    bot.send_message(message.chat.id, text)

# ========== YORDAM ==========
@bot.message_handler(func=lambda m: m.text == "❓ Yordam")
def help_user(message):
    bot.send_message(
        message.chat.id,
        "❓ YORDAM\n\n"
        "🎬 Kino kodi orqali kino toping.\n"
        "🔎 Kino nomi orqali qidiring.\n"
        "💎 Premium orqali yopiq kontentga kiring."
    )

# ========== BOSH MENYU ==========
@bot.message_handler(func=lambda m: m.text == "🏠 Bosh menyu")
def back(message):
    bot.send_message(
        message.chat.id,
        "🏠 Asosiy menyu",
        reply_markup=main_menu()
    )

# ========== XATOLIKLAR ==========
@bot.message_handler(func=lambda m: True)
def unknown(message):
    bot.send_message(
        message.chat.id,
        "Kerakli bo‘limni menyudan tanlang.",
        reply_markup=main_menu()
    )

# ========== ISHGA TUSHIRISH ==========
print("AXIY KINO BOT PRO ISHGA TUSHDI!")
bot.infinity_polling(
    skip_pending=True,
    timeout=30,
    long_polling_timeout=30
