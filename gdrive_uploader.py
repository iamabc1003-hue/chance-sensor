"""
Google Drive 업로드 모듈
- Service Account 인증으로 HTML 리포트를 Google Drive에 업로드
- google-auth + requests 기반 (googleapis-common-protos 불필요)
"""

import json
import logging
import os

import requests
from google.oauth2 import service_account

from config import GDRIVE_FOLDER_ID, GDRIVE_SERVICE_ACCOUNT_JSON

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def _get_credentials():
    """Service Account 인증 정보 로드"""
    sa_json = GDRIVE_SERVICE_ACCOUNT_JSON
    if not sa_json:
        logger.warning("GDRIVE_SERVICE_ACCOUNT_JSON 미설정")
        return None

    try:
        sa_info = json.loads(sa_json)
        creds = service_account.Credentials.from_service_account_info(sa_info, scopes=SCOPES)
        return creds
    except Exception as e:
        logger.error(f"Service Account 인증 실패: {e}")
        return None


def upload_report(html_path: str, issue_number: int) -> dict:
    """
    HTML 리포트를 Google Drive에 업로드
    Returns: {"file_id": ..., "url": ..., "name": ...}
    """
    creds = _get_credentials()
    if not creds:
        return {"file_id": None, "url": None, "name": None}

    filename = os.path.basename(html_path)

    # 인증 토큰 획득
    from google.auth.transport.requests import Request
    creds.refresh(Request())
    token = creds.token

    headers = {"Authorization": f"Bearer {token}"}

    try:
        # Multipart upload
        metadata = {
            "name": filename,
            "parents": [GDRIVE_FOLDER_ID],
        }

        # multipart/related 요청
        import io
        boundary = "chance_sensor_boundary"

        with open(html_path, "rb") as f:
            file_content = f.read()

        body = (
            f"--{boundary}\r\n"
            f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
            f"{json.dumps(metadata)}\r\n"
            f"--{boundary}\r\n"
            f"Content-Type: text/html\r\n\r\n"
        ).encode("utf-8") + file_content + f"\r\n--{boundary}--".encode("utf-8")

        resp = requests.post(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": f"multipart/related; boundary={boundary}",
            },
            data=body,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        file_id = data.get("id", "")
        file_url = f"https://drive.google.com/file/d/{file_id}/view"

        # 누구나 볼 수 있도록 권한 설정 (조직 내)
        try:
            requests.post(
                f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "role": "reader",
                    "type": "anyone",
                },
                timeout=15,
            )
        except Exception:
            logger.warning("Drive 파일 공유 권한 설정 실패 (수동 공유 필요)")

        logger.info(f"Google Drive 업로드 완료: {filename}")
        logger.info(f"  URL: {file_url}")

        return {
            "file_id": file_id,
            "url": file_url,
            "name": filename,
        }

    except Exception as e:
        logger.error(f"Google Drive 업로드 실패: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"  응답: {e.response.text[:500]}")
        return {"file_id": None, "url": None, "name": None}
