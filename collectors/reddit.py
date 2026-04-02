"""
Reddit 데이터 수집 모듈
- OAuth 인증 기반 Reddit API
- 게임 관련 서브레딧 주간 인기 포스트 수집
"""

import requests
import logging
from typing import Optional

from config import (
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_USER_AGENT,
    REDDIT_SUBREDDITS,
    REDDIT_TOP_N_PER_SUB,
    REDDIT_MIN_UPVOTES,
)

logger = logging.getLogger(__name__)


class RedditCollector:
    BASE_URL = "https://oauth.reddit.com"
    AUTH_URL = "https://www.reddit.com/api/v1/access_token"

    def __init__(self):
        self.token = None
        self._authenticate()

    def _authenticate(self):
        """Reddit OAuth2 인증 (script app)"""
        try:
            resp = requests.post(
                self.AUTH_URL,
                auth=(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET),
                data={"grant_type": "client_credentials"},
                headers={"User-Agent": REDDIT_USER_AGENT},
                timeout=15,
            )
            resp.raise_for_status()
            self.token = resp.json().get("access_token")
            logger.info("Reddit 인증 성공")
        except Exception as e:
            logger.error(f"Reddit 인증 실패: {e}")
            self.token = None

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "User-Agent": REDDIT_USER_AGENT,
        }

    def get_top_posts(self, subreddit: str, time_filter: str = "week", limit: int = None) -> list[dict]:
        """특정 서브레딧의 주간 인기 포스트 수집"""
        if not self.token:
            logger.warning("Reddit 토큰 없음, 수집 건너뜀")
            return []

        limit = limit or REDDIT_TOP_N_PER_SUB

        try:
            resp = requests.get(
                f"{self.BASE_URL}/r/{subreddit}/top",
                headers=self._headers(),
                params={"t": time_filter, "limit": limit},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            posts = []
            for child in data.get("data", {}).get("children", []):
                post = child.get("data", {})
                upvotes = post.get("ups", 0)

                if upvotes < REDDIT_MIN_UPVOTES:
                    continue

                posts.append({
                    "subreddit": subreddit,
                    "title": post.get("title", ""),
                    "url": f"https://www.reddit.com{post.get('permalink', '')}",
                    "upvotes": upvotes,
                    "num_comments": post.get("num_comments", 0),
                    "created_utc": post.get("created_utc", 0),
                    "author": post.get("author", ""),
                    "selftext": post.get("selftext", "")[:500],  # 본문 500자까지
                    "link_flair_text": post.get("link_flair_text", ""),
                })

            return posts

        except Exception as e:
            logger.error(f"Reddit r/{subreddit} 수집 실패: {e}")
            return []

    def collect_all_subreddits(self) -> list[dict]:
        """설정된 모든 서브레딧에서 인기 포스트 수집"""
        all_posts = []
        for sub in REDDIT_SUBREDDITS:
            logger.info(f"Reddit r/{sub} 수집 중...")
            posts = self.get_top_posts(sub)
            all_posts.extend(posts)
            logger.info(f"  → {len(posts)}건 수집")

        # 업보트 수 기준 내림차순 정렬
        all_posts.sort(key=lambda x: x["upvotes"], reverse=True)
        return all_posts

    def search_game_mentions(self, game_name: str, subreddits: list[str] = None) -> list[dict]:
        """특정 게임명으로 Reddit 검색"""
        if not self.token:
            return []

        subreddits = subreddits or REDDIT_SUBREDDITS
        results = []

        for sub in subreddits:
            try:
                resp = requests.get(
                    f"{self.BASE_URL}/r/{sub}/search",
                    headers=self._headers(),
                    params={
                        "q": game_name,
                        "restrict_sr": "on",
                        "sort": "relevance",
                        "t": "week",
                        "limit": 10,
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()

                for child in data.get("data", {}).get("children", []):
                    post = child.get("data", {})
                    results.append({
                        "subreddit": sub,
                        "title": post.get("title", ""),
                        "url": f"https://www.reddit.com{post.get('permalink', '')}",
                        "upvotes": post.get("ups", 0),
                        "num_comments": post.get("num_comments", 0),
                    })

            except Exception as e:
                logger.error(f"Reddit 검색 r/{sub} '{game_name}' 실패: {e}")

        results.sort(key=lambda x: x["upvotes"], reverse=True)
        return results
