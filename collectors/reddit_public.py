"""
Reddit 데이터 수집 모듈
- 공개 JSON 엔드포인트 사용 (OAuth 인증 불필요)
- Reddit API 승인 후 OAuth 방식으로 전환 가능
"""

import requests
import time
import logging

from config import (
    REDDIT_USER_AGENT,
    REDDIT_SUBREDDITS,
    REDDIT_TOP_N_PER_SUB,
    REDDIT_MIN_UPVOTES,
)

logger = logging.getLogger(__name__)


class RedditCollector:
    """공개 JSON 엔드포인트 기반 Reddit 수집"""

    BASE_URL = "https://www.reddit.com"

    def __init__(self):
        self.session = requests.Session()
        # Reddit 공개 JSON은 봇 User-Agent를 차단하므로 브라우저 UA 사용
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "application/json",
        })

    def get_top_posts(self, subreddit: str, time_filter: str = "week", limit: int = None) -> list[dict]:
        """특정 서브레딧의 주간 인기 포스트 수집"""
        limit = limit or REDDIT_TOP_N_PER_SUB

        try:
            resp = self.session.get(
                f"{self.BASE_URL}/r/{subreddit}/top.json",
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
                    "selftext": post.get("selftext", "")[:500],
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
            time.sleep(2)  # 공개 엔드포인트 rate limit 준수

        all_posts.sort(key=lambda x: x["upvotes"], reverse=True)
        return all_posts

    def search_game_mentions(self, game_name: str, subreddits: list[str] = None) -> list[dict]:
        """특정 게임명으로 Reddit 검색"""
        subreddits = subreddits or REDDIT_SUBREDDITS
        results = []

        for sub in subreddits:
            try:
                resp = self.session.get(
                    f"{self.BASE_URL}/r/{sub}/search.json",
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

                time.sleep(2)

            except Exception as e:
                logger.error(f"Reddit 검색 r/{sub} '{game_name}' 실패: {e}")

        results.sort(key=lambda x: x["upvotes"], reverse=True)
        return results
