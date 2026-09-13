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

# Force Subscription Channel ID (Bot must be an admin here)
FORCE_SUB_CHANNEL = "@WHATSAPP_VAULT"

# JSONBin.io Cloud Storage Credentials
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

# Load persistent records into memory
user_balances, user_referrers, referral_counts, user_usernames = load_data_sync()
active_orders = {}  
ITEMS_PER_PAGE = 15  

# ==========================================
# 🏷️ ALL 187 COUNTRY PRICES & NAMES
# ==========================================
COUNTRY_PRICES = {
    "0": 250.0,   # 🇷🇺 Russia
    "1": 189.0,   # 🇺🇦 Ukraine
    "2": 312.0,   # 🇰🇿 Kazakhstan
    "3": 250.0,   # 🇨🇳 China
    "4": 250.0,   # 🇵🇭 Philippines
    "5": 187.0,   # 🇲🇲 Myanmar
    "6": 87.0,    # 🇲🇩 Moldova
    "7": 147.0,   # 🇲🇾 Malaysia
    "8": 159.0,   # 🇰🇪 Kenya
    "9": 132.0,   # 🇹🇿 Tanzania
    "10": 99.0,   # 🇻🇳 Vietnam
    "11": 196.0,  # 🇰🇬 Kyrgyzstan
    "12": 178.0,  # 🇺🇸 USA
    "13": 314.0,  # 🇮🇱 Israel
    "14": 156.0,  # 🇭🇰 Hong Kong
    "15": 186.0,  # 🇵🇱 Poland
    "16": 185.0,  # 🇬🇧 UK
    "17": 256.0,  # 🇲🇬 Madagascar
    "18": 98.0,   # 🇨🇬 Congo
    "19": 199.0,  # 🇳🇬 Nigeria
    "20": 167.0,  # 🇲🇴 Macau
    "21": 173.0,  # 🇪🇬 Egypt
    "22": 179.0,  # 🇮🇳 India
    "23": 3204.0, # 🇮🇪 Ireland
    "24": 213.0,  # 🇰🇭 Cambodia
    "25": 190.0,  # 🇱🇦 Laos
    "26": 143.0,  # 🇭🇹 Haiti
    "27": 199.0,  # 🇨🇮 Ivory Coast
    "28": 175.0,  # 🇬🇲 Gambia
    "29": 234.0,  # 🇸🇪 Sweden
    "30": 156.0,  # 🇮🇶 Iraq
    "31": 132.0,  # 🇿🇦 South Africa
    "32": 213.0,  # 🇷🇴 Romania
    "33": 75.0,   # 🇨🇴 Colombia
    "34": 195.0,  # 🇪🇪 Estonia
    "35": 145.0,  # 🇦🇿 Azerbaijan
    "36": 112.0,  # 🇨🇦 Canada
    "37": 89.0,   # 🇲🇦 Morocco
    "38": 140.0,  # 🇬🇭 Ghana
    "39": 178.0,  # 🇦🇷 Argentina
    "40": 189.0,  # 🇺🇿 Uzbekistan
    "41": 168.0,  # 🇨🇲 Cameroon
    "42": 157.0,  # 🇹🇩 Chad
    "43": 360.0,  # 🇩🇪 Germany
    "44": 234.0,  # 🇱🇹 Lithuania
    "45": 297.0,  # 🇭🇷 Croatia
    "46": 256.0,  # 🇸🇮 Slovenia
    "47": 167.0,  # 🇸🇳 Senegal
    "48": 189.0,  # 🇵🇹 Portugal
    "49": 198.0,  # 🇹🇷 Turkey
    "50": 309.0,  # 🇨🇿 Czechia
    "51": 178.0,  # 🇱🇺 Luxembourg
    "52": 176.0,  # 🇱🇰 Sri Lanka
    "53": 189.0,  # 🇵🇪 Peru
    "54": 250.0,  # 🇵🇰 Pakistan
    "55": 781.0,  # 🇳🇿 New Zealand
    "56": 180.0,  # 🇬🇳 Guinea
    "57": 230.0,  # 🇲🇱 Mali
    "58": 178.0,  # 🇻🇪 Venezuela
    "59": 198.0,  # 🇪🇹 Ethiopia
    "60": 130.0,  # 🇲🇳 Mongolia
    "61": 340.0,  # 🇧🇷 Brazil
    "62": 176.0,  # 🇦🇫 Afghanistan
    "63": 198.0,  # 🇺🇬 Uganda
    "64": 178.0,  # 🇦🇴 Angola
    "65": 671.0,  # 🇨🇾 Cyprus
    "66": 990.0,  # 🇫🇷 France
    "67": 156.0,  # 🇿🇼 Zimbabwe
    "68": 139.0,  # 🇲🇼 Malawi
    "69": 40.0,   # 🇳🇦 Namibia
    "70": 187.0,  # 🇳🇪 Niger
    "71": 178.0,  # 🇷🇼 Rwanda
    "72": 158.0,  # 🇸🇱 Sierra Leone
    "73": 167.0,  # 🇸🇴 Somalia
    "74": 199.0,  # 🇸🇩 Sudan
    "75": 40.0,   # 🇸🇿 Eswatini
    "76": 193.0,  # 🇹🇬 Togo
    "77": 173.0,  # 🇿🇲 Zambia
    "78": 212.0,  # 🇦🇱 Albania
    "79": 245.0,  # 🇦🇲 Armenia
    "80": 999.0,  # 🇦🇹 Austria
    "81": 179.0,  # 🇧🇾 Belarus
    "82": 640.0,  # 🇧🇪 Belgium
    "83": 198.0,  # 🇧🇦 Bosnia
    "84": 654.0,  # 🇧🇬 Bulgaria
    "85": 290.0,  # 🇩🇰 Denmark
    "86": 599.0,  # 🇪🇸 Spain
    "87": 456.0,  # 🇫🇮 Finland
    "88": 210.0,  # 🇬🇪 Georgia
    "89": 245.0,  # 🇬🇷 Greece
    "90": 350.0,  # 🇭🇺 Hungary
    "91": 190.0,  # 🇮🇸 Iceland
    "92": 560.0,  # 🇮🇹 Italy
    "93": 198.0,  # 🇧🇩 Bangladesh
    "94": 190.0,  # 🇱🇻 Latvia
    "95": 225.0,  # 🇱🇮 Liechtenstein
    "96": 234.0,  # 🇲🇰 N. Macedonia
    "97": 40.0,   # 🇲🇹 Malta
    "98": 230.0,  # 🇲🇩 Moldova
    "99": 190.0,  # 🇲🇨 Monaco
    "100": 200.0, # 🇲🇪 Montenegro
    "101": 245.0, # 🇳🇱 Netherlands
    "102": 234.0, # 🇳🇴 Norway
    "103": 304.0, # 🇸🇰 Slovakia
    "104": 250.0, # 🇨🇭 Switzerland
    "105": 168.0, # 🇹🇭 Thailand
    "106": 1472.0,# 🇯🇵 Japan
    "107": 250.0, # 🇰🇷 South Korea
    "108": 198.0, # 🇸🇦 Saudi Arabia
    "109": 234.0, # 🇦🇪 UAE
    "110": 196.0, # 🇯🇴 Jordan
    "111": 178.0, # 🇱🇧 Lebanon
    "112": 40.0,  # 🇴🇲 Oman
    "113": 180.0, # 🇶🇦 Qatar
    "114": 365.0, # 🇰🇼 Kuwait
    "115": 234.0, # 🇧🇭 Bahrain
    "116": 189.0, # 🇾🇪 Yemen
    "117": 230.0, # 🇲🇽 Mexico
    "118": 204.0, # 🇨🇷 Costa Rica
    "119": 203.0, # 🇵🇦 Panama
    "120": 150.0, # 🇨🇺 Cuba
    "121": 178.0, # 🇩🇴 Dominican Rep.
    "122": 200.0, # 🇯🇲 Jamaica
    "123": 198.0, # 🇧🇴 Bolivia
    "124": 158.0, # 🇪🇨 Ecuador
    "125": 205.0, # 🇵🇾 Paraguay
    "126": 196.0, # 🇺🇾 Uruguay
    "127": 1134.0,# 🇹🇼 Taiwan
    "128": 1098.0,# 🇸🇬 Singapore
    "129": 209.0, # 🇳🇵 Nepal
    "130": 189.0, # 🇧🇹 Bhutan
    "131": 240.0, # 🇲🇻 Maldives
    "132": 199.0, # 🇧🇳 Brunei
    "133": 199.0, # 🇹🇲 Turkmenistan
    "134": 156.0, # 🇹🇯 Tajikistan
    "135": 196.0, # 🇸🇾 Syria
    "136": 205.0, # 🇵🇸 Palestine
    "137": 204.0, # 🇱🇾 Libya
    "138": 199.0, # 🇹🇳 Tunisia
    "139": 197.0, # 🇩🇿 Algeria
    "140": 199.0, # 🇲🇷 Mauritania
    "141": 230.0, # 🇪🇷 Eritrea
    "142": 257.0, # 🇩🇯 Djibouti
    "143": 171.0, # 🇸🇸 South Sudan
    "144": 679.0, # 🇦🇺 Australia
    "145": 198.0, # 🇵🇬 Papua New Guinea
    "146": 40.0,  # 🇫🇯 Fiji
    "147": 40.0,  # 🇸🇧 Solomon Is.
    "148": 40.0,  # 🇻🇺 Vanuatu
    "149": 267.0, # 🇼🇸 Samoa
    "150": 267.0, # 🇹🇴 Tonga
    "151": 195.0, # 🇧🇿 Belize
    "152": 198.0, # 🇬🇹 Guatemala
    "153": 200.0, # 🇸🇻 El Salvador
    "154": 199.0, # 🇭🇳 Honduras
    "155": 140.0, # 🇳🇮 Nicaragua
    "156": 190.0, # 🇬🇾 Guyana
    "157": 198.0, # 🇸🇷 Suriname
    "158": 197.0, # 🇧🇸 Bahamas
    "159": 176.0, # 🇧🇧 Barbados
    "160": 189.0, # 🇹🇹 Trinidad
    "161": 198.0, # 🇬🇩 Grenada
    "162": 194.0, # 🇱🇨 St. Lucia
    "163": 149.0, # 🇻🇨 St. Vincent
    "164": 128.0, # 🇦🇬 Antigua
    "165": 278.0, # 🇰🇳 St. Kitts
    "166": 190.0, # 🇩🇲 Dominica
    "167": 194.0, # 🇨🇻 Cape Verde
    "168": 190.0, # 🇸🇹 Sao Tome
    "169": 194.0, # 🇬🇼 Guinea-Bissau
    "170": 194.0, # 🇬🇶 Eq. Guinea
    "171": 190.0, # 🇬🇦 Gabon
    "172": 184.0, # 🇨🇫 CAR
    "173": 170.0, # 🇰🇲 Comoros
    "174": 204.0, # 🇲🇺 Mauritius
    "175": 214.0, # 🇸🇨 Seychelles
    "176": 214.0, # 🇱🇸 Lesotho
    "177": 194.0, # 🇧🇼 Botswana
    "178": 184.0, # 🇦🇩 Andorra
    "179": 194.0, # 🇸🇲 San Marino
    "180": 1040.0,# 🇻🇦 Vatican
    "181": 1040.0,# 🇲🇨 Monaco
    "182": 1940.0,# 🇯🇵 Japan
    "183": 1040.0,# 🇰🇷 S. Korea
    "184": 1940.0,# 🇹🇼 Taiwan
    "185": 1940.0,# 🇭🇰 Hong Kong
    "186": 375.0, # 🇲🇴 Macau
    "187": 375.0  # 🇸🇬 Singapore
}
DEFAULT_PRICE = 250.0  

