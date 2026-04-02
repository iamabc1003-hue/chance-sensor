"""
Steam 데이터 수집 모듈
- SteamSpy API를 통한 인기 게임 및 장르 데이터 수집
- Steam Store API를 통한 게임 상세정보 수집
"""

import requests
import time
import logging
from typing import Optional

from config import STEAMSPY_BASE_URL, STEAM_TRENDING_TOP_N

logger = logging.getLogger(__name__)


def get_top_games_2weeks() -> list[dict]:
    """최근 2주간 인기 게임 목록 (SteamSpy)"""
    try:
        resp = requests.get(
            STEAMSPY_BASE_URL,
            params={"request": "top100in2weeks"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        games = []
        for appid, info in data.items():
            games.append({
                "appid": int(appid),
                "name": info.get("name", ""),
                "developer": info.get("developer", ""),
                "publisher": info.get("publisher", ""),
                "owners": info.get("owners", ""),
                "positive": info.get("positive", 0),
                "negative": info.get("negative", 0),
                "average_playtime": info.get("average_forever", 0),
                "tags": info.get("tags", {}),
            })

        # 소유자 수 기준 정렬
        games.sort(key=lambda x: _parse_owners_mid(x["owners"]), reverse=True)
        return games[:STEAM_TRENDING_TOP_N * 3]  # 여유분 확보

    except Exception as e:
        logger.error(f"SteamSpy top100in2weeks 수집 실패: {e}")
        return []


def get_genre_games(genre_tag: str) -> list[dict]:
    """특정 태그의 인기 게임 목록"""
    try:
        resp = requests.get(
            STEAMSPY_BASE_URL,
            params={"request": "tag", "tag": genre_tag},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        games = []
        for appid, info in data.items():
            games.append({
                "appid": int(appid),
                "name": info.get("name", ""),
                "owners": info.get("owners", ""),
                "positive": info.get("positive", 0),
                "negative": info.get("negative", 0),
                "tags": info.get("tags", {}),
            })

        return games

    except Exception as e:
        logger.error(f"SteamSpy tag '{genre_tag}' 수집 실패: {e}")
        return []


def get_app_details(appid: int) -> Optional[dict]:
    """Steam Store API를 통한 게임 상세정보"""
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
        logger.error(f"Steam appdetails {appid} 수집 실패: {e}")
        return None


def get_new_releases() -> list[dict]:
    """최근 신규 출시 게임"""
    try:
        resp = requests.get(
            STEAMSPY_BASE_URL,
            params={"request": "top100in2weeks"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        # 소유자 수가 적은 (= 최근 출시 가능성) 게임 필터링
        games = []
        for appid, info in data.items():
            owners_mid = _parse_owners_mid(info.get("owners", "0 .. 0"))
            if owners_mid < 500000:  # 50만 미만 = 비교적 신규
                games.append({
                    "appid": int(appid),
                    "name": info.get("name", ""),
                    "owners": info.get("owners", ""),
                    "positive": info.get("positive", 0),
                    "negative": info.get("negative", 0),
                    "tags": info.get("tags", {}),
                })

        return games

    except Exception as e:
        logger.error(f"신규 출시 수집 실패: {e}")
        return []


def enrich_games_with_details(games: list[dict], delay: float = 1.0) -> list[dict]:
    """게임 목록에 Steam Store 상세정보 추가 (rate limit 준수)"""
    enriched = []
    for game in games:
        details = get_app_details(game["appid"])
        if details:
            game.update(details)
        enriched.append(game)
        time.sleep(delay)  # Steam API rate limit
    return enriched


def _parse_owners_mid(owners_str: str) -> int:
    """'20,000 .. 50,000' 형식에서 중간값 추출"""
    try:
        parts = owners_str.replace(",", "").split(" .. ")
        low = int(parts[0])
        high = int(parts[1]) if len(parts) > 1 else low
        return (low + high) // 2
    except (ValueError, IndexError):
        return 0
