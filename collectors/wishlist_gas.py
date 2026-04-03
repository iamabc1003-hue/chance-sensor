"""
Steam Wishlist 수집 모듈
- GAS 웹훅을 경유하여 Steam "인기 출시 예정" (Wishlist 기반) 데이터 수집
"""

import logging
import requests

from config import GAS_WEBHOOK_URL

logger = logging.getLogger(__name__)


def collect_wishlist_trending() -> list[dict]:
    """Steam 인기 출시 예정 게임 (Wishlist 기반 정렬)"""
    if not GAS_WEBHOOK_URL:
        logger.warning("GAS_WEBHOOK_URL 미설정, Wishlist 수집 건너뜀")
        return []

    try:
        resp = requests.get(
            GAS_WEBHOOK_URL,
            params={"action": "wishlist"},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("success"):
            games = data.get("games", [])
            logger.info(f"  Wishlist Trending 수집 완료: {len(games)}개")
            return games
        else:
            logger.warning(f"  Wishlist 수집 실패: {data.get('error', 'unknown')}")
            return []

    except Exception as e:
        logger.error(f"Wishlist 수집 실패: {e}")
        return []
