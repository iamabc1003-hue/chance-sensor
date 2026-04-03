"""
Gmail 발송 모듈
- HTML 리포트를 이메일 첨부파일로 발송
- smtplib + Gmail App Password 사용
"""

import smtplib
import logging
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

from config import GMAIL_SENDER, GMAIL_APP_PASSWORD, GMAIL_RECIPIENTS

logger = logging.getLogger(__name__)


def send_report_email(html_path: str, summary: str, issue_number: int, confluence_url: str = None) -> bool:
    """HTML 리포트를 이메일로 발송"""
    if not GMAIL_SENDER or not GMAIL_APP_PASSWORD or not GMAIL_RECIPIENTS:
        logger.warning("Gmail 설정 미완료, 이메일 발송 건너뜀")
        return False

    today = datetime.now().strftime("%Y.%m.%d")

    # 이메일 구성
    msg = MIMEMultipart()
    msg["From"] = GMAIL_SENDER
    msg["To"] = ", ".join(GMAIL_RECIPIENTS)
    msg["Subject"] = f"🔥 Chance Sensor Weekly #{issue_number:03d} ({today})"

    # 본문
    body_parts = [
        f"Chance Sensor Weekly #{issue_number:03d}",
        f"발행일: {today}",
        "",
        f"이번 주 핵심: {summary}",
        "",
    ]

    if confluence_url:
        body_parts.append(f"Confluence 페이지: {confluence_url}")
        body_parts.append("")

    body_parts.extend([
        "첨부된 HTML 파일을 다운로드하여 브라우저에서 열면",
        "인터랙티브 상세 리포트를 확인할 수 있습니다.",
        "(다크 테마, 펼쳐보기 기능 포함)",
        "",
        "---",
        "Chance Sensor · RisingWings Internal",
    ])

    body = "\n".join(body_parts)
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # HTML 파일 첨부
    if html_path and os.path.exists(html_path):
        filename = os.path.basename(html_path)
        try:
            with open(html_path, "rb") as f:
                part = MIMEBase("text", "html")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={filename}")
                msg.attach(part)
        except Exception as e:
            logger.error(f"HTML 파일 첨부 실패: {e}")
            return False

    # 발송
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_SENDER, GMAIL_RECIPIENTS, msg.as_string())

        logger.info(f"이메일 발송 성공: #{issue_number:03d} → {', '.join(GMAIL_RECIPIENTS)}")
        return True

    except Exception as e:
        logger.error(f"이메일 발송 실패: {e}")
        return False
