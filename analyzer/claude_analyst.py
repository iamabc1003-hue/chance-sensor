"""
Claude API Analyst
- 수집된 데이터를 Claude API에 전달하여 분석 텍스트 생성
- Signal Alert 분석, Genre Watch 상세, 헤더 요약
"""

import json
import logging
import requests

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, CLAUDE_MAX_TOKENS

logger = logging.getLogger(__name__)

API_URL = "https://api.anthropic.com/v1/messages"
HEADERS = {
    "Content-Type": "application/json",
    "x-api-key": ANTHROPIC_API_KEY,
    "anthropic-version": "2023-06-01",
}


def _call_claude(system_prompt: str, user_prompt: str) -> str:
    """Claude API 호출 공통 함수"""
    try:
        resp = requests.post(
            API_URL,
            headers=HEADERS,
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

        text_parts = [
            block["text"]
            for block in data.get("content", [])
            if block.get("type") == "text"
        ]
        return "\n".join(text_parts)

    except Exception as e:
        logger.error(f"Claude API 호출 실패: {e}")
        return ""


def analyze_signal(game_data: dict, reddit_mentions: list[dict]) -> dict:
    """
    Signal Alert 게임 분석
    Returns: {"signal_text": ..., "why_signal": ..., "aegis_relevance": ..., "relevance_level": ...}
    """
    system = """당신은 게임 시장 분석 전문가입니다. RisingWings는 크래프톤 그룹 산하 모바일 게임 개발 스튜디오이며, 
현재 Aegis라는 턴제 RPG/JRPG 프로젝트를 개발 중입니다. 
주어진 게임 데이터를 분석하여 왜 이 게임이 시장 신호로 주목할 만한지, 
그리고 Aegis 프로젝트와의 관련도를 평가해주세요.
반드시 한국어로 응답하세요. JSON 형식으로만 응답하세요."""

    user = f"""다음 게임 데이터를 분석해주세요:

게임 정보:
{json.dumps(game_data, ensure_ascii=False, indent=2)}

Reddit 관련 포스트:
{json.dumps(reddit_mentions[:5], ensure_ascii=False, indent=2)}

다음 JSON 형식으로 응답하세요 (마크다운 코드블록 없이 순수 JSON만):
{{
  "signal_text": "이 게임이 왜 주목받고 있는지 1~2문장 요약",
  "why_signal": "왜 신호인가에 대한 상세 분석 (2~3문장, HTML <br> 줄바꿈 사용)",
  "aegis_relevance": "Aegis 프로젝트와의 관련도 분석 (2~3문장, HTML <br> 줄바꿈 사용)",
  "relevance_level": "높음/중간/낮음 중 하나"
}}"""

    result = _call_claude(system, user)
    try:
        cleaned = result.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.error(f"Signal 분석 JSON 파싱 실패: {result[:200]}")
        return {
            "signal_text": "분석 데이터 수집 완료. AI 분석 생성 실패.",
            "why_signal": "",
            "aegis_relevance": "",
            "relevance_level": "낮음",
        }


def analyze_genre_trend(genre_name: str, genre_games: list[dict], reddit_posts: list[dict]) -> dict:
    """
    Genre Watch 상세 분석
    Returns: {"summary": ..., "analysis": ..., "key_titles": [...], "trend": ...}
    """
    system = """당신은 게임 시장 장르 트렌드 분석 전문가입니다. RisingWings의 Aegis(턴제 RPG) 프로젝트 관점에서 
각 장르의 시장 동향을 분석합니다. 반드시 한국어로 응답하세요. JSON 형식으로만 응답하세요."""

    user = f"""장르: {genre_name}

관련 인기 게임 목록 (최근 2주):
{json.dumps(genre_games[:10], ensure_ascii=False, indent=2)}

관련 Reddit 인기 포스트:
{json.dumps(reddit_posts[:5], ensure_ascii=False, indent=2)}

다음 JSON 형식으로 응답하세요 (마크다운 코드블록 없이 순수 JSON만):
{{
  "summary": "장르 트렌드 1줄 요약",
  "analysis": "판단 근거 상세 분석. 정량/정성/시사점 구분. HTML <strong>태그와 <br> 줄바꿈 사용. Aegis 관점 시사점 포함",
  "key_titles": ["주요 타이틀1", "주요 타이틀2", ...],
  "trend": "HOT/UP/FLAT/DOWN 중 하나"
}}"""

    result = _call_claude(system, user)
    try:
        cleaned = result.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.error(f"Genre 분석 JSON 파싱 실패: {result[:200]}")
        return {
            "summary": f"{genre_name} 장르 데이터 수집 완료.",
            "analysis": "AI 분석 생성 실패.",
            "key_titles": [],
            "trend": "FLAT",
        }


def generate_weekly_summary(signals: list[dict], genre_trends: list[dict], buzz_items: list[dict]) -> str:
    """리포트 헤더의 이번 주 핵심 한줄 요약 생성"""
    system = """게임 시장 주간 리포트의 핵심 요약을 한국어 1~2문장으로 작성합니다. 
RisingWings(Aegis 프로젝트, 턴제 RPG) 관점에서 가장 중요한 신호를 강조합니다.
순수 텍스트만 응답하세요."""

    user = f"""이번 주 주요 신호:
{json.dumps([{"name": s["name"], "delta_pct": s.get("delta_pct", 0)} for s in signals[:3]], ensure_ascii=False)}

장르 트렌드:
{json.dumps([{"genre": g.get("genre_name", ""), "trend": g.get("trend", "")} for g in genre_trends], ensure_ascii=False)}

커뮤니티 화제 (상위 3건):
{json.dumps([{"title": b.get("title", ""), "upvotes": b.get("upvotes", 0)} for b in buzz_items[:3]], ensure_ascii=False)}

이번 주 핵심을 1~2문장으로 요약해주세요."""

    return _call_claude(system, user).strip()
