import os
import sys
import html
import sqlite3

# 1. هەوڵدان بۆ هاوردەکردن و دابەزاندنی کتێبخانە پێویستەکان
required_libraries = {
    "telebot": "pyTelegramBotAPI",
    "requests": "requests"
}

for lib_name, pip_name in required_libraries.items():
    try:
        __import__(lib_name)
    except ImportError:
        print(f"کتێبخانەی '{lib_name}' نەدۆزرایەوە. هەوڵی دابەزاندنی دەدەین...")
        import subprocess
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])
            print(f"کتێبخانەی '{lib_name}' بە سەرکەوتوویی دابەزێندرا!\n")
        except Exception as e:
            print(f"خەتا لە دابەزاندنی {lib_name}: {e}")
            print(f"تکایە بە دەستی خۆت دایبەزێنە: pip install {pip_name}")
            sys.exit(1)

import telebot
from telebot import types
import sqlite3
import os
import html
import pyodbc
import requests

def download_databases():
    urls = {
        "IRAQI.accdb": "https://huggingface.co/datasets/Huba090909/09/resolve/main/IRAQI.accdb",
        "duhok_db.db": "https://huggingface.co/datasets/Huba090909/09/resolve/main/duhok_db.db",
        "erbil_db.db": "https://huggingface.co/datasets/Huba090909/09/resolve/main/erbil_db.db",
        "slemani_db.db": "https://huggingface.co/datasets/Huba090909/09/resolve/main/slemani_db.db",
        "users_v2.db": "https://huggingface.co/datasets/Huba090909/09/resolve/main/users_v2.db"
    }
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    for filename, url in urls.items():
        file_path = os.path.join(current_dir, filename)
        if not os.path.exists(file_path):
            print(f"داگرتنی فایلی {filename} لە ئینتەرنێتەوە... تکایە چاوەڕێ بە")
            try:
                response = requests.get(url, stream=True)
                response.raise_for_status()
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"فایلی {filename} بە سەرکەوتوویی داگیرا!")
            except Exception as e:
                print(f"کێشە لە داگرتنی {filename} ڕوویدا: {e}")
        else:
            print(f"فایلی {filename} پێشتر داگیراوە و ئامادەیە.")

# ڕاستەوخۆ داگرتنی فایلەکان ئەگەر بوونیان نەبێت (بۆ Render زۆر گرنگە)
download_databases()

# ----------------- ڕێکخستنەکان -----------------
BOT_TOKEN = "8830140936:AAFb0fxkszDkshr8ZpvEoTpFR8C9pKfymHs"
ADMIN_ID = 7116467842

# دۆخی بەکارهێنەران
user_states = {}

# دروستکردنی بۆتەکە
bot = telebot.TeleBot(BOT_TOKEN)

