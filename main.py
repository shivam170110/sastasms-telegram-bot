import os
import time
import json
import asyncio
import logging
import httpx
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ==========================================
# 🔑 CREDENTIALS & SETTINGS
# ==========================================
BOT_TOKEN = "8849599952:AAHtd5gL1GbWNadv2njQsW5SnqANqJILcfs"
SASTASMS_API_KEY = "stp_680975d2e24b68ca754ff0b20856d559e345D382bd9ff5ca"

ADMIN_CHANNEL_ID = -1004499634002 
SUPPORT_USERNAME = "@WSPCS01"
FORCE_SUB_CHANNEL = "@WHATSAPP_VAULT" 

JSONBIN_BIN_ID = "6aa58b12ffd5d16053fef63e"
JSONBIN_API_KEY = "$2a$10$1mqlsEiBEOr8/LOpCc09aeebMqgiBoKPuKYAnmvmeRomHUv1wJ7WK"

logging.basicConfig(level=logging.INFO)

# ==========================================
# ☁️ CLOUD STORAGE FUNCTIONS (JSONBin)
# ==========================================
def load_data_sync():
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest"
    headers = {"X-Master-Key": JSONBIN_API_KEY}
    try:
        response = httpx.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json().get("record", {})
            balances = {int(k): float(v) for k, v in data.get("balances", {}).items() if k.isdigit()}
            referrals = {int(k): int(v) for k, v in data.get("referrals", {}).items() if k.isdigit()}
            ref_counts = {int(k): int(v) for k, v in data.get("ref_counts", {}).items() if k.isdigit()}
            usernames = {int(k): str(v) for k, v in data.get("usernames", {}).items() if k.isdigit()}
            return balances, referrals, ref_counts, usernames
    except Exception as e:
        logging.error(f"Error loading data from cloud: {e}")
    return {}, {}, {}, {}

def save_data_sync(balances_dict, referrals_dict, ref_counts_dict, usernames_dict):
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
    headers = {
        "Content-Type": "application/json",
        "X-Master-Key": JSONBIN_API_KEY
    }
    try:
        payload = {
            "balances": {str(k): v for k, v in balances_dict.items()},
            "referrals": {str(k): v for k, v in referrals_dict.items()},
            "ref_counts": {str(k): v for k, v in ref_counts_dict.items()},
            "usernames": {str(k): v for k, v in usernames_dict.items()}
        }
        httpx.put(url, headers=headers, json=payload, timeout=10)
    except Exception as e:
        logging.error(f"Error saving data to cloud: {e}")

user_balances, user_referrers, referral_counts, user_usernames = load_data_sync()
active_orders = {}  
ITEMS_PER_PAGE = 15  

