"""
Slack 발송 모듈
- Confluence에 아카이빙된 리포트의 URL을 Slack 메시지로 공유
- Confluence 발행 실패 시 HTML 파일 직접 업로드 (fallback)
"""

import requests
import logging
from datetime import datetime

from config import SLACK_BOT_TOKEN, SLACK_CHANNEL_ID

logger = logging.getLogger(__name__)


def send_report_link(confluence_url: str, summary: str, issue_number: int) -> bool:
    """Confluence 리포트 URL을 Slack 메시지로 발송"""
    if not SLACK_BOT_TOKEN or not SLACK_CHANNEL_ID:
        logger.warning("Slack 토큰 또는 채널 ID 미설정, 발송 건너뜀")
        return False

    today = datetime.now().strftime("%Y.%m.%d")

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🔥 Chance Sensor Weekly #{issue_number:03d}",
            },
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"📅 {today} 발행 · RisingWings Internal"}
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*이번 주 핵심:*\n>{summary}",
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📄 리포트 전문 보기"},
                    "url": confluence_url,
                    "style": "primary",
                },
            ],
        },
    ]

    try:
        resp = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "channel": SLACK_CHANNEL_ID,
                "text": f"🔥 Chance Sensor Weekly #{issue_number:03d} — {summary}",
                "blocks": blocks,
                "unfurl_links": False,
            },
            timeout=15,
        )

        result = resp.json()
        if result.get("ok"):
            logger.info(f"Slack 메시지 발송 성공: #{issue_number:03d}")
            return True
        else:
            logger.error(f"Slack 메시지 발송 실패: {result.get('error', 'unknown')}")
            return False

    except Exception as e:
        logger.error(f"Slack 발송 예외: {e}")
        return False


def send_report_file_fallback(html_path: str, summary: str, issue_number: int) -> bool:
    """Confluence 발행 실패 시 HTML 파일 직접 업로드 (fallback)"""
    if not SLACK_BOT_TOKEN or not SLACK_CHANNEL_ID:
        logger.warning("Slack 토큰 또는 채널 ID 미설정, 발송 건너뜀")
        return False

    today = datetime.now().strftime("%Y.%m.%d")
    filename = f"chance_sensor_{today.replace('.', '')}.html"

    message = (
        f"🔥 *Chance Sensor Weekly #{issue_number:03d}*\n"
        f"_{today} 발행_\n\n"
        f">{summary}\n\n"
        f"⚠️ Confluence 발행 실패로 HTML 파일을 직접 첨부합니다. "
        f"다운로드 후 브라우저에서 열어주세요."
    )

    try:
        with open(html_path, "rb") as f:
            resp = requests.post(
                "https://slack.com/api/files.upload",
                headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
                data={
                    "channels": SLACK_CHANNEL_ID,
                    "initial_comment": message,
                    "filename": filename,
                    "filetype": "html",
                    "title": f"Chance Sensor Weekly #{issue_number:03d}",
                },
                files={"file": (filename, f, "text/html")},
                timeout=30,
            )

        result = resp.json()
        if result.get("ok"):
            logger.info(f"Slack 파일 업로드 성공 (fallback): #{issue_number:03d}")
            return True
        else:
            logger.error(f"Slack 파일 업로드 실패: {result.get('error', 'unknown')}")
            return False

    except Exception as e:
        logger.error(f"Slack fallback 발송 예외: {e}")
        return False
