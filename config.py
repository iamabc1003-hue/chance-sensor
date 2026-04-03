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
SIGNAL_MAX_ALERTS = 5
# Signal/Watchlist 진입 기준: 소유자 500만 미만
MAX_OWNERS_FOR_SIGNAL = 5_000_000
# Trending 진입 기준: 소유자 5만~500만, 리뷰 100개 이상
TRENDING_OWNERS_MIN = 50_000
TRENDING_OWNERS_MAX = 5_000_000
TRENDING_MIN_REVIEWS = 100

# ── SteamSpy API ──
STEAMSPY_BASE_URL = "https://steamspy.com/api.php"

# 장르별 SteamSpy 태그 매핑 (중복 없이 장르 특성에 맞는 태그만)
STEAMSPY_GENRE_TAGS = {
    "턴제 RPG / JRPG": ["RPG", "Strategy"],
    "슈터": ["Shooter", "FPS"],
    "생존 크래프트": ["Survival", "Sandbox"],
    "로그라이크": ["Roguelike", "Roguelite"],
    "액션 RPG": ["Adventure"],
    "시뮬레이션": ["Simulation"],
    "메트로배니아 / 플랫포머": ["Metroidvania", "Platformer"],
    "인디": ["Indie"],
}

# ── Watchlist ──
WATCHLIST_PATH = "watchlist.json"
# Watchlist에 동시 추적할 최대 게임 수
WATCHLIST_MAX_SIZE = 30