# ==========================================
# 📋 EXACT HARDCODED RETAIL PRICES FROM SCREEN RECORDING
# ==========================================
EXACT_PRices = {
    "Philippines": 69.57, "Dominican Republic": 74.93, "Jordan": 74.93, "South Sudan": 74.93,
    "Trinidad and Tobago": 74.93, "Bosnia and Herzegovina": 74.93, "Albania": 77.07, "Venezuela": 77.07,
    "Costa Rica": 77.07, "Hong Kong": 81.34, "French Guiana": 81.34, "Guadeloupe": 81.34,
    "Saint Lucia": 81.34, "Cape Verde": 81.34, "Sao Tome & Principe": 81.34, "Djibouti": 81.34,
    "Cayman Islands": 81.34, "Saint Vincent": 81.34, "Andorra": 83.34, "Greenland": 83.34,
    "Saudi Arabia": 85.63, "Malaysia": 85.63, "Comoros": 85.63, "Reunion": 85.63, "Mauritius": 85.63,
    "Seychelles": 85.63, "New Caledonia": 85.63, "United Kingdom": 92.05, "Madagascar": 92.05,
    "Tanzania": 92.05, "Algeria": 92.05, "Liberia": 92.05, "Tajikistan": 92.05, "Kyrgyzstan": 92.05,
    "Ghana": 92.05, "Sierra Leone": 92.05, "Swaziland": 92.05, "Zambia": 92.05, "Malawi": 92.05,
    "Haiti": 92.05, "Gambia": 92.05, "Equatorial Guinea": 92.05, "Zimbabwe": 93.12, "Cameroon": 94.19,
    "Egypt": 96.34, "Belize": 96.34, "DR Congo": 96.34, "Aruba": 96.34, "Eritrea": 96.34,
    "Jamaica": 98.48, "Kosovo": 100.61, "Niger": 104.90, "Lebanon": 104.90, "Burundi": 104.90,
    "Iran": 104.90, "Ethiopia": 107.04, "Iraq": 107.04, "Peru": 107.04, "Luxembourg": 107.04,
    "Gabon": 107.04, "Guinea": 109.18, "Namibia": 109.18, "Bangladesh": 111.31, "Benin": 111.31,
    "Kenya": 111.31, "Ivory Coast": 111.31, "Afghanistan": 111.31, "Burkina Faso": 111.31,
    "Nigeria": 113.46, "Thailand": 113.46, "Qatar": 113.46, "Slovakia": 113.46, "Uzbekistan": 113.46,
    "Senegal": 113.46, "Suriname": 113.46, "Monaco": 113.46, "Niue": 113.46, "Azerbaijan": 115.60,
    "Bahrain": 115.60, "Angola": 117.74, "Anguilla": 117.74, "Ukraine": 119.89, "Myanmar": 119.89,
    "Sri Lanka": 119.89, "Libya": 119.89, "Mozambique": 119.89, "Turkey": 126.30, "Nicaragua": 126.30,
    "Guatemala": 126.30, "Turkmenistan": 126.30, "Tunisia": 126.30, "Chad": 126.30, "Nepal": 126.30,
    "Honduras": 126.30, "Guyana": 126.30, "Maldives": 126.30, "Timor-Leste": 126.30, "Montenegro": 126.30,
    "Puerto Rico": 126.30, "Montserrat": 126.30, "Saint Kitts & Nevis": 126.30, "Macedonia": 126.30,
    "Iceland": 126.30, "Salvador": 126.30, "Bermuda": 126.30, "China": 128.45, "Serbia": 128.45,
    "Latvia": 128.45, "Panama": 130.59, "Lao": 130.59, "Mali": 130.59, "Uruguay": 130.59,
    "Palestine": 138.90, "Argentina": 139.15, "Papua New Guinea": 139.15, "Mexico": 145.57,
    "Cambodia": 147.71, "Togo": 149.86, "Georgia": 156.27, "Poland": 158.42, "Armenia": 158.42,
    "Belarus": 150.53, "Greece": 160.56, "United Arab Emirates": 160.56, "Paraguay": 162.56,
    "Norway": 162.56, "Estonia": 172.59, "Moldova": 172.59, "Samoa": 172.59, "Tonga": 172.59,
    "Liechtenstein": 172.59, "South Korea": 172.59, "American Samoa": 172.59, "Sint Maarten": 172.59,
    "Sweden": 188.66, "Country #173": 200.70, "Denmark": 202.70, "Netherlands": 206.72,
    "Romania": 212.73, "Lithuania": 220.77, "Kuwait": 226.79, "Israel": 226.79, "Hungary": 226.79,
    "Brazil": 240.83, "Czechia": 240.83, "Kazakhstan": 248.87, "Croatia": 260.90, "Macao": 262.91,
    "Bulgaria": 276.96, "Germany": 280.97, "Belgium": 337.16, "Cyprus": 352.16, "Spain": 355.89,
    "Finland": 421.46, "France": 468.29, "Pakistan": 468.29, "New Zealand": 505.75, "Italy": 543.21,
    "Australia": 599.41, "Austria": 636.87, "Taiwan": 878.50, "Singapore": 936.57, "Ireland": 1685.82,
    "Japan": 2200.94, "Gibraltar": 4214.56,
    # Custom Overrides requested
    "Indonesia": 50.0, "Yemen": 70.0, "Syria": 80.0, "South Africa": 60.0, "USA": 120.0, "India": 187.0
}

COUNTRY_NAMES = {
    "4": "🇵🇭 Philippines", "6": "🇮🇩 Indonesia", "12": "🇺🇸 USA", "22": "🇮🇳 India",
    "31": "🇿🇦 South Africa", "116": "🇾🇪 Yemen", "135": "🇸🇾 Syria"
}

