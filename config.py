import os

# ── Google Drive (via Google Apps Script) ──
GAS_WEBHOOK_URL = os.environ.get("GAS_WEBHOOK_URL", "")

# ── Claude API ──
CLAUDE_MODEL = "claude-sonnet-4-20250514"
CLAUDE_MAX_TOKENS = 4096

# ── Steam 수집 설정 ──
STEAM_TRENDING_TOP_N = 10
SIGNAL_MAX_ALERTS = 5
MAX_OWNERS_FOR_SIGNAL = 5_000_000
TRENDING_OWNERS_MIN = 50_000
TRENDING_OWNERS_MAX = 5_000_000
TRENDING_MIN_REVIEWS = 500

# ── SteamSpy API ──
STEAMSPY_BASE_URL = "https://steamspy.com/api.php"

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
WATCHLIST_MAX_SIZE = 30
