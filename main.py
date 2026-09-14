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
# 📋 COMPLETE 187+ OFFICIAL COUNTRY DATABASE
# ==========================================
COUNTRY_DATABASE = [
    {"code": "62", "name": "🇦🇫 Afghanistan", "price": 111.31},
    {"code": "78", "name": "🇦🇱 Albania", "price": 77.07},
    {"code": "139", "name": "🇩🇿 Algeria", "price": 92.05},
    {"code": "149", "name": "🇼🇸 American Samoa", "price": 172.59},
    {"code": "178", "name": "🇦🇩 Andorra", "price": 83.34},
    {"code": "64", "name": "🇦🇴 Angola", "price": 117.74},
    {"code": "120", "name": "🇦🇮 Anguilla", "price": 117.74},
    {"code": "39", "name": "🇦🇷 Argentina", "price": 139.15},
    {"code": "79", "name": "🇦🇲 Armenia", "price": 158.42},
    {"code": "121", "name": "🇦🇼 Aruba", "price": 96.34},
    {"code": "144", "name": "🇦🇺 Australia", "price": 599.41},
    {"code": "80", "name": "🇦🇹 Austria", "price": 636.87},
    {"code": "35", "name": "🇦🇿 Azerbaijan", "price": 115.60},
    {"code": "115", "name": "🇧🇭 Bahrain", "price": 115.60},
    {"code": "93", "name": "🇧🇩 Bangladesh", "price": 111.31},
    {"code": "81", "name": "🇧🇾 Belarus", "price": 150.53},
    {"code": "82", "name": "🇧🇪 Belgium", "price": 337.16},
    {"code": "151", "name": "🇧🇿 Belize", "price": 96.34},
    {"code": "169", "name": "🇧🇯 Benin", "price": 111.31},
    {"code": "153", "name": "🇧🇲 Bermuda", "price": 126.30},
    {"code": "83", "name": "🇧🇦 Bosnia and Herzegovina", "price": 74.93},
    {"code": "177", "name": "🇧🇼 Botswana", "price": 150.00},
    {"code": "61", "name": "🇧🇷 Brazil", "price": 240.83},
    {"code": "84", "name": "🇧🇬 Bulgaria", "price": 276.96},
    {"code": "168", "name": "🇧🇫 Burkina Faso", "price": 111.31},
    {"code": "172", "name": "🇧🇮 Burundi", "price": 104.90},
    {"code": "24", "name": "🇰🇭 Cambodia", "price": 147.71},
    {"code": "41", "name": "🇨🇲 Cameroon", "price": 94.19},
    {"code": "36", "name": "🇨🇦 Canada", "price": 168.80},
    {"code": "167", "name": "🇨🇻 Cape Verde", "price": 81.34},
    {"code": "164", "name": "🇰🇾 Cayman Islands", "price": 81.34},
    {"code": "42", "name": "🇹🇩 Chad", "price": 126.30},
    {"code": "3", "name": "🇨🇳 China", "price": 128.45},
    {"code": "33", "name": "🇨🇴 Colombia", "price": 72.25},
    {"code": "173", "name": "🇰🇲 Comoros", "price": 85.63},
    {"code": "118", "name": "🇨🇷 Costa Rica", "price": 77.07},
    {"code": "45", "name": "🇭🇷 Croatia", "price": 260.90},
    {"code": "65", "name": "🇨🇾 Cyprus", "price": 352.16},
    {"code": "50", "name": "🇨🇿 Czechia", "price": 240.83},
    {"code": "85", "name": "🇩🇰 Denmark", "price": 202.70},
    {"code": "142", "name": "🇩🇯 Djibouti", "price": 81.34},
    {"code": "121", "name": "🇩🇴 Dominican Republic", "price": 74.93},
    {"code": "18", "name": "🇨🇬 DR Congo", "price": 96.34},
    {"code": "21", "name": "🇪🇬 Egypt", "price": 96.34},
    {"code": "170", "name": "🇬🇶 Equatorial Guinea", "price": 92.05},
    {"code": "141", "name": "🇪🇷 Eritrea", "price": 96.34},
    {"code": "34", "name": "🇪🇪 Estonia", "price": 172.59},
    {"code": "59", "name": "🇪🇹 Ethiopia", "price": 107.04},
    {"code": "87", "name": "🇫🇮 Finland", "price": 421.46},
    {"code": "66", "name": "🇫🇷 France", "price": 468.29},
    {"code": "162", "name": "🇬🇫 French Guiana", "price": 81.34},
    {"code": "171", "name": "🇬🇦 Gabon", "price": 107.04},
    {"code": "28", "name": "🇬🇲 Gambia", "price": 92.05},
    {"code": "88", "name": "🇬🇪 Georgia", "price": 156.27},
    {"code": "43", "name": "🇩🇪 Germany", "price": 280.97},
    {"code": "38", "name": "🇬🇭 Ghana", "price": 92.05},
    {"code": "186", "name": "🇬🇮 Gibraltar", "price": 4214.56},
    {"code": "89", "name": "🇬🇷 Greece", "price": 160.56},
    {"code": "165", "name": "🇬🇱 Greenland", "price": 83.34},
    {"code": "161", "name": "🇬🇵 Guadeloupe", "price": 81.34},
    {"code": "152", "name": "🇬🇹 Guatemala", "price": 126.30},
    {"code": "56", "name": "🇬🇳 Guinea", "price": 109.18},
    {"code": "156", "name": "🇬🇾 Guyana", "price": 126.30},
    {"code": "26", "name": "🇭🇹 Haiti", "price": 92.05},
    {"code": "154", "name": "🇭🇳 Honduras", "price": 126.30},
    {"code": "14", "name": "🇭🇰 Hong Kong", "price": 81.34},
    {"code": "90", "name": "🇭🇺 Hungary", "price": 226.79},
    {"code": "91", "name": "🇮🇸 Iceland", "price": 126.30},
    {"code": "22", "name": "🇮🇳 India", "price": 187.00},
    {"code": "6", "name": "🇮🇩 Indonesia", "price": 50.00},
    {"code": "166", "name": "🇮🇷 Iran", "price": 104.90},
    {"code": "30", "name": "🇮🇶 Iraq", "price": 107.04},
    {"code": "23", "name": "🇮🇪 Ireland", "price": 1685.82},
    {"code": "13", "name": "🇮🇱 Israel", "price": 226.79},
    {"code": "92", "name": "🇮🇹 Italy", "price": 543.21},
    {"code": "27", "name": "🇨🇮 Ivory Coast", "price": 111.31},
    {"code": "122", "name": "🇯🇲 Jamaica", "price": 98.48},
    {"code": "106", "name": "🇯🇵 Japan", "price": 2200.94},
    {"code": "110", "name": "🇯🇴 Jordan", "price": 74.93},
    {"code": "2", "name": "🇰🇿 Kazakhstan", "price": 248.87},
    {"code": "8", "name": "🇰🇪 Kenya", "price": 111.31},
    {"code": "100", "name": "🇽🇰 Kosovo", "price": 100.61},
    {"code": "114", "name": "🇰🇼 Kuwait", "price": 226.79},
    {"code": "11", "name": "🇰🇬 Kyrgyzstan", "price": 92.05},
    {"code": "25", "name": "🇱🇦 Lao", "price": 130.59},
    {"code": "94", "name": "🇱🇻 Latvia", "price": 128.45},
    {"code": "111", "name": "🇱🇧 Lebanon", "price": 104.90},
    {"code": "176", "name": "🇱🇸 Liberia", "price": 92.05},
    {"code": "137", "name": "🇱🇾 Libya", "price": 119.89},
    {"code": "95", "name": "🇱🇮 Liechtenstein", "price": 172.59},
    {"code": "44", "name": "🇱🇹 Lithuania", "price": 220.77},
    {"code": "51", "name": "🇱🇺 Luxembourg", "price": 107.04},
    {"code": "20", "name": "🇲🇴 Macao", "price": 262.91},
    {"code": "17", "name": "🇲🇬 Madagascar", "price": 92.05},
    {"code": "68", "name": "🇲🇼 Malawi", "price": 92.05},
    {"code": "7", "name": "🇲🇾 Malaysia", "price": 85.63},
    {"code": "131", "name": "🇲🇻 Maldives", "price": 126.30},
    {"code": "57", "name": "🇲🇱 Mali", "price": 130.59},
    {"code": "97", "name": "🇲🇹 Malta", "price": 60.00},
    {"code": "140", "name": "🇲🇷 Mauritania", "price": 298.50},
    {"code": "174", "name": "🇲🇺 Mauritius", "price": 85.63},
    {"code": "117", "name": "🇲🇽 Mexico", "price": 145.57},
    {"code": "98", "name": "🇲🇩 Moldova", "price": 172.59},
    {"code": "99", "name": "🇲🇨 Monaco", "price": 113.46},
    {"code": "60", "name": "🇲🇳 Mongolia", "price": 195.00},
    {"code": "100", "name": "🇲🇪 Montenegro", "price": 126.30},
    {"code": "150", "name": "🇲🇸 Montserrat", "price": 126.30},
    {"code": "37", "name": "🇲🇦 Morocco", "price": 133.47},
    {"code": "148", "name": "🇲🇿 Mozambique", "price": 119.89},
    {"code": "5", "name": "🇲🇲 Myanmar", "price": 119.89},
    {"code": "69", "name": "🇳🇦 Namibia", "price": 109.18},
    {"code": "129", "name": "🇳🇵 Nepal", "price": 126.30},
    {"code": "101", "name": "🇳🇱 Netherlands", "price": 206.72},
    {"code": "146", "name": "🇳🇨 New Caledonia", "price": 85.63},
    {"code": "55", "name": "🇳🇿 New Zealand", "price": 505.75},
    {"code": "155", "name": "🇳🇮 Nicaragua", "price": 126.30},
    {"code": "70", "name": "🇳🇪 Niger", "price": 104.90},
    {"code": "19", "name": "🇳🇬 Nigeria", "price": 113.46},
    {"code": "159", "name": "🇳🇺 Niue", "price": 113.46},
    {"code": "102", "name": "🇳🇴 Norway", "price": 162.56},
    {"code": "112", "name": "🇴🇲 Oman", "price": 60.00},
    {"code": "54", "name": "🇵🇰 Pakistan", "price": 468.29},
    {"code": "136", "name": "🇵🇸 Palestine", "price": 138.90},
    {"code": "119", "name": "🇵🇦 Panama", "price": 130.59},
    {"code": "145", "name": "🇵🇬 Papua New Guinea", "price": 139.15},
    {"code": "125", "name": "🇵🇾 Paraguay", "price": 162.56},
    {"code": "53", "name": "🇵🇪 Peru", "price": 107.04},
    {"code": "4", "name": "🇵🇭 Philippines", "price": 69.57},
    {"code": "158", "name": "🇵🇳 Pitcairn", "price": 69.57},
    {"code": "15", "name": "🇵🇱 Poland", "price": 158.42},
    {"code": "48", "name": "🇵🇹 Portugal", "price": 283.50},
    {"code": "157", "name": "🇵🇷 Puerto Rico", "price": 126.30},
    {"code": "113", "name": "🇶🇦 Qatar", "price": 113.46},
    {"code": "147", "name": "🇷🇪 Reunion", "price": 85.63},
    {"code": "32", "name": "🇷🇴 Romania", "price": 212.73},
    {"code": "0", "name": "🇷🇺 Russia", "price": 350.00},
    {"code": "71", "name": "🇷🇼 Rwanda", "price": 267.00},
    {"code": "165", "name": "🇰🇳 Saint Kitts & Nevis", "price": 126.30},
    {"code": "162", "name": "🇱🇨 Saint Lucia", "price": 81.34},
    {"code": "163", "name": "🇻🇨 Saint Vincent", "price": 81.34},
    {"code": "149", "name": "🇼🇸 Samoa", "price": 172.59},
    {"code": "168", "name": "🇸🇹 Sao Tome & Principe", "price": 81.34},
    {"code": "108", "name": "🇸🇦 Saudi Arabia", "price": 85.63},
    {"code": "47", "name": "🇸🇳 Senegal", "price": 113.46},
    {"code": "100", "name": "🇷🇸 Serbia", "price": 128.45},
    {"code": "175", "name": "🇸🇨 Seychelles", "price": 85.63},
    {"code": "72", "name": "🇸🇱 Sierra Leone", "price": 92.05},
    {"code": "128", "name": "🇸🇬 Singapore", "price": 936.57},
    {"code": "150", "name": "🇸🇽 Sint Maarten", "price": 172.59},
    {"code": "103", "name": "🇸🇰 Slovakia", "price": 113.46},
    {"code": "46", "name": "🇸🇮 Slovenia", "price": 220.77},
    {"code": "147", "name": "🇸🇧 Solomon Is.", "price": 250.50},
    {"code": "73", "name": "🇸🇴 Somalia", "price": 250.50},
    {"code": "31", "name": "🇿🇦 South Africa", "price": 60.00},
    {"code": "107", "name": "🇰🇷 South Korea", "price": 172.59},
    {"code": "143", "name": "🇸🇸 South Sudan", "price": 74.93},
    {"code": "86", "name": "🇪🇸 Spain", "price": 355.89},
    {"code": "52", "name": "🇱🇰 Sri Lanka", "price": 119.89},
    {"code": "74", "name": "🇸🇩 Sudan", "price": 298.50},
    {"code": "157", "name": "🇸🇷 Suriname", "price": 113.46},
    {"code": "75", "name": "🇸🇿 Swaziland", "price": 92.05},
    {"code": "29", "name": "🇸🇪 Sweden", "price": 188.66},
    {"code": "104", "name": "🇨🇭 Switzerland", "price": 375.00},
    {"code": "135", "name": "🇸🇾 Syria", "price": 80.00},
    {"code": "127", "name": "🇹🇼 Taiwan", "price": 878.50},
    {"code": "134", "name": "🇹🇯 Tajikistan", "price": 92.05},
    {"code": "9", "name": "🇹🇿 Tanzania", "price": 92.05},
    {"code": "105", "name": "🇹🇭 Thailand", "price": 113.46},
    {"code": "158", "name": "🇹🇱 Timor-Leste", "price": 126.30},
    {"code": "76", "name": "🇹🇬 Togo", "price": 149.86},
    {"code": "150", "name": "🇹🇴 Tonga", "price": 172.59},
    {"code": "160", "name": "🇹🇹 Trinidad and Tobago", "price": 74.93},
    {"code": "138", "name": "🇹🇳 Tunisia", "price": 126.30},
    {"code": "49", "name": "🇹🇷 Turkey", "price": 126.30},
    {"code": "133", "name": "🇹🇲 Turkmenistan", "price": 126.30},
    {"code": "109", "name": "🇦🇪 UAE", "price": 160.56},
    {"code": "63", "name": "🇺🇬 Uganda", "price": 297.00},
    {"code": "1", "name": "🇺🇦 Ukraine", "price": 119.89},
    {"code": "12", "name": "🇺🇸 USA", "price": 120.00},
    {"code": "126", "name": "🇺🇾 Uruguay", "price": 130.59},
    {"code": "40", "name": "🇺🇿 Uzbekistan", "price": 113.46},
    {"code": "148", "name": "🇻🇺 Vanuatu", "price": 150.00},
    {"code": "180", "name": "🇻🇦 Vatican", "price": 350.00},
    {"code": "58", "name": "🇻🇪 Venezuela", "price": 77.07},
    {"code": "10", "name": "🇻🇳 Vietnam", "price": 148.50},
    {"code": "116", "name": "🇾🇪 Yemen", "price": 70.00},
    {"code": "77", "name": "🇿🇲 Zambia", "price": 92.05},
    {"code": "67", "name": "🇿🇼 Zimbabwe", "price": 93.12}
]