async def get_all_country_list():
    url = "https://sastasms.pro/stubs/handler_api.php"
    params = {"api_key": SASTASMS_API_KEY, "action": "getServicesList", "service": "wa", "format": "json"}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                countries_data = data.get("countries", [])
                
                full_list = []
                for c in countries_data:
                    code = str(c.get("country_code", c.get("id", "0")))
                    api_name = c.get("country", "").strip()
                    
                    # Match price directly from screen recording mapping dictionary
                    final_price = EXACT_PRices.get(api_name, 150.0)
                    
                    # Apply specific overrides if matched by code or name
                    if code == "6" or "indonesia" in api_name.lower():
                        final_price = 50.0
                    elif code == "12" or "usa" in api_name.lower():
                        final_price = 120.0
                    elif code == "22" or "india" in api_name.lower():
                        final_price = 187.0
                    elif code == "31" or "south africa" in api_name.lower():
                        final_price = 60.0
                    elif code == "116" or "yemen" in api_name.lower():
                        final_price = 70.0
                    elif code == "135" or "syria" in api_name.lower():
                        final_price = 80.0

                    raw_name = COUNTRY_NAMES.get(code, f"🌍 {api_name}")
                    clean_name = api_name if api_name else f"Country {code}"
                    
                    full_list.append({
                        "name": f"{raw_name} - ₹{final_price:.2f}",
                        "code": code,
                        "raw_name": clean_name,
                        "price": final_price
                    })
                
                if full_list:
                    full_list.sort(key=lambda x: x["raw_name"])
                    return full_list
        except Exception as e:
            logging.error(f"Error fetching live pricing from API: {e}")

    # Fallback list mapping from exact dictionary if API is unreachable
    fallback_list = []
    for name, price in EXACT_PRices.items():
        fallback_list.append({
            "name": f"🌍 {name} - ₹{price:.2f}",
            "code": "0",
            "raw_name": name,
            "price": price
        })
    fallback_list.sort(key=lambda x: x["raw_name"])
    return fallback_list

async def check_user_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=FORCE_SUB_CHANNEL, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except Exception as e:
        logging.error(f"Error checking sub status for user {user_id}: {e}")
    return False

async def safe_send_or_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup: InlineKeyboardMarkup = None):
    query = update.callback_query
    if query:
        try: await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
        except Exception:
            try: await query.message.delete()
            except Exception: pass
            await context.bot.send_message(chat_id=query.message.chat_id, text=text, parse_mode="HTML", reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)

class SastaSMSProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://sastasms.pro/stubs/handler_api.php"

    async def get_number(self, service: str = "wa", country: str = "0"):
        # Explicitly request JSON format to prevent parsing glitches with plain text responses
        params = {
            "api_key": self.api_key, 
            "action": "getNumber", 
            "service": service, 
            "country": country,
            "format": "json"
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.base_url, params=params, timeout=15)
                
                # Check if response can be parsed as JSON
                try:
                    data = response.json()
                except Exception:
                    text = response.text.strip()
                    # Fallback check if it's standard plain text (e.g. ACCESS_NUMBER:id:number)
                    if text.startswith("ACCESS_NUMBER"):
                        parts = text.split(":")
                        if len(parts) >= 3:
                            return {"status": "SUCCESS", "id": parts[1], "number": parts[2]}
                    return {"status": "ERROR", "message": f"Provider error: {text}"}

                # Handle SastaSMS JSON response structure or fallback standard layout
                if isinstance(data, dict):
                    if data.get("status") == "OK" or "activation_id" in data or "order_id" in data:
                        activation_id = str(data.get("activation_id") or data.get("order_id"))
                        phone_number = str(data.get("phone_number") or data.get("number"))
                        return {"status": "SUCCESS", "id": activation_id, "number": phone_number}
                    
                    err_msg = data.get("msg") or data.get("message") or str(data)
                    return {"status": "ERROR", "message": f"Provider error: {err_msg}"}
                
                return {"status": "ERROR", "message": f"Invalid response format: {response.text}"}

            except Exception as e: 
                return {"status": "ERROR", "message": str(e)}

    async def get_status(self, order_id: str):
        params = {"api_key": self.api_key, "action": "getStatus", "id": order_id, "format": "json"}
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.base_url, params=params, timeout=12)
                try:
                    data = response.json()
                    status_text = str(data.get("status") or data.get("msg") or "")
                    if status_text == "STATUS_OK" or "OK" in status_text.upper():
                        return {"status": "RECEIVED", "code": data.get("code") or data.get("sms")}
                    elif status_text == "STATUS_WAIT_CODE" or "WAIT" in status_text.upper():
                        return {"status": "WAITING"}
                    else:
                        return {"status": "OTHER", "message": status_text}
                except Exception:
                    text = response.text.strip()
                    if text.startswith("STATUS_OK"): return {"status": "RECEIVED", "code": text.split(":")[1]}
                    elif text == "STATUS_WAIT_CODE": return {"status": "WAITING"}
                    else: return {"status": "OTHER", "message": text}
            except Exception as e: return {"status": "ERROR", "message": str(e)}

    async def set_status(self, order_id: str, status: int):
        params = {"api_key": self.api_key, "action": "setStatus", "status": status, "id": order_id}
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.base_url, params=params, timeout=12)
                return response.text.strip()
            except Exception as e:
                return str(e)

