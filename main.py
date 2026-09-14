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
# ☁️ CLOUD STORAGE FUNCTIONS
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
    headers = {"Content-Type": "application/json", "X-Master-Key": JSONBIN_API_KEY}
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
ITEMS_PER_PAGE = 14  

# ==========================================
# 📋 FIXED SMS-ACTIVATE ID PROTOCOL DATABASE 
# ==========================================
COUNTRY_DATABASE = [
    {"code": "74", "name": "🇦🇫 Afghanistan", "price": 111.31},
    {"code": "155", "name": "🇦🇱 Albania", "price": 77.07},
    {"code": "58", "name": "🇩🇿 Algeria", "price": 92.05},
    {"code": "197", "name": "🇼🇸 American Samoa", "price": 172.59},
    {"code": "189", "name": "🇦🇩 Andorra", "price": 83.34},
    {"code": "76", "name": "🇦🇴 Angola", "price": 117.74},
    {"code": "181", "name": "🇦🇮 Anguilla", "price": 117.74},
    {"code": "39", "name": "🇦🇷 Argentina", "price": 139.15},
    {"code": "148", "name": "🇦🇲 Armenia", "price": 158.42},
    {"code": "179", "name": "🇦🇼 Aruba", "price": 96.34},
    {"code": "175", "name": "🇦🇺 Australia", "price": 599.41},
    {"code": "50", "name": "🇦🇹 Austria", "price": 636.87},
    {"code": "35", "name": "🇦🇿 Azerbaijan", "price": 115.60},
    {"code": "145", "name": "🇧🇭 Bahrain", "price": 115.60},
    {"code": "60", "name": "🇧🇩 Bangladesh", "price": 111.31},
    {"code": "51", "name": "🇧🇾 Belarus", "price": 150.53},
    {"code": "82", "name": "🇧🇪 Belgium", "price": 337.16},
    {"code": "124", "name": "🇧🇿 Belize", "price": 96.34},
    {"code": "120", "name": "🇧🇯 Benin", "price": 111.31},
    {"code": "200", "name": "🇧🇲 Bermuda", "price": 126.30},
    {"code": "108", "name": "🇧🇦 Bosnia and Herzegovina", "price": 74.93},
    {"code": "123", "name": "🇧🇼 Botswana", "price": 150.00},
    {"code": "73", "name": "🇧🇷 Brazil", "price": 240.83},
    {"code": "83", "name": "🇧🇬 Bulgaria", "price": 276.96},
    {"code": "152", "name": "🇧🇫 Burkina Faso", "price": 111.31},
    {"code": "119", "name": "🇧🇮 Burundi", "price": 104.90},
    {"code": "24", "name": "🇰🇭 Cambodia", "price": 147.71},
    {"code": "41", "name": "🇨🇲 Cameroon", "price": 94.19},
    {"code": "36", "name": "🇨🇦 Canada", "price": 168.80},
    {"code": "186", "name": "🇨🇻 Cape Verde", "price": 81.34},
    {"code": "170", "name": "🇰🇾 Cayman Islands", "price": 81.34},
    {"code": "42", "name": "🇹🇩 Chad", "price": 126.30},
    {"code": "3", "name": "🇨🇳 China", "price": 128.45},
    {"code": "33", "name": "🇨🇴 Colombia", "price": 72.25},
    {"code": "133", "name": "🇰🇲 Comoros", "price": 85.63},
    {"code": "93", "name": "🇨🇷 Costa Rica", "price": 77.07},
    {"code": "45", "name": "🇭🇷 Croatia", "price": 260.90},
    {"code": "77", "name": "🇨🇾 Cyprus", "price": 352.16},
    {"code": "63", "name": "🇨🇿 Czechia", "price": 240.83},
    {"code": "172", "name": "🇩🇰 Denmark", "price": 202.70},
    {"code": "168", "name": "🇩🇯 Djibouti", "price": 81.34},
    {"code": "109", "name": "🇩🇴 Dominican Republic", "price": 74.93},
    {"code": "18", "name": "🇨🇩 DR Congo", "price": 96.34},
    {"code": "21", "name": "🇪🇬 Egypt", "price": 96.34},
    {"code": "167", "name": "🇬🇶 Equatorial Guinea", "price": 92.05},
    {"code": "176", "name": "🇪🇷 Eritrea", "price": 96.34},
    {"code": "34", "name": "🇪🇪 Estonia", "price": 172.59},
    {"code": "71", "name": "🇪🇹 Ethiopia", "price": 107.04},
    {"code": "163", "name": "🇫🇮 Finland", "price": 421.46},
    {"code": "78", "name": "🇫🇷 France", "price": 468.29},
    {"code": "162", "name": "🇬🇫 French Guiana", "price": 81.34},
    {"code": "154", "name": "🇬🇦 Gabon", "price": 107.04},
    {"code": "28", "name": "🇬🇲 Gambia", "price": 92.05},
    {"code": "128", "name": "🇬🇪 Georgia", "price": 156.27},
    {"code": "43", "name": "🇩🇪 Germany", "price": 280.97},
    {"code": "38", "name": "🇬🇭 Ghana", "price": 92.05},
    {"code": "198", "name": "🇬🇮 Gibraltar", "price": 4214.56},
    {"code": "129", "name": "🇬🇷 Greece", "price": 160.56},
    {"code": "190", "name": "🇬🇱 Greenland", "price": 83.34},
    {"code": "160", "name": "🇬🇵 Guadeloupe", "price": 81.34},
    {"code": "94", "name": "🇬🇹 Guatemala", "price": 126.30},
    {"code": "68", "name": "🇬🇳 Guinea", "price": 109.18},
    {"code": "131", "name": "🇬🇾 Guyana", "price": 126.30},
    {"code": "26", "name": "🇭🇹 Haiti", "price": 92.05},
    {"code": "88", "name": "🇭🇳 Honduras", "price": 126.30},
    {"code": "14", "name": "🇭🇰 Hong Kong", "price": 81.34},
    {"code": "84", "name": "🇭🇺 Hungary", "price": 226.79},
    {"code": "132", "name": "🇮🇸 Iceland", "price": 126.30},
    {"code": "22", "name": "🇮🇳 India", "price": 187.00},
    {"code": "6", "name": "🇮🇩 Indonesia", "price": 50.00},
    {"code": "57", "name": "🇮🇷 Iran", "price": 104.90},
    {"code": "47", "name": "🇮🇶 Iraq", "price": 107.04},
    {"code": "23", "name": "🇮🇪 Ireland", "price": 1685.82},
    {"code": "13", "name": "🇮🇱 Israel", "price": 226.79},
    {"code": "86", "name": "🇮🇹 Italy", "price": 543.21},
    {"code": "27", "name": "🇨🇮 Ivory Coast", "price": 111.31},
    {"code": "103", "name": "🇯🇲 Jamaica", "price": 98.48},
    {"code": "182", "name": "🇯🇵 Japan", "price": 2200.94},
    {"code": "116", "name": "🇯🇴 Jordan", "price": 74.93},
    {"code": "2", "name": "🇰🇿 Kazakhstan", "price": 248.87},
    {"code": "8", "name": "🇰🇪 Kenya", "price": 111.31},
    {"code": "202", "name": "🇽🇰 Kosovo", "price": 100.61},
    {"code": "100", "name": "🇰🇼 Kuwait", "price": 226.79},
    {"code": "11", "name": "🇰🇬 Kyrgyzstan", "price": 92.05},
    {"code": "25", "name": "🇱🇦 Lao", "price": 130.59},
    {"code": "49", "name": "🇱🇻 Latvia", "price": 128.45},
    {"code": "153", "name": "🇱🇧 Lebanon", "price": 104.90},
    {"code": "135", "name": "🇱🇷 Liberia", "price": 92.05},
    {"code": "102", "name": "🇱🇾 Libya", "price": 119.89},
    {"code": "203", "name": "🇱🇮 Liechtenstein", "price": 172.59},
    {"code": "44", "name": "🇱🇹 Lithuania", "price": 220.77},
    {"code": "165", "name": "🇱🇺 Luxembourg", "price": 107.04},
    {"code": "20", "name": "🇲🇴 Macao", "price": 262.91},
    {"code": "17", "name": "🇲🇬 Madagascar", "price": 92.05},
    {"code": "137", "name": "🇲🇼 Malawi", "price": 92.05},
    {"code": "7", "name": "🇲🇾 Malaysia", "price": 85.63},
    {"code": "159", "name": "🇲🇻 Maldives", "price": 126.30},
    {"code": "69", "name": "🇲🇱 Mali", "price": 130.59},
    {"code": "204", "name": "🇲🇹 Malta", "price": 60.00},
    {"code": "114", "name": "🇲🇷 Mauritania", "price": 298.50},
    {"code": "157", "name": "🇲🇺 Mauritius", "price": 85.63},
    {"code": "54", "name": "🇲🇽 Mexico", "price": 145.57},
    {"code": "85", "name": "🇲🇩 Moldova", "price": 172.59},
    {"code": "144", "name": "🇲🇨 Monaco", "price": 113.46},
    {"code": "72", "name": "🇲🇳 Mongolia", "price": 195.00},
    {"code": "171", "name": "🇲🇪 Montenegro", "price": 126.30},
    {"code": "180", "name": "🇲🇸 Montserrat", "price": 126.30},
    {"code": "37", "name": "🇲🇦 Morocco", "price": 133.47},
    {"code": "80", "name": "🇲🇿 Mozambique", "price": 119.89},
    {"code": "5", "name": "🇲🇲 Myanmar", "price": 119.89},
    {"code": "138", "name": "🇳🇦 Namibia", "price": 109.18},
    {"code": "81", "name": "🇳🇵 Nepal", "price": 126.30},
    {"code": "48", "name": "🇳🇱 Netherlands", "price": 206.72},
    {"code": "185", "name": "🇳🇨 New Caledonia", "price": 85.63},
    {"code": "67", "name": "🇳🇿 New Zealand", "price": 505.75},
    {"code": "90", "name": "🇳🇮 Nicaragua", "price": 126.30},
    {"code": "139", "name": "🇳🇪 Niger", "price": 104.90},
    {"code": "19", "name": "🇳🇬 Nigeria", "price": 113.46},
    {"code": "193", "name": "🇳🇺 Niue", "price": 113.46},
    {"code": "174", "name": "🇳🇴 Norway", "price": 162.56},
    {"code": "107", "name": "🇴🇲 Oman", "price": 60.00},
    {"code": "66", "name": "🇵🇰 Pakistan", "price": 468.29},
    {"code": "191", "name": "🇵🇸 Palestine", "price": 138.90},
    {"code": "112", "name": "🇵🇦 Panama", "price": 130.59},
    {"code": "79", "name": "🇵🇬 Papua New Guinea", "price": 139.15},
    {"code": "87", "name": "🇵🇾 Paraguay", "price": 162.56},
    {"code": "65", "name": "🇵🇪 Peru", "price": 107.04},
    {"code": "4", "name": "🇵🇭 Philippines", "price": 69.57},
    {"code": "15", "name": "🇵🇱 Poland", "price": 158.42},
    {"code": "117", "name": "🇵🇹 Portugal", "price": 283.50},
    {"code": "97", "name": "🇵🇷 Puerto Rico", "price": 126.30},
    {"code": "111", "name": "🇶🇦 Qatar", "price": 113.46},
    {"code": "146", "name": "🇷🇪 Reunion", "price": 85.63},
    {"code": "32", "name": "🇷🇴 Romania", "price": 212.73},
    {"code": "0", "name": "🇷🇺 Russia", "price": 350.00},
    {"code": "140", "name": "🇷🇼 Rwanda", "price": 267.00},
    {"code": "134", "name": "🇰🇳 Saint Kitts & Nevis", "price": 126.30},
    {"code": "164", "name": "🇱🇨 Saint Lucia", "price": 81.34},
    {"code": "166", "name": "🇻🇨 Saint Vincent", "price": 81.34},
    {"code": "101", "name": "🇸🇻 Salvador", "price": 126.30},
    {"code": "194", "name": "🇼🇸 Samoa", "price": 172.59},
    {"code": "178", "name": "🇸🇹 Sao Tome & Principe", "price": 81.34},
    {"code": "53", "name": "🇸🇦 Saudi Arabia", "price": 85.63},
    {"code": "61", "name": "🇸🇳 Senegal", "price": 113.46},
    {"code": "29", "name": "🇷🇸 Serbia", "price": 128.45},
    {"code": "184", "name": "🇸🇨 Seychelles", "price": 85.63},
    {"code": "115", "name": "🇸🇱 Sierra Leone", "price": 92.05},
    {"code": "205", "name": "🇸🇬 Singapore", "price": 936.57},
    {"code": "196", "name": "🇸🇽 Sint Maarten", "price": 172.59},
    {"code": "141", "name": "🇸🇰 Slovakia", "price": 113.46},
    {"code": "59", "name": "🇸🇮 Slovenia", "price": 220.77},
    {"code": "149", "name": "🇸🇴 Somalia", "price": 250.50},
    {"code": "31", "name": "🇿🇦 South Africa", "price": 60.00},
    {"code": "206", "name": "🇰🇷 South Korea", "price": 172.59},
    {"code": "177", "name": "🇸🇸 South Sudan", "price": 74.93},
    {"code": "56", "name": "🇪🇸 Spain", "price": 355.89},
    {"code": "64", "name": "🇱🇰 Sri Lanka", "price": 119.89},
    {"code": "98", "name": "🇸🇩 Sudan", "price": 298.50},
    {"code": "142", "name": "🇸🇷 Suriname", "price": 113.46},
    {"code": "106", "name": "🇸🇿 Swaziland", "price": 92.05},
    {"code": "46", "name": "🇸🇪 Sweden", "price": 188.66},
    {"code": "173", "name": "🇨🇭 Switzerland", "price": 375.00},
    {"code": "110", "name": "🇸🇾 Syria", "price": 80.00},
    {"code": "55", "name": "🇹🇼 Taiwan", "price": 878.50},
    {"code": "143", "name": "🇹🇯 Tajikistan", "price": 92.05},
    {"code": "9", "name": "🇹🇿 Tanzania", "price": 92.05},
    {"code": "52", "name": "🇹🇭 Thailand", "price": 113.46},
    {"code": "91", "name": "🇹🇱 Timor-Leste", "price": 126.30},
    {"code": "99", "name": "🇹🇬 Togo", "price": 149.86},
    {"code": "195", "name": "🇹🇴 Tonga", "price": 172.59},
    {"code": "104", "name": "🇹🇹 Trinidad and Tobago", "price": 74.93},
    {"code": "89", "name": "🇹🇳 Tunisia", "price": 126.30},
    {"code": "62", "name": "🇹🇷 Turkey", "price": 126.30},
    {"code": "161", "name": "🇹🇲 Turkmenistan", "price": 126.30},
    {"code": "95", "name": "🇦🇪 UAE", "price": 160.56},
    {"code": "75", "name": "🇺🇬 Uganda", "price": 297.00},
    {"code": "1", "name": "🇺🇦 Ukraine", "price": 119.89},
    {"code": "16", "name": "🇬🇧 United Kingdom", "price": 92.05},
    {"code": "156", "name": "🇺🇾 Uruguay", "price": 130.59},
    {"code": "12", "name": "🇺🇸 USA", "price": 120.00},
    {"code": "40", "name": "🇺🇿 Uzbekistan", "price": 113.46},
    {"code": "192", "name": "🇻🇺 Vanuatu", "price": 150.00},
    {"code": "207", "name": "🇻🇦 Vatican", "price": 350.00},
    {"code": "70", "name": "🇻🇪 Venezuela", "price": 77.07},
    {"code": "10", "name": "🇻🇳 Vietnam", "price": 148.50},
    {"code": "30", "name": "🇾🇪 Yemen", "price": 70.00},
    {"code": "147", "name": "🇿🇲 Zambia", "price": 92.05},
    {"code": "96", "name": "🇿🇼 Zimbabwe", "price": 93.12}
]

