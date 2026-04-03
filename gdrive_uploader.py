"""
Google Drive 업로드 모듈
- Google Apps Script 웹훅을 통해 HTML 리포트를 Google Drive에 업로드
"""

import base64
import json
import logging
import os

import requests

from config import GAS_WEBHOOK_URL

logger = logging.getLogger(__name__)


def upload_report(html_path: str, issue_number: int) -> dict:
    """
    HTML 리포트를 GAS 웹훅을 통해 Google Drive에 업로드
    Returns: {"file_id": ..., "url": ..., "name": ...}
    """
    if not GAS_WEBHOOK_URL:
        logger.warning("GAS_WEBHOOK_URL 미설정, 업로드 건너뜀")
        return {"file_id": None, "url": None, "name": None}

    filename = os.path.basename(html_path)

    try:
        with open(html_path, "rb") as f:
            content_b64 = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "filename": filename,
            "content": content_b64,
        }

        resp = requests.post(
            GAS_WEBHOOK_URL,
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("success"):
            file_url = data.get("url", "")
            logger.info(f"Google Drive 업로드 완료: {filename}")
            logger.info(f"  URL: {file_url}")
            return {
                "file_id": data.get("fileId", ""),
                "url": file_url,
                "name": filename,
            }
        else:
            logger.error(f"GAS 업로드 실패: {data.get('error', 'unknown')}")
            return {"file_id": None, "url": None, "name": None}

    except Exception as e:
        logger.error(f"Google Drive 업로드 실패: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"  응답: {e.response.text[:500]}")
        return {"file_id": None, "url": None, "name": None}