sms_provider = SastaSMSProvider(api_key=SASTASMS_API_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = f"@{user.username}" if user.username else f"{user.first_name} (No username)"

    if user_id not in user_usernames:
        user_usernames[user_id] = username
        
        if context.args and len(context.args) > 0:
            arg = context.args[0]
            if arg.startswith("ref_") and user_id not in user_referrers:
                try:
                    referrer_id = int(arg.split("_")[1])
                    if referrer_id != user_id:
                        user_referrers[user_id] = referrer_id
                        referral_counts[referrer_id] = referral_counts.get(referrer_id, 0) + 1
                        
                        current_ref_bal = user_balances.get(referrer_id, 0.0)
                        user_balances[referrer_id] = current_ref_bal + 2.0
                        
                        try:
                            await context.bot.send_message(
                                chat_id=referrer_id,
                                text=f"🎉 <b>Referral Bonus Earned!</b>\n\nA new user joined via your link. ₹2.00 has been added to your balance.\nNew Balance: ₹{user_balances[referrer_id]:.2f}",
                                parse_mode="HTML"
                            )
                        except Exception:
                            pass
                except Exception:
                    pass

        save_data_sync(user_balances, user_referrers, referral_counts, user_usernames)
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHANNEL_ID,
                text=f"👤 <b>New Bot User Started!</b>\n\nName: {user.first_name}\nUsername: {username}\nID: <code>{user_id}</code>",
                parse_mode="HTML"
            )
        except Exception:
            pass

    is_subbed = await check_user_subscription(user_id, context)
    if not is_subbed:
        try:
            chat_info = await context.bot.get_chat(FORCE_SUB_CHANNEL)
            channel_invite_link = chat_info.invite_link or (f"https://t.me/{chat_info.username}" if chat_info.username else f"https://t.me/c/{str(FORCE_SUB_CHANNEL).replace('-100', '')}/1")
        except Exception:
            channel_invite_link = "https://t.me/"

        sub_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=channel_invite_link)],
            [InlineKeyboardButton("✅ I Have Joined", callback_data="check_sub")]
        ])
        text = "⚠️ <b>Access Denied!</b>\n\nYou must join our official channel first to use this bot. Please join and click 'I Have Joined'."
        if update.message:
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=sub_markup)
        else:
            await safe_send_or_edit(update, context, text, sub_markup)
        return

    if user_id not in user_balances:
        user_balances[user_id] = 0.0  
        save_data_sync(user_balances, user_referrers, referral_counts, user_usernames)

    context.user_data.clear()

    reply_keyboard = [
        [KeyboardButton("🛒 Buy Number"), KeyboardButton("📦 Order History")],
        [KeyboardButton("👤 My Profile"), KeyboardButton("🎁 Gift")],
        [KeyboardButton("👥 Refer & Earn"), KeyboardButton("💳 Deposit")],
        [KeyboardButton("💬 Support")]
    ]
    bottom_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    inline_keyboard = [
        [InlineKeyboardButton("🛒 Buy Number (All Countries)", callback_data="buy_menu_0")], 
        [InlineKeyboardButton("🎁 Gift", callback_data="gift_menu"), InlineKeyboardButton("👥 Refer & Earn", callback_data="refer_menu")],
        [InlineKeyboardButton("💳 Deposit", callback_data="deposit_menu")]
    ]
    
    if update.message:
        await update.message.reply_text("Loading Bot Menu...", reply_markup=bottom_markup)
        await update.message.reply_text(f"👋 Welcome, <b>{user.first_name}</b>!\n\nSelect an option below:", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard))
    elif update.callback_query:
        await safe_send_or_edit(update, context, f"👋 Welcome, <b>{user.first_name}</b>!\n\nSelect an option below:", InlineKeyboardMarkup(inline_keyboard))

