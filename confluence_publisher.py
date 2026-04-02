"""
Confluence Publisher
- 페이지 본문: 요약 텍스트 (Confluence 네이티브)
- 첨부파일: 상세 HTML 리포트
- Confluence REST API (Basic Auth)
"""

import requests
import logging
import os
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


def _link(url: str, label: str) -> str:
    if not url or url == "#":
        return _esc(label)
    return f'<a href="{url}">{_esc(label)}</a>'


class ConfluencePublisher:
    def __init__(self):
        self.base_url = CONFLUENCE_BASE_URL.rstrip("/")
        self.api_base = f"{self.base_url}/wiki"
        self.auth = (CONFLUENCE_USER_EMAIL, CONFLUENCE_API_TOKEN)
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def publish_report(self, report_data: dict, issue_number: int, html_path: str) -> dict:
        """
        1. 요약 본문으로 Confluence 페이지 생성
        2. HTML 리포트를 첨부파일로 업로드
        """
        today = datetime.now().strftime("%Y.%m.%d")
        title = f"Chance Sensor Weekly #{issue_number:03d} ({today})"

        # 요약 본문 생성
        summary_body = self._build_summary(report_data, issue_number, today)

        # 페이지 생성 또는 업데이트
        existing = self._find_page_by_title(title)
        if existing:
            logger.info(f"기존 페이지 업데이트: {title}")
            result = self._update_page(existing["id"], title, summary_body, existing["version"])
        else:
            logger.info(f"신규 페이지 생성: {title}")
            result = self._create_page(title, summary_body)

        # HTML 첨부파일 업로드
        if result.get("page_id") and html_path and os.path.exists(html_path):
            self._attach_file(result["page_id"], html_path)

        return result

    def _build_summary(self, data: dict, issue_number: int, today: str) -> str:
        """Confluence 페이지 본문 — 요약 + 안내"""
        parts = []

        # 핵심 요약
        summary = data.get("summary", "")
        parts.append(f'<ac:structured-macro ac:name="info"><ac:rich-text-body>')
        parts.append(f'<p><strong>이번 주 핵심:</strong> {_esc(summary)}</p>')
        parts.append(f'</ac:rich-text-body></ac:structured-macro>')

        # Signal Alert 요약
        signals = data.get("signals", [])
        parts.append('<h2>🔥 Signal Alert</h2>')
        if signals:
            for s in signals:
                level = s.get("relevance_level", "낮음")
                color = {"높음": "Red", "중간": "Yellow"}.get(level, "Grey")
                name = s.get("name", "")
                url = s.get("steam_url", "#")
                signal_text = s.get("signal_text", "")
                parts.append(f'<p>{_link(url, name)} {_status("관련도 " + level, color)}<br/>{_esc(signal_text)}</p>')
        else:
            parts.append('<p><em>이번 주 감지된 주요 신호 없음</em></p>')

        # Trending 요약 (상위 5개만)
        trending = data.get("trending", [])
        if trending:
            parts.append('<h2>📈 Steam Trending Top 5</h2>')
            rows = ['<tr><th>#</th><th>게임명</th><th>장르</th><th>소유자</th></tr>']
            for i, t in enumerate(trending[:5], 1):
                rows.append(f'<tr><td>{i}</td><td>{_link(t.get("steam_url", "#"), t.get("name", ""))}</td><td>{_esc(t.get("genre", ""))}</td><td>{_format_number(t.get("owners_mid", 0))}</td></tr>')
            parts.append(f'<table><tbody>{"".join(rows)}</tbody></table>')

        # Genre Watch 요약
        genres = data.get("genre_watches", [])
        if genres:
            parts.append('<h2>🎯 Genre Watch</h2>')
            for g in genres:
                trend = g.get("trend", "FLAT")
                trend_color = {"HOT": "Red", "UP": "Green", "DOWN": "Yellow"}.get(trend, "Grey")
                trend_label = {"HOT": "HOT", "UP": "↑ UP", "DOWN": "↓ DOWN"}.get(trend, "— FLAT")
                genre_name = g.get("genre_name", "")
                genre_summary = g.get("summary", "")
                parts.append(f'<p>{_esc(genre_name)} {_status(trend_label, trend_color)} — {_esc(genre_summary)}</p>')

        # Community Buzz 요약
        buzz = data.get("buzz_items", [])
        if buzz:
            parts.append('<h2>💬 Community Buzz</h2>')
            for b in buzz[:5]:
                parts.append(f'<p>{_status(b.get("source", "Reddit"), "Purple")} {_link(b.get("url", "#"), b.get("title", ""))}</p>')

        # 상세 리포트 안내
        parts.append('<hr/>')
        parts.append('<ac:structured-macro ac:name="note"><ac:rich-text-body>')
        parts.append('<p><strong>📄 상세 리포트:</strong> 첨부된 HTML 파일을 다운로드하여 브라우저에서 열면 인터랙티브 상세 리포트를 확인할 수 있습니다. (다크 테마, 펼쳐보기 기능 포함)</p>')
        parts.append('</ac:rich-text-body></ac:structured-macro>')

        # Footer
        parts.append('<p><small><strong>데이터 소스:</strong> Steam API, SteamSpy, Reddit API · <strong>AI 분석:</strong> Claude API (Sonnet 4.6) · <strong>면책:</strong> 공개 데이터 기반 추정치</small></p>')

        return "\n".join(parts)

    def _attach_file(self, page_id: str, file_path: str):
        """Confluence 페이지에 파일 첨부"""
        filename = os.path.basename(file_path)
        try:
            with open(file_path, "rb") as f:
                resp = requests.post(
                    f"{self.api_base}/rest/api/content/{page_id}/child/attachment",
                    auth=self.auth,
                    headers={"X-Atlassian-Token": "nocheck"},
                    files={"file": (filename, f, "text/html")},
                    data={"comment": "Chance Sensor 상세 리포트 (HTML)"},
                    timeout=30,
                )
            resp.raise_for_status()
            logger.info(f"HTML 첨부 완료: {filename}")
        except Exception as e:
            logger.error(f"첨부파일 업로드 실패: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"  응답: {e.response.text[:500]}")

    # ── API Methods ──

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


def _format_number(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)
