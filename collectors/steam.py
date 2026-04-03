"""
Steam 데이터 수집 모듈 v2
- SteamSpy 태그별 장르 수집으로 중소형/신작 타이틀 포착
- Steam Store API로 상세정보 보강
- 대형 기존작 필터링
"""

import requests
import time
import logging
from typing import Optional

from config import STEAMSPY_BASE_URL, STEAMSPY_GENRE_TAGS, STEAM_TRENDING_TOP_N

logger = logging.getLogger(__name__)

# 대형 기존작 제외 — top 2weeks에서만 적용
MEGA_TITLE_THRESHOLD = 5_000_000  # 500만 이상은 이미 알려진 게임


def get_top_games_2weeks() -> list[dict]:
    """최근 2주간 인기 게임 (대형 기존작 제외)"""
    try:
        resp = requests.get(
            STEAMSPY_BASE_URL,
            params={"request": "top100in2weeks"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        games = []
        skipped = []
        for appid, info in data.items():
            owners_raw = info.get("owners", "0 .. 0")
            owners_mid = _parse_owners_mid(owners_raw)
            if owners_mid >= MEGA_TITLE_THRESHOLD:
                skipped.append(f"{info.get('name', '')}({owners_raw})")
                continue
            games.append(_parse_steamspy_game(appid, info))

        if skipped:
            logger.info(f"  대형작 제외 {len(skipped)}개: {', '.join(skipped[:5])}...")

        games.sort(key=lambda x: _parse_owners_mid(x["owners"]), reverse=True)
        # 상위 5개 로그
        for g in games[:5]:
            logger.info(f"    포함: {g['name']} (owners: {g['owners']})")
        return games

    except Exception as e:
        logger.error(f"SteamSpy top100in2weeks 수집 실패: {e}")
        return []


def get_games_by_tag(tag: str) -> list[dict]:
    """SteamSpy 태그별 게임 수집"""
    try:
        resp = requests.get(
            STEAMSPY_BASE_URL,
            params={"request": "tag", "tag": tag},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        # SteamSpy가 빈 응답이나 에러를 반환하는 경우 로깅
        if not data or not isinstance(data, dict):
            logger.warning(f"SteamSpy tag '{tag}': 빈 응답 또는 비정상 형식")
            logger.warning(f"  응답 타입: {type(data)}, 길이: {len(str(data)[:200])}")
            return []

        games = []
        for appid, info in data.items():
            if isinstance(info, dict) and info.get("name"):
                games.append(_parse_steamspy_game(appid, info))

        logger.info(f"    → '{tag}': {len(games)}개 게임 수집")
        games.sort(key=lambda x: _parse_owners_mid(x["owners"]), reverse=True)
        return games

    except Exception as e:
        logger.error(f"SteamSpy tag '{tag}' 수집 실패: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"  응답 코드: {e.response.status_code}")
            logger.error(f"  응답 본문: {e.response.text[:300]}")
        return []


def collect_genre_games() -> dict[str, list[dict]]:
    """설정된 모든 장르 태그별로 게임 수집"""
    genre_data = {}
    for genre_name, steam_tags in STEAMSPY_GENRE_TAGS.items():
        all_games = {}
        for tag in steam_tags:
            logger.info(f"  Steam tag '{tag}' 수집 중...")
            games = get_games_by_tag(tag)
            for g in games:
                all_games[g["appid"]] = g  # 중복 제거
            time.sleep(1.5)  # SteamSpy rate limit

        genre_data[genre_name] = list(all_games.values())
        logger.info(f"  → {genre_name}: {len(genre_data[genre_name])}개 게임")

    return genre_data


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


def enrich_games_with_details(games: list[dict], delay: float = 1.5, max_count: int = 15) -> list[dict]:
    """게임 목록에 Steam Store 상세정보 추가"""
    enriched = []
    for game in games[:max_count]:
        details = get_app_details(game["appid"])
        if details:
            game.update(details)
        enriched.append(game)
        time.sleep(delay)
    return enriched


def _parse_steamspy_game(appid, info: dict) -> dict:
    """SteamSpy 응답을 표준 게임 dict로 변환"""
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


def _parse_owners_mid(owners_str: str) -> int:
    try:
        parts = owners_str.replace(",", "").split(" .. ")
        low = int(parts[0])
        high = int(parts[1]) if len(parts) > 1 else low
        return (low + high) // 2
    except (ValueError, IndexError):
        return 0