async def show_countries(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    all_countries = await get_all_country_list()
    total_pages = max(1, (len(all_countries) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    
    page_countries = all_countries[page * ITEMS_PER_PAGE : (page * ITEMS_PER_PAGE) + ITEMS_PER_PAGE]
    keyboard = []
    for i in range(0, len(page_countries), 2):
        row = []
        for j in range(2):
            if i + j < len(page_countries):
                c = page_countries[i + j]
                row.append(InlineKeyboardButton(c["name"], callback_data=f"prep_buy_{c['code']}_{c['price']}"))
        keyboard.append(row)

    nav_row = []
    if page > 0: nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"cpage_{page - 1}"))
    nav_row.append(InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1: nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"cpage_{page + 1}"))
    keyboard.append(nav_row)

    if total_pages > 3: keyboard.append([InlineKeyboardButton("⏮️ Page 1", callback_data="cpage_0"), InlineKeyboardButton("⏭️ End", callback_data=f"cpage_{total_pages - 1}")])
    keyboard.append([InlineKeyboardButton("🔍 Search Country", callback_data="search_country")])
    keyboard.append([InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")])

    await safe_send_or_edit(update, context, f"<b>🌍 Select Country ({len(all_countries)} Available):</b>\n<i>Page {page + 1} of {total_pages}</i>", InlineKeyboardMarkup(keyboard))

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await check_user_subscription(user_id, context):
        await update.message.reply_text("⚠️ Please join our official channel first, then send /start again.")
        return

    if context.user_data.get("awaiting_deposit_amount"):
        amount_text = update.message.text.strip()
        context.user_data["awaiting_deposit_amount"] = False
        
        try:
            amount = float(amount_text)
            if amount <= 0:
                raise ValueError()
        except ValueError:
            await update.message.reply_text("❌ Invalid amount. Please enter a valid number:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="main_menu")]]))
            context.user_data["awaiting_deposit_amount"] = True
            return

        context.user_data["pending_deposit_amount"] = amount
        context.user_data["awaiting_deposit_screenshot"] = True

        caption = (
            f"💳 <b>Deposit Amount Set: ₹{amount:.2f}</b>\n\n"
            f"Please scan the QR code above to pay, and then <b>send your payment screenshot</b> here in chat to submit your request."
        )
        
        if os.path.exists("qr_code.png"):
            with open("qr_code.png", "rb") as photo_file:
                await update.message.reply_photo(
                    photo=photo_file,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="main_menu")]])
                )
        else:
            await update.message.reply_text(
                f"{caption}\n\n⚠️ <i>(Note: qr_code.png file is missing on the server storage).</i>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="main_menu")]])
            )
        return

    if context.user_data.get("awaiting_search"):
        query_text = update.message.text.strip().lower()
        context.user_data["awaiting_search"] = False
        all_countries = await get_all_country_list()
        matching = [c for c in all_countries if query_text in c["raw_name"].lower()]
        
        if not matching:
            await update.message.reply_text("❌ No countries found matching your search.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Countries", callback_data="buy_menu_0")]]))
            return

        keyboard = []
        for i in range(0, len(matching), 2):
            row = [InlineKeyboardButton(matching[i]["name"], callback_data=f"prep_buy_{matching[i]['code']}_{matching[i]['price']}")]
            if i + 1 < len(matching):
                row.append(InlineKeyboardButton(matching[i+1]["name"], callback_data=f"prep_buy_{matching[i+1]['code']}_{matching[i+1]['price']}"))
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")])
        
        await update.message.reply_text(f"🔍 <b>Search Results for '{query_text}':</b>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    text = update.message.text.strip()

    if text == "🛒 Buy Number":
        await show_countries(update, context, page=0)
    elif text == "💳 Deposit":
        context.user_data["awaiting_deposit_amount"] = True
        await update.message.reply_text("💳 <b>Deposit Funds</b>\n\nEnter the amount to deposit:", parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="main_menu")]]))
    elif text == "👤 My Profile":
        bal = user_balances.get(user_id, 0.0)
        refs = referral_counts.get(user_id, 0)
        username = user_usernames.get(user_id, "N/A")
        await update.message.reply_text(f"<b>👤 Profile</b>\n\nUsername: {username}\nID: <code>{user_id}</code>\nBalance: ₹{bal:.2f}\nValid Referrals: {refs}", parse_mode="HTML")
    elif text == "🎁 Gift":
        await update.message.reply_text("🎁 <b>Special Gift</b>\n\nCheck back later for promotional gifts and bonus vouchers, or contact support to redeem ongoing offers!", parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]))
    elif text == "👥 Refer & Earn":
        bot_username = context.bot.username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        refs = referral_counts.get(user_id, 0)
        text_msg = (
            f"👥 <b>Refer & Earn Program</b>\n\n"
            f"Earn <b>₹2.00</b> directly into your balance for every unique user who starts the bot using your referral link!\n\n"
            f"📊 <b>Your Total Valid Referrals:</b> {refs}\n"
            f"💰 <b>Total Earned:</b> ₹{refs * 2.00:.2f}\n\n"
            f"🔗 <b>Your Referral Link:</b>\n<code>{ref_link}</code>"
        )
        await update.message.reply_text(text_msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]))
    elif text == "💬 Support":
        await update.message.reply_text(f"📞 <b>Contact Support:</b> {SUPPORT_USERNAME}", parse_mode="HTML")

