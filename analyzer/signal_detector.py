"""
Signal Detector
- Steam 데이터에서 급등 신호를 감지
- 이전 watchlist 대비 변화율 계산
- Signal Alert 후보 선별
"""

import json
import logging
from datetime import datetime
from typing import Optional

from config import (
    SIGNAL_WISHLIST_THRESHOLD_PCT,
    SIGNAL_MAX_ALERTS,
    WATCHLIST_PATH,
    GENRE_KEYWORDS,
)

logger = logging.getLogger(__name__)


def load_watchlist() -> dict:
    """기존 watchlist.json 로드"""
    try:
        with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_watchlist(watchlist: dict):
    """watchlist.json 저장"""
    with open(WATCHLIST_PATH, "w", encoding="utf-8") as f:
        json.dump(watchlist, f, ensure_ascii=False, indent=2)


def classify_genre_tags(steam_tags: dict) -> list[str]:
    """Steam 태그를 기반으로 장르 해시태그 생성"""
    tags_lower = [t.lower() for t in steam_tags.keys()]
    hashtags = set()

    for genre_name, keywords in GENRE_KEYWORDS.items():
        for kw in keywords:
            if any(kw in tag for tag in tags_lower):
                # 장르명에서 해시태그 생성
                short = genre_name.split("/")[0].strip().replace(" ", "")
                hashtags.add(f"#{short}")
                break

    # Steam 태그에서 직접 해시태그 추가
    priority_tags = [
        "Indie", "Early Access", "Free to Play", "Co-op", "Multiplayer",
        "Singleplayer", "PvP", "PvE", "Open World", "Roguelike",
    ]
    for tag in steam_tags.keys():
        if tag in priority_tags:
            hashtags.add(f"#{tag.replace(' ', '')}")

    return list(hashtags)[:5]  # 최대 5개


def detect_signals(current_games: list[dict], watchlist: dict) -> list[dict]:
    """
    급등 신호 감지
    - 이전 watchlist에 없는 신규 진입 게임
    - 기존 추적 게임 중 지표 급등 게임
    """
    signals = []
    today = datetime.now().strftime("%Y-%m-%d")

    for game in current_games:
        appid = str(game.get("appid", ""))
        name = game.get("name", "")
        if not appid or not name:
            continue

        owners_str = game.get("owners", "0 .. 0")
        current_owners = _parse_owners_mid(owners_str)
        steam_tags = game.get("tags", {})
        genre_tags = classify_genre_tags(steam_tags)

        # 기존 watchlist에 있는지 확인
        if appid in watchlist:
            prev = watchlist[appid]
            prev_data = prev.get("weekly_data", [])

            if prev_data:
                last_owners = prev_data[-1].get("owners_mid", 0)
                if last_owners > 0:
                    delta_pct = ((current_owners - last_owners) / last_owners) * 100
                else:
                    delta_pct = 100 if current_owners > 0 else 0

                if delta_pct >= SIGNAL_WISHLIST_THRESHOLD_PCT:
                    signals.append({
                        "appid": appid,
                        "name": name,
                        "status": "rising",
                        "delta_pct": round(delta_pct),
                        "current_owners": current_owners,
                        "tags": genre_tags,
                        "steam_url": game.get("steam_url", f"https://store.steampowered.com/app/{appid}/"),
                        "details": game,
                        "weeks_tracked": len(prev_data),
                    })

            # watchlist 업데이트
            prev["weekly_data"].append({
                "date": today,
                "owners_mid": current_owners,
            })

        else:
            # 신규 진입
            signals.append({
                "appid": appid,
                "name": name,
                "status": "new",
                "delta_pct": 0,
                "current_owners": current_owners,
                "tags": genre_tags,
                "steam_url": game.get("steam_url", f"https://store.steampowered.com/app/{appid}/"),
                "details": game,
                "weeks_tracked": 0,
            })

            # watchlist에 추가
            watchlist[appid] = {
                "name": name,
                "url": game.get("steam_url", f"https://store.steampowered.com/app/{appid}/"),
                "tags": genre_tags,
                "first_detected": today,
                "weekly_data": [{
                    "date": today,
                    "owners_mid": current_owners,
                }],
            }

    # delta_pct 기준 내림차순 정렬, 상위 N개
    signals.sort(key=lambda x: x["delta_pct"], reverse=True)
    return signals[:SIGNAL_MAX_ALERTS]


def update_watchlist_status(watchlist: dict) -> list[dict]:
    """Watchlist 전체 항목의 상태(신규/상승/안정/하락) 판정"""
    items = []
    for appid, data in watchlist.items():
        weekly = data.get("weekly_data", [])
        if len(weekly) < 2:
            status = "new"
            delta_pct = 0
        else:
            prev = weekly[-2].get("owners_mid", 0)
            curr = weekly[-1].get("owners_mid", 0)
            if prev > 0:
                delta_pct = round(((curr - prev) / prev) * 100)
            else:
                delta_pct = 0

            if delta_pct >= 30:
                status = "rising"
            elif delta_pct <= -10:
                status = "declining"
            else:
                status = "stable"

        items.append({
            "appid": appid,
            "name": data.get("name", ""),
            "url": data.get("url", ""),
            "tags": data.get("tags", []),
            "status": status,
            "delta_pct": delta_pct,
            "weeks_tracked": len(weekly),
            "first_detected": data.get("first_detected", ""),
        })

    # 상태 우선순위: new > rising > stable > declining
    status_order = {"new": 0, "rising": 1, "stable": 2, "declining": 3}
    items.sort(key=lambda x: (status_order.get(x["status"], 9), -x["delta_pct"]))
    return items


def _parse_owners_mid(owners_str: str) -> int:
    try:
        parts = owners_str.replace(",", "").split(" .. ")
        low = int(parts[0])
        high = int(parts[1]) if len(parts) > 1 else low
        return (low + high) // 2
    except (ValueError, IndexError):
        return 0
