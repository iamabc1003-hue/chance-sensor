"""
Chance Sensor - Main Pipeline
매주 목요일 오후 5시(KST) 자동 실행

Pipeline:
1. Steam 데이터 수집 (태그별 장르 + top 2weeks)
2. Signal 감지
3. Claude API 분석
4. HTML 리포트 생성
5. Google Drive 업로드
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
from config import STEAM_TRENDING_TOP_N

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

    logger.info("  장르별 태그 수집 시작...")
    genre_game_map = collect_genre_games()
    total_genre_games = sum(len(v) for v in genre_game_map.values())
    logger.info(f"  → 장르별 총 {total_genre_games}개 게임 수집")

    # 전체 게임 풀 구성 (중복 제거)
    all_games = {}
    for g in raw_games:
        all_games[g["appid"]] = g
    for genre_games in genre_game_map.values():
        for g in genre_games:
            if g["appid"] not in all_games:
                all_games[g["appid"]] = g
    all_games_list = list(all_games.values())
    logger.info(f"  → 전체 고유 게임: {len(all_games_list)}개")

    # 상위 게임 상세정보 보강
    top_sorted = sorted(all_games_list, key=lambda x: _parse_owners_mid(x.get("owners", "0 .. 0")), reverse=True)
    top_games = enrich_games_with_details(top_sorted[:15], delay=1.5)
    logger.info(f"  → {len(top_games)}개 상세정보 보강 완료")

    # ── Step 2: Signal 감지 ──
    logger.info("[2/5] Signal 감지...")
    watchlist = load_watchlist()
    signals = detect_signals(all_games_list, watchlist)
    logger.info(f"  → {len(signals)}개 신호 감지")

    # ── Step 3: Claude API 분석 ──
    logger.info("[3/5] Claude API 분석...")

    for i, signal in enumerate(signals):
        logger.info(f"  Signal 분석 {i+1}/{len(signals)}: {signal['name']}")
        analysis = analyze_signal(signal["details"], [])
        signal.update(analysis)

    genre_watches = []
    for genre_name, genre_games in genre_game_map.items():
        if not genre_games:
            continue
        logger.info(f"  Genre 분석: {genre_name} ({len(genre_games)}개 게임)")
        analysis = analyze_genre_trend(genre_name, genre_games, [])
        analysis["genre_name"] = genre_name
        genre_watches.append(analysis)

    logger.info("  헤더 요약 생성...")
    weekly_summary = generate_weekly_summary(signals, genre_watches, [])
    if not weekly_summary:
        weekly_summary = f"이번 주 {len(signals)}개 신호 감지. 상세 내용은 리포트 참조."

    # Trending + Watchlist 구성
    trending = []
    for game in top_sorted[:STEAM_TRENDING_TOP_N]:
        # 장르: Steam Store genres 우선, 없으면 SteamSpy tags 첫 번째 키
        genres = game.get("genres", [])
        tags = game.get("tags", {})
        if genres:
            genre = genres[0] if isinstance(genres, list) else str(genres)
        elif isinstance(tags, dict) and tags:
            genre = list(tags.keys())[0]
        else:
            genre = ""
        trending.append({
            "name": game.get("name", ""),
            "steam_url": game.get("steam_url", f"https://store.steampowered.com/app/{game.get('appid', '')}/"),
            "genre": genre,
            "owners_mid": _parse_owners_mid(game.get("owners", "0 .. 0")),
            "delta_pct": 0,
        })

    watchlist_items = update_watchlist_status(watchlist)
    save_watchlist(watchlist)

    # ── Step 4: HTML 리포트 생성 ──
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

    # ── Step 5: Google Drive 업로드 ──
    logger.info("[5/5] Google Drive 업로드...")
    result = upload_report(report_path, issue_number)
    if result.get("url"):
        logger.info(f"  Drive URL: {result['url']}")
    else:
        logger.warning("  Google Drive 업로드 실패")

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