# داتابەیسی پاراستن (کلیلەکان)
def init_users_db():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users_v2.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (chat_id TEXT PRIMARY KEY, join_date TEXT, expiration_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS keys (key_code TEXT PRIMARY KEY, is_used INTEGER, used_by TEXT, duration_days INTEGER)''')
    conn.commit()
    conn.close()

init_users_db()

def is_authorized(chat_id):
    if str(chat_id) == str(ADMIN_ID): return True
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users_v2.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT expiration_date FROM users WHERE chat_id = ?", (str(chat_id),))
    res = c.fetchone()
    conn.close()
    
    if not res:
        return False
        
    exp_date_str = res[0]
    import datetime
    try:
        exp_date = datetime.datetime.strptime(exp_date_str, "%Y-%m-%d %H:%M:%S")
        if datetime.datetime.now() > exp_date:
            return False
        return True
    except:
        return False

# دروستکردنی پەیوەندی بە داتابەیسی SQLite
def get_db_connection(prov_id="erbil"):
    # نەخشەی ناوی داتابەیسەکان
    db_name_map = {
        "erbil": "erbil_db.db",
        "sulaymaniyah": "slemani_db.db",
        "duhok": "duhok_db.db",
        "kirkuk": "kirkuk_db.db",
        "nineveh": "nenwa_db.db",
        "baghdad": "baghdad_db.db"
    }
    
    # فایلی داتابەیسەکە بەپێی شارەکە، ئەگەر نەبوو ئەوا هی هەولێر بەکاردەهێنێت
    file_name = db_name_map.get(prov_id, "erbil_db.db")
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_name)
    
    # ئەگەر فایلی شارەکە بوونی نەبوو، ئەوا با بگەڕێتەوە سەر فایلی هەولێر (کە ئێستا قوفڵەکەی کراوەتەوە)
    if not os.path.exists(db_path):
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "erbil_db.db")
        
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except Exception as e:
        print(f"Error connecting to SQLite db: {e}")
        return None

# ----------------- فۆرماتکردنی داتاکانی داتابەیسی ڕاستەقینە -----------------

def get_friendly_province_title(prov_name):
    clean_name = prov_name.replace("ـ", "").strip()
    provinces_map = {
        "erbil": "هەولێر", "sulaymaniyah": "سلێمانی", "duhok": "دهۆک", 
        "kirkuk": "کەرکوک", "nineveh": "نەینەوا", "baghdad": "بەغداد",
        "بغداد": "بەغداد", "اربيل": "هەولێر", "دهوك": "دهۆک", "سليمانية": "سلێمانی",
        "كركوك": "کەرکوک", "بصرة": "بەسرە", "نينوى": "نەینەوا", "موصل": "نەینەوا",
        "الانبار": "ئەنبار", "انبار": "ئەنبار", "بابل": "بابل", "ديالى": "دیالە",
        "كربلاء": "کەربەلا", "النجف": "نەجەف", "نجف": "نەجەف", "صلاح الدين": "سەڵاحەددین",
        "واسط": "واست", "المثنى": "موسەننا", "مثنى": "موسەننا", "القادسية": "قادسیە",
        "قادسية": "قادسیە", "ميسان": "میسان", "ذي قار": "زیقار", "بلد": "بەلەد"
    }
    for key, val in provinces_map.items():
        if key in clean_name or clean_name in key:
            return val
    return clean_name

def get_rc_details(rc_no, prov_id="erbil"):
    # چون لە داتابەیسە نوێیەکان خشتەی RC نییە، تەنیا ناوی شارەکە دەگەڕێنینەوە
    friendly_city = get_friendly_province_title(prov_id)
    return "", friendly_city

def get_family_extra_info(fam_no, prov_id="erbil"):
    conn = get_db_connection(prov_id)
    if not conn:
        return "دیاری نەکراوە", "نەزانراو"
    try:
        cursor = conn.cursor()
        fam_id_str = str(int(float(fam_no))) if str(fam_no).replace(".", "").isdigit() else str(fam_no)
        
        cursor.execute(
            "SELECT P_FIRST, P_RELATION FROM PERSON WHERE FAM_NO = ? OR FAM_NO = ? OR FAM_NO = ?",
            (fam_no, fam_id_str, f"{fam_id_str}.0")
        )
        members = cursor.fetchall()
        
        mother_name = "دیاری نەکراوە"
        for row in members:
            p_first = row[0]
            p_rel = row[1]
            try:
                if p_rel is not None and float(p_rel) == 2.0:
                    name = str(p_first).strip()
                    for char in ["„", "“", "”", "٫", "״"]:
                        name = name.replace(char, "")
                    mother_name = name if name else "دیاری نەکراوە"
                    break
            except:
                pass
                
        cursor.execute("PRAGMA table_info(FAMILY)")
        fam_cols = [col[1].upper().replace("_", "") for col in cursor.fetchall()]
        
        cursor.execute(
            "SELECT * FROM FAMILY WHERE FAM_NO = ? OR FAM_NO = ? OR FAM_NO = ?",
            (fam_no, fam_id_str, f"{fam_id_str}.0")
        )
        fam_row = cursor.fetchone()
        
        city_name = "نەزانراو"
        if fam_row:
            data_upper = {col: val for col, val in zip(fam_cols, fam_row)}
            parts = []
            
            frc = data_upper.get("FRC", "")
            rc_name = ""
            if frc:
                try:
                    cursor.execute("SELECT RC_NAME FROM RC WHERE RC_NO = ? OR RC_NO = ?", (frc, str(frc).zfill(3)))
                    rc_row = cursor.fetchone()
                    if rc_row and rc_row[0]:
                        rc_name = str(rc_row[0]).strip()
                        parts.append(rc_name)
                except:
                    pass
                    
            dist = data_upper.get("FDIST", "")
            if str(dist).lower() not in ["", "none", "0", "0.0"]:
                parts.append(str(dist).strip())
                
            area = data_upper.get("FAREA", "")
            if str(area).lower() not in ["", "none", "0", "0.0"]:
                if str(area).strip() not in parts:
                    parts.append(str(area).strip())
                    
            if parts:
                city_name = " - ".join(parts)
            else:
                city_name = get_friendly_province_title(prov_id)
                
        cursor.close()
        conn.close()
        
        return mother_name, city_name
    except Exception:
        return "دیاری نەکراوە", "نەزانراو"

def format_person_card(row, prov_id="erbil"):
    # لە SQLite تەنیا FAM_NO بوونی هەیە نەک RC_NO
    fam_no, seq_no, p_first, p_father, p_grand, p_relation, p_birth = row
    
    first = str(p_first).strip() if p_first else ""
    father = str(p_father).strip() if p_father else ""
    grand = str(p_grand).strip() if p_grand else ""
    
    for char in ["„", "“", "”", "٫", "״"]:
        first = first.replace(char, "")
        father = father.replace(char, "")
        grand = grand.replace(char, "")
        
    birth_year = "دیاری نەکراوە"
    age_str = "دیاری نەکراوە"
    if p_birth and str(p_birth).lower() not in ["none", "0", "0.0"]:
        try:
            year_val = int(float(p_birth))
            if year_val > 100000:
                year_val = year_val // 100
            birth_year = str(year_val)
            age_str = f"{2026 - year_val} ساڵ"
        except Exception:
            pass
            
    mother_name, city_name = get_family_extra_info(fam_no, prov_id)
    fam_id_str = str(int(float(fam_no))) if str(fam_no).replace(".", "").isdigit() else str(fam_no)
    
    card = (
        f"👥 ناوی: {html.escape(first)}\n"
        f"👤 ناوی باوک: {html.escape(father)}\n"
        f"👤 ناوی باپیر: {html.escape(grand)}\n"
        f"🧑‍🤝‍🧑 ناوی دایک: {html.escape(mother_name)}\n"
        f"📅 ساڵی لەدایکبوون: {html.escape(birth_year)}\n"
        f"⏳ تەمەن: {html.escape(age_str)}\n"
        f"🏠 ژمارەی خێزان: {html.escape(fam_id_str)}\n"
        f"📍 ناوچە/شار: {html.escape(city_name)}\n"
        f"_______________________"
    )
    return card, fam_id_str

def format_family_card(columns, row, members, friendly_city_title):
    def safe_html(val):
        if val is None:
            return ""
        return html.escape(str(val))
        
    data_upper = {col.upper().replace("_", ""): val for col, val in zip(columns, row)}
    
    first_name = data_upper.get("FHFIRST", data_upper.get("FHFIRSTNAME", ""))
    father_name = data_upper.get("FHFATHER", "")
    grand_name = data_upper.get("FHGRAND", "")
    
    first_name = str(first_name).strip() if first_name else ""
    father_name = str(father_name).strip() if father_name else ""
    grand_name = str(grand_name).strip() if grand_name else ""
    
    for char in ["„", "“", "”", "٫", "״"]:
        first_name = first_name.replace(char, "")
        father_name = father_name.replace(char, "")
        grand_name = grand_name.replace(char, "")
        
    full_name = f"{first_name} {father_name} {grand_name}".strip()
    if not full_name:
        full_name = "دیاری نەکراوە"
    
    fam_no = data_upper.get("FAMNO", "")
    fam_no = str(int(float(fam_no))) if fam_no and str(fam_no).replace(".", "").isdigit() else str(fam_no)
    
    no_per = data_upper.get("FNOPER", "")
    if no_per and str(no_per).replace(".", "").isdigit():
        no_per = str(int(float(no_per)))
        
    district = data_upper.get("FDIST", "")
    area = data_upper.get("FAREA", "")
    street = data_upper.get("FSTREET", "")
    house = data_upper.get("FHOUSE", "")
    
    district = "" if str(district).lower() in ["none", "0", "0.0"] else str(district).strip()
    area = "" if str(area).lower() in ["none", "0", "0.0"] else str(area).strip()
    street = "" if str(street).lower() in ["none", "0", "0.0"] else str(street).strip()
    house = "" if str(house).lower() in ["none", "0", "0.0"] else str(house).strip()
    
    member_lines = []
    head_birth_year = "دیاری نەکراوە"
    
    for m in members:
        m_first = str(m[0]).strip() if m[0] else ""
        m_father = str(m[1]).strip() if m[1] else ""
        m_grand = str(m[2]).strip() if m[2] else ""
        m_relation = str(m[3]).strip() if m[3] else ""
        m_birth = str(m[4]).strip() if m[4] else ""
        
        for char in ["„", "“", "”", "٫", "״"]:
            m_first = m_first.replace(char, "")
            m_father = m_father.replace(char, "")
            m_grand = m_grand.replace(char, "")
            
        m_fullname = f"{m_first} {m_father} {m_grand}".strip()
        
        m_birth_clean = "دیاری نەکراوە"
        m_age = "نەزانراو"
        if m_birth and m_birth.lower() not in ["none", "0", "0.0"]:
            try:
                year_val = int(float(m_birth))
                if year_val > 100000: year_val = year_val // 100
                m_birth_clean = str(year_val)
                m_age = f"{2026 - year_val} ساڵ"
            except Exception:
                m_birth_clean = m_birth
                
        rel_icon = "👥"
        rel_title = "ئەندام"
        
        try:
            rel_num = float(m_relation)
            if rel_num == 1.0:
                rel_icon = "👤"
                rel_title = "سەرۆکی خێزان"
                head_birth_year = m_birth_clean
            elif rel_num == 2.0:
                rel_icon = "👩"
                rel_title = "هاوسەر"
            elif rel_num == 3.0:
                rel_icon = "👶"
                rel_title = "منداڵ"
        except Exception:
            pass
            
        member_lines.append(
            f"{rel_icon} <b>{rel_title}:</b> {safe_html(m_fullname)}\n"
            f"   └ 🎂 ساڵ: {safe_html(m_birth_clean)} | ⏳ تەمەن: {safe_html(m_age)}\n"
        )
        
    formatted = (
        f"📦 <b>زانیاری تەواوی خێزان لە شاری: {friendly_city_title}</b>\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"👤 <b>ناوی سەرۆکی خێزان:</b> {safe_html(full_name)}\n"
        f"🆔 <b>کۆدی خێزان (Family ID):</b> {safe_html(fam_no)}\n"
        f"📅 <b>ساڵی لەدایکبوونی سەرۆک:</b> {safe_html(head_birth_year)}\n"
        f"👨‍👩‍👧‍👦 <b>ژمارەی ئەندامان:</b> {safe_html(no_per)}\n"
    )
    
    address_parts = []
    if friendly_city_title: address_parts.append(friendly_city_title)
    if district: address_parts.append(f"ناوچەی {district}")
    if street: address_parts.append(f"شەقامی {street}")
    if house: address_parts.append(f"خانووی {house}")
    
    if address_parts:
        formatted += f"📍 <b>ناونیشان:</b> {safe_html(', '.join(address_parts))}\n"
        
    if member_lines:
        formatted += (
            f"──────────────────\n"
            f"👨‍👩‍👧‍👦 <b>لیستی ئەندامانی خێزان:</b>\n"
            + "\n".join(member_lines) + "\n"
        )
        
    formatted += f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
    return formatted

import itertools

def get_spelling_variations(word):
    # یەکسانکردنی ئەلفەکان
    word = word.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    
    chars = []
    for char in word:
        if char in ['ك', 'ک', 'گ']: # هەندێک جار بە گ دەنووسرێت
            chars.append(['ك', 'ک'])
        elif char in ['ي', 'ی', 'ى', 'ئ']:
            chars.append(['ي', 'ی', 'ى'])
        elif char in ['ه', 'ة', 'ە']:
            chars.append(['ه', 'ة', 'ە'])
        else:
            chars.append([char])
            
    variations = set()
    for combo in itertools.product(*chars):
        variations.add("".join(combo))
        
    return list(variations)

def build_fast_name_query(words):
    query_parts = []
    params = []
    
    if len(words) == 1:
        vars_0 = get_spelling_variations(words[0])
        part = "(" + " OR ".join("P_FIRST LIKE ?" for _ in vars_0) + ")"
        query_parts.append(part)
        params.extend(f"{v}%" for v in vars_0)
    elif len(words) == 2:
        vars_0 = get_spelling_variations(words[0])
        vars_1 = get_spelling_variations(words[1])
        
        part_0 = "(" + " OR ".join("P_FIRST LIKE ?" for _ in vars_0) + ")"
        part_1 = "(" + " OR ".join("P_FATHER LIKE ?" for _ in vars_1) + ")"
        
        query_parts.append(f"({part_0} AND {part_1})")
        params.extend(f"{v}%" for v in vars_0)
        params.extend(f"{v}%" for v in vars_1)
    else:
        vars_0 = get_spelling_variations(words[0])
        vars_1 = get_spelling_variations(words[1])
        vars_2 = get_spelling_variations(words[2])
        
        part_0 = "(" + " OR ".join("P_FIRST LIKE ?" for _ in vars_0) + ")"
        part_1 = "(" + " OR ".join("P_FATHER LIKE ?" for _ in vars_1) + ")"
        part_2 = "(" + " OR ".join("P_GRAND LIKE ?" for _ in vars_2) + ")"
        
        query_parts.append(f"({part_0} AND {part_1} AND {part_2})")
        params.extend(f"{v}%" for v in vars_0)
        params.extend(f"{v}%" for v in vars_1)
        params.extend(f"{v}%" for v in vars_2)
        
    return "".join(query_parts), params

def search_persons_in_db(words, prov_id="erbil"):
    conn = get_db_connection(prov_id)
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        clause, query_params = build_fast_name_query(words)
        
        # SQLite uses LIMIT instead of TOP and doesn't have RC_NO
        query = (
            f"SELECT FAM_NO, SEQ_NO, P_FIRST, P_FATHER, P_GRAND, P_RELATION, P_BIRTH FROM PERSON WHERE {clause} "
            f"LIMIT 1500"
        )
        
        cursor.execute(query, query_params)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows
    except Exception as e:
        print("Error searching persons:", e)
        return []

# ================== چارەسەرکەری نامەکان و نەخشەکان ==================

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    chat_id = message.chat.id
    if str(chat_id) != str(ADMIN_ID):
        return
        
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users_v2.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM keys WHERE is_used = 0")
    unused_keys = c.fetchone()[0]
    conn.close()
    
    text = (
        "👨‍💻 <b>بەخێربێیت بۆ کۆنتڕۆڵ پانێڵی ئەدمین</b>\n\n"
        f"👥 کۆی بەکارهێنەران: {total_users}\n"
        f"🔑 کلیلە بەکارنەهاتووەکان: {unused_keys}\n\n"
        "چی دەتەوێت بکەیت؟"
    )
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ دروستکردنی کلیل", callback_data="admin_gen_key"),
        types.InlineKeyboardButton("⏸ وەستاندنی کلیل", callback_data="admin_stop_key")
    )
    bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_gen_key" and str(call.message.chat.id) == str(ADMIN_ID))
def admin_gen_key_callback(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("٧ ڕۆژ", callback_data="adminkey_7"),
        types.InlineKeyboardButton("٣٠ ڕۆژ", callback_data="adminkey_30"),
        types.InlineKeyboardButton("٣٦٥ ڕۆژ", callback_data="adminkey_365")
    )
    bot.edit_message_text("⏱ کلیلەکە بۆ چەند ڕۆژ بێت؟", chat_id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("adminkey_") and str(call.message.chat.id) == str(ADMIN_ID))
def admin_create_key_duration(call):
    chat_id = call.message.chat.id
    duration = int(call.data.split("_")[1])
    bot.answer_callback_query(call.id)
    
    import random
    import string
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    key_name = f"VIP-{random_str}"
    
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users_v2.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO keys (key_code, is_used, duration_days) VALUES (?, 0, ?)", (key_name, duration))
        conn.commit()
        bot.edit_message_text(f"🎉 کلیل بە سەرکەوتوویی دروستکرا!\n\n🔑 کلیل: `{key_name}`\n⏳ ماوە: {duration} ڕۆژ\n\nکۆپی بکە و بینێرە بۆ بەکارهێنەر.", chat_id, call.message.message_id, parse_mode="Markdown")
    except:
        bot.edit_message_text("❌ هەڵەیەک ڕوویدا لە دروستکردنی کلیل.", chat_id, call.message.message_id)
    conn.close()

@bot.callback_query_handler(func=lambda call: call.data == "admin_stop_key" and str(call.message.chat.id) == str(ADMIN_ID))
def admin_stop_key_callback(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    user_states[chat_id] = {'step': 'admin_waiting_stop_key'}
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 گەڕانەوە", callback_data="admin_stats"))
    bot.edit_message_text("🛑 تکایە ئەو کلیلە بنێرە کە دەتەوێت بیوەستێنیت یان بیسڕیتەوە:", chat_id, call.message.message_id, reply_markup=markup)

@bot.message_handler(func=lambda message: str(message.chat.id) == str(ADMIN_ID) and user_states.get(message.chat.id, {}).get('step') == 'admin_waiting_stop_key')
def admin_execute_stop_key(message):
    chat_id = message.chat.id
    key_to_stop = message.text.strip()
    
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users_v2.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute("SELECT used_by FROM keys WHERE key_code = ?", (key_to_stop,))
    row = c.fetchone()
    
    if not row:
        bot.send_message(chat_id, "❌ ئەم کلیلە بوونی نییە.")
    else:
        used_by = row[0]
        c.execute("DELETE FROM keys WHERE key_code = ?", (key_to_stop,))
        if used_by:
            c.execute("DELETE FROM users WHERE chat_id = ?", (used_by,))
            try:
                bot.send_message(used_by, "🚫 هەژمارەکەت ڕاگیرا لەلایەن ئەدمینەوە و دەستگەیشتنت بە بۆتەکە داخرا.")
            except:
                pass
        conn.commit()
        bot.send_message(chat_id, f"✅ کلیلەکەی ({key_to_stop}) بە سەرکەوتوویی سڕایەوە و بەکارهێنەرەکەشی دەرکرا.")
        
    conn.close()
    user_states.pop(chat_id, None)

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats" and str(call.message.chat.id) == str(ADMIN_ID))
def admin_show_stats(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users_v2.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM keys WHERE is_used = 0")
    unused_keys = c.fetchone()[0]
    conn.close()
    
    text = (
        "👨‍💻 <b>بەخێربێیت بۆ کۆنتڕۆڵ پانێڵی ئەدمین</b>\n\n"
        f"👥 کۆی بەکارهێنەران: {total_users}\n"
        f"🔑 کلیلە بەکارنەهاتووەکان: {unused_keys}\n\n"
        "چی دەتەوێت بکەیت؟"
    )
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ دروستکردنی کلیل", callback_data="admin_gen_key"),
        types.InlineKeyboardButton("⏸ وەستاندنی کلیل", callback_data="admin_stop_key")
    )
    bot.edit_message_text(text, chat_id, call.message.message_id, parse_mode="HTML", reply_markup=markup)

@bot.message_handler(commands=['info', 'profile'])
def send_user_info(message):
    chat_id = message.chat.id
    if str(chat_id) == str(ADMIN_ID):
        bot.send_message(chat_id, "👨‍💻 تۆ ئەدمینی گشتیت، کلیلەکەت قەت بەسەرناچێت!")
        return
        
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users_v2.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT expiration_date FROM users WHERE chat_id = ?", (str(chat_id),))
    res = c.fetchone()
    conn.close()
    
    if not res:
        bot.send_message(chat_id, "❌ تۆ هیچ کلیلێکت چالاک نەکردووە.")
        return
        
    exp_date_str = res[0]
    import datetime
    try:
        exp_date = datetime.datetime.strptime(exp_date_str, "%Y-%m-%d %H:%M:%S")
        now = datetime.datetime.now()
        if now > exp_date:
            bot.send_message(chat_id, "❌ ماوەی کلیلەکەت بەسەرچووە! تکایە کلیلێکی نوێ بکڕە و /start بکە.")
            user_states[chat_id] = {'step': 'waiting_for_key'}
        else:
            diff = exp_date - now
            days = diff.days
            hours = diff.seconds // 3600
            mins = (diff.seconds // 60) % 60
            bot.send_message(chat_id, f"👤 <b>زانیاری هەژمارەکەت:</b>\n\n📅 کاتی بەسەرچوون: {exp_date_str}\n⏳ کاتی ماوە: <b>{days} ڕۆژ و {hours} کاتژمێر و {mins} خولەک</b>", parse_mode="HTML")
    except:
        pass

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    chat_id = message.chat.id
    
    if not is_authorized(chat_id):
        bot.send_message(chat_id, "🔒 ئەم بۆتە داخراوە و تایبەتە.\n\nتکایە کلیلی چوونەژوورەوە (Key) بنێرە بۆ ئەوەی بۆتەکەت بۆ بکرێتەوە:")
        user_states[chat_id] = {'step': 'waiting_for_key'}
        return
        
    user_states.pop(chat_id, None)
    
    welcome_text = (
        "سڵاو! بەخێربێیت بۆ سیستەمی زیرەکی گەڕان 🔍\n\n"
        "تکایە لە خوارەوە یەکێک لە پارێزگاکان یان ناوچەکان هەڵبژێرە بۆ گەڕان:"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        types.InlineKeyboardButton("📍 هەولێر (سەنتەر)", callback_data="selprov_erbil"),
        types.InlineKeyboardButton("📍 سلێمانی (سەنتەر)", callback_data="selprov_sulaymaniyah")
    )
    markup.add(
        types.InlineKeyboardButton("سۆران", callback_data="selprov_erbil_soran"),
        types.InlineKeyboardButton("کۆیە", callback_data="selprov_erbil_koya")
    )
    markup.add(
        types.InlineKeyboardButton("شەقڵاوە", callback_data="selprov_erbil_shaqlawa"),
        types.InlineKeyboardButton("خەبات", callback_data="selprov_erbil_khabat")
    )
    markup.add(
        types.InlineKeyboardButton("هەڵەبجە", callback_data="selprov_sulaymaniyah_halabja"),
        types.InlineKeyboardButton("گەرمیان (کەلار)", callback_data="selprov_sulaymaniyah_garmyan")
    )
    markup.add(
        types.InlineKeyboardButton("ڕاپەڕین (ڕانیە)", callback_data="selprov_sulaymaniyah_raparin"),
        types.InlineKeyboardButton("چەمچەماڵ", callback_data="selprov_sulaymaniyah_chamchamal")
    )
    markup.add(
        types.InlineKeyboardButton("دەربەندیخان", callback_data="selprov_sulaymaniyah_darbandixan"),
        types.InlineKeyboardButton("پێنجوێن و سەیدسادق", callback_data="selprov_sulaymaniyah_penjwen")
    )
    markup.add(
        types.InlineKeyboardButton("کەرکوک", callback_data="selprov_kirkuk"),
        types.InlineKeyboardButton("دهۆک", callback_data="selprov_duhok")
    )
    markup.add(
        types.InlineKeyboardButton("نەینەوا", callback_data="selprov_nineveh"),
        types.InlineKeyboardButton("بەغداد", callback_data="selprov_baghdad")
    )
    markup.add(types.InlineKeyboardButton("👤 دۆخی هەژمار", callback_data="user_profile"))
    
    bot.send_message(chat_id, welcome_text, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "user_profile")
def callback_user_profile(call):
    chat_id = call.message.chat.id
    if str(chat_id) == str(ADMIN_ID):
        text = "👨‍💻 تۆ ئەدمینی گشتیت، کلیلەکەت قەت بەسەرناچێت!"
    else:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users_v2.db")
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT expiration_date FROM users WHERE chat_id = ?", (str(chat_id),))
        res = c.fetchone()
        conn.close()
        
        if not res:
            text = "❌ تۆ هیچ کلیلێکت چالاک نەکردووە."
        else:
            exp_date_str = res[0]
            import datetime
            try:
                exp_date = datetime.datetime.strptime(exp_date_str, "%Y-%m-%d %H:%M:%S")
                now = datetime.datetime.now()
                if now > exp_date:
                    text = "❌ ماوەی کلیلەکەت بەسەرچووە! تکایە کلیلێکی نوێ بکڕە و /start بکە."
                    user_states[chat_id] = {'step': 'waiting_for_key'}
                else:
                    diff = exp_date - now
                    days = diff.days
                    hours = diff.seconds // 3600
                    mins = (diff.seconds // 60) % 60
                    text = f"👤 <b>زانیاری هەژمارەکەت:</b>\n\n📅 کاتی بەسەرچوون: {exp_date_str}\n⏳ کاتی ماوە: <b>{days} ڕۆژ و {hours} کاتژمێر و {mins} خولەک</b>"
            except:
                text = "❌ هەڵەیەک ڕوویدا لە خوێندنەوەی کاتەکە."
                
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 گەڕانەوە بۆ مێنۆی سەرەکی", callback_data="back_to_start"))
    bot.edit_message_text(text, chat_id, call.message.message_id, parse_mode="HTML", reply_markup=markup)

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get('step') == 'waiting_for_key')
def handle_key_entry(message):
    chat_id = message.chat.id
    key_input = message.text.strip()
    
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users_v2.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT is_used, duration_days FROM keys WHERE key_code = ?", (key_input,))
    row = c.fetchone()
    
    if not row:
        bot.send_message(chat_id, "❌ ئەم کلیلە هەڵەیە یان بوونی نییە. تکایە دووبارە هەوڵبدەرەوە.")
        conn.close()
        return
        
    if row[0] == 1:
        bot.send_message(chat_id, "❌ ئەم کلیلە پێشتر بەکارهاتووە لەلایەن کەسێکی ترەوە و بەسەرچووە.")
        conn.close()
        return
        
    duration_days = row[1]
    import datetime
    now = datetime.datetime.now()
    exp_date = now + datetime.timedelta(days=duration_days)
    
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    exp_str = exp_date.strftime("%Y-%m-%d %H:%M:%S")
    
    c.execute("INSERT OR REPLACE INTO users (chat_id, join_date, expiration_date) VALUES (?, ?, ?)", (str(chat_id), now_str, exp_str))
    c.execute("UPDATE keys SET is_used = 1, used_by = ? WHERE key_code = ?", (str(chat_id), key_input))
    conn.commit()
    conn.close()
    
    bot.send_message(chat_id, f"✅ زۆر باشە! بە سەرکەوتوویی چوویته‌ ژوورەوە.\n⏳ کلیلەکەت بۆ ماوەی {duration_days} ڕۆژ کارایە.\n\nبۆ بینینی دۆخی هەژمارەکەت دەتوانیت کلیک لە دوگمەی (دۆخی هەژمار) بکەیت لە مێنۆی سەرەکی.")
    user_states.pop(chat_id, None)
    
    message.text = "/start"
    send_welcome(message)

@bot.callback_query_handler(func=lambda call: not is_authorized(call.message.chat.id))
def block_unauthorized_callbacks(call):
    bot.answer_callback_query(call.id, "🔒 تکایە سەرەتا کلیلی چوونەژوورەوە بنێرە بە نامە.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_start")
def callback_back_to_start(call):
    bot.answer_callback_query(call.id)
    send_welcome(call.message)

@bot.callback_query_handler(func=lambda call: call.data.startswith("selprov_"))
def callback_select_province(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    
    parts = call.data.split("_")
    prov_id = parts[1]
    sub_city = parts[2] if len(parts) > 2 else None
    
    user_states[chat_id] = {
        'prov_id': prov_id,
        'step': 'waiting_for_triple_name'
    }
    
    prov_name = get_friendly_province_title(prov_id)
    if sub_city == "soran": prov_name = "سۆران (هەولێر)"
    elif sub_city == "koya": prov_name = "کۆیە (هەولێر)"
    elif sub_city == "shaqlawa": prov_name = "شەقڵاوە (هەولێر)"
    elif sub_city == "khabat": prov_name = "خەبات (هەولێر)"
    elif sub_city == "halabja": prov_name = "هەڵەبجە"
    elif sub_city == "garmyan": prov_name = "گەرمیان و کەلار"
    elif sub_city == "raparin": prov_name = "ڕاپەڕین و ڕانیە"
    elif sub_city == "chamchamal": prov_name = "چەمچەماڵ"
    elif sub_city == "darbandixan": prov_name = "دەربەندیخان"
    elif sub_city == "penjwen": prov_name = "پێنجوێن و سەیدسادق"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 گەڕانەوە بۆ مێنۆی سەرەکی", callback_data="back_to_start"))
    
    bot.send_message(chat_id, f"✅ ناوچەی (<b>{prov_name}</b>) هەڵبژێردرا.\n\nتێبینی: گەڕانەکە لە تەواوی پارێزگاکە دەکرێت و لە کارتی کەسەکەدا ناوی شارۆچکەکەی دەنووسرێت.\n\nتکایە ئێستا ناوی سێیانی کەسەکە بنووسە (بۆ نموونە: محمد احمد محمود):", parse_mode="HTML", reply_markup=markup)

@bot.message_handler(func=lambda message: is_authorized(message.chat.id) and user_states.get(message.chat.id, {}).get('step') == 'waiting_for_triple_name')
def handle_triple_name_search(message):
    chat_id = message.chat.id
    raw_keyword = message.text.strip()
    
    keyword = raw_keyword.replace("'", "").replace('"', '').strip()
    words = [w for w in keyword.split() if w]
    
    if not words:
        bot.send_message(chat_id, "❌ تکایە ناوێک بنووسە بۆ گەڕان.")
        return
        
    state = user_states.get(chat_id)
    prov_id = state['prov_id'] if state else "erbil"
    
    bot.send_message(chat_id, f"🔍 گەڕان بۆ <b>'{html.escape(keyword)}'</b> دەستی پێکرد...", parse_mode="HTML")
    
    rows = search_persons_in_db(words, prov_id)
    
    if not rows:
        bot.send_message(chat_id, f"🤷‍♂️ هیچ ئەنجامێک نەدۆزرایەوە بۆ ناوەکە: '<b>{html.escape(keyword)}</b>'.\n\nتێبینی: ئەگەر خەریکی گەڕانیت لە شارێک بێجگە لە هەولێر، دڵنیابە داتابەیسەکانی تریش قوفڵەکانیان شکێنراوە وەکو فایلی هەولێرەکە.", parse_mode="HTML")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 گەڕانەوە بۆ سەرەتا", callback_data="back_to_start"))
        bot.send_message(chat_id, "دەتەوێت چی بکەیت ئێستا؟", reply_markup=markup)
    else:
        user_states[chat_id] = {
            'prov_id': prov_id,
            'step': 'waiting_for_triple_name',
            'search_results': rows,
            'search_page': 0
        }
        send_search_page(chat_id, 0)

def send_search_page(chat_id, page, message_id=None):
    state = user_states.get(chat_id, {})
    rows = state.get('search_results', [])
    prov_id = state.get('prov_id', 'erbil')
    
    if not rows:
        return
        
    total = len(rows)
    if page < 0: page = 0
    if page >= total: page = total - 1
    
    row = rows[page]
    formatted_card, fam_id_str = format_person_card(row, prov_id)
    seq_no = str(int(float(row[1]))) if str(row[1]).replace(".", "").isdigit() else str(row[1])
    
    final_text = f"📊 ئەنجامی {page + 1} لە کۆی {total} ئەنجام\n\n" + formatted_card
    
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("👥 بینینی خێزان", callback_data=f"vf_{prov_id}_{fam_id_str}_{seq_no}"),
        types.InlineKeyboardButton("🌳 دۆزینەوەی خزمەکان", callback_data=f"rels_{prov_id}_{fam_id_str}")
    )
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ پێشتر", callback_data=f"spage_{page-1}"))
    else:
        nav_buttons.append(types.InlineKeyboardButton(" ", callback_data="ignore"))
        
    nav_buttons.append(types.InlineKeyboardButton(f"{page+1}/{total}", callback_data="ignore"))
    
    if page < total - 1:
        nav_buttons.append(types.InlineKeyboardButton("دواتر ➡️", callback_data=f"spage_{page+1}"))
    else:
        nav_buttons.append(types.InlineKeyboardButton(" ", callback_data="ignore"))
        
    markup.row(*nav_buttons)
    markup.add(types.InlineKeyboardButton("🔙 گەڕانەوە بۆ سەرەتا", callback_data="back_to_start"))
    
    if message_id:
        try:
            bot.edit_message_text(final_text, chat_id, message_id, parse_mode="HTML", reply_markup=markup)
        except Exception:
            pass
    else:
        bot.send_message(chat_id, final_text, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("spage_"))
def callback_search_page(call):
    bot.answer_callback_query(call.id)
    page = int(call.data.split("_")[1])
    state = user_states.get(call.message.chat.id, {})
    state['search_page'] = page
    user_states[call.message.chat.id] = state
    send_search_page(call.message.chat.id, page, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "ignore")
def callback_ignore(call):
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("vf_"))
def callback_view_family(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    
    try:
        parts = call.data.split("_")
        prov_id = parts[1]
        fam_no = parts[2]
        seq_no = parts[3] if len(parts) > 3 else "1"
        
        conn = get_db_connection(prov_id)
        if not conn:
            bot.answer_callback_query(call.id, "❌ خەتا لە پەیوەندی داتابەیس.", show_alert=True)
            return
            
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM FAMILY WHERE FAM_NO = ?", (fam_no,))
        fam_row = cursor.fetchone()
        
        if not fam_row:
            bot.answer_callback_query(call.id, "❌ ئەم خێزانە نەدۆزرایەوە لە داتابەیسدا.", show_alert=True)
            cursor.close()
            conn.close()
            return
            
        cursor.execute("PRAGMA table_info(FAMILY)")
        fam_cols = [col[1] for col in cursor.fetchall()]
        
        cursor.execute(
            "SELECT P_FIRST, P_FATHER, P_GRAND, P_RELATION, P_BIRTH FROM PERSON WHERE FAM_NO = ? ORDER BY CAST(SEQ_NO AS INTEGER)",
            (fam_no,)
        )
        members = cursor.fetchall()
        cursor.close()
        conn.close()
        
        friendly_city = get_friendly_province_title(prov_id)
        
        formatted = format_family_card(fam_cols, fam_row, members, friendly_city)
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 گەڕانەوە بۆ کەسەکە", callback_data="back_to_search"))
        
        bot.edit_message_text(formatted, chat_id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ خەتایەک ڕوویدا:\n{e}", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_search")
def callback_back_to_search(call):
    bot.answer_callback_query(call.id)
    chat_id = call.message.chat.id
    state = user_states.get(chat_id, {})
    page = state.get('search_page', 0)
    send_search_page(chat_id, page, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("rels_"))
def callback_find_relatives(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    
    try:
        parts = call.data.split("_")
        prov_id = parts[1]
        fam_no = parts[2]
        
        conn = get_db_connection(prov_id)
        if not conn:
            bot.answer_callback_query(call.id, "❌ خەتا لە پەیوەندی داتابەیس.", show_alert=True)
            return
            
        cursor = conn.cursor()
        
        # دۆزینەوەی ناوی باوک و باپیری کەسەکە (یان سەرۆکی خێزانەکە)
        cursor.execute(
            "SELECT P_FATHER, P_GRAND FROM PERSON WHERE FAM_NO = ? AND P_RELATION = 1.0",
            (fam_no,)
        )
        row = cursor.fetchone()
        
        if not row:
            cursor.execute(
                "SELECT P_FATHER, P_GRAND FROM PERSON WHERE FAM_NO = ? LIMIT 1",
                (fam_no,)
            )
            row = cursor.fetchone()
            
        if not row:
            bot.answer_callback_query(call.id, "❌ نەتوانرا زانیاری ئەم خێزانە بدۆزرێتەوە بۆ دۆزینەوەی خزم.", show_alert=True)
            cursor.close()
            conn.close()
            return
            
        p_father = str(row[0]).strip() if row[0] else ""
        p_grand = str(row[1]).strip() if row[1] else ""
        
        for char in ["„", "“", "”", "٫", "״"]:
            p_father = p_father.replace(char, "")
            p_grand = p_grand.replace(char, "")
            
        if not p_father or not p_grand:
            bot.answer_callback_query(call.id, "❌ زانیاری باوک و باپیری ئەم کەسە تەواو نییە بۆ دۆزینەوەی خزم.", show_alert=True)
            cursor.close()
            conn.close()
            return
            
        # گەڕان بۆ مامەکان (ئەوانەی باوکیان هەمان ناوی باپیری ئەمەیە)
        # یان ئامۆزاکان (ئەوانەی باپیریان هەمان ناوی باپیری ئەمەیە)
        # بەکارهێنانی get_spelling_variations بۆ دڵنیابوون لەوەی هیچ کەس لێدەرناچێت
        vars_grand = get_spelling_variations(p_grand)
        
        clause = "(" + " OR ".join("P_FATHER LIKE ?" for _ in vars_grand) + " OR " + " OR ".join("P_GRAND LIKE ?" for _ in vars_grand) + ")"
        params = [f"{v}%" for v in vars_grand] * 2
        
        cursor.execute(
            f"SELECT P_FIRST, P_FATHER, P_GRAND, P_BIRTH FROM PERSON WHERE {clause} LIMIT 2000",
            params
        )
        relatives = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not relatives:
            bot.answer_callback_query(call.id, "🤷‍♂️ هیچ خزمێکی نزیک نەدۆزرایەوە.", show_alert=True)
            return
            
        lines = []
        for r in relatives:
            r_first = str(r[0]).strip() if r[0] else ""
            r_father = str(r[1]).strip() if r[1] else ""
            r_grand = str(r[2]).strip() if r[2] else ""
            r_birth = str(r[3]).strip() if r[3] else ""
            
            for char in ["„", "“", "”", "٫", "״"]:
                r_first = r_first.replace(char, "")
                r_father = r_father.replace(char, "")
                r_grand = r_grand.replace(char, "")
                
            full_name = f"{r_first} {r_father} {r_grand}".strip()
            
            rel_type = "خزم"
            if r_father in vars_grand or any(r_father.startswith(v) for v in vars_grand):
                rel_type = "مام/پور"
            elif r_grand in vars_grand or any(r_grand.startswith(v) for v in vars_grand):
                rel_type = "ئامۆزا/برا/خوشک"
                
            birth_clean = "نەزانراو"
            r_age = "نەزانراو"
            if r_birth and r_birth.lower() not in ["none", "0", "0.0"]:
                try:
                    year_val = int(float(r_birth))
                    if year_val > 100000: year_val = year_val // 100
                    birth_clean = str(year_val)
                    r_age = f"{2026 - year_val} ساڵ"
                except:
                    birth_clean = r_birth
                    
            lines.append(
                f"▪️ <b>{html.escape(full_name)}</b> ({rel_type})\n"
                f"   └ 🎂 ساڵ: {html.escape(birth_clean)} | ⏳ تەمەن: {r_age}\n"
            )
            
        state = user_states.get(chat_id, {})
        state['relatives_lines'] = lines
        state['relatives_grand'] = p_grand
        state['relatives_page'] = 0
        user_states[chat_id] = state
        
        send_relatives_page(chat_id, 0)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ خەتایەک لە دۆزینەوەی خزمدایە:\n{e}", show_alert=True)

def send_relatives_page(chat_id, page, message_id=None):
    state = user_states.get(chat_id, {})
    lines = state.get('relatives_lines', [])
    p_grand = state.get('relatives_grand', 'نەزانراو')
    
    if not lines:
        return
        
    items_per_page = 15
    total_items = len(lines)
    total_pages = (total_items + items_per_page - 1) // items_per_page
    
    if page < 0: page = 0
    if page >= total_pages: page = total_pages - 1
    
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, total_items)
    
    page_lines = lines[start_idx:end_idx]
    
    res_text = (
        f"🌳 <b>لیستی خزمەکانی لای باوک</b>\n"
        f"ناوی باپیرە گەورەیان: <b>{html.escape(p_grand)}</b>\n"
        f"📊 ئەنجامی {start_idx + 1} تا {end_idx} لە کۆی {total_items} خزم\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        + "\n".join(page_lines) + "\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
    )
    
    markup = types.InlineKeyboardMarkup(row_width=3)
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ پێشتر", callback_data=f"rpage_{page-1}"))
    else:
        nav_buttons.append(types.InlineKeyboardButton(" ", callback_data="ignore"))
        
    nav_buttons.append(types.InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="ignore"))
    
    if page < total_pages - 1:
        nav_buttons.append(types.InlineKeyboardButton("دواتر ➡️", callback_data=f"rpage_{page+1}"))
    else:
        nav_buttons.append(types.InlineKeyboardButton(" ", callback_data="ignore"))
        
    markup.row(*nav_buttons)
    
    if message_id:
        try:
            bot.edit_message_text(res_text, chat_id, message_id, parse_mode="HTML", reply_markup=markup)
        except Exception:
            pass
    else:
        bot.send_message(chat_id, res_text, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("rpage_"))
def callback_relatives_page(call):
    bot.answer_callback_query(call.id)
    page = int(call.data.split("_")[1])
    state = user_states.get(call.message.chat.id, {})
    state['relatives_page'] = page
    user_states[call.message.chat.id] = state
    send_relatives_page(call.message.chat.id, page, call.message.message_id)

if __name__ == "__main__":
    print("Telegram Bot is running using SQLite databases natively!")
    bot.infinity_polling()
