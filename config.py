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

# SteamSpy tag API에서 단일 단어만 정상 동작 (공백/하이픈 포함 태그는 비정상 응답)
# 장르별로 가장 특징적인 단일 단어 태그를 선정
STEAMSPY_GENRE_TAGS = {
    "RPG": ["RPG"],
    "슈터": ["Shooter"],
    "생존": ["Survival"],
    "로그라이크": ["Roguelike", "Roguelite"],
    "시뮬레이션": ["Simulation"],
    "전략": ["Strategy"],
    "메트로배니아 / 플랫포머": ["Metroidvania", "Platformer"],
    "인디": ["Indie"],
    "어드벤처": ["Adventure"],
    "퍼즐": ["Puzzle"],
}

# ── Watchlist ──
WATCHLIST_PATH = "watchlist.json"
WATCHLIST_MAX_SIZE = 30