COUNTRY_NAMES = {
    "0": "🇷🇺 Russia", "1": "🇺🇦 Ukraine", "2": "🇰🇿 Kazakhstan", "3": "🇨🇳 China",
    "4": "🇵🇭 Philippines", "5": "🇲🇲 Myanmar", "6": "🇮🇩 Indonesia", "7": "🇲🇾 Malaysia",
    "8": "🇰🇪 Kenya", "9": "🇹🇿 Tanzania", "10": "🇻🇳 Vietnam", "11": "🇰🇬 Kyrgyzstan",
    "12": "🇺🇸 USA", "13": "🇮🇱 Israel", "14": "🇭🇰 Hong Kong", "15": "🇵🇱 Poland",
    "16": "🇬🇧 UK", "17": "🇲🇬 Madagascar", "18": "🇨🇬 Congo", "19": "🇳🇬 Nigeria",
    "20": "🇲🇴 Macau", "21": "🇪🇬 Egypt", "22": "🇮🇳 India", "23": "🇮🇪 Ireland",
    "24": "🇰🇭 Cambodia", "25": "🇱🇦 Laos", "26": "🇭🇹 Haiti", "27": "🇨🇮 Ivory Coast",
    "28": "🇬🇲 Gambia", "29": "🇸🇪 Sweden", "30": "🇮🇶 Iraq", "31": "🇿🇦 South Africa",
    "32": "🇷🇴 Romania", "33": "🇨🇴 Colombia", "34": "🇪🇪 Estonia", "35": "🇦🇿 Azerbaijan",
    "36": "🇨🇦 Canada", "37": "🇲🇦 Morocco", "38": "🇬🇭 Ghana", "39": "🇦🇷 Argentina",
    "40": "🇺🇿 Uzbekistan", "41": "🇨🇲 Cameroon", "42": "🇹🇩 Chad", "43": "🇩🇪 Germany",
    "44": "🇱🇹 Lithuania", "45": "🇭🇷 Croatia", "46": "🇸🇮 Slovenia", "47": "🇸🇳 Senegal",
    "48": "🇵🇹 Portugal", "49": "🇹🇷 Turkey", "50": "🇨🇿 Czechia", "51": "🇱🇺 Luxembourg",
    "52": "🇱🇰 Sri Lanka", "53": "🇵🇪 Peru", "54": "🇵🇰 Pakistan", "55": "🇳🇿 New Zealand",
    "56": "🇬🇳 Guinea", "57": "🇲🇱 Mali", "58": "🇻🇪 Venezuela", "59": "🇪🇹 Ethiopia",
    "60": "🇲🇳 Mongolia", "61": "🇧🇷 Brazil", "62": "🇦🇫 Afghanistan", "63": "🇺🇬 Uganda",
    "64": "🇦🇴 Angola", "65": "🇨🇾 Cyprus", "66": "🇫🇷 France", "67": "🇿🇼 Zimbabwe",
    "68": "🇲🇼 Malawi", "69": "🇳🇦 Namibia", "70": "🇳🇪 Niger", "71": "🇷🇼 Rwanda",
    "72": "🇸🇱 Sierra Leone", "73": "🇸🇴 Somalia", "74": "🇸🇩 Sudan", "75": "🇸🇿 Eswatini",
    "76": "🇹🇬 Togo", "77": "🇿🇲 Zambia", "78": "🇦🇱 Albania", "79": "🇦🇲 Armenia",
    "80": "🇦🇹 Austria", "81": "🇧🇾 Belarus", "82": "🇧🇪 Belgium", "83": "🇧🇦 Bosnia",
    "84": "🇧🇬 Bulgaria", "85": "🇩🇰 Denmark", "86": "🇪🇸 Spain", "87": "🇫🇮 Finland",
    "88": "🇬🇪 Georgia", "89": "🇬🇷 Greece", "90": "🇭🇺 Hungary", "91": "🇮🇸 Iceland",
    "92": "🇮🇹 Italy", "93": "🇧🇩 Bangladesh", "94": "🇱🇻 Latvia", "95": "🇱🇮 Liechtenstein",
    "96": "🇲🇰 N. Macedonia", "97": "🇲🇹 Malta", "98": "🇲🇩 Moldova", "99": "🇲🇨 Monaco",
    "100": "🇲🇪 Montenegro", "101": "🇳🇱 Netherlands", "102": "🇳🇴 Norway", "103": "🇸🇰 Slovakia",
    "104": "🇨🇭 Switzerland", "105": "🇹🇭 Thailand", "106": "🇯🇵 Japan", "107": "🇰🇷 South Korea",
    "108": "🇸🇦 Saudi Arabia", "109": "🇦🇪 UAE", "110": "🇯🇴 Jordan", "111": "🇱🇧 Lebanon",
    "112": "🇴🇲 Oman", "113": "🇶🇦 Qatar", "114": "🇰🇼 Kuwait", "115": "🇧🇭 Bahrain",
    "116": "🇾🇪 Yemen", "117": "🇲🇽 Mexico", "118": "🇨🇷 Costa Rica", "119": "🇵🇦 Panama",
    "120": "🇨🇺 Cuba", "121": "🇩🇴 Dominican Rep.", "122": "🇯🇲 Jamaica", "123": "🇧🇴 Bolivia",
    "124": "🇪🇨 Ecuador", "125": "🇵🇾 Paraguay", "126": "🇺🇾 Uruguay", "127": "🇹🇼 Taiwan",
    "128": "🇸🇬 Singapore", "129": "🇳🇵 Nepal", "130": "🇧🇹 Bhutan", "131": "🇲🇻 Maldives",
    "132": "🇧🇳 Brunei", "133": "🇹🇲 Turkmenistan", "134": "🇹🇯 Tajikistan", "135": "🇸🇾 Syria",
    "136": "🇵🇸 Palestine", "137": "🇱🇾 Libya", "138": "🇹🇳 Tunisia", "139": "🇩🇿 Algeria",
    "140": "🇲🇷 Mauritania", "141": "🇪🇷 Eritrea", "142": "🇩🇯 Djibouti", "143": "🇸🇸 South Sudan",
    "144": "🇦🇺 Australia", "145": "🇵🇬 Papua New Guinea", "146": "🇫🇯 Fiji", "147": "🇸🇧 Solomon Is.",
    "148": "🇻🇺 Vanuatu", "149": "🇼🇸 Samoa", "150": "🇹🇴 Tonga", "151": "🇧🇿 Belize",
    "152": "🇬🇹 Guatemala", "153": "🇸🇻 El Salvador", "154": "🇭🇳 Honduras", "155": "🇳🇮 Nicaragua",
    "156": "🇬🇾 Guyana", "157": "🇸🇷 Suriname", "158": "🇧🇸 Bahamas", "159": "🇧🇧 Barbados",
    "160": "🇹🇹 Trinidad", "161": "🇬🇩 Grenada", "162": "🇱🇨 St. Lucia", "163": "🇻🇨 St. Vincent",
    "164": "🇦🇬 Antigua", "165": "🇰🇳 St. Kitts", "166": "🇩🇲 Dominica", "167": "🇨🇻 Cape Verde",
    "168": "🇸🇹 Sao Tome", "169": "🇬🇼 Guinea-Bissau", "170": "🇬🇶 Eq. Guinea", "171": "🇬🇦 Gabon",
    "172": "🇨🇫 CAR", "173": "🇰🇲 Comoros", "174": "🇲🇺 Mauritius", "175": "🇸🇨 Seychelles",
    "176": "🇱🇸 Lesotho", "177": "🇧🇼 Botswana", "178": "🇦🇩 Andorra", "179": "🇸🇲 San Marino",
    "180": "🇻🇦 Vatican", "181": "🇲🇨 Monaco", "182": "🇯🇵 Japan", "183": "🇰🇷 S. Korea",
    "184": "🇹🇼 Taiwan", "185": "🇭🇰 Hong Kong", "186": "🇲🇴 Macau", "187": "🇸🇬 Singapore"
}