def get_all_country_list():
    sorted_list = sorted(COUNTRY_DATABASE, key=lambda x: x["name"])
    formatted_list = []
    for c in sorted_list:
        formatted_list.append({
            "name": f"{c['name']} - ₹{c['price']:.2f}",
            "code": str(c["code"]),
            "raw_name": c["name"].split(" ", 1)[1] if " " in c["name"] else c["name"],
            "price": float(c["price"])
        })
    return formatted_list

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
        params = {
            "api_key": self.api_key, 
            "action": "getNumber", 
            "service": service, 
            "country": str(country),
            "format": "json"
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.base_url, params=params, timeout=15)
                try:
                    data = response.json()
                except Exception:
                    text = response.text.strip()
                    if text.startswith("ACCESS_NUMBER"):
                        parts = text.split(":")
                        if len(parts) >= 3:
                            return {"status": "SUCCESS", "id": parts[1], "number": parts[2]}
                    return {"status": "ERROR", "message": f"Provider error: {text}"}

                if isinstance(data, dict):
                    if data.get("status") == "OK" or "activation_id" in data or "order_id" in data:
                        activation_id = str(data.get("activation_id") or data.get("order_id"))
                        phone_number = str(data.get("phone_number") or data.get("number"))
                        return {"status": "SUCCESS", "id": activation_id, "number": phone_number}
                    
                    err_msg = data.get("msg") or data.get("message") or data.get("error") or "Temporarily out of stock."
                    return {"status": "ERROR", "message": f"Provider error: {err_msg}"}
                
                return {"status": "ERROR", "message": f"Provider error: {response.text.strip()}"}

            except Exception as e: 
                return {"status": "ERROR", "message": str(e)}

    # 🔧 FIX 1: The correct plain text parser for getStatus so OTPs actually arrive!
    async def get_status(self, order_id: str):
        params = {"api_key": self.api_key, "action": "getStatus", "id": order_id}
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.base_url, params=params, timeout=12)
                text = response.text.strip()
                if text.startswith("STATUS_OK"):
                    parts = text.split(":")
                    code = parts[1] if len(parts) > 1 else "Received"
                    return {"status": "RECEIVED", "code": code}
                elif text in ["STATUS_WAIT_CODE", "STATUS_WAIT_RESEND", "STATUS_WAIT_RETRY"]:
                    return {"status": "WAITING"}
                elif text == "STATUS_CANCEL":
                    return {"status": "CANCELLED"}
                else:
                    return {"status": "OTHER", "message": text}
            except Exception as e: 
                return {"status": "ERROR", "message": str(e)}

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

    # Record the user if new
    if user_id not in user_usernames:
        user_usernames[user_id] = username
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHANNEL_ID,
           app.add_handler(CommandHandler("send", send_to_user))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    app.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_photo_messages))
    app.add_handler(CallbackQueryHandler(button_router

if __name__ == "__main__":
    main()
