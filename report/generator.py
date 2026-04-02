"""
HTML Report Generator
- 수집/분석 데이터를 확정된 HTML 템플릿에 주입하여 리포트 생성
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def generate_report(
    issue_number: int,
    summary: str,
    signals: list[dict],
    trending: list[dict],
    buzz_items: list[dict],
    genre_watches: list[dict],
    watchlist_items: list[dict],
    output_path: str = "report.html",
):
    """전체 HTML 리포트 생성"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    period = f"{start_date.strftime('%Y.%m.%d')} — {end_date.strftime('%Y.%m.%d')}"

    # 각 섹션 HTML 생성
    signals_html = _render_signals(signals)
    trending_html = _render_trending(trending)
    buzz_html = _render_buzz(buzz_items)
    genre_html = _render_genre_watches(genre_watches)
    watchlist_html = _render_watchlist(watchlist_items)

    html = TEMPLATE.format(
        issue_number=f"{issue_number:03d}",
        period=period,
        summary=_escape(summary),
        signal_count=len(signals),
        signals_html=signals_html,
        trending_html=trending_html,
        buzz_count=len(buzz_items),
        buzz_html=buzz_html,
        genre_count=len(genre_watches),
        genre_html=genre_html,
        watchlist_count=len(watchlist_items),
        watchlist_html=watchlist_html,
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"리포트 생성 완료: {output_path}")
    return output_path


def _escape(text: str) -> str:
    """기본 HTML 이스케이프 (이미 HTML 태그가 포함된 분석 텍스트는 제외)"""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _render_signals(signals: list[dict]) -> str:
    """Signal Alert 카드 렌더링"""
    cards = []
    for s in signals:
        level = s.get("relevance_level", "낮음")
        alert_class = {"높음": "alert-high", "중간": "alert-mid"}.get(level, "alert-low")
        rel_class = {"높음": "rel-high", "중간": "rel-mid"}.get(level, "rel-low")

        status_tag = ""
        status = s.get("game_status", "개발중")
        if status == "Early Access":
            status_tag = '<span class="card-tag tag-status-ea">Early Access</span>'
        elif status == "출시":
            status_tag = '<span class="card-tag tag-status-released">출시</span>'
        else:
            status_tag = '<span class="card-tag tag-status-dev">개발중</span>'

        genre_tag = f'<span class="card-tag tag-genre">{_escape(s.get("genre", ""))}</span>' if s.get("genre") else ""

        cards.append(f'''
    <div class="signal-card {alert_class}" onclick="this.classList.toggle('open')">
      <div class="card-main">
        <div class="card-info">
          <div class="card-title-row">
            <span class="card-game-name"><a href="{s.get("steam_url", "#")}" target="_blank" onclick="event.stopPropagation()">{_escape(s["name"])}</a></span>
            {genre_tag}
            {status_tag}
          </div>
          <div class="card-meta">{_escape(s.get("developer", ""))} · {_escape(s.get("platform", "PC"))}</div>
          <div class="card-signal-text">{s.get("signal_text", "")}</div>
        </div>
        <div class="card-right">
          <span class="relevance-badge {rel_class}">관련도 {level}</span>
          <span class="expand-icon">▼</span>
        </div>
      </div>
      <div class="card-detail">
        <div class="detail-text">
          <strong>왜 신호인가:</strong> {s.get("why_signal", "")}<br><br>
          <strong>Aegis 관련도:</strong> {s.get("aegis_relevance", "")}
        </div>
        <div class="detail-links">
          <a href="{s.get("steam_url", "#")}" class="detail-link" target="_blank">Steam 페이지</a>
        </div>
      </div>
    </div>''')

    return "\n".join(cards)


def _render_trending(trending: list[dict]) -> str:
    """Steam Trending 테이블 행 렌더링"""
    rows = []
    for i, t in enumerate(trending, 1):
        delta = t.get("delta_pct", 0)
        delta_class = "change-up" if delta > 0 else "change-down" if delta < 0 else ""
        delta_str = f"▲ {delta}%" if delta > 0 else f"▼ {abs(delta)}%" if delta < 0 else "— 0%"

        rows.append(f'''
        <tr>
          <td class="trending-rank">{i}</td>
          <td class="trending-name"><a href="{t.get("steam_url", "#")}" target="_blank">{_escape(t.get("name", ""))}</a></td>
          <td class="trending-genre">{_escape(t.get("genre", ""))}</td>
          <td class="trending-metric">{_format_number(t.get("owners_mid", 0))}</td>
          <td class="trending-metric {delta_class}">{delta_str}</td>
        </tr>''')

    return "\n".join(rows)