def get_all_country_list():
    full_list = []
    for code, name in COUNTRY_NAMES.items():
        price = COUNTRY_PRICES.get(code, DEFAULT_PRICE)
        full_list.append({"name": f"{name} - ₹{price:.2f}", "code": code, "raw_name": name, "price": price})
    return full_list

# ==========================================
# 🔒 FORCE SUBSCRIPTION CHECK
# ==========================================
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

# ==========================================
# 📡 SASTASMS API PROVIDER
# ==========================================
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

# ==========================================
# 🤖 BOT COMMANDS & ROUTING
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = f"@{user.username}" if user.username else f"{user.first_name} (No username)"

    # Save Username tracking
    if user_id not in user_usernames:
        user_usernames[user_id] = username
        save_data_sync(user_balances, user_referrers, referral_counts, user_usernames)
        
        # Notify Admin Channel about a new user
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHANNEL_ID,
                text=f"👤 <b>New Bot User Started!</b>\n\nName: {user.first_name}\nUsername: {username}\nID: <code>{user_id}</code>",
                parse_mode="HTML"
            )
        except Exception:
            pass

    # Handle Referral Tracking
    if context.args and len(context.args) > 0:
        arg = context.args[0]
        if arg.startswith("ref_") and user_id not in user_referrers:
            try:
                referrer_id = int(arg.split("_")[1])
                if referrer_id != user_id:
                    user_referrers[user_id] = referrer_id
                    referral_counts[referrer_id] = referral_counts.get(referrer_id, 0) + 1
                    save_data_sync(user_balances, user_referrers, referral_counts, user_usernames)
            except Exception:
                pass

    # Force Subscription Validation
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
        [KeyboardButton("🛒 Buy Number"), KeyboardButton("💳 Deposit")],
        [KeyboardButton("👤 My Profile"), KeyboardButton("📦 Order History")],
        [KeyboardButton("🎁 Gift"), KeyboardButton("👥 Refer & Earn")],
        [KeyboardButton("💬 Support")]
    ]
    bottom_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    inline_keyboard = [
        [InlineKeyboardButton("🛒 Buy Number (180+ Countries)", callback_data="buy_menu_0")], 
        [InlineKeyboardButton("🎁 Gift", callback_data="gift_menu"), InlineKeyboardButton("👥 Refer & Earn", callback_data="refer_menu")]
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
    for i in range(0, len(page_countries), 3):
        row = []
        for j in range(3):
            if i + j < len(page_countries):
                c = page_countries[i + j]
                row.append(InlineKeyboardButton(c["raw_name"], callback_data=f"prep_buy_{c['code']}_{c['price']}"))
        keyboard.append(row)

    nav_row = []
    if page > 0: nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"cpage_{page - 1}"))
    nav_row.append(InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1: nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"cpage_{page + 1}"))
    keyboard.append(nav_row)

    if total_pages > 3: keyboard.append([InlineKeyboardButton("⏮️ Page 1", callback_data="cpage_0"), InlineKeyboardButton("⏭️ End", callback_data=f"cpage_{total_pages - 1}")])
    keyboard.append([InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")])

    await safe_send_or_edit(update, context, f"<b>🌍 Select Country ({len(all_countries)} Available):</b>\n<i>Page {page + 1} of {total_pages}</i>", InlineKeyboardMarkup(keyboard))

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await check_user_subscription(user_id, context):
        await update.message.reply_text("⚠️ Please join our official channel first, then send /start again.")
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
            f"👥 <b>Refer & Earn Milestones</b>\n\n"
            f"Invite valid users to unlock free accounts:\n"
            f"• <b>25 Referrals:</b> Free Colombian Account 🇨🇴\n"
            f"• <b>40 Referrals:</b> Free USA Account 🇺🇸\n"
            f"• <b>50 Referrals:</b> Free Indian Account 🇮🇳\n"
            f"• <b>More than 50?</b> Contact Support for custom rewards!\n\n"
            f"⚠️ <i>Make sure you have done valid referrals! For redeem, contact customer support.</i>\n\n"
            f"📊 <b>Your Total Valid Referrals:</b> {refs}\n\n"
            f"🔗 <b>Your Referral Link:</b>\n<code>{ref_link}</code>"
        )
        await update.message.reply_text(text_msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💬 Contact Support", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}"), InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]))
    elif text == "💬 Support":
        await update.message.reply_text(f"📞 <b>Contact Support:</b> {SUPPORT_USERNAME}", parse_mode="HTML")

