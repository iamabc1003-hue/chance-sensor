"""
Genre Aggregator
- 수집된 게임 데이터를 장르별로 분류/집계
- Reddit 포스트를 장르별로 매핑
"""

import logging
from config import GENRE_KEYWORDS

logger = logging.getLogger(__name__)


def aggregate_by_genre(games: list[dict]) -> dict[str, list[dict]]:
    """게임 목록을 장르별로 분류"""
    genre_map = {genre: [] for genre in GENRE_KEYWORDS}

    for game in games:
        tags = game.get("tags", {})
        tags_lower = [t.lower() for t in tags.keys()] if isinstance(tags, dict) else [t.lower() for t in tags]

        matched = False
        for genre_name, keywords in GENRE_KEYWORDS.items():
            for kw in keywords:
                if any(kw in tag for tag in tags_lower):
                    genre_map[genre_name].append(game)
                    matched = True
                    break

    return genre_map


def filter_reddit_by_genre(posts: list[dict], genre_name: str) -> list[dict]:
    """Reddit 포스트 중 특정 장르와 관련된 것 필터링"""
    keywords = GENRE_KEYWORDS.get(genre_name, [])
    if not keywords:
        return []

    filtered = []
    for post in posts:
        title_lower = post.get("title", "").lower()
        text_lower = post.get("selftext", "").lower()
        combined = title_lower + " " + text_lower

        if any(kw in combined for kw in keywords):
            filtered.append(post)

    return filtered


def get_genre_summary_stats(genre_games: list[dict]) -> dict:
    """장르별 요약 통계"""
    if not genre_games:
        return {"count": 0, "total_owners": 0, "avg_positive_ratio": 0}

    total_owners = 0
    positive_ratios = []

    for game in genre_games:
        owners_str = game.get("owners", "0 .. 0")
        total_owners += _parse_owners_mid(owners_str)

        pos = game.get("positive", 0)
        neg = game.get("negative", 0)
        if pos + neg > 0:
            positive_ratios.append(pos / (pos + neg) * 100)

    return {
        "count": len(genre_games),
        "total_owners": total_owners,
        "avg_positive_ratio": round(sum(positive_ratios) / len(positive_ratios), 1) if positive_ratios else 0,
    }


def _parse_owners_mid(owners_str: str) -> int:
    try:
        parts = owners_str.replace(",", "").split(" .. ")
        low = int(parts[0])
        high = int(parts[1]) if len(parts) > 1 else low
        return (low + high) // 2
    except (ValueError, IndexError):
        return 0