def _render_buzz(buzz_items: list[dict]) -> str:
    """Community Buzz 렌더링"""
    items = []
    for b in buzz_items:
        source = _escape(b.get("source", "Reddit"))
        items.append(f'''
    <div class="buzz-item">
      <span class="buzz-source">{source}</span>
      <div class="buzz-content">
        <div class="buzz-title"><a href="{b.get("url", "#")}" target="_blank">{_escape(b.get("title", ""))}</a></div>
        <div class="buzz-desc">{_escape(b.get("description", ""))}</div>
        <div class="buzz-stats">{_escape(b.get("stats", ""))}</div>
      </div>
    </div>''')

    return "\n".join(items)


def _render_genre_watches(genres: list[dict]) -> str:
    """Genre Watch 카드 렌더링"""
    cards = []
    for g in genres:
        trend = g.get("trend", "FLAT")
        trend_class = {"HOT": "trend-hot", "UP": "trend-up", "DOWN": "trend-down"}.get(trend, "trend-flat")
        trend_label = {"HOT": "HOT", "UP": "↑ UP", "DOWN": "↓ DOWN"}.get(trend, "— FLAT")

        key_titles_html = ""
        for title in g.get("key_titles", []):
            url = title.get("url", "#") if isinstance(title, dict) else "#"
            name = title.get("name", title) if isinstance(title, dict) else title
            key_titles_html += f'<span class="genre-key-title"><a href="{url}" target="_blank">{_escape(str(name))}</a></span>\n'

        ref_links_html = ""
        for link in g.get("ref_links", []):
            ref_links_html += f'<a href="{link.get("url", "#")}" class="genre-ref-link" target="_blank">{_escape(link.get("label", ""))}</a>\n'

        cards.append(f'''
      <div class="genre-card" onclick="this.classList.toggle('open')">
        <div class="genre-card-main">
          <div>
            <div class="genre-card-title">{_escape(g.get("genre_name", ""))} <span class="genre-trend {trend_class}">{trend_label}</span></div>
            <div class="genre-card-summary">{_escape(g.get("summary", ""))}</div>
          </div>
          <span class="genre-expand-icon">▼</span>
        </div>
        <div class="genre-detail">
          <div class="genre-detail-section">
            <div class="genre-detail-label">판단 근거</div>
            <div class="genre-detail-text">{g.get("analysis", "")}</div>
          </div>
          <div class="genre-detail-section">
            <div class="genre-detail-label">주요 타이틀</div>
            <div class="genre-key-titles">{key_titles_html}</div>
          </div>
          <div class="genre-detail-section">
            <div class="genre-detail-label">참고 링크</div>
            <div class="genre-ref-links">{ref_links_html}</div>
          </div>
        </div>
      </div>''')

    return "\n".join(cards)


def _render_watchlist(items: list[dict]) -> str:
    """Watchlist 렌더링"""
    rows = []
    for w in items:
        status = w.get("status", "stable")
        status_class = {"new": "ws-new", "rising": "ws-rising", "declining": "ws-declining"}.get(status, "ws-stable")

        delta = w.get("delta_pct", 0)
        if delta > 0:
            delta_html = f'<span class="watchlist-delta change-up">▲ {delta}%</span>'
        elif delta < 0:
            delta_html = f'<span class="watchlist-delta change-down">▼ {abs(delta)}%</span>'
        else:
            delta_html = '<span class="watchlist-delta" style="color: var(--text-muted);">— 0%</span>'

        weeks = w.get("weeks_tracked", 0)
        weeks_str = "신규" if weeks <= 1 else f"{weeks}주차"

        tags_html = " ".join(
            f'<span class="watchlist-tag">{_escape(t)}</span>' for t in w.get("tags", [])
        )

        rows.append(f'''
      <div class="watchlist-item">
        <span class="watchlist-status {status_class}"></span>
        <div class="watchlist-name-wrap">
          <div class="watchlist-name-text"><a href="{w.get("url", "#")}" target="_blank">{_escape(w.get("name", ""))}</a></div>
          <div class="watchlist-tags">{tags_html}</div>
        </div>
        {delta_html}
        <span class="watchlist-weeks">{weeks_str}</span>
      </div>''')

    return "\n".join(rows)


def _format_number(n: int) -> str:
    """숫자 포맷: 1234567 → 1.2M, 12345 → 12.3K"""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


