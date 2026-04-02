"""
Confluence Publisher
- 리포트 데이터를 Confluence Storage Format(네이티브)으로 변환하여 페이지 생성
- expand macro로 펼쳐보기 구현
- Confluence REST API (Basic Auth)
"""

import requests
import logging
from datetime import datetime

from config import (
    CONFLUENCE_BASE_URL,
    CONFLUENCE_USER_EMAIL,
    CONFLUENCE_API_TOKEN,
    CONFLUENCE_SPACE_KEY,
    CONFLUENCE_PARENT_PAGE_ID,
)

logger = logging.getLogger(__name__)


def _esc(text: str) -> str:
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _status(label: str, color: str = "Grey") -> str:
    return f'<ac:structured-macro ac:name="status"><ac:parameter ac:name="colour">{color}</ac:parameter><ac:parameter ac:name="title">{_esc(label)}</ac:parameter></ac:structured-macro>'


def _expand(title: str, body: str) -> str:
    return f'<ac:structured-macro ac:name="expand"><ac:parameter ac:name="title">{title}</ac:parameter><ac:rich-text-body>{body}</ac:rich-text-body></ac:structured-macro>'


def _panel(body: str, panel_type: str = "info") -> str:
    return f'<ac:structured-macro ac:name="{panel_type}"><ac:rich-text-body>{body}</ac:rich-text-body></ac:structured-macro>'


def _link(url: str, label: str) -> str:
    if not url or url == "#":
        return _esc(label)
    return f'<a href="{url}">{_esc(label)}</a>'


