"""공통 유틸리티 함수"""


def parse_owners_mid(owners_str: str) -> int:
    """SteamSpy owners 범위 문자열에서 중간값 추출
    예: '20,000 .. 50,000' → 35000
    """
    try:
        parts = owners_str.replace(",", "").split(" .. ")
        low = int(parts[0])
        high = int(parts[1]) if len(parts) > 1 else low
        return (low + high) // 2
    except (ValueError, IndexError):
        return 0
