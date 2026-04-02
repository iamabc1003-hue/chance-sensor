"""
Confluence Publisher
- HTML 리포트를 Confluence 페이지로 생성/업데이트
- Confluence REST API (Basic Auth) 사용
- 상위 페이지 아래에 주간 리포트를 하위 페이지로 아카이빙
"""

import requests
import logging
import re
from datetime import datetime

from config import (
    CONFLUENCE_BASE_URL,
    CONFLUENCE_USER_EMAIL,
    CONFLUENCE_API_TOKEN,
    CONFLUENCE_SPACE_KEY,
    CONFLUENCE_PARENT_PAGE_ID,
)

logger = logging.getLogger(__name__)


class ConfluencePublisher:
    def __init__(self):
        self.base_url = CONFLUENCE_BASE_URL.rstrip("/")
        # Atlassian Cloud는 /wiki/rest/api 경로 사용
        self.api_base = f"{self.base_url}/wiki"
        self.auth = (CONFLUENCE_USER_EMAIL, CONFLUENCE_API_TOKEN)
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def publish_report(self, html_content: str, issue_number: int) -> dict:
        """
        리포트를 Confluence 페이지로 생성
        Returns: {"page_id": ..., "url": ..., "title": ...}
        """
        today = datetime.now().strftime("%Y.%m.%d")
        title = f"Chance Sensor Weekly #{issue_number:03d} ({today})"

        # Confluence Storage Format으로 변환
        storage_body = self._convert_to_storage_format(html_content)

        # 기존 동일 제목 페이지 확인 (중복 방지)
        existing = self._find_page_by_title(title)
        if existing:
            logger.info(f"기존 페이지 업데이트: {title}")
            return self._update_page(existing["id"], title, storage_body, existing["version"])
        else:
            logger.info(f"신규 페이지 생성: {title}")
            return self._create_page(title, storage_body)

    def _create_page(self, title: str, body: str) -> dict:
        """Confluence 페이지 생성"""
        payload = {
            "type": "page",
            "title": title,
            "space": {"key": CONFLUENCE_SPACE_KEY},
            "body": {
                "storage": {
                    "value": body,
                    "representation": "storage",
                }
            },
        }

        # 상위 페이지가 설정되어 있으면 하위 페이지로 생성
        if CONFLUENCE_PARENT_PAGE_ID:
            payload["ancestors"] = [{"id": CONFLUENCE_PARENT_PAGE_ID}]

        try:
            resp = requests.post(
                f"{self.api_base}/rest/api/content",
                auth=self.auth,
                headers=self.headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            page_id = data["id"]
            page_url = f"{self.base_url}/wiki/spaces/{CONFLUENCE_SPACE_KEY}/pages/{page_id}"

            # _links에서 정확한 URL 추출
            if "_links" in data:
                base = data["_links"].get("base", self.base_url)
                webui = data["_links"].get("webui", "")
                if webui:
                    page_url = f"{base}{webui}"

            logger.info(f"Confluence 페이지 생성 완료: {page_url}")
            return {
                "page_id": page_id,
                "url": page_url,
                "title": title,
            }

        except Exception as e:
            logger.error(f"Confluence 페이지 생성 실패: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"  응답: {e.response.text[:500]}")
            return {"page_id": None, "url": None, "title": title}

    def _update_page(self, page_id: str, title: str, body: str, current_version: int) -> dict:
        """기존 Confluence 페이지 업데이트"""
        payload = {
            "type": "page",
            "title": title,
            "body": {
                "storage": {
                    "value": body,
                    "representation": "storage",
                }
            },
            "version": {"number": current_version + 1},
        }

        try:
            resp = requests.put(
                f"{self.api_base}/rest/api/content/{page_id}",
                auth=self.auth,
                headers=self.headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            page_url = f"{self.base_url}/wiki/spaces/{CONFLUENCE_SPACE_KEY}/pages/{page_id}"
            if "_links" in data:
                base = data["_links"].get("base", self.base_url)
                webui = data["_links"].get("webui", "")
                if webui:
                    page_url = f"{base}{webui}"

            logger.info(f"Confluence 페이지 업데이트 완료: {page_url}")
            return {
                "page_id": page_id,
                "url": page_url,
                "title": title,
            }

        except Exception as e:
            logger.error(f"Confluence 페이지 업데이트 실패: {e}")
            return {"page_id": None, "url": None, "title": title}

    def _find_page_by_title(self, title: str) -> dict | None:
        """제목으로 기존 페이지 검색"""
        try:
            resp = requests.get(
                f"{self.api_base}/rest/api/content",
                auth=self.auth,
                headers=self.headers,
                params={
                    "title": title,
                    "spaceKey": CONFLUENCE_SPACE_KEY,
                    "expand": "version",
                },
                timeout=15,
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])

            if results:
                page = results[0]
                return {
                    "id": page["id"],
                    "version": page["version"]["number"],
                }
            return None

        except Exception as e:
            logger.error(f"Confluence 페이지 검색 실패: {e}")
            return None

    def _convert_to_storage_format(self, html_content: str) -> str:
        """
        HTML 리포트를 Confluence Storage Format으로 변환
        - <style> 태그는 Confluence에서 지원하지 않으므로 HTML macro로 감싸기
        - 또는 전체 HTML을 HTML macro 안에 삽입
        """
        # Confluence HTML macro로 전체 HTML을 감싸는 방식
        # 이렇게 하면 원본 HTML의 스타일과 인터랙션이 그대로 유지됨
        escaped_html = (
            html_content
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        # ac:structured-macro로 HTML 삽입
        storage = f"""
<ac:structured-macro ac:name="html" ac:schema-version="1">
  <ac:plain-text-body><![CDATA[{html_content}]]></ac:plain-text-body>
</ac:structured-macro>
"""
        return storage
