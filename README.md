# 🔥 Chance Sensor

게임 시장 모니터링을 통한 주간 시장 신호 감지 시스템.

## 개요

- **목적**: 게임 시장에서 급부상하는 타이틀과 장르 트렌드를 조기에 포착
- **실행 주기**: 매주 목요일 오후 5시 (KST) 자동 실행
- **출력**: HTML 리포트 → Slack 채널 발송
- **수신 대상**: RisingWings 핵심 리더 (PD/CD/Core Unit장)

## 아키텍처

```
[Steam API + SteamSpy] → collectors/steam.py
[Reddit API]           → collectors/reddit.py
                              ↓
                    analyzer/signal_detector.py   (급등 감지)
                    analyzer/genre_aggregator.py  (장르별 집계)
                    analyzer/claude_analyst.py    (Claude API 분석)
                              ↓
                    report/generator.py           (HTML 생성)
                              ↓
                    slack_sender.py               (Slack 발송)
```

## 리포트 섹션

1. **Signal Alert** — 이번 주 가장 주목할 급등 타이틀 (최대 5건)
2. **Steam Trending** — Wishlist/소유자 기준 상위 10개 게임
3. **Community Buzz** — Reddit 주요 게임 커뮤니티 화제 포스트
4. **Genre Watch** — 장르별 트렌드 심층 분석 (펼쳐보기)
5. **Watchlist** — 누적 추적 대상의 주간 변동

## 설정

### GitHub Secrets 필요:

| Secret | 설명 |
|--------|------|
| `ANTHROPIC_API_KEY` | Claude API 키 |
| `REDDIT_CLIENT_ID` | Reddit 앱 Client ID |
| `REDDIT_CLIENT_SECRET` | Reddit 앱 Client Secret |
| `SLACK_BOT_TOKEN` | Slack Bot OAuth Token |
| `SLACK_CHANNEL_ID` | 발송 대상 Slack 채널 ID |

### Reddit 앱 생성:

1. https://www.reddit.com/prefs/apps 접속
2. "create another app" 클릭
3. "script" 타입 선택
4. Client ID와 Secret 확보

### Slack 앱 설정:

1. https://api.slack.com/apps 에서 앱 생성
2. OAuth & Permissions에서 `files:write`, `chat:write` scope 추가
3. Bot Token 확보
4. 대상 채널에 앱 초대

## 로컬 실행

```bash
export ANTHROPIC_API_KEY="sk-..."
export REDDIT_CLIENT_ID="..."
export REDDIT_CLIENT_SECRET="..."
export SLACK_BOT_TOKEN="xoxb-..."
export SLACK_CHANNEL_ID="C..."

pip install -r requirements.txt
python main.py
```

## Phase 2 예정 (YouTube, Twitter)

- YouTube Data API v3: 트레일러 조회수 급등 감지
- Twitter/X: 게임 관련 트렌딩 키워드 모니터링
- Discord: 주요 서버 멤버 수 자동 추적