async def handle_photo_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.user_data.get("awaiting_deposit_screenshot"):
        return

    context.user_data["awaiting_deposit_screenshot"] = False
    amount = context.user_data.get("pending_deposit_amount", 0.0)
    
    photo_file = update.message.photo[-1].file_id
    user = update.effective_user
    username = f"@{user.username}" if user.username else f"{user.first_name} (No username)"

    approval_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user.id}_{amount}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user.id}_{amount}")
        ]
    ])

    try:
        await context.bot.send_photo(
            chat_id=ADMIN_CHANNEL_ID,
            photo=photo_file,
            caption=(
                f"💳 <b>New Deposit Request with Proof!</b>\n\n"
                f"• <b>User:</b> {user.first_name} ({username})\n"
                f"• <b>ID:</b> <code>{user.id}</code>\n"
                f"• <b>Amount Requested:</b> ₹{amount:.2f}"
            ),
            parse_mode="HTML",
            reply_markup=approval_markup
        )
        await update.message.reply_text(
            "✅ <b>Screenshot Submitted Successfully!</b>\n\nYour payment proof has been sent to administration. You will be notified once approved.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]))
    except Exception as e:
        logging.error(f"Error forwarding deposit screenshot to admin channel: {e}")
        await update.message.reply_text("❌ Failed to send screenshot. Please try again or contact support.")

async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ <b>Usage:</b> <code>/add user_id amount</code>", parse_mode="HTML")
        return

    try:
        target_user_id = int(context.args[0])
        amount_to_add = float(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID or amount format.", parse_mode="HTML")
        return

    current_bal = user_balances.get(target_user_id, 0.0)
    user_balances[target_user_id] = current_bal + amount_to_add
    save_data_sync(user_balances, user_referrers, referral_counts, user_usernames)

    await update.message.reply_text(
        f"✅ <b>Successfully Credited!</b>\n\n"
        f"• <b>User ID:</b> <code>{target_user_id}</code>\n"
        f"• <b>Added:</b> ₹{amount_to_add:.2f}\n"
        f"• <b>New Balance:</b> ₹{user_balances[target_user_id]:.2f}",
        parse_mode="HTML"
    )

async def deduct_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ <b>Usage:</b> <code>/deduct user_id amount</code>", parse_mode="HTML")
        return

    try:
        target_user_id = int(context.args[0])
        amount_to_deduct = float(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID or amount format.", parse_mode="HTML")
        return

    current_bal = user_balances.get(target_user_id, 0.0)
    if current_bal < amount_to_deduct:
        await update.message.reply_text(f"⚠️ User only has ₹{current_bal:.2f}. Cannot deduct ₹{amount_to_deduct:.2f}.", parse_mode="HTML")
        return

    user_balances[target_user_id] = current_bal - amount_to_deduct
    save_data_sync(user_balances, user_referrers, referral_counts, user_usernames)

    await update.message.reply_text(
        f"✅ <b>Successfully Deducted!</b>\n\n"
        f"• <b>User ID:</b> <code>{target_user_id}</code>\n"
        f"• <b>Deducted:</b> ₹{amount_to_deduct:.2f}\n"
        f"• <b>New Balance:</b> ₹{user_balances[target_user_id]:.2f}",
        parse_mode="HTML"
    )

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ <b>Usage:</b> <code>/broadcast Your message here</code>", parse_mode="HTML")
        return

    message_text = " ".join(context.args)
    sent_count = 0
    failed_count = 0
    
    all_users = set(list(user_balances.keys()) + list(user_usernames.keys()))
    status_msg = await update.message.reply_text("📢 Broadcasting message to users...", parse_mode="HTML")
    
    for uid in all_users:
        try:
            await context.bot.send_message(chat_id=uid, text=message_text, parse_mode="HTML")
            sent_count += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed_count += 1
            
    await status_msg.edit_text(
        f"✅ <b>Broadcast Completed!</b>\n\n"
        f"• <b>Successfully Sent:</b> {sent_count}\n"
        f"• <b>Failed / Blocked:</b> {failed_count}",
        parse_mode="HTML"
    )

async def send_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ <b>Usage:</b> <code>/send user_id Your message</code>", parse_mode="HTML")
        return

    try:
        target_user_id = int(context.args[0])
        message_text = " ".join(context.args[1:])
        
        await context.bot.send_message(chat_id=target_user_id, text=message_text, parse_mode="HTML")
        await update.message.reply_text(f"✅ Message successfully sent to <code>{target_user_id}</code>!", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to send message: {e}")

async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except: pass
    data = query.data
    user_id = query.from_user.id

    if data == "check_sub":
        if await check_user_subscription(user_id, context):
            await start(update, context)
        else:
            await query.answer("❌ You have not joined the channel yet!", show_alert=True)
        return

    if not await check_user_subscription(user_id, context):
        await query.answer("⚠️ Please join the channel first!", show_alert=True)
        return

    if data == "main_menu": await start(update, context)
    elif data.startswith("buy_menu"): await show_countries(update, context, page=0)
    elif data.startswith("cpage_"): await show_countries(update, context, page=int(data.split("_")[1]))
    elif data == "search_country":
        context.user_data["awaiting_search"] = True
        await safe_send_or_edit(update, context, "🔍 <b>Search Country</b>\n\nType part of the country name you want to find:", InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="buy_menu_0")]]))
    elif data == "deposit_menu":
        context.user_data["awaiting_deposit_amount"] = True
        await safe_send_or_edit(update, context, "💳 <b>Deposit Funds</b>\n\nEnter the amount to deposit:", InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="main_menu")]]))
    elif data == "gift_menu":
        await safe_send_or_edit(update, context, "🎁 <b>Special Gift</b>\n\nCheck back later for promotional gifts and bonus vouchers, or contact support to redeem ongoing offers!", InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]))
    elif data == "refer_menu":
        bot_username = context.bot.username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        refs = referral_counts.get(user_id, 0)
        text_msg = (
            f"👥 <b>Refer & Earn Program</b>\n\n"
            f"Earn <b>₹2.00</b> directly into your balance for every unique user who starts the bot using your referral link!\n\n"
            f"📊 <b>Your Total Valid Referrals:</b> {refs}\n"
            f"💰 <b>Total Earned:</b> ₹{refs * 2.00:.2f}\n\n"
            f"🔗 <b>Your Referral Link:</b>\n<code>{ref_link}</code>"
        )
        await safe_send_or_edit(update, context, text_msg, InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]))
    
    elif data.startswith("approve_"):
        parts = data.split("_")
        target_user_id, added_amount = int(parts[1]), float(parts[2])
        
        current_bal = user_balances.get(target_user_id, 0.0)
        user_balances[target_user_id] = current_bal + added_amount
        save_data_sync(user_balances, user_referrers, referral_counts, user_usernames)
        
        try:
            admin_user = query.from_user.first_name
            if query.message.caption:
                await query.edit_message_caption(
                    caption=query.message.caption_html + f"\n\n<b>STATUS:</b> ✅ Approved & Credited ₹{added_amount:.2f} by {admin_user}",
                    parse_mode="HTML",
                    reply_markup=None
                )
            else:
                await query.edit_message_text(
                    text=query.message.text_html + f"\n\n<b>STATUS:</b> ✅ Approved & Credited ₹{added_amount:.2f} by {admin_user}",
                    parse_mode="HTML",
                    reply_markup=None
                )
        except Exception:
            pass
            
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"🎉 <b>Deposit Approved!</b>\n\nYour account has been successfully credited with ₹{added_amount:.2f}.\nNew Balance: ₹{user_balances[target_user_id]:.2f}",
                parse_mode="HTML"
            )
        except Exception:
            pass
        return

    elif data.startswith("reject_"):
        parts = data.split("_")
        target_user_id, rejected_amount = int(parts[1]), float(parts[2])
        
        try:
            admin_user = query.from_user.first_name
            if query.message.caption:
                await query.edit_message_caption(
                    caption=query.message.caption_html + f"\n\n<b>STATUS:</b> ❌ Rejected by {admin_user}",
                    parse_mode="HTML",
                    reply_markup=None
                )
            else:
                await query.edit_message_text(
                    text=query.message.text_html + f"\n\n<b>STATUS:</b> ❌ Rejected by {admin_user}",
                    parse_mode="HTML",
                    reply_markup=None
                )
        except Exception:
            pass
            
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"❌ <b>Deposit Rejected</b>\n\nYour deposit request of ₹{rejected_amount:.2f} was declined by administration. Please contact support {SUPPORT_USERNAME} if you think this is a mistake.",
                parse_mode="HTML"
            )
        except Exception:
            pass
        return

    elif data.startswith("prep_buy_"):
        parts = data.split("_")
        country_code, price = parts[2], float(parts[3])
        current_bal = user_balances.get(user_id, 0.0)
        
        if current_bal < price:
            await safe_send_or_edit(update, context, f"⚠️ <b>Insufficient Balance!</b>\n\nPrice: ₹{price:.2f}\nBalance: ₹{current_bal:.2f}", InlineKeyboardMarkup([[InlineKeyboardButton("💳 Deposit Funds", callback_data="deposit_menu")]]))
            return
            
        keyboard = [[InlineKeyboardButton("✅ Confirm Purchase", callback_data=f"confirm_buy_{country_code}_{price}")], [InlineKeyboardButton("❌ Cancel", callback_data="buy_menu_0")]]
        await safe_send_or_edit(update, context, f"🛒 <b>Confirm Purchase:</b>\n• <b>Price:</b> ₹{price:.2f}", InlineKeyboardMarkup(keyboard))
        
    elif data.startswith("confirm_buy_"):
        parts = data.split("_")
        country_code, price = parts[2], float(parts[3])
        if user_balances.get(user_id, 0.0) < price: return
        
        await query.edit_message_text("⏳ <i>Issuing your number...</i>", parse_mode="HTML")
        res = await sms_provider.get_number(service="wa", country=country_code)
        
        if res.get("status") == "SUCCESS":
            user_balances[user_id] -= price
            save_data_sync(user_balances, user_referrers, referral_counts, user_usernames)
            order_id, number = res["id"], res["number"]
            active_orders[order_id] = {"user_id": user_id, "price": price, "time": time.time()}
            
            text = (
                f"✅ <b>Number Issued!</b>\n\n"
                f"📱 <b>Phone:</b> <code>+{number}</code>\n"
                f"🆔 <b>Order:</b> <code>{order_id}</code>\n\n"
                f"⏳ <i>Waiting for OTP (Valid for 20 minutes).</i>\n"
                f"⚠️ <i>Cancel & Refund will be available after 3 minutes.</i>"
            )
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh OTP Status", callback_data=f"refresh_{order_id}")],
                [InlineKeyboardButton("❌ Cancel & Refund", callback_data=f"cancel_order_{order_id}")]
            ]
            await safe_send_or_edit(update, context, text, InlineKeyboardMarkup(keyboard))
            
            try:
                buyer = query.from_user
                buyer_username = f"@{buyer.username}" if buyer.username else f"{buyer.first_name} (No username)"
                await context.bot.send_message(
                    chat_id=ADMIN_CHANNEL_ID,
                    text=(
                        f"🛒 <b>New Number Purchased!</b>\n\n"
                        f"• <b>Buyer:</b> {buyer.first_name} ({buyer_username})\n"
                        f"• <b>Buyer ID:</b> <code>{buyer.id}</code>\n"
                        f"• <b>Price Paid:</b> ₹{price:.2f}\n"
                        f"• <b>Phone Number:</b> <code>+{number}</code>"
                    ),
                    parse_mode="HTML"
                )
            except Exception as e:
                logging.error(f"Error sending purchase notification to admin channel: {e}")
        else:
            await safe_send_or_edit(update, context, f"❌ <b>Error:</b> {res.get('message', 'Out of stock.')}", InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="buy_menu_0")]]))

    elif data.startswith("refresh_"):
        order_id = data.split("_")[1]
        order = active_orders.get(order_id)
        if not order:
            await query.answer("❌ Order not found or closed.", show_alert=True)
            return

        res = await sms_provider.get_status(order_id)
        status = res.get("status")

        if status == "RECEIVED":
            code = res.get("code")
            del active_orders[order_id]
            await safe_send_or_edit(update, context, f"🎉 <b>OTP Received Successfully!</b>\n\n🔑 <b>Verification Code:</b> <code>{code}</code>", InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]))
        elif status == "WAITING":
            await query.answer("⏳ Still waiting for OTP... (Valid for 20 mins)", show_alert=True)
        else:
            await query.answer(f"ℹ️ Status: {res.get('message', 'Waiting...')}", show_alert=True)

    elif data.startswith("cancel_order_"):
        order_id = data.split("_")[2]
        order = active_orders.get(order_id)
        if not order:
            await query.answer("❌ Order not found or already closed.", show_alert=True)
            return

        elapsed = time.time() - order["time"]
        if elapsed < 180:
            remaining = int(180 - elapsed)
            mins = remaining // 60
            secs = remaining % 60
            await query.answer(f"⚠️ Please wait {mins}m {secs}s more before you can cancel and refund.", show_alert=True)
            return

        await sms_provider.set_status(order_id, 8)
        
        target_user_id = order["user_id"]
        price = order["price"]
        user_balances[target_user_id] = user_balances.get(target_user_id, 0.0) + price
        save_data_sync(user_balances, user_referrers, referral_counts, user_usernames)
        
        del active_orders[order_id]
        
        await safe_send_or_edit(update, context, f"❌ <b>Order Cancelled & Refunded!</b>\n\n₹{price:.2f} has been refunded to your balance.", InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]))

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_balance))
    app.add_handler(CommandHandler("deduct", deduct_balance))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("send", send_to_user))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    app.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_photo_messages))
    app.add_handler(CallbackQueryHandler(button_router))
    print("🚀 Bot Online with Fixed JSON/Text Response Parsing & Robust Error Handlers!")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app.run_polling()

if __name__ == "__main__":
    main()
