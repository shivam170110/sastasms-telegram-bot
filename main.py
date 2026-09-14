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

COUNTRY_PRICES = {
    "0": 250.0, "1": 189.0, "2": 312.0, "3": 250.0, "4": 250.0, "5": 187.0, "6": 50.0, "7": 147.0, "8": 159.0, "9": 132.0,
    "10": 99.0, "11": 196.0, "12": 115.0, "13": 314.0, "14": 156.0, "15": 186.0, "16": 185.0, "17": 256.0, "18": 98.0, "19": 199.0,
    "20": 167.0, "21": 173.0, "22": 179.0, "23": 3204.0, "24": 213.0, "25": 190.0, "26": 143.0, "27": 199.0, "28": 175.0, "29": 234.0,
    "30": 156.0, "31": 132.0, "32": 213.0, "33": 75.0, "34": 195.0, "35": 145.0, "36": 112.0, "37": 89.0, "38": 140.0, "39": 178.0,
    "40": 189.0, "41": 168.0, "42": 157.0, "43": 360.0, "44": 234.0, "45": 297.0, "46": 256.0, "47": 167.0, "48": 189.0, "49": 198.0,
    "50": 309.0, "51": 178.0, "52": 176.0, "53": 189.0, "54": 250.0, "55": 781.0, "56": 180.0, "57": 230.0, "58": 178.0, "59": 198.0,
    "60": 130.0, "61": 340.0, "62": 176.0, "63": 198.0, "64": 178.0, "65": 671.0, "66": 990.0, "67": 156.0, "68": 139.0, "69": 40.0,
    "70": 187.0, "71": 178.0, "72": 158.0, "73": 167.0, "74": 199.0, "75": 40.0, "76": 193.0, "77": 173.0, "78": 212.0, "79": 245.0,
    "80": 999.0, "81": 179.0, "82": 640.0, "83": 198.0, "84": 654.0, "85": 290.0, "86": 599.0, "87": 456.0, "88": 210.0, "89": 245.0,
    "90": 350.0, "91": 190.0, "92": 560.0, "93": 198.0, "94": 190.0, "95": 225.0, "96": 234.0, "97": 40.0, "98": 230.0, "99": 190.0,
    "100": 200.0, "101": 245.0, "102": 234.0, "103": 304.0, "104": 250.0, "105": 168.0, "106": 1472.0, "107": 250.0, "108": 198.0, "109": 234.0,
    "110": 196.0, "111": 178.0, "112": 40.0, "113": 180.0, "114": 365.0, "115": 234.0, "116": 189.0, "117": 230.0, "118": 204.0, "119": 203.0,
    "120": 150.0, "121": 178.0, "122": 200.0, "123": 198.0, "124": 158.0, "125": 205.0, "126": 196.0, "127": 1134.0, "128": 1098.0, "129": 209.0,
    "130": 189.0, "131": 240.0, "132": 199.0, "133": 199.0, "134": 156.0, "135": 196.0, "136": 205.0, "137": 204.0, "138": 199.0, "139": 197.0,
    "140": 199.0, "141": 230.0, "142": 257.0, "143": 171.0, "144": 679.0, "145": 198.0, "146": 40.0, "147": 40.0, "148": 40.0, "149": 267.0,
    "150": 267.0, "151": 195.0, "152": 198.0, "153": 200.0, "154": 199.0, "155": 140.0, "156": 190.0, "157": 198.0, "158": 197.0, "159": 176.0,
    "160": 189.0, "161": 198.0, "162": 194.0, "163": 149.0, "164": 128.0, "165": 278.0, "166": 190.0, "167": 194.0, "168": 190.0, "169": 194.0,
    "170": 194.0, "171": 190.0, "172": 184.0, "173": 170.0, "174": 204.0, "175": 214.0, "176": 214.0, "177": 194.0, "178": 184.0, "179": 194.0,
    "180": 1040.0, "181": 1040.0, "182": 1940.0, "183": 1040.0, "184": 1940.0, "185": 1940.0, "186": 375.0, "187": 375.0
}
COUNTRY_PRICES = {k: (78.0 if v == 40.0 else v) for k, v in COUNTRY_PRICES.items()}

