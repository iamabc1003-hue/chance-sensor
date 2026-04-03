"""
Signal Detector
- Steam 데이터에서 급등 신호를 감지
- Watchlist 관리 (최대 크기 제한)
"""

import json
import logging
import math
from datetime import datetime

from config import (
    SIGNAL_MAX_ALERTS,
    WATCHLIST_PATH,
    MAX_OWNERS_FOR_SIGNAL,
    WATCHLIST_MAX_SIZE,
)
from utils import parse_owners_mid

logger = logging.getLogger(__name__)


def load_watchlist() -> dict:
    try:
        with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_watchlist(watchlist: dict):
    # Watchlist 크기 제한 — 최신 데이터 기준 상위만 유지
    if len(watchlist) > WATCHLIST_MAX_SIZE * 2:
        sorted_items = sorted(
            watchlist.items(),
            key=lambda x: x[1].get("weekly_data", [{}])[-1].get("date", ""),
            reverse=True,
        )
        watchlist_trimmed = dict(sorted_items[:WATCHLIST_MAX_SIZE * 2])
        watchlist.clear()
        watchlist.update(watchlist_trimmed)

    with open(WATCHLIST_PATH, "w", encoding="utf-8") as f:
        json.dump(watchlist, f, ensure_ascii=False, indent=2)


def classify_genre_tags(steam_tags: dict) -> list[str]:
    """Steam 태그에서 해시태그 생성"""
    if not steam_tags or not isinstance(steam_tags, dict):
        return []

    hashtags = set()
    priority_tags = [
        "Indie", "Early Access", "Free to Play", "Co-op", "Multiplayer",
        "Singleplayer", "PvP", "PvE", "Roguelike", "Survival",
        "RPG", "Strategy", "Simulation", "Adventure", "Action",
        "Shooter", "FPS", "Platformer", "Puzzle",
    ]
    for tag in steam_tags.keys():
        if tag in priority_tags:
            hashtags.add(f"#{tag.replace(' ', '')}")

    return list(hashtags)[:5]


def detect_signals(current_games: list[dict], watchlist: dict) -> list[dict]:
    """
    급등 신호 감지
    - 소유자 500만 미만만 대상
    - 기존 watchlist 대비 급등 감지 (2주차 이후)
    - 신규 진입은 Signal에는 포함하되, Watchlist에는 상위 N개만 추가
    """
    signals = []
    new_entries = []
    today = datetime.now().strftime("%Y-%m-%d")

    for game in current_games:
        appid = str(game.get("appid", ""))
        name = game.get("name", "")
        if not appid or not name:
            continue

        owners_str = game.get("owners", "0 .. 0")
        current_owners = parse_owners_mid(owners_str)

        if current_owners >= MAX_OWNERS_FOR_SIGNAL:
            continue

        steam_tags = game.get("tags", {})
        genre_tags = classify_genre_tags(steam_tags)

        if appid in watchlist:
            # 기존 추적 게임 — 변화율 계산
            prev = watchlist[appid]
            prev_data = prev.get("weekly_data", [])

            if prev_data:
                last_owners = prev_data[-1].get("owners_mid", 0)
                if last_owners > 0:
                    delta_pct = ((current_owners - last_owners) / last_owners) * 100
                else:
                    delta_pct = 100 if current_owners > 0 else 0

                if delta_pct >= 30:  # 30% 이상 증가 시 Signal
                    signals.append(_make_signal(appid, name, "rising", round(delta_pct),
                                                current_owners, genre_tags, game, len(prev_data)))

            prev["weekly_data"].append({"date": today, "owners_mid": current_owners})

        else:
            # 신규 발견 — 나중에 상위만 watchlist에 추가
            new_entries.append({
                "appid": appid,
                "name": name,
                "current_owners": current_owners,
                "genre_tags": genre_tags,
                "game": game,
            })

    # 신규 진입 중 복합 점수 상위만 Signal + Watchlist에 추가
    # 베이지안 보정으로 리뷰 적은 게임의 과대평가 방지
    PRIOR_RATIO = 75.0
    PRIOR_WEIGHT = 100

    scored_new = []
    for entry in new_entries:
        game = entry["game"]
        pos = game.get("positive", 0)
        neg = game.get("negative", 0)
        total = pos + neg
        if total < 50:  # 리뷰 50개 미만은 제외
            continue

        raw_ratio = pos / total * 100
        bayesian = (pos + PRIOR_WEIGHT * PRIOR_RATIO / 100) / (total + PRIOR_WEIGHT) * 100
        review_bonus = min(math.log10(max(total, 1)) * 5, 20)
        entry["score"] = bayesian + review_bonus
        entry["positive_ratio"] = raw_ratio
        scored_new.append(entry)

    scored_new.sort(key=lambda x: x["score"], reverse=True)

    # 상위 Signal 후보만 추가
    for entry in scored_new[:SIGNAL_MAX_ALERTS * 2]:
        appid = entry["appid"]
        signals.append(_make_signal(
            appid, entry["name"], "new", 0,
            entry["current_owners"], entry["genre_tags"], entry["game"], 0,
        ))

    # Watchlist에는 상위만 추가 (폭증 방지)
    for entry in scored_new[:WATCHLIST_MAX_SIZE]:
        appid = entry["appid"]
        if appid not in watchlist:
            watchlist[appid] = {
                "name": entry["name"],
                "url": entry["game"].get("steam_url", f"https://store.steampowered.com/app/{appid}/"),
                "tags": entry["genre_tags"],
                "first_detected": today,
                "weekly_data": [{"date": today, "owners_mid": entry["current_owners"]}],
            }

    # Signal 정렬: rising(변화율 높은 순) > new(긍정률 높은 순)
    signals.sort(key=lambda x: (0 if x["status"] == "rising" else 1, -x["delta_pct"]))
    return signals[:SIGNAL_MAX_ALERTS]


def _make_signal(appid, name, status, delta_pct, owners, tags, game, weeks):
    return {
        "appid": appid,
        "name": name,
        "status": status,
        "delta_pct": delta_pct,
        "current_owners": owners,
        "tags": tags,
        "steam_url": game.get("steam_url", f"https://store.steampowered.com/app/{appid}/"),
        "details": game,
        "weeks_tracked": weeks,
    }


def update_watchlist_status(watchlist: dict) -> list[dict]:
    """Watchlist 항목의 주간 상태 판정"""
    items = []
    for appid, data in watchlist.items():
        weekly = data.get("weekly_data", [])
        if len(weekly) < 2:
            status = "new"
            delta_pct = 0
        else:
            prev = weekly[-2].get("owners_mid", 0)
            curr = weekly[-1].get("owners_mid", 0)
            delta_pct = round(((curr - prev) / prev) * 100) if prev > 0 else 0

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

    status_order = {"new": 0, "rising": 1, "stable": 2, "declining": 3}
    items.sort(key=lambda x: (status_order.get(x["status"], 9), -x["delta_pct"]))
    return items[:WATCHLIST_MAX_SIZE]
