"""
Claude API Analyst
- 시장에서 새로운 기회를 발견하는 관점으로 분석
"""

import json
import logging
import os
import requests

from config import CLAUDE_MODEL, CLAUDE_MAX_TOKENS
from utils import parse_owners_mid

logger = logging.getLogger(__name__)

API_URL = "https://api.anthropic.com/v1/messages"


def _get_headers() -> dict:
    """호출 시점에 API 키를 읽어 헤더 생성"""
    return {
        "Content-Type": "application/json",
        "x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""),
        "anthropic-version": "2023-06-01",
    }


def _call_claude(system_prompt: str, user_prompt: str) -> str:
    try:
        resp = requests.post(
            API_URL,
            headers=_get_headers(),
            json={
                "model": CLAUDE_MODEL,
                "max_tokens": CLAUDE_MAX_TOKENS,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return "\n".join(
            block["text"] for block in data.get("content", [])
            if block.get("type") == "text"
        )
    except Exception as e:
        logger.error(f"Claude API 호출 실패: {e}")
        return ""


def analyze_signal(game_data: dict, reddit_mentions: list[dict]) -> dict:
    """Signal Alert 게임 분석"""
    system = """당신은 게임 시장 분석 전문가입니다. 
RisingWings는 크래프톤 그룹 산하 게임 개발 스튜디오로, 시장에서 새로운 기회를 발견하여 신작 게임을 기획하는 데 참고하고자 합니다.
중요한 것은 대형 AAA 타이틀보다 소규모라도 혁신적인 게임플레이나 새로운 장르 조합으로 주목받는 게임을 감지하는 것입니다.
반드시 한국어로 응답하세요. JSON 형식으로만 응답하세요."""

    user = f"""다음 게임 데이터를 분석해주세요:

게임 정보:
{json.dumps(game_data, ensure_ascii=False, indent=2)}

다음 JSON 형식으로 응답하세요 (마크다운 코드블록 없이 순수 JSON만):
{{
  "signal_text": "이 게임이 왜 주목받고 있는지 1~2문장 요약",
  "why_signal": "왜 신호인가 — 게임플레이 혁신, 장르 조합, 시장 반응 등 (2~3문장, HTML <br> 줄바꿈 사용)",
  "market_value": "신작 기획 시 참고할 요소 — 어떤 게임플레이가 시장에서 통하는지 (2~3문장, HTML <br> 줄바꿈 사용)",
  "signal_level": "높음/중간/낮음 중 하나 (소규모라도 혁신적이면 높음)"
}}"""

    result = _call_claude(system, user)
    try:
        cleaned = result.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.error(f"Signal 분석 JSON 파싱 실패: {result[:200]}")
        return {"signal_text": "AI 분석 생성 실패.", "why_signal": "", "market_value": "", "signal_level": "낮음"}


def analyze_genre_trend(genre_name: str, genre_games: list[dict], reddit_posts: list[dict]) -> dict:
    """Genre Watch 상세 분석"""
    system = """당신은 게임 시장 장르 트렌드 분석 전문가입니다.
대형 타이틀보다 새롭게 부상하는 소규모/인디 게임과 혁신적 게임플레이 트렌드에 주목합니다.
반드시 한국어로 응답하세요. JSON 형식으로만 응답하세요."""

    small = [g for g in genre_games if parse_owners_mid(g.get("owners", "0")) < 5_000_000][:10]
    big = [g for g in genre_games if parse_owners_mid(g.get("owners", "0")) >= 5_000_000][:5]
    sample = small + big

    user = f"""장르: {genre_name}

게임 목록 (소규모~대형 혼합):
{json.dumps(sample[:15], ensure_ascii=False, indent=2)}

다음 JSON 형식으로 응답하세요 (마크다운 코드블록 없이 순수 JSON만):
{{
  "summary": "장르 트렌드 1줄 요약 (새로운 움직임/혁신에 초점)",
  "analysis": "판단 근거. 소규모 게임의 새 트렌드, 장르 혼합 실험, 유저 반응 등. HTML <strong>태그와 <br> 사용",
  "key_titles": ["주목할 타이틀1", "타이틀2", ...],
  "trend": "HOT/UP/FLAT/DOWN 중 하나"
}}"""

    result = _call_claude(system, user)
    try:
        cleaned = result.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.error(f"Genre 분석 JSON 파싱 실패: {result[:200]}")
        return {"summary": f"{genre_name} 데이터 수집 완료.", "analysis": "AI 분석 실패.", "key_titles": [], "trend": "FLAT"}


def generate_weekly_summary(signals: list[dict], genre_trends: list[dict], buzz_items: list[dict]) -> str:
    """리포트 헤더 핵심 요약"""
    system = """게임 시장 주간 리포트의 핵심을 한국어 1~2문장으로 작성합니다.
신작 기획 기회 발견 관점에서 가장 주목할 시장 신호를 강조합니다. 순수 텍스트만 응답하세요."""

    user = f"""이번 주 주요 신호:
{json.dumps([{"name": s["name"], "delta_pct": s.get("delta_pct", 0)} for s in signals[:5]], ensure_ascii=False)}

장르 트렌드:
{json.dumps([{"genre": g.get("genre_name", ""), "trend": g.get("trend", "")} for g in genre_trends], ensure_ascii=False)}

이번 주 핵심을 1~2문장으로 요약해주세요."""

    return _call_claude(system, user).strip()


def analyze_buzz_posts(posts: list[dict]) -> list[dict]:
    """Community Buzz 포스트별 한글 요약 + 인사이트 + 유형 분류"""
    if not posts:
        return []

    system = """당신은 게임 커뮤니티 동향 분석가입니다.
Reddit 게임 커뮤니티 포스트를 분석하여:
1. 유저들의 게임 토론, 추천, 팬심, 경험 공유 등 "유저 관점" 포스트를 높이 평가
2. 업계 뉴스, 해고, 기업 논란 등 "업계 뉴스" 포스트는 낮게 평가
3. 각 포스트의 핵심 내용을 한국어로 요약하고 게임 기획 관점의 인사이트를 제공

반드시 한국어로 응답하세요. JSON 형식으로만 응답하세요."""

    posts_data = []
    for p in posts[:10]:
        posts_data.append({
            "subreddit": p.get("subreddit", ""),
            "title": p.get("title", ""),
            "selftext": p.get("selftext", "")[:300],
        })

    user = f"""다음 Reddit 인기 포스트들을 분석해주세요:

{json.dumps(posts_data, ensure_ascii=False, indent=2)}

각 포스트에 대해 다음 JSON 배열로 응답하세요 (마크다운 코드블록 없이 순수 JSON만):
[
  {{
    "summary": "포스트 핵심 내용 한국어 요약 (1~2문장)",
    "insight": "게임 기획자 관점 인사이트 — 유저가 원하는 것, 시장에서 통하는 것 중심 (1문장)",
    "type": "user_discussion/fan_love/game_recommendation/industry_news/controversy 중 하나",
    "relevance": 1~5 (유저 토론/팬심이면 5, 업계 뉴스/논란이면 1)
  }},
  ...
]"""

    result = _call_claude(system, user)
    try:
        cleaned = result.strip().replace("```json", "").replace("```", "").strip()
        analyses = json.loads(cleaned)
        # relevance 3 이상만 유지 (업계 뉴스/논란 제외)
        for a in analyses:
            if a.get("relevance", 3) < 3:
                a["summary"] = ""
                a["insight"] = ""
        return analyses
    except json.JSONDecodeError:
        logger.error(f"Buzz 분석 JSON 파싱 실패: {result[:200]}")
        return []