DEFAULT_PRICE = 250.0  

COUNTRY_NAMES = {
    "0": "🇷🇺 Russia", "1": "🇺🇦 Ukraine", "2": "🇰🇿 Kazakhstan", "3": "🇨🇳 China", "4": "🇵🇭 Philippines",
    "5": "🇲🇲 Myanmar", "6": "🇮🇩 Indonesia", "7": "🇲🇾 Malaysia", "8": "🇰🇪 Kenya", "9": "🇹🇿 Tanzania",
    "10": "🇻🇳 Vietnam", "11": "🇰🇬 Kyrgyzstan", "12": "🇺🇸 USA", "13": "🇮🇱 Israel", "14": "🇭🇰 Hong Kong",
    "15": "🇵🇱 Poland", "16": "🇬🇧 UK", "17": "🇲🇬 Madagascar", "18": "🇨🇬 Congo", "19": "🇳🇬 Nigeria",
    "20": "🇲🇴 Macau", "21": "🇪🇬 Egypt", "22": "🇮🇳 India", "23": "🇮🇪 Ireland", "24": "🇰🇭 Cambodia",
    "25": "🇱🇦 Laos", "26": "🇭🇹 Haiti", "27": "🇨🇮 Ivory Coast", "28": "🇬🇲 Gambia", "29": "🇸🇪 Sweden",
    "30": "🇮🇶 Iraq", "31": "🇿🇦 South Africa", "32": "🇷🇴 Romania", "33": "🇨🇴 Colombia", "34": "🇪🇪 Estonia",
    "35": "🇦🇿 Azerbaijan", "36": "🇨🇦 Canada", "37": "🇲🇦 Morocco", "38": "🇬🇭 Ghana", "39": "🇦🇷 Argentina",
    "40": "🇺🇿 Uzbekistan", "41": "🇨🇲 Cameroon", "42": "🇹🇩 Chad", "43": "🇩🇪 Germany", "44": "🇱🇹 Lithuania",
    "45": "🇭🇷 Croatia", "46": "🇸🇮 Slovenia", "47": "🇸🇳 Senegal", "48": "🇵🇹 Portugal", "49": "🇹🇷 Turkey",
    "50": "🇨🇿 Czechia", "51": "🇱🇺 Luxembourg", "52": "🇱🇰 Sri Lanka", "53": "🇵🇪 Peru", "54": "🇵🇰 Pakistan",
    "55": "🇳🇿 New Zealand", "56": "🇬🇳 Guinea", "57": "🇲🇱 Mali", "58": "🇻🇪 Venezuela", "59": "🇪🇹 Ethiopia",
    "60": "🇲🇳 Mongolia", "61": "🇧🇷 Brazil", "62": "🇦🇫 Afghanistan", "63": "🇺🇬 Uganda", "64": "🇦🇴 Angola",
    "65": "🇨🇾 Cyprus", "66": "🇫🇷 France", "67": "🇿🇼 Zimbabwe", "68": "🇲🇼 Malawi", "69": "🇳🇦 Namibia",
    "70": "🇳🇪 Niger", "71": "🇷🇼 Rwanda", "72": "🇸🇱 Sierra Leone", "73": "🇸🇴 Somalia", "74": "🇸🇩 Sudan",
    "75": "🇸🇿 Eswatini", "76": "🇹🇬 Togo", "77": "🇿🇲 Zambia", "78": "🇦🇱 Albania", "79": "🇦🇲 Armenia",
    "80": "🇦🇹 Austria", "81": "🇧🇾 Belarus", "82": "🇧🇪 Belgium", "83": "🇧🇦 Bosnia", "84": "🇧🇬 Bulgaria",
    "85": "🇩🇰 Denmark", "86": "🇪🇸 Spain", "87": "🇫🇮 Finland", "88": "🇬🇪 Georgia", "89": "🇬🇷 Greece",
    "90": "🇭🇺 Hungary", "91": "🇮🇸 Iceland", "92": "🇮🇹 Italy", "93": "🇧🇩 Bangladesh", "94": "🇱🇻 Latvia",
    "95": "🇱🇮 Liechtenstein", "96": "🇲🇰 N. Macedonia", "97": "🇲🇹 Malta", "98": "🇲🇩 Moldova", "99": "🇲🇨 Monaco",
    "100": "🇲🇪 Montenegro", "101": "🇳🇱 Netherlands", "102": "🇳🇴 Norway", "103": "🇸🇰 Slovakia", "104": "🇨🇭 Switzerland",
    "105": "🇹🇭 Thailand", "106": "🇯🇵 Japan", "107": "🇰🇷 South Korea", "108": "🇸🇦 Saudi Arabia", "109": "🇦🇪 UAE",
    "110": "🇯🇴 Jordan", "111": "🇱🇧 Lebanon", "112": "🇴🇲 Oman", "113": "🇶🇦 Qatar", "114": "🇰🇼 Kuwait",
    "115": "🇧🇭 Bahrain", "116": "🇾🇪 Yemen", "117": "🇲🇽 Mexico", "118": "🇨🇷 Costa Rica", "119": "🇵🇦 Panama",
    "120": "🇨🇺 Cuba", "121": "🇩🇴 Dominican Rep.", "122": "🇯🇲 Jamaica", "123": "🇧🇴 Bolivia", "124": "🇪🇨 Ecuador",
    "125": "🇵🇾 Paraguay", "126": "🇺🇾 Uruguay", "127": "🇹🇼 Taiwan", "128": "🇸🇬 Singapore", "129": "🇳🇵 Nepal",
    "130": "🇧🇹 Bhutan", "131": "🇲🇻 Maldives", "132": "🇧🇳 Brunei", "133": "🇹🇲 Turkmenistan", "134": "🇹🇯 Tajikistan",
    "135": "🇸🇾 Syria", "136": "🇵🇸 Palestine", "137": "🇱🇾 Libya", "138": "🇹🇳 Tunisia", "139": "🇩🇿 Algeria",
    "140": "🇲🇷 Mauritania", "141": "🇪🇷 Eritrea", "142": "🇩🇯 Djibouti", "143": "🇸🇸 South Sudan", "144": "🇦🇺 Australia",
    "145": "🇵🇬 Papua New Guinea", "146": "🇫🇯 Fiji", "147": "🇸🇧 Solomon Is.", "148": "🇻🇺 Vanuatu", "149": "🇼🇸 Samoa",
    "150": "🇹🇴 Tonga", "151": "🇧🇿 Belize", "152": "🇬🇹 Guatemala", "153": "🇸🇻 El Salvador", "154": "🇭🇳 Honduras",
    "155": "🇳🇮 Nicaragua", "156": "🇬🇾 Guyana", "157": "🇸🇷 Suriname", "158": "🇧🇸 Bahamas", "159": "🇧🇧 Barbados",
    "160": "🇹🇹 Trinidad", "161": "🇬🇩 Grenada", "162": "🇱🇨 St. Lucia", "163": "🇻🇨 St. Vincent", "164": "🇦🇬 Antigua",
    "165": "🇰🇳 St. Kitts", "166": "🇩🇲 Dominica", "167": "🇨🇻 Cape Verde", "168": "🇸🇹 Sao Tome", "169": "🇬🇼 Guinea-Bissau",
    "170": "🇬🇶 Eq. Guinea", "171": "🇬🇦 Gabon", "172": "🇨🇫 CAR", "173": "🇰🇲 Comoros", "174": "🇲🇺 Mauritius",
    "175": "🇸🇨 Seychelles", "176": "🇱🇸 Lesotho", "177": "🇧🇼 Botswana", "178": "🇦🇩 Andorra", "179": "🇸🇲 San Marino",
    "180": "🇻🇦 Vatican", "181": "🇲🇨 Monaco", "182": "🇯🇵 Japan", "183": "🇰🇷 S. Korea", "184": "🇹🇼 Taiwan",
    "185": "🇭🇰 Hong Kong", "186": "🇲🇴 Macau", "187": "🇸🇬 Singapore"
}

