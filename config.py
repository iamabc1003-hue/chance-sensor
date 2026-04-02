import os
from datetime import datetime, timedelta

# ── API Keys (from environment / GitHub Secrets) ──
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL_ID = os.environ.get("SLACK_CHANNEL_ID", "")

# ── Confluence ──
CONFLUENCE_BASE_URL = os.environ.get("CONFLUENCE_BASE_URL", "")  # e.g. https://risingwings.atlassian.net
CONFLUENCE_USER_EMAIL = os.environ.get("CONFLUENCE_USER_EMAIL", "")
CONFLUENCE_API_TOKEN = os.environ.get("CONFLUENCE_API_TOKEN", "")
CONFLUENCE_SPACE_KEY = os.environ.get("CONFLUENCE_SPACE_KEY", "")  # e.g. "PNIX" or 별도 스페이스
CONFLUENCE_PARENT_PAGE_ID = os.environ.get("CONFLUENCE_PARENT_PAGE_ID", "")  # 아카이브 상위 페이지 ID

# ── Claude API ──
CLAUDE_MODEL = "claude-sonnet-4-20250514"
CLAUDE_MAX_TOKENS = 4096

# ── Report ──
REPORT_TITLE = "Chance Sensor"
REPORT_ORG = "RisingWings Internal"
REPORT_PERIOD_DAYS = 7

def get_report_period():
    """이번 주 리포트 기간 (목요일 기준 지난 7일)"""
    end = datetime.now()
    start = end - timedelta(days=REPORT_PERIOD_DAYS)
    return start, end

# ── Steam 수집 설정 ──
STEAM_TRENDING_TOP_N = 10  # Trending 테이블에 표시할 상위 N개
SIGNAL_WISHLIST_THRESHOLD_PCT = 50  # Wishlist 변화율 이 이상이면 Signal 후보 (%)
SIGNAL_MAX_ALERTS = 5  # Signal Alert 최대 표시 수

# ── SteamSpy API ──
STEAMSPY_BASE_URL = "https://steamspy.com/api.php"

# SteamSpy 태그명 매핑 (장르 → SteamSpy에서 사용하는 태그명)
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

# ── Reddit 수집 설정 ──
REDDIT_USER_AGENT = "ChanceSensor/1.0 (by RisingWings)"
REDDIT_SUBREDDITS = [
    "Games",
    "pcgaming",
    "JRPG",
    "indiegaming",
    "gamedev",
    "Steam",
]
REDDIT_TOP_N_PER_SUB = 5  # 서브레딧당 상위 N개 포스트
REDDIT_MIN_UPVOTES = 500  # 최소 업보트 수 필터

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

# ── Watchlist 파일 경로 ──
WATCHLIST_PATH = "watchlist.json"