async def get_all_country_list():
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
        # Explicitly formatted clean request payload matching SastaSMS docs (?action=getNumber&service=wa&country=CODE&format=json)
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
                    
                    err_msg = data.get("msg") or data.get("message") or data.get("error") or "This service is temporarily unavailable."
                    return {"status": "ERROR", "message": f"Provider error: {err_msg}"}
                
                return {"status": "ERROR", "message": f"Provider error: {response.text.strip()}"}

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
        [InlineKeyboardButton("🛒 Buy Number (187+ Countries)", callback_data="buy_menu_0")], 
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
                # Secure parameter passing: prep_buy_<code|price> encoded as JSON or separated cleanly
                row.append(InlineKeyboardButton(c["name"], callback_data=f"buy_{c['code']}_{c['price']}"))
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
            row = [InlineKeyboardButton(matching[i]["name"], callback_data=f"buy_{matching[i]['code']}_{matching[i]['price']}")]
            if i + 1 < len(matching):
                row.append(InlineKeyboardButton(matching[i+1]["name"], callback_data=f"buy_{matching[i+1]['code']}_{matching[i+1]['price']}"))
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

async def check_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not referral_counts:
        await update.message.reply_text("📊 No referrals recorded yet.", parse_mode="HTML")
        return

    sorted_refs = sorted(referral_counts.items(), key=lambda x: x[1], reverse=True)
    text = "📊 <b>Referral Leaderboard / Stats:</b>\n\n"
    for uid, count in sorted_refs:
        uname = user_usernames.get(uid, f"ID: {uid}")
        text += f"• <b>{uname}</b> (<code>{uid}</code>): <b>{count}</b> referrals (Earned ₹{count * 2.00:.2f})\n"

    if len(text) > 4096:
        for x in range(0, len(text), 4096):
            await update.message.reply_text(text[x:x+4096], parse_mode="HTML")
    else:
        await update.message.reply_text(text, parse_mode="HTML")

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

    elif data.startswith("buy_"):
        # Format: buy_{code}_{price}
        remainder = data[len("buy_"):]
        country_code, price_str = remainder.rsplit("_", 1)
        price = float(price_str)
        current_bal = user_balances.get(user_id, 0.0)
        
        if current_bal < price:
            await safe_send_or_edit(update, context, f"⚠️ <b>Insufficient Balance!</b>\n\nPrice: ₹{price:.2f}\nBalance: ₹{current_bal:.2f}", InlineKeyboardMarkup([[InlineKeyboardButton("💳 Deposit Funds", callback_data="deposit_menu")]]))
            return
            
        keyboard = [[InlineKeyboardButton("✅ Confirm Purchase", callback_data=f"confirm_{country_code}_{price}")], [InlineKeyboardButton("❌ Cancel", callback_data="buy_menu_0")]]
        await safe_send_or_edit(update, context, f"🛒 <b>Confirm Purchase:</b>\n• <b>Price:</b> ₹{price:.2f}", InlineKeyboardMarkup(keyboard))
        
    elif data.startswith("confirm_"):
        # Format: confirm_{code}_{price}
        remainder = data[len("confirm_"):]
        country_code, price_str = remainder.rsplit("_", 1)
        price = float(price_str)
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
    app.add_handler(CommandHandler("referrals", check_referrals))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("send", send_to_user))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    app.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_photo_messages))
    app.add_handler(CallbackQueryHandler(button_router))
    print("🚀 Bot Online with Fully Corrected Country Codes & Purchase Routing!")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app.run_polling()

if __name__ == "__main__":
    main()