def get_all_country_list():
    full_list = []
    for code, name in COUNTRY_NAMES.items():
        price = COUNTRY_PRICES.get(code, DEFAULT_PRICE)
        # Keeping flag emoji included with name for buttons
        full_list.append({"name": f"{name} - ₹{price:.2f}", "code": code, "raw_name": name, "price": price})
    full_list.sort(key=lambda x: x["raw_name"])
    return full_list

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
        params = {"api_key": self.api_key, "action": "getNumber", "service": service, "country": country}
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.base_url, params=params, timeout=15)
                text = response.text.strip()
                if text.startswith("ACCESS_NUMBER"):
                    parts = text.split(":")
                    if len(parts) >= 3:
                        return {"status": "SUCCESS", "id": parts[1], "number": parts[2]}
                return {"status": "ERROR", "message": f"Provider error: {text}"}
            except Exception as e: 
                return {"status": "ERROR", "message": str(e)}

    async def get_status(self, order_id: str):
        params = {"api_key": self.api_key, "action": "getStatus", "id": order_id}
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.base_url, params=params, timeout=12)
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
                        user_balances[referrer_id] = current_ref_bal + 5.0
                        
                        try:
                            await context.bot.send_message(
                                chat_id=referrer_id,
                                text=f"🎉 <b>Referral Bonus Earned!</b>\n\nA new user joined via your link. ₹5.00 has been added to your balance.\nNew Balance: ₹{user_balances[referrer_id]:.2f}",
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
        [InlineKeyboardButton("🛒 Buy Number (180+ Countries)", callback_data="buy_menu_0")], 
        [InlineKeyboardButton("🎁 Gift", callback_data="gift_menu"), InlineKeyboardButton("👥 Refer & Earn", callback_data="refer_menu")],
        [InlineKeyboardButton("💳 Deposit", callback_data="deposit_menu")]
    ]
    
    if update.message:
        await update.message.reply_text("Loading Bot Menu...", reply_markup=bottom_markup)
        await update.message.reply_text(f"👋 Welcome, <b>{user.first_name}</b>!\n\nSelect an option below:", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard))
    elif update.callback_query:
        await safe_send_or_edit(update, context, f"👋 Welcome, <b>{user.first_name}</b>!\n\nSelect an option below:", InlineKeyboardMarkup(inline_keyboard))

