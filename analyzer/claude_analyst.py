"""
Claude API Analyst
- 수집된 데이터를 Claude API에 전달하여 분석 텍스트 생성
- Signal Alert 분석, Genre Watch 상세, 헤더 요약
- 특정 프로젝트 관련도가 아닌, 시장에서 새로운 기회를 발견하는 관점
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
    Returns: {"signal_text": ..., "why_signal": ..., "market_value": ..., "signal_level": ...}
    """
    system = """당신은 게임 시장 분석 전문가입니다. 
RisingWings는 크래프톤 그룹 산하 게임 개발 스튜디오로, 시장에서 새로운 기회를 발견하여 신작 게임을 기획하는 데 참고하고자 합니다.
중요한 것은 대형 AAA 타이틀보다 소규모라도 혁신적인 게임플레이나 새로운 장르 조합으로 주목받는 게임을 감지하는 것입니다.
주어진 게임 데이터를 분석하여:
1. 이 게임이 시장에서 왜 주목할 만한 신호인지
2. 이 게임의 게임플레이/메커니즘에서 신작 기획 시 참고할 만한 요소가 있는지
를 평가해주세요.
반드시 한국어로 응답하세요. JSON 형식으로만 응답하세요."""

    user = f"""다음 게임 데이터를 분석해주세요:

게임 정보:
{json.dumps(game_data, ensure_ascii=False, indent=2)}

다음 JSON 형식으로 응답하세요 (마크다운 코드블록 없이 순수 JSON만):
{{
  "signal_text": "이 게임이 왜 주목받고 있는지 1~2문장 요약",
  "why_signal": "왜 신호인가에 대한 상세 분석 — 게임플레이 혁신, 장르 조합, 시장 반응 등 (2~3문장, HTML <br> 줄바꿈 사용)",
  "market_value": "신작 기획 시 참고할 만한 요소 분석 — 어떤 게임플레이 요소가 시장에서 통하고 있는지 (2~3문장, HTML <br> 줄바꿈 사용)",
  "signal_level": "높음/중간/낮음 중 하나 (소규모라도 혁신적이면 높음)"
}}"""

    result = _call_claude(system, user)
    try:
        cleaned = result.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.error(f"Signal 분석 JSON 파싱 실패: {result[:200]}")
        return {
            "signal_text": "AI 분석 생성 실패.",
            "why_signal": "",
            "market_value": "",
            "signal_level": "낮음",
        }


def analyze_genre_trend(genre_name: str, genre_games: list[dict], reddit_posts: list[dict]) -> dict:
    """
    Genre Watch 상세 분석
    Returns: {"summary": ..., "analysis": ..., "key_titles": [...], "trend": ...}
    """
    system = """당신은 게임 시장 장르 트렌드 분석 전문가입니다.
각 장르의 시장 동향을 분석하되, 대형 타이틀보다는 새롭게 부상하는 소규모/인디 게임과 혁신적 게임플레이 트렌드에 주목합니다.
신작 게임 기획의 기회를 발견하는 관점에서 분석해주세요.
반드시 한국어로 응답하세요. JSON 형식으로만 응답하세요."""

    # 장르 게임 중 소규모 타이틀 우선 포함
    small_games = [g for g in genre_games if _parse_owners_mid(g.get("owners", "0 .. 0")) < 5_000_000][:10]
    big_games = [g for g in genre_games if _parse_owners_mid(g.get("owners", "0 .. 0")) >= 5_000_000][:5]
    sample_games = small_games + big_games

    user = f"""장르: {genre_name}

이 장르의 주요 게임 목록 (소규모~대형 혼합):
{json.dumps(sample_games[:15], ensure_ascii=False, indent=2)}

다음 JSON 형식으로 응답하세요 (마크다운 코드블록 없이 순수 JSON만):
{{
  "summary": "장르 트렌드 1줄 요약 (특히 새로운 움직임이나 혁신에 초점)",
  "analysis": "판단 근거 상세 분석. 소규모 게임에서 보이는 새로운 트렌드, 장르 혼합 실험, 유저 반응 등. HTML <strong>태그와 <br> 줄바꿈 사용",
  "key_titles": ["주목할 타이틀1", "주목할 타이틀2", ...],
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
RisingWings가 신작 게임 기획의 기회를 발견하는 관점에서, 이번 주 가장 주목할 만한 시장 신호를 강조합니다.
대형 타이틀보다 소규모 혁신적 게임플레이 트렌드에 주목합니다.
순수 텍스트만 응답하세요."""

    user = f"""이번 주 주요 신호:
{json.dumps([{"name": s["name"], "delta_pct": s.get("delta_pct", 0)} for s in signals[:5]], ensure_ascii=False)}

장르 트렌드:
{json.dumps([{"genre": g.get("genre_name", ""), "trend": g.get("trend", "")} for g in genre_trends], ensure_ascii=False)}

이번 주 핵심을 1~2문장으로 요약해주세요."""

    return _call_claude(system, user).strip()


def _parse_owners_mid(owners_str: str) -> int:
    try:
        parts = owners_str.replace(",", "").split(" .. ")
        low = int(parts[0])
        high = int(parts[1]) if len(parts) > 1 else low
        return (low + high) // 2
    except (ValueError, IndexError):
        return 0
