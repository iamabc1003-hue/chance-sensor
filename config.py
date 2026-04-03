import os
from datetime import datetime, timedelta

# ── API Keys ──
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ── Google Drive (via Google Apps Script) ──
GAS_WEBHOOK_URL = os.environ.get("GAS_WEBHOOK_URL", "")

# ── Claude API ──
CLAUDE_MODEL = "claude-sonnet-4-20250514"
CLAUDE_MAX_TOKENS = 4096

# ── Report ──
REPORT_TITLE = "Chance Sensor"
REPORT_ORG = "RisingWings Internal"
REPORT_PERIOD_DAYS = 7

def get_report_period():
    end = datetime.now()
    start = end - timedelta(days=REPORT_PERIOD_DAYS)
    return start, end

# ── Steam 수집 설정 ──
STEAM_TRENDING_TOP_N = 10
SIGNAL_WISHLIST_THRESHOLD_PCT = 50
SIGNAL_MAX_ALERTS = 5

# ── SteamSpy API ──
STEAMSPY_BASE_URL = "https://steamspy.com/api.php"

STEAMSPY_GENRE_TAGS = {
    "턴제 RPG / JRPG": ["Turn-Based", "JRPG", "Turn-Based Combat", "Turn-Based Strategy", "Turn-Based Tactics"],
    "히어로 슈터 / MOBA": ["Hero Shooter", "MOBA"],
    "생존 크래프트": ["Survival", "Crafting"],
    "로그라이크 / 오토배틀러": ["Roguelike", "Roguelite", "Roguelike Deckbuilder", "Auto Battler"],
    "액션 RPG": ["Action RPG", "Hack and Slash", "Souls-like"],
    "오픈월드": ["Open World"],
    "택티컬 슈터": ["Tactical", "Extraction Shooter"],
    "메트로배니아": ["Metroidvania"],
}

# ── 장르 분류 키워드 매핑 ──
GENRE_KEYWORDS = {
    "턴제 RPG / JRPG": ["turn-based", "jrpg", "turn based", "tactical rpg", "strategy rpg"],
    "히어로 슈터 / MOBA": ["hero shooter", "moba", "team shooter", "overwatch", "deadlock"],
    "생존 크래프트": ["survival", "crafting", "survival craft", "sandbox survival"],
    "로그라이크 / 오토배틀러": ["roguelike", "roguelite", "auto battler", "autobattler", "survivors-like"],
    "액션 RPG": ["action rpg", "arpg", "hack and slash", "souls-like", "soulslike"],
    "오픈월드": ["open world", "open-world", "sandbox"],
    "택티컬 슈터": ["tactical shooter", "extraction shooter", "mil-sim"],
    "메트로배니아": ["metroidvania", "platformer"],
}

# ── Watchlist ──
WATCHLIST_PATH = "watchlist.json"
