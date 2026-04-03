"""
Reddit 수집 모듈
- Google Apps Script 웹훅을 경유하여 Reddit 데이터 수집
- GitHub Actions IP에서 Reddit 직접 접근이 차단되므로 GAS(Google 서버)를 프록시로 사용
"""

import logging
import requests

from config import GAS_WEBHOOK_URL

logger = logging.getLogger(__name__)


def collect_reddit_posts() -> list[dict]:
    """GAS 웹훅을 통해 Reddit 인기 포스트 수집"""
    if not GAS_WEBHOOK_URL:
        logger.warning("GAS_WEBHOOK_URL 미설정, Reddit 수집 건너뜀")
        return []

    try:
        # GAS doGet에 action=reddit 파라미터로 호출
        resp = requests.get(
            GAS_WEBHOOK_URL,
            params={"action": "reddit"},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("success"):
            posts = data.get("posts", [])
            logger.info(f"  Reddit 수집 완료: {len(posts)}개 포스트")
            return posts
        else:
            logger.warning(f"  Reddit 수집 실패: {data.get('error', 'unknown')}")
            return []

    except Exception as e:
        logger.error(f"Reddit 수집 실패: {e}")
        return []
