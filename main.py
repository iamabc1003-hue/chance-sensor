"""
Chance Sensor - Main Pipeline
매주 목요일 오후 5시(KST) GitHub Actions 자동 실행

Steam 수집 → Signal 감지 → Claude 분석 → HTML 생성 → Google Drive 업로드
"""

import logging
import sys
from datetime import datetime

from collectors.steam import get_top_games_2weeks, collect_genre_games, enrich_games_with_details
from analyzer.signal_detector import (
    load_watchlist, save_watchlist,
    detect_signals, update_watchlist_status,
)
from analyzer.claude_analyst import (
    analyze_signal, analyze_genre_trend, generate_weekly_summary,
)
from report.generator import generate_report
from gdrive_uploader import upload_report
from config import STEAM_TRENDING_TOP_N, TRENDING_OWNERS_MIN, TRENDING_OWNERS_MAX, TRENDING_MIN_REVIEWS
from utils import parse_owners_mid

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("chance-sensor")


def get_issue_number() -> int:
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
    logger.info("[1/5] Steam 데이터 수집...")

    raw_games = get_top_games_2weeks()
    logger.info(f"  → Top 2weeks: {len(raw_games)}개")

    logger.info("  장르별 태그 수집...")
    genre_game_map = collect_genre_games()
    total = sum(len(v) for v in genre_game_map.values())
    logger.info(f"  → 장르별 총 {total}개")

    # 전체 게임 풀 (중복 제거)
    all_games = {}
    for g in raw_games:
        all_games[g["appid"]] = g
    for games in genre_game_map.values():
        for g in games:
            if g["appid"] not in all_games:
                all_games[g["appid"]] = g
    all_games_list = list(all_games.values())
    logger.info(f"  → 전체 고유: {len(all_games_list)}개")

    # ── Step 2: Signal 감지 ──
    logger.info("[2/5] Signal 감지...")
    watchlist = load_watchlist()
    signals = detect_signals(all_games_list, watchlist)
    logger.info(f"  → {len(signals)}개 신호")

    # Signal 게임에 상세정보 보강
    signal_games = [s["details"] for s in signals if s.get("details")]
    if signal_games:
        logger.info(f"  Signal {len(signal_games)}개 상세정보 보강...")
        enriched_signals = enrich_games_with_details(signal_games, delay=1.5)
        for s in signals:
            for eg in enriched_signals:
                if s.get("appid") == str(eg.get("appid", "")):
                    s["details"] = eg
                    break

    # ── Step 3: Claude API 분석 ──
    logger.info("[3/5] Claude API 분석...")

    for i, signal in enumerate(signals):
        logger.info(f"  Signal {i+1}/{len(signals)}: {signal['name']}")
        analysis = analyze_signal(signal["details"], [])
        signal.update(analysis)

    genre_watches = []
    for genre_name, genre_games in genre_game_map.items():
        if not genre_games:
            continue
        logger.info(f"  Genre: {genre_name} ({len(genre_games)}개)")
        analysis = analyze_genre_trend(genre_name, genre_games, [])
        analysis["genre_name"] = genre_name
        genre_watches.append(analysis)

    logger.info("  헤더 요약...")
    weekly_summary = generate_weekly_summary(signals, genre_watches, [])
    if not weekly_summary:
        weekly_summary = f"이번 주 {len(signals)}개 신호 감지."

    # ── Trending: 복합 점수 (베이지안 긍정률 + 리뷰수 + 소규모 가산) ──
    # 베이지안 보정: 리뷰 적으면 평균(75%)으로 수렴, 많으면 실제 긍정률 반영
    PRIOR_RATIO = 75.0  # 사전 평균 긍정률
    PRIOR_WEIGHT = 100  # 사전 가중치 (리뷰 100개 수준에서 반반 영향)

    trending_candidates = []
    for game in all_games_list:
        owners = parse_owners_mid(game.get("owners", "0 .. 0"))
        if owners < TRENDING_OWNERS_MIN or owners >= TRENDING_OWNERS_MAX:
            continue

        pos = game.get("positive", 0)
        neg = game.get("negative", 0)
        total_reviews = pos + neg
        if total_reviews < TRENDING_MIN_REVIEWS:
            continue

        # 베이지안 보정 긍정률: 리뷰 적으면 75%로 수렴
        raw_ratio = pos / total_reviews * 100
        bayesian_ratio = (pos + PRIOR_WEIGHT * PRIOR_RATIO / 100) / (total_reviews + PRIOR_WEIGHT) * 100

        # 리뷰수 가산: log 스케일, 리뷰 1000개 → +10, 5000개 → +15, 10000개 → +17
        import math
        review_bonus = min(math.log10(max(total_reviews, 1)) * 5, 20)

        # 소규모 가산: 소유자 적을수록 "숨은 보석" 가능성
        small_bonus = 15 if owners < 300_000 else (8 if owners < 1_000_000 else 0)

        score = bayesian_ratio + review_bonus + small_bonus

        tags = game.get("tags", {})
        genre = list(tags.keys())[0] if isinstance(tags, dict) and tags else ""

        trending_candidates.append({
            "name": game.get("name", ""),
            "steam_url": f"https://store.steampowered.com/app/{game.get('appid', '')}/",
            "genre": genre,
            "owners_mid": owners,
            "positive_ratio": round(raw_ratio, 1),
            "trending_score": round(score, 1),
            "total_reviews": total_reviews,
            "delta_pct": 0,
        })

    trending_candidates.sort(key=lambda x: x["trending_score"], reverse=True)
    trending = trending_candidates[:STEAM_TRENDING_TOP_N]
    logger.info(f"  Trending: {len(trending_candidates)}개 후보 → 상위 {len(trending)}개")

    # Watchlist
    watchlist_items = update_watchlist_status(watchlist)
    save_watchlist(watchlist)

    # ── Step 4: HTML 리포트 ──
    logger.info("[4/5] HTML 리포트 생성...")
    report_path = generate_report(
        issue_number=issue_number,
        summary=weekly_summary,
        signals=signals,
        trending=trending,
        buzz_items=[],
        genre_watches=genre_watches,
        watchlist_items=watchlist_items,
        output_path=f"chance_sensor_{datetime.now().strftime('%Y%m%d')}.html",
    )

    # ── Step 5: Google Drive ──
    logger.info("[5/5] Google Drive 업로드...")
    result = upload_report(report_path, issue_number)
    if result.get("url"):
        logger.info(f"  Drive URL: {result['url']}")
    else:
        logger.warning("  업로드 실패")

    logger.info("=" * 60)
    logger.info("Chance Sensor Weekly Report 생성 완료!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