def _format_number(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


class ConfluencePublisher:
    def __init__(self):
        self.base_url = CONFLUENCE_BASE_URL.rstrip("/")
        self.api_base = f"{self.base_url}/wiki"
        self.auth = (CONFLUENCE_USER_EMAIL, CONFLUENCE_API_TOKEN)
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def publish_report(self, report_data: dict, issue_number: int) -> dict:
        today = datetime.now().strftime("%Y.%m.%d")
        title = f"Chance Sensor Weekly #{issue_number:03d} ({today})"
        storage_body = self._build_storage_format(report_data, issue_number, today)

        existing = self._find_page_by_title(title)
        if existing:
            logger.info(f"기존 페이지 업데이트: {title}")
            return self._update_page(existing["id"], title, storage_body, existing["version"])
        else:
            logger.info(f"신규 페이지 생성: {title}")
            return self._create_page(title, storage_body)

    def _build_storage_format(self, data: dict, issue_number: int, today: str) -> str:
        parts = []

        summary = data.get("summary", "")
        parts.append(_panel(f'<p><strong>이번 주 핵심:</strong> {_esc(summary)}</p>', "info"))

        # Signal Alert
        signals = data.get("signals", [])
        parts.append('<h2>🔥 Signal Alert</h2>')
        if signals:
            for s in signals:
                level = s.get("relevance_level", "낮음")
                color = {"높음": "Red", "중간": "Yellow"}.get(level, "Grey")
                header = f'{_link(s.get("steam_url", "#"), s.get("name", ""))} {_status("관련도 " + level, color)}'

                body_parts = []
                dev = s.get("developer", "") or ", ".join(s.get("details", {}).get("developers", [])) or "알 수 없음"
                body_parts.append(f'<p><strong>개발사:</strong> {_esc(dev)}</p>')
                body_parts.append(f'<p>{_esc(s.get("signal_text", ""))}</p>')
                why = s.get("why_signal", "")
                aegis = s.get("aegis_relevance", "")
                if why:
                    body_parts.append(f'<p><strong>왜 신호인가:</strong><br/>{why}</p>')
                if aegis:
                    body_parts.append(f'<p><strong>Aegis 관련도:</strong><br/>{aegis}</p>')

                parts.append(_expand(header, "\n".join(body_parts)))
        else:
            parts.append('<p><em>이번 주 감지된 신호 없음</em></p>')

        # Steam Trending
        trending = data.get("trending", [])
        parts.append('<h2>📈 Steam Trending</h2>')
        if trending:
            rows = ['<tr><th>#</th><th>게임명</th><th>장르</th><th>소유자</th><th>변동</th></tr>']
            for i, t in enumerate(trending, 1):
                delta = t.get("delta_pct", 0)
                delta_str = f"▲ {delta}%" if delta > 0 else f"▼ {abs(delta)}%" if delta < 0 else "— 0%"
                rows.append(f'<tr><td>{i}</td><td>{_link(t.get("steam_url", "#"), t.get("name", ""))}</td><td>{_esc(t.get("genre", ""))}</td><td>{_format_number(t.get("owners_mid", 0))}</td><td>{delta_str}</td></tr>')
            parts.append(f'<table><tbody>{"".join(rows)}</tbody></table>')

        # Community Buzz
        buzz = data.get("buzz_items", [])
        parts.append('<h2>💬 Community Buzz</h2>')
        if buzz:
            for b in buzz:
                source = b.get("source", "Reddit")
                parts.append(f'<p>{_status(source, "Purple")} {_link(b.get("url", "#"), b.get("title", ""))}</p>')
                desc = b.get("description", "")
                if desc:
                    parts.append(f'<p><em>{_esc(desc[:200])}</em></p>')
                stats = b.get("stats", "")
                if stats:
                    parts.append(f'<p><small>{_esc(stats)}</small></p>')
        else:
            parts.append('<p><em>Reddit 데이터 수집 대기 중</em></p>')

        # Genre Watch
        genres = data.get("genre_watches", [])
        parts.append('<h2>🎯 Genre Watch</h2>')
        if genres:
            for g in genres:
                trend = g.get("trend", "FLAT")
                trend_color = {"HOT": "Red", "UP": "Green", "DOWN": "Yellow"}.get(trend, "Grey")
                trend_label = {"HOT": "HOT", "UP": "↑ UP", "DOWN": "↓ DOWN"}.get(trend, "— FLAT")
                genre_header = f'{_esc(g.get("genre_name", ""))} {_status(trend_label, trend_color)}'

                body_parts = []
                analysis = g.get("analysis", "")
                if analysis:
                    body_parts.append(f'<p>{analysis}</p>')
                key_titles = g.get("key_titles", [])
                if key_titles:
                    titles = []
                    for t in key_titles:
                        if isinstance(t, dict):
                            titles.append(_link(t.get("url", "#"), t.get("name", "")))
                        else:
                            titles.append(_esc(str(t)))
                    body_parts.append(f'<p><strong>주요 타이틀:</strong> {" · ".join(titles)}</p>')

                expand_body = "\n".join(body_parts) if body_parts else f'<p>{_esc(g.get("summary", ""))}</p>'
                parts.append(_expand(genre_header, expand_body))

        # Watchlist
        watchlist = data.get("watchlist_items", [])
        parts.append('<h2>📋 Watchlist</h2>')
        if watchlist:
            rows = ['<tr><th>상태</th><th>게임명</th><th>태그</th><th>변동</th><th>추적</th></tr>']
            for w in watchlist:
                status = w.get("status", "stable")
                s_color = {"new": "Red", "rising": "Green", "declining": "Yellow"}.get(status, "Grey")
                s_label = {"new": "신규", "rising": "상승", "declining": "하락"}.get(status, "안정")
                delta = w.get("delta_pct", 0)
                delta_str = f"▲ {delta}%" if delta > 0 else f"▼ {abs(delta)}%" if delta < 0 else "— 0%"
                weeks = w.get("weeks_tracked", 0)
                weeks_str = "신규" if weeks <= 1 else f"{weeks}주차"
                tags_str = " ".join(_esc(t) for t in w.get("tags", []))
                rows.append(f'<tr><td>{_status(s_label, s_color)}</td><td>{_link(w.get("url", "#"), w.get("name", ""))}</td><td><small>{tags_str}</small></td><td>{delta_str}</td><td>{weeks_str}</td></tr>')
            parts.append(f'<table><tbody>{"".join(rows)}</tbody></table>')

        # Footer
        parts.append('<hr/>')
        parts.append('<p><small><strong>데이터 소스:</strong> Steam API, SteamSpy, Reddit API · <strong>AI 분석:</strong> Claude API (Sonnet 4.6) · <strong>면책:</strong> 본 리포트의 수치는 공개 데이터 기반 추정치임</small></p>')

        return "\n".join(parts)

    def _create_page(self, title: str, body: str) -> dict:
        payload = {
            "type": "page",
            "title": title,
            "space": {"key": CONFLUENCE_SPACE_KEY},
            "body": {"storage": {"value": body, "representation": "storage"}},
        }
        if CONFLUENCE_PARENT_PAGE_ID:
            payload["ancestors"] = [{"id": CONFLUENCE_PARENT_PAGE_ID}]
        try:
            resp = requests.post(f"{self.api_base}/rest/api/content", auth=self.auth, headers=self.headers, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            page_id = data["id"]
            page_url = f"{self.base_url}/wiki/spaces/{CONFLUENCE_SPACE_KEY}/pages/{page_id}"
            if "_links" in data:
                base = data["_links"].get("base", self.base_url)
                webui = data["_links"].get("webui", "")
                if webui:
                    page_url = f"{base}{webui}"
            logger.info(f"Confluence 페이지 생성 완료: {page_url}")
            return {"page_id": page_id, "url": page_url, "title": title}
        except Exception as e:
            logger.error(f"Confluence 페이지 생성 실패: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"  응답: {e.response.text[:500]}")
            return {"page_id": None, "url": None, "title": title}

    def _update_page(self, page_id: str, title: str, body: str, current_version: int) -> dict:
        payload = {
            "type": "page",
            "title": title,
            "body": {"storage": {"value": body, "representation": "storage"}},
            "version": {"number": current_version + 1},
        }
        try:
            resp = requests.put(f"{self.api_base}/rest/api/content/{page_id}", auth=self.auth, headers=self.headers, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            page_url = f"{self.base_url}/wiki/spaces/{CONFLUENCE_SPACE_KEY}/pages/{page_id}"
            if "_links" in data:
                base = data["_links"].get("base", self.base_url)
                webui = data["_links"].get("webui", "")
                if webui:
                    page_url = f"{base}{webui}"
            logger.info(f"Confluence 페이지 업데이트 완료: {page_url}")
            return {"page_id": page_id, "url": page_url, "title": title}
        except Exception as e:
            logger.error(f"Confluence 페이지 업데이트 실패: {e}")
            return {"page_id": None, "url": None, "title": title}

    def _find_page_by_title(self, title: str) -> dict | None:
        try:
            resp = requests.get(f"{self.api_base}/rest/api/content", auth=self.auth, headers=self.headers, params={"title": title, "spaceKey": CONFLUENCE_SPACE_KEY, "expand": "version"}, timeout=15)
            resp.raise_for_status()
            results = resp.json().get("results", [])
            if results:
                return {"id": results[0]["id"], "version": results[0]["version"]["number"]}
            return None
        except Exception as e:
            logger.error(f"Confluence 페이지 검색 실패: {e}")
            return None