# ── HTML 템플릿 (확정 레이아웃 기반, CSS 포함) ──
# 실제 운영 시에는 별도 template.html 파일로 분리 가능
TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Chance Sensor Weekly #{issue_number}</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
/* CSS는 확정된 샘플과 동일 — 여기서는 간략화, 실제로는 전체 CSS 삽입 */
:root {{
  --bg: #0a0a0f; --bg-card: #12121a; --bg-card-hover: #1a1a26; --bg-detail: #0e0e16;
  --border: #1e1e2e; --border-accent: #2a2a3e;
  --text: #e0e0e8; --text-dim: #8888a0; --text-muted: #55556a;
  --accent-fire: #ff4d2e; --accent-fire-dim: #ff4d2e33;
  --accent-gold: #ffb800; --accent-gold-dim: #ffb80022;
  --accent-green: #22c55e; --accent-green-dim: #22c55e22;
  --accent-blue: #3b82f6; --accent-blue-dim: #3b82f622;
  --accent-purple: #a855f7; --accent-purple-dim: #a855f722;
  --radius: 10px; --radius-sm: 6px;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Noto Sans KR', sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }}
.container {{ max-width: 860px; margin: 0 auto; padding: 24px 20px 60px; }}
.header {{ padding: 40px 0 32px; border-bottom: 1px solid var(--border); margin-bottom: 32px; }}
.header-top {{ display: flex; align-items: center; gap: 12px; margin-bottom: 6px; }}
.header-logo {{ width: 36px; height: 36px; background: linear-gradient(135deg, var(--accent-fire), var(--accent-gold)); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 18px; }}
.header-title {{ font-size: 26px; font-weight: 900; background: linear-gradient(135deg, var(--accent-fire), var(--accent-gold)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
.header-issue {{ font-family: 'JetBrains Mono', monospace; font-size: 13px; color: var(--text-muted); margin-top: 4px; }}
.header-summary {{ margin-top: 16px; padding: 14px 18px; background: var(--accent-fire-dim); border-left: 3px solid var(--accent-fire); border-radius: 0 var(--radius-sm) var(--radius-sm) 0; font-size: 14px; font-weight: 500; }}
.section {{ margin-bottom: 36px; }}
.section-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 16px; padding-bottom: 10px; border-bottom: 1px solid var(--border); }}
.section-icon {{ font-size: 20px; width: 32px; text-align: center; }}
.section-title {{ font-size: 17px; font-weight: 700; }}
.section-count {{ font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--text-muted); background: var(--bg-card); padding: 2px 8px; border-radius: 10px; border: 1px solid var(--border); }}
.signal-card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); margin-bottom: 12px; overflow: hidden; }}
.signal-card.alert-high {{ border-left: 3px solid var(--accent-fire); }}
.signal-card.alert-mid {{ border-left: 3px solid var(--accent-gold); }}
.signal-card.alert-low {{ border-left: 3px solid var(--text-muted); }}
.card-main {{ padding: 16px 18px; cursor: pointer; display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }}
.card-main:hover {{ background: var(--bg-card-hover); }}
.card-info {{ flex: 1; }}
.card-title-row {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 6px; }}
.card-game-name {{ font-size: 15px; font-weight: 700; }}
.card-game-name a {{ color: var(--text); text-decoration: none; border-bottom: 1px dashed var(--text-muted); }}
.card-game-name a:hover {{ color: var(--accent-blue); border-color: var(--accent-blue); }}
.card-tag {{ font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 3px; }}
.tag-genre {{ background: var(--accent-blue-dim); color: var(--accent-blue); }}
.tag-status-ea {{ background: var(--accent-green-dim); color: var(--accent-green); }}
.tag-status-dev {{ background: var(--accent-purple-dim); color: var(--accent-purple); }}
.tag-status-released {{ background: var(--accent-gold-dim); color: var(--accent-gold); }}
.card-meta {{ font-size: 12px; color: var(--text-dim); margin-bottom: 8px; }}
.card-signal-text {{ font-size: 13px; line-height: 1.5; }}
.card-right {{ display: flex; flex-direction: column; align-items: flex-end; gap: 6px; flex-shrink: 0; }}
.relevance-badge {{ font-size: 10px; font-weight: 600; padding: 3px 8px; border-radius: 3px; }}
.rel-high {{ background: var(--accent-fire-dim); color: var(--accent-fire); }}
.rel-mid {{ background: var(--accent-gold-dim); color: var(--accent-gold); }}
.rel-low {{ background: #55556a22; color: var(--text-muted); }}
.expand-icon {{ font-size: 12px; color: var(--text-muted); transition: transform 0.2s; }}
.signal-card.open .expand-icon {{ transform: rotate(180deg); }}
.card-detail {{ display: none; padding: 0 18px 16px; border-top: 1px solid var(--border); background: var(--bg-detail); }}
.signal-card.open .card-detail {{ display: block; }}
.detail-text {{ margin-top: 14px; font-size: 13px; color: var(--text-dim); line-height: 1.7; }}
.detail-text strong {{ color: var(--text); font-weight: 500; }}
.detail-links {{ margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap; }}
.detail-link {{ font-size: 11px; color: var(--accent-blue); text-decoration: none; padding: 4px 10px; border: 1px solid var(--accent-blue-dim); border-radius: 4px; }}
.detail-link:hover {{ background: var(--accent-blue-dim); }}
.trending-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
.trending-table thead th {{ text-align: left; font-size: 10px; font-weight: 600; color: var(--text-muted); padding: 8px 12px; border-bottom: 1px solid var(--border); }}
.trending-table tbody tr {{ border-bottom: 1px solid var(--border); }}
.trending-table tbody tr:hover {{ background: var(--bg-card); }}
.trending-table td {{ padding: 10px 12px; }}
.trending-rank {{ font-family: 'JetBrains Mono', monospace; font-weight: 600; color: var(--text-muted); }}
.trending-name {{ font-weight: 500; }}
.trending-name a {{ color: var(--text); text-decoration: none; border-bottom: 1px dashed var(--text-muted); }}
.trending-name a:hover {{ color: var(--accent-blue); border-color: var(--accent-blue); }}
.trending-genre {{ font-size: 11px; color: var(--text-dim); }}
.trending-metric {{ font-family: 'JetBrains Mono', monospace; font-size: 12px; text-align: right; }}
.change-up {{ color: var(--accent-green); }}
.change-down {{ color: var(--accent-fire); }}
.buzz-item {{ display: flex; gap: 14px; padding: 12px 0; border-bottom: 1px solid var(--border); }}
.buzz-item:last-child {{ border-bottom: none; }}
.buzz-source {{ font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 600; color: var(--accent-purple); background: var(--accent-purple-dim); padding: 3px 8px; border-radius: 3px; height: fit-content; min-width: 56px; text-align: center; }}
.buzz-title {{ font-size: 13px; font-weight: 500; margin-bottom: 4px; }}
.buzz-title a {{ color: var(--text); text-decoration: none; }}
.buzz-title a:hover {{ color: var(--accent-blue); }}
.buzz-title a::after {{ content: ' ↗'; font-size: 10px; color: var(--text-muted); }}
.buzz-desc {{ font-size: 12px; color: var(--text-dim); line-height: 1.5; }}
.buzz-stats {{ font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--text-muted); margin-top: 4px; }}
.genre-list {{ display: flex; flex-direction: column; gap: 10px; }}
.genre-card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }}
.genre-card-main {{ padding: 14px 18px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }}
.genre-card-main:hover {{ background: var(--bg-card-hover); }}
.genre-card-title {{ font-size: 14px; font-weight: 700; display: flex; align-items: center; gap: 8px; }}
.genre-trend {{ font-family: 'JetBrains Mono', monospace; font-size: 10px; padding: 2px 6px; border-radius: 3px; }}
.trend-up {{ background: var(--accent-green-dim); color: var(--accent-green); }}
.trend-flat {{ background: #55556a22; color: var(--text-muted); }}
.trend-hot {{ background: var(--accent-fire-dim); color: var(--accent-fire); }}
.genre-card-summary {{ font-size: 12px; color: var(--text-dim); margin-top: 4px; }}
.genre-expand-icon {{ font-size: 12px; color: var(--text-muted); transition: transform 0.2s; }}
.genre-card.open .genre-expand-icon {{ transform: rotate(180deg); }}
.genre-detail {{ display: none; padding: 0 18px 16px; border-top: 1px solid var(--border); background: var(--bg-detail); }}
.genre-card.open .genre-detail {{ display: block; }}
.genre-detail-section {{ margin-top: 14px; }}
.genre-detail-label {{ font-size: 10px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px; }}
.genre-detail-text {{ font-size: 13px; color: var(--text-dim); line-height: 1.7; }}
.genre-detail-text strong {{ color: var(--text); font-weight: 500; }}
.genre-key-titles {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }}
.genre-key-title {{ font-size: 11px; padding: 4px 10px; background: var(--bg-card); border: 1px solid var(--border); border-radius: 4px; }}
.genre-key-title a {{ color: var(--text-dim); text-decoration: none; }}
.genre-key-title a:hover {{ color: var(--accent-blue); }}
.genre-ref-links {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }}
.genre-ref-link {{ font-size: 11px; color: var(--accent-blue); text-decoration: none; padding: 4px 10px; border: 1px solid var(--accent-blue-dim); border-radius: 4px; }}
.genre-ref-link:hover {{ background: var(--accent-blue-dim); }}
.watchlist-item {{ display: flex; align-items: center; padding: 10px 14px; border-bottom: 1px solid var(--border); gap: 14px; font-size: 13px; }}
.watchlist-item:last-child {{ border-bottom: none; }}
.watchlist-status {{ width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }}
.ws-rising {{ background: var(--accent-green); box-shadow: 0 0 6px var(--accent-green-dim); }}
.ws-stable {{ background: var(--accent-gold); }}
.ws-new {{ background: var(--accent-fire); box-shadow: 0 0 6px var(--accent-fire-dim); }}
.ws-declining {{ background: var(--text-muted); }}
.watchlist-name-wrap {{ flex: 1; }}
.watchlist-name-text {{ font-weight: 500; font-size: 13px; }}
.watchlist-name-text a {{ color: var(--text); text-decoration: none; border-bottom: 1px dashed var(--text-muted); }}
.watchlist-name-text a:hover {{ color: var(--accent-blue); border-color: var(--accent-blue); }}
.watchlist-tags {{ display: flex; flex-wrap: wrap; gap: 4px; margin-top: 3px; }}
.watchlist-tag {{ font-family: 'JetBrains Mono', monospace; font-size: 9px; color: var(--text-muted); background: var(--bg); padding: 1px 6px; border-radius: 3px; border: 1px solid var(--border); }}
.watchlist-delta {{ font-family: 'JetBrains Mono', monospace; font-size: 11px; }}
.watchlist-weeks {{ font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--text-muted); min-width: 50px; text-align: right; }}
.footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid var(--border); font-size: 11px; color: var(--text-muted); line-height: 1.8; }}
.footer a {{ color: var(--text-dim); }}
@media (max-width: 600px) {{
  .card-main {{ flex-direction: column; }}
  .card-right {{ flex-direction: row; }}
  .header-title {{ font-size: 22px; }}
}}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="header-top">
      <div class="header-logo">🔥</div>
      <div class="header-title">Chance Sensor</div>
    </div>
    <div class="header-issue">Weekly #{issue_number} · {period} · RisingWings Internal</div>
    <div class="header-summary">{summary}</div>
  </div>

  <div class="section">
    <div class="section-header">
      <div class="section-icon">🔥</div>
      <div class="section-title">Signal Alert</div>
      <div class="section-count">{signal_count}건</div>
    </div>
    {signals_html}
  </div>

  <div class="section">
    <div class="section-header">
      <div class="section-icon">📈</div>
      <div class="section-title">Steam Trending</div>
    </div>
    <table class="trending-table">
      <thead><tr><th>#</th><th>게임명</th><th>장르</th><th style="text-align:right">소유자</th><th style="text-align:right">변동</th></tr></thead>
      <tbody>{trending_html}</tbody>
    </table>
  </div>

  <div class="section">
    <div class="section-header">
      <div class="section-icon">💬</div>
      <div class="section-title">Community Buzz</div>
      <div class="section-count">{buzz_count}건</div>
    </div>
    {buzz_html}
  </div>

  <div class="section">
    <div class="section-header">
      <div class="section-icon">🎯</div>
      <div class="section-title">Genre Watch</div>
      <div class="section-count">{genre_count}개 장르</div>
    </div>
    <div class="genre-list">
      {genre_html}
    </div>
  </div>

  <div class="section">
    <div class="section-header">
      <div class="section-icon">📋</div>
      <div class="section-title">Watchlist</div>
      <div class="section-count">추적 중 {watchlist_count}건</div>
    </div>
    <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden;">
      {watchlist_html}
    </div>
  </div>

  <div class="footer">
    <strong>데이터 소스:</strong> Steam API, SteamSpy, Reddit API<br>
    <strong>AI 분석:</strong> Claude API (Sonnet 4.6) — 요약 생성, 장르 트렌드 분석, RisingWings 관련도 판정<br>
    <strong>면책:</strong> 본 리포트의 수치는 공개 데이터 기반 추정치이며, 투자 판단의 근거로 사용될 수 없음
  </div>
</div>
</body>
</html>"""