async def show_countries(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    all_countries = get_all_country_list()
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
        all_countries = get_all_country_list()
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
            f"Earn <b>₹5.00</b> directly into your balance for every unique user who starts the bot using your referral link!\n\n"
            f"📊 <b>Your Total Valid Referrals:</b> {refs}\n"
            f"💰 <b>Total Earned:</b> ₹{refs * 5.00:.2f}\n\n"
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
            f"Earn <b>₹5.00</b> directly into your balance for every unique user who starts the bot using your referral link!\n\n"
            f"📊 <b>Your Total Valid Referrals:</b> {refs}\n"
            f"💰 <b>Total Earned:</b> ₹{refs * 5.00:.2f}\n\n"
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
                country_name = COUNTRY_NAMES.get(country_code, f"Country {country_code}")
                await context.bot.send_message(
                    chat_id=ADMIN_CHANNEL_ID,
                    text=(
                        f"🛒 <b>New Number Purchased!</b>\n\n"
                        f"• <b>Buyer:</b> {buyer.first_name} ({buyer_username})\n"
                        f"• <b>Buyer ID:</b> <code>{buyer.id}</code>\n"
                        f"• <b>Country:</b> {country_name}\n"
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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    app.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_photo_messages))
    app.add_handler(CallbackQueryHandler(button_router))
    print("🚀 Bot Online with Country Flags Included, Indonesia (₹50), USA (₹115), and All Features!")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app.run_polling()

if __name__ == "__main__":
    main()