# ==========================================
# 🛠️ ADMIN BALANCE DEDUCTION COMMAND
# ==========================================
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

    # Deduct balance and sync to cloud
    user_balances[target_user_id] = current_bal - amount_to_deduct
    save_data_sync(user_balances, user_referrers, referral_counts, user_usernames)

    await update.message.reply_text(
        f"✅ <b>Successfully Deducted!</b>\n\n"
        f"• <b>User ID:</b> <code>{target_user_id}</code>\n"
        f"• <b>Deducted:</b> ₹{amount_to_deduct:.2f}\n"
        f"• <b>New Balance:</b> ₹{user_balances[target_user_id]:.2f}",
        parse_mode="HTML"
    )

# ==========================================
# 🎛️ CALLBACK ROUTER
# ==========================================
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
    elif data == "gift_menu":
        await safe_send_or_edit(update, context, "🎁 <b>Special Gift</b>\n\nCheck back later for promotional gifts and bonus vouchers, or contact support to redeem ongoing offers!", InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]))
    elif data == "refer_menu":
        bot_username = context.bot.username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        refs = referral_counts.get(user_id, 0)
        text_msg = (
            f"👥 <b>Refer & Earn Milestones</b>\n\n"
            f"• <b>25 Referrals:</b> Free Colombian Account 🇨🇴\n"
            f"• <b>40 Referrals:</b> Free USA Account 🇺🇸\n"
            f"• <b>50 Referrals:</b> Free Indian Account 🇮🇳\n"
            f"• <b>More:</b> Contact Support 💬\n\n"
            f"⚠️ <i>Make sure you have done valid referrals! For redeem, contact customer support.</i>\n\n"
            f"📊 <b>Your Total Valid Referrals:</b> {refs}\n\n"
            f"🔗 <b>Your Referral Link:</b>\n<code>{ref_link}</code>"
        )
        await safe_send_or_edit(update, context, text_msg, InlineKeyboardMarkup([[InlineKeyboardButton("💬 Contact Support", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}"), InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]))
    
    elif data.startswith("prep_buy_"):
        parts = data.split("_")
        country_code, price = parts[2], float(parts[3])
        current_bal = user_balances.get(user_id, 0.0)
        
        if current_bal < price:
            await safe_send_or_edit(update, context, f"⚠️ <b>Insufficient Balance!</b>\n\nPrice: ₹{price:.2f}\nBalance: ₹{current_bal:.2f}", InlineKeyboardMarkup([[InlineKeyboardButton("💳 Deposit Funds", callback_data="deposit")]]))
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
            
            text = f"✅ <b>Number Issued!</b>\n\n📱 <b>Phone:</b> <code>+{number}</code>\n🆔 <b>Order:</b> <code>{order_id}</code>"
            keyboard = [[InlineKeyboardButton("🔄 Refresh OTP Status", callback_data=f"refresh_{order_id}_{number}_{price}")]]
            await safe_send_or_edit(update, context, text, InlineKeyboardMarkup(keyboard))
        else:
            await safe_send_or_edit(update, context, f"❌ <b>Error:</b> {res.get('message', 'Out of stock.')}", InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="buy_menu_0")]]))

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
    app.add_handler(CommandHandler("deduct", deduct_balance))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    app.add_handler(CallbackQueryHandler(button_router))
    print("🚀 Bot Online with All Features & Balance Deduction Command!")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app.run_polling()

if __name__ == "__main__":
    main()
