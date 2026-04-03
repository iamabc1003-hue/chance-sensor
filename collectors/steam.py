"""
Steam 데이터 수집 모듈
- SteamSpy API: top100in2weeks + 태그별 장르 수집
- Steam Store API: 개별 게임 상세정보
"""

import requests
import time
import logging
from typing import Optional

from config import STEAMSPY_BASE_URL, STEAMSPY_GENRE_TAGS
from utils import parse_owners_mid

logger = logging.getLogger(__name__)


def get_top_games_2weeks() -> list[dict]:
    """최근 2주간 인기 게임 (전체)"""
    try:
        resp = requests.get(STEAMSPY_BASE_URL, params={"request": "top100in2weeks"}, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        games = []
        for appid, info in data.items():
            if isinstance(info, dict) and info.get("name"):
                games.append(_parse_steamspy_game(appid, info))

        games.sort(key=lambda x: parse_owners_mid(x["owners"]), reverse=True)
        logger.info(f"  Top 2weeks: {len(games)}개")
        return games

    except Exception as e:
        logger.error(f"SteamSpy top100in2weeks 수집 실패: {e}")
        return []


def get_games_by_tag(tag: str) -> list[dict]:
    """SteamSpy 태그별 게임 수집"""
    try:
        resp = requests.get(STEAMSPY_BASE_URL, params={"request": "tag", "tag": tag}, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if not data or not isinstance(data, dict) or len(data) <= 2:
            logger.warning(f"  SteamSpy tag '{tag}': 비정상 응답 (len={len(data) if data else 0})")
            logger.warning(f"    내용: {str(data)[:200]}")
            return []

        games = []
        for appid, info in data.items():
            if isinstance(info, dict) and info.get("name"):
                games.append(_parse_steamspy_game(appid, info))

        logger.info(f"    '{tag}': {len(games)}개")
        games.sort(key=lambda x: parse_owners_mid(x["owners"]), reverse=True)
        return games

    except Exception as e:
        logger.error(f"  SteamSpy tag '{tag}' 실패: {e}")
        return []


def collect_genre_games() -> dict[str, list[dict]]:
    """모든 장르 태그별 게임 수집"""
    genre_data = {}
    for genre_name, steam_tags in STEAMSPY_GENRE_TAGS.items():
        all_games = {}
        for tag in steam_tags:
            logger.info(f"  Steam tag '{tag}' 수집 중...")
            games = get_games_by_tag(tag)
            for g in games:
                all_games[g["appid"]] = g
            time.sleep(1.5)

        genre_data[genre_name] = list(all_games.values())
        logger.info(f"  → {genre_name}: {len(genre_data[genre_name])}개")

    return genre_data


def get_app_details(appid: int) -> Optional[dict]:
    """Steam Store API 게임 상세정보"""
    try:
        resp = requests.get(
            "https://store.steampowered.com/api/appdetails",
            params={"appids": appid, "l": "english"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        app_data = data.get(str(appid), {})
        if not app_data.get("success"):
            return None

        info = app_data["data"]
        return {
            "appid": appid,
            "name": info.get("name", ""),
            "type": info.get("type", ""),
            "is_free": info.get("is_free", False),
            "short_description": info.get("short_description", ""),
            "developers": info.get("developers", []),
            "publishers": info.get("publishers", []),
            "genres": [g["description"] for g in info.get("genres", [])],
            "categories": [c["description"] for c in info.get("categories", [])],
            "release_date": info.get("release_date", {}),
            "platforms": info.get("platforms", {}),
            "steam_url": f"https://store.steampowered.com/app/{appid}/",
        }

    except Exception as e:
        logger.error(f"  Steam appdetails {appid} 실패: {e}")
        return None


def enrich_games_with_details(games: list[dict], delay: float = 1.5) -> list[dict]:
    """게임 목록에 Steam Store 상세정보 추가"""
    enriched = []
    for game in games:
        details = get_app_details(game["appid"])
        if details:
            game.update(details)
        enriched.append(game)
        time.sleep(delay)
    return enriched


def _parse_steamspy_game(appid, info: dict) -> dict:
    return {
        "appid": int(appid),
        "name": info.get("name", ""),
        "developer": info.get("developer", ""),
        "publisher": info.get("publisher", ""),
        "owners": info.get("owners", ""),
        "positive": info.get("positive", 0),
        "negative": info.get("negative", 0),
        "average_playtime": info.get("average_forever", 0),
        "tags": info.get("tags", {}),
    }
