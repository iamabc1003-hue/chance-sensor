"""
Chance Sensor - Main Pipeline
매주 목요일 오후 5시(KST) 자동 실행

Pipeline:
1. Steam 데이터 수집
2. Reddit 데이터 수집
3. Signal 감지
4. Claude API 분석
5. HTML 리포트 생성
6. Slack 발송
"""

import json
import logging
import sys
from datetime import datetime

from collectors.steam import get_top_games_2weeks, enrich_games_with_details
from collectors.reddit_public import RedditCollector
from analyzer.signal_detector import (
    load_watchlist, save_watchlist,
    detect_signals, update_watchlist_status,
)
from analyzer.genre_aggregator import aggregate_by_genre, filter_reddit_by_genre
from analyzer.claude_analyst import (
    analyze_signal, analyze_genre_trend, generate_weekly_summary,
)
from report.generator import generate_report
from confluence_publisher import ConfluencePublisher
from slack_sender import send_report_link, send_report_file_fallback
from config import GENRE_KEYWORDS, STEAM_TRENDING_TOP_N

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("chance-sensor")


def get_issue_number() -> int:
    """이슈 번호 관리 (간단히 파일 기반)"""
    try:
        with open(".issue_number", "r") as f:
            num = int(f.read().strip())
    except (FileNotFoundError, ValueError):
        num = 0
    num += 1
    with open(".issue_number", "w") as f:
        f.write(str(num))
    return num


def main():
    logger.info("=" * 60)
    logger.info("Chance Sensor Weekly Report 생성 시작")
    logger.info(f"실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    issue_number = get_issue_number()
    logger.info(f"Issue #{issue_number:03d}")

    # ── Step 1: Steam 데이터 수집 ──
    logger.info("[1/6] Steam 데이터 수집...")
    raw_games = get_top_games_2weeks()
    logger.info(f"  → {len(raw_games)}개 게임 수집")

    # 상위 게임에 대해 상세정보 보강 (rate limit 고려하여 상위 20개만)
    top_games = enrich_games_with_details(raw_games[:20], delay=1.5)
    logger.info(f"  → {len(top_games)}개 상세정보 보강 완료")

    # ── Step 2: Reddit 데이터 수집 ──
    logger.info("[2/6] Reddit 데이터 수집...")
    reddit = RedditCollector()
    reddit_posts = reddit.collect_all_subreddits()
    logger.info(f"  → {len(reddit_posts)}개 포스트 수집")

    # ── Step 3: Signal 감지 ──
    logger.info("[3/6] Signal 감지...")
    watchlist = load_watchlist()
    signals = detect_signals(top_games, watchlist)
    logger.info(f"  → {len(signals)}개 신호 감지")

    # ── Step 4: Claude API 분석 ──
    logger.info("[4/6] Claude API 분석...")

    # Signal 분석
    for i, signal in enumerate(signals):
        logger.info(f"  Signal 분석 {i+1}/{len(signals)}: {signal['name']}")
        game_mentions = reddit.search_game_mentions(signal["name"])
        analysis = analyze_signal(signal["details"], game_mentions)
        signal.update(analysis)

    # Genre 분석
    genre_map = aggregate_by_genre(raw_games)
    genre_watches = []
    for genre_name in GENRE_KEYWORDS:
        genre_games = genre_map.get(genre_name, [])
        if not genre_games:
            continue

        logger.info(f"  Genre 분석: {genre_name} ({len(genre_games)}개 게임)")
        genre_reddit = filter_reddit_by_genre(reddit_posts, genre_name)
        analysis = analyze_genre_trend(genre_name, genre_games, genre_reddit)
        analysis["genre_name"] = genre_name
        genre_watches.append(analysis)

    # Community Buzz 구성 (Reddit 상위 포스트)
    buzz_items = []
    for post in reddit_posts[:10]:
        buzz_items.append({
            "source": "Reddit",
            "title": post["title"],
            "url": post["url"],
            "description": post.get("selftext", "")[:200],
            "stats": f"{post['upvotes']:,} upvotes · {post['num_comments']:,} comments · r/{post['subreddit']}",
        })

    # 헤더 요약 생성
    logger.info("  헤더 요약 생성...")
    weekly_summary = generate_weekly_summary(signals, genre_watches, buzz_items)
    if not weekly_summary:
        weekly_summary = f"이번 주 {len(signals)}개 신호 감지. 상세 내용은 리포트 참조."

    # ── Step 5: Trending 데이터 구성 ──
    trending = []
    for game in top_games[:STEAM_TRENDING_TOP_N]:
        tags = game.get("tags", {})
        genre = ""
        if isinstance(tags, dict) and tags:
            genre = list(tags.keys())[0] if tags else ""
        trending.append({
            "name": game.get("name", ""),
            "steam_url": game.get("steam_url", f"https://store.steampowered.com/app/{game.get('appid', '')}/"),
            "genre": genre,
            "owners_mid": _parse_owners_mid(game.get("owners", "0 .. 0")),
            "delta_pct": 0,  # TODO: 전주 대비 비교 로직 추가
        })

    # Watchlist 상태 업데이트
    watchlist_items = update_watchlist_status(watchlist)
    save_watchlist(watchlist)

    # ── Step 6: HTML 리포트 생성 ──
    logger.info("[5/7] HTML 리포트 생성...")
    report_path = generate_report(
        issue_number=issue_number,
        summary=weekly_summary,
        signals=signals,
        trending=trending,
        buzz_items=buzz_items,
        genre_watches=genre_watches,
        watchlist_items=watchlist_items,
        output_path=f"chance_sensor_{datetime.now().strftime('%Y%m%d')}.html",
    )

    # ── Step 7: Confluence 아카이빙 ──
    logger.info("[6/7] Confluence 발행...")
    with open(report_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    confluence = ConfluencePublisher()
    publish_result = confluence.publish_report(html_content, issue_number)

    # ── Step 8: Slack 발송 ──
    logger.info("[7/7] Slack 발송...")
    if publish_result.get("url"):
        # Confluence 발행 성공 → URL 링크 메시지
        send_report_link(publish_result["url"], weekly_summary, issue_number)
        logger.info(f"  Confluence URL: {publish_result['url']}")
    else:
        # Confluence 발행 실패 → HTML 파일 직접 업로드 (fallback)
        logger.warning("  Confluence 발행 실패, HTML 파일 직접 업로드로 전환")
        send_report_file_fallback(report_path, weekly_summary, issue_number)

    logger.info("=" * 60)
    logger.info("Chance Sensor Weekly Report 생성 완료!")
    logger.info("=" * 60)


def _parse_owners_mid(owners_str: str) -> int:
    try:
        parts = owners_str.replace(",", "").split(" .. ")
        low = int(parts[0])
        high = int(parts[1]) if len(parts) > 1 else low
        return (low + high) // 2
    except (ValueError, IndexError):
        return 0


if __name__ == "__main__":
    main()
