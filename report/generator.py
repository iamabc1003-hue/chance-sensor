"""
HTML Report Generator — v3 Card-News + Dashboard Design
- 2-view 탭 구조: 📰 카드뉴스 / 📊 대시보드
- Signal 캐러셀, Buzz 그리드, Genre 탭, Radar 컴팩트 리스트
- 정보 오버레이 (!) 버튼
"""

import logging
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def _format_number(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _slug(text: str) -> str:
    return re.sub(r'[^a-z0-9]', '', text.lower().replace(" ", "").replace("/", ""))


def generate_report(
    issue_number: int,
    summary: str,
    signals: list[dict],
    trending: list[dict],
    buzz_items: list[dict],
    genre_watches: list[dict],
    watchlist_items: list[dict],
    rising_items: list[dict] = None,
    wishlist_games: list[dict] = None,
    output_path: str = "report.html",
):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    period = f"{start_date.strftime('%Y.%m.%d')} — {end_date.strftime('%Y.%m.%d')}"

    rising_items = rising_items or []
    wishlist_games = wishlist_games or []

    # Build sections
    signals_html = _render_signals(signals)
    buzz_html = _render_buzz(buzz_items)
    trending_html = _render_trending(trending)
    genre_tabs_html, genre_panels_html = _render_genre_tabs(genre_watches)
    wishlist_html = _render_wishlist_compact(wishlist_games)
    watchlist_html = _render_watchlist_compact(watchlist_items)

    # Hero brief items from summary
    brief_items = _extract_brief_items(summary, signals)

    html = _TEMPLATE.format(
        issue_number=f"{issue_number:03d}",
        period=period,
        signal_count=len(signals),
        genre_count=len(genre_watches),
        watchlist_count=len(watchlist_items),
        buzz_count=len(buzz_items),
        brief_items_html=brief_items,
        signals_html=signals_html,
        buzz_html=buzz_html,
        trending_count=len(trending),
        trending_html=trending_html,
        genre_tabs_html=genre_tabs_html,
        genre_panels_html=genre_panels_html,
        wishlist_count=len(wishlist_games),
        wishlist_html=wishlist_html,
        watchlist_html=watchlist_html,
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"리포트 생성 완료: {output_path}")
    return output_path


def _extract_brief_items(summary: str, signals: list[dict]) -> str:
    """Hero brief 인사이트 3개 추출"""
    items = []
    # summary에서 문장 분리
    sentences = [s.strip() for s in summary.replace(".", ".\n").split("\n") if s.strip() and len(s.strip()) > 10]
    for i, sent in enumerate(sentences[:3], 1):
        items.append(f'''
          <div class="hero-brief-item">
            <span class="hero-brief-num">{i}</span>
            <span>{sent}</span>
          </div>''')
    if not items:
        for i, s in enumerate(signals[:3], 1):
            text = s.get("signal_text", s.get("name", ""))
            items.append(f'''
          <div class="hero-brief-item">
            <span class="hero-brief-num">{i}</span>
            <span>{_escape(text)}</span>
          </div>''')
    return "\n".join(items)


def _render_signals(signals: list[dict]) -> str:
    cards = []
    for s in signals:
        level = s.get("signal_level", "낮음")
        accent_class = "high" if level == "높음" else "mid"
        lv_class = "lv-high" if level == "높음" else "lv-mid"
        lv_emoji = "🔴 HIGH" if level == "높음" else "🟡 MID"

        details = s.get("details", {})
        release_info = details.get("release_date", {})
        release_date_str = release_info.get("date", "")
        owners_str = details.get("owners", "")

        pos = details.get("positive", 0)
        neg = details.get("negative", 0)
        total = pos + neg
        pct = f"{pos / total * 100:.1f}%" if total > 0 else ""

        meta_parts = ["PC"]
        if release_date_str:
            meta_parts.insert(0, release_date_str)
        if owners_str:
            meta_parts.append(f"{owners_str} 소유자")
        meta = " · ".join(meta_parts)

        tags_html = ""
        for tag in s.get("tags", [])[:3]:
            tags_html += f'<span class="sig-tag">{_escape(tag)}</span>'
        if not tags_html and s.get("genre"):
            tags_html = f'<span class="sig-tag">{_escape(s["genre"])}</span>'

        cards.append(f'''
          <div class="sig-card" onclick="this.classList.toggle('open')">
            <div class="sig-accent {accent_class}"></div>
            <div class="sig-body">
              <div class="sig-top"><span class="sig-level {lv_class}">{lv_emoji}</span><span class="sig-pct">{pct}</span></div>
              <div class="sig-game"><a href="{s.get("steam_url", "#")}" target="_blank" onclick="event.stopPropagation()">{_escape(s["name"])}</a></div>
              <div class="sig-meta">{_escape(meta)}</div>
              <div class="sig-text">{s.get("signal_text", "")}</div>
              <div class="sig-tags">{tags_html}</div>
            </div>
            <div class="sig-detail"><div class="sig-detail-inner">
              <div class="sig-dl">왜 신호인가</div>
              <div class="sig-dt">{s.get("why_signal", "")}</div>
              <div class="sig-dl">기획 인사이트</div>
              <div class="sig-dt">{s.get("market_value", "")}</div>
              <a href="{s.get("steam_url", "#")}" class="sig-link" target="_blank">Steam 페이지 →</a>
            </div></div>
          </div>''')
    return "\n".join(cards)


def _render_buzz(buzz_items: list[dict]) -> str:
    cards = []
    for b in buzz_items:
        source = _escape(b.get("source", "Reddit"))
        sub = b.get("stats", "")
        # subreddit 추출
        sub_match = re.search(r'r/(\w+)', sub)
        sub_label = f"r/{sub_match.group(1)}" if sub_match else sub[:30]

        summary = b.get("summary", "")
        insight = b.get("insight", "")

        insight_html = f'<div class="bz-insight">💡 {_escape(insight)}</div>' if insight else ""

        cards.append(f'''
        <div class="bz-card"><div class="bz-top"><span class="bz-src">{source}</span><span class="bz-sub">{_escape(sub_label)}</span></div><div class="bz-summary">{_escape(summary) if summary else _escape(b.get("title", ""))}</div>{insight_html}<a href="{b.get("url", "#")}" target="_blank" class="bz-link">원문 보기 ↗</a></div>''')
    return "\n".join(cards)


def _render_trending(trending: list[dict]) -> str:
    rows = []
    for i, t in enumerate(trending, 1):
        rank_class = "d-rank top" if i <= 3 else "d-rank"
        rows.append(f'''
            <tr><td class="{rank_class}">{i}</td><td class="d-name"><a href="{t.get("steam_url", "#")}" target="_blank">{_escape(t.get("name", ""))}</a></td><td class="d-num">{_format_number(t.get("owners_mid", 0))}</td><td class="d-num">{_format_number(t.get("total_reviews", 0))}</td><td class="d-num d-pos">{t.get("positive_ratio", 0)}%</td><td class="d-score">{t.get("trending_score", 0)}</td></tr>''')
    return "\n".join(rows)


def _render_genre_tabs(genres: list[dict]) -> tuple:
    tabs = []
    panels = []
    for i, g in enumerate(genres):
        slug = _slug(g.get("genre_name", f"genre{i}"))
        trend = g.get("trend", "FLAT")
        tb_class = "tb-hot" if trend == "HOT" else ("tb-up" if trend == "UP" else "")
        tb_label = {"HOT": "HOT", "UP": "↑UP", "DOWN": "↓DOWN"}.get(trend, "")
        tb_html = f' <span class="tb {tb_class}">{tb_label}</span>' if tb_label else ""
        active = " active" if i == 0 else ""

        tabs.append(f'<button class="gtab{active}" data-g="{slug}">{_escape(g.get("genre_name", ""))}{tb_html}</button>')

        # chips
        chips = ""
        for title in g.get("key_titles", []):
            name = title.get("name", title) if isinstance(title, dict) else str(title)
            chips += f'<span class="gp-chip">{_escape(name)}</span>'

        panels.append(f'''
      <div class="gpanel{active}" id="gp-{slug}">
        <div class="gp-sum">{_escape(g.get("summary", ""))}</div>
        <div class="gp-block"><div class="gp-label">판단 근거</div><div class="gp-text">{g.get("analysis", "")}</div></div>
        <div class="gp-block"><div class="gp-label">주요 타이틀</div><div class="gp-chips">{chips}</div></div>
      </div>''')

    return "\n        ".join(tabs), "\n".join(panels)


def _render_wishlist_compact(games: list[dict]) -> str:
    rows = []
    for i, g in enumerate(games[:10], 1):
        rank_class = "ci-rank t3" if i <= 3 else "ci-rank"
        rows.append(f'<div class="ci"><span class="{rank_class}">{i}</span><div class="ci-name"><a href="{g.get("url", "#")}" target="_blank">{_escape(g.get("name", ""))}</a></div></div>')
    if not rows:
        rows.append('<div class="ci" style="color:var(--text-tertiary);padding:16px 20px;">데이터 없음</div>')
    return "\n          ".join(rows)


def _render_watchlist_compact(items: list[dict]) -> str:
    rows = []
    for w in items[:30]:
        status = w.get("status", "stable")
        dot_class = {"new": "dot-new", "rising": "dot-rising", "declining": "dot-declining"}.get(status, "dot-stable")
        # dot-rising/stable/declining이 CSS에 없으므로 인라인
        dot_style = ""
        if dot_class == "dot-new":
            dot_style = ""
        elif status == "rising":
            dot_style = 'style="background:var(--accent-emerald);box-shadow:0 0 8px var(--accent-emerald-glow);"'
        elif status == "declining":
            dot_style = 'style="background:var(--text-tertiary);"'
        else:
            dot_style = 'style="background:var(--accent-amber);"'

        delta = w.get("delta_pct", 0)
        weeks = w.get("weeks_tracked", 0)
        if weeks <= 1:
            status_label = "신규"
        elif delta > 0:
            status_label = f"▲{delta}%"
        elif delta < 0:
            status_label = f"▼{abs(delta)}%"
        else:
            status_label = f"{weeks}주차"

        rows.append(f'<div class="ci"><span class="ci-dot {dot_class}" {dot_style}></span><div class="ci-name"><a href="{w.get("url", "#")}" target="_blank">{_escape(w.get("name", ""))}</a></div><span class="ci-status">{status_label}</span></div>')
    if not rows:
        rows.append('<div class="ci" style="color:var(--text-tertiary);padding:16px 20px;">추적 중인 게임 없음</div>')
    return "\n          ".join(rows)


# ═══════════════════════════════════════════════════════════
#  TEMPLATE
# ═══════════════════════════════════════════════════════════
_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Chance Sensor — Weekly Game Intelligence</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800;900&family=Noto+Sans+KR:wght@300;400;500;600;700;900&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {{
  --bg-base: #08080c;
  --bg-elevated: #0f0f15;
  --bg-card: #13131c;
  --bg-card-hover: #1a1a27;
  --bg-glass: rgba(8,8,12,0.88);
  --border: rgba(255,255,255,0.06);
  --border-hover: rgba(255,255,255,0.12);
  --text-primary: #f0f0f5;
  --text-secondary: #9898b0;
  --text-tertiary: #5a5a74;
  --accent-ember: #ff5533;
  --accent-ember-glow: rgba(255,85,51,0.15);
  --accent-amber: #ffb800;
  --accent-amber-glow: rgba(255,184,0,0.12);
  --accent-emerald: #22c55e;
  --accent-emerald-glow: rgba(34,197,94,0.12);
  --accent-sky: #38bdf8;
  --accent-sky-glow: rgba(56,189,248,0.12);
  --accent-violet: #a78bfa;
  --accent-violet-glow: rgba(167,139,250,0.12);
  --radius-sm: 8px; --radius-md: 14px; --radius-lg: 20px;
  --font-display: 'Outfit','Noto Sans KR',sans-serif;
  --font-body: 'Noto Sans KR','Outfit',sans-serif;
  --font-mono: 'DM Mono',monospace;
  --shadow-card: 0 4px 24px rgba(0,0,0,0.35);
  --nav-h: 60px;
}}
*{{margin:0;padding:0;box-sizing:border-box;}}
html{{scroll-behavior:smooth;}}
body{{font-family:var(--font-body);background:var(--bg-base);color:var(--text-primary);line-height:1.6;overflow-x:hidden;}}
.container{{max-width:1200px;margin:0 auto;padding:0 24px;}}
.topnav{{position:fixed;top:0;left:0;right:0;z-index:200;background:var(--bg-glass);backdrop-filter:blur(24px) saturate(1.4);-webkit-backdrop-filter:blur(24px) saturate(1.4);border-bottom:1px solid var(--border);}}
.topnav-inner{{max-width:1200px;margin:0 auto;padding:0 24px;display:flex;align-items:center;justify-content:space-between;height:var(--nav-h);}}
.topnav-brand{{display:flex;align-items:center;gap:10px;font-family:var(--font-display);font-weight:800;font-size:17px;color:var(--text-primary);text-decoration:none;}}
.topnav-brand-icon{{width:30px;height:30px;background:linear-gradient(135deg,var(--accent-ember),var(--accent-amber));border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:14px;}}
.primary-tabs{{display:flex;gap:2px;background:rgba(255,255,255,0.04);border-radius:10px;padding:3px;}}
.primary-tab{{font-family:var(--font-display);font-size:13px;font-weight:600;color:var(--text-tertiary);padding:7px 20px;border-radius:8px;border:none;background:transparent;cursor:pointer;transition:all 0.25s;white-space:nowrap;}}
.primary-tab:hover{{color:var(--text-secondary);}}
.primary-tab.active{{color:var(--text-primary);background:rgba(255,255,255,0.08);}}
.topnav-issue{{font-family:var(--font-mono);font-size:11px;color:var(--text-tertiary);padding:4px 10px;border:1px solid var(--border);border-radius:20px;}}
@media(max-width:640px){{.topnav-issue{{display:none;}}.primary-tab{{font-size:12px;padding:6px 14px;}}}}
.view{{display:none;}}.view.active{{display:block;}}
.hero{{padding:calc(var(--nav-h) + 40px) 0 48px;position:relative;overflow:hidden;}}
.hero::before{{content:'';position:absolute;top:-180px;right:-180px;width:500px;height:500px;background:radial-gradient(circle,var(--accent-ember-glow) 0%,transparent 70%);pointer-events:none;}}
.hero-eyebrow{{font-family:var(--font-mono);font-size:12px;font-weight:500;color:var(--accent-ember);letter-spacing:2px;text-transform:uppercase;margin-bottom:12px;display:flex;align-items:center;gap:8px;}}
.hero-eyebrow::before{{content:'';width:20px;height:1px;background:var(--accent-ember);}}
.hero-title{{font-family:var(--font-display);font-size:clamp(28px,4.5vw,48px);font-weight:900;line-height:1.15;margin-bottom:14px;position:relative;z-index:1;}}
.hero-gradient{{background:linear-gradient(135deg,var(--accent-ember),var(--accent-amber),var(--accent-emerald));-webkit-background-clip:text;-webkit-text-fill-color:transparent;}}
.hero-brief{{position:relative;z-index:1;background:var(--bg-card);border:1px solid var(--border);border-left:3px solid var(--accent-ember);border-radius:0 var(--radius-md) var(--radius-md) 0;padding:20px 24px;margin-bottom:32px;max-width:700px;}}
.hero-brief-title{{font-family:var(--font-display);font-size:13px;font-weight:700;color:var(--text-primary);margin-bottom:14px;}}
.hero-brief-body{{display:flex;flex-direction:column;gap:12px;}}
.hero-brief-item{{display:flex;gap:12px;align-items:flex-start;font-size:13px;color:var(--text-secondary);line-height:1.7;}}
.hero-brief-item strong{{color:var(--text-primary);font-weight:600;}}
.hero-brief-num{{flex-shrink:0;width:22px;height:22px;display:flex;align-items:center;justify-content:center;font-family:var(--font-mono);font-size:11px;font-weight:700;color:var(--accent-ember);background:var(--accent-ember-glow);border-radius:6px;margin-top:1px;}}
.hero-stats{{display:flex;gap:28px;flex-wrap:wrap;position:relative;z-index:1;}}
.hero-stat{{position:relative;cursor:pointer;}}
.hero-stat-value{{font-family:var(--font-display);font-size:26px;font-weight:800;}}
.hero-stat-label{{font-family:var(--font-mono);font-size:11px;color:var(--text-tertiary);}}
.hero-stat .info-trigger{{position:absolute;top:-4px;right:-20px;}}
.section{{padding:48px 0;}}
.section-head{{display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:28px;gap:16px;}}
.section-label{{font-family:var(--font-mono);font-size:10px;font-weight:500;color:var(--accent-ember);letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;}}
.section-title{{font-family:var(--font-display);font-size:24px;font-weight:800;}}
.section-sub{{font-size:13px;color:var(--text-tertiary);margin-top:2px;}}
.section-badge{{font-family:var(--font-mono);font-size:11px;color:var(--text-tertiary);padding:5px 12px;border:1px solid var(--border);border-radius:20px;white-space:nowrap;flex-shrink:0;}}
.divider{{height:1px;background:linear-gradient(90deg,transparent,var(--border),transparent);}}
.carousel-wrap{{position:relative;}}
.carousel-track{{display:flex;gap:16px;overflow-x:auto;scroll-snap-type:x mandatory;scroll-behavior:smooth;padding:4px 0 12px;-ms-overflow-style:none;scrollbar-width:none;}}
.carousel-track::-webkit-scrollbar{{display:none;}}
.carousel-arrow{{position:absolute;top:50%;transform:translateY(-50%);width:44px;height:44px;background:var(--bg-card);border:1px solid var(--border-hover);border-radius:50%;cursor:pointer;display:flex;align-items:center;justify-content:center;color:var(--text-primary);font-size:18px;z-index:10;transition:all 0.2s;box-shadow:0 4px 16px rgba(0,0,0,0.4);opacity:0.9;}}
.carousel-arrow:hover{{background:var(--bg-card-hover);border-color:var(--accent-ember);opacity:1;box-shadow:0 4px 24px rgba(255,85,51,0.15);}}
.carousel-arrow.disabled{{opacity:0.2;pointer-events:none;}}
.carousel-arrow-left{{left:-16px;}}.carousel-arrow-right{{right:-16px;}}
@media(max-width:768px){{.carousel-arrow-left{{left:4px;}}.carousel-arrow-right{{right:4px;}}.carousel-arrow{{width:36px;height:36px;font-size:14px;}}}}
.carousel-dots{{display:flex;justify-content:center;gap:6px;margin-top:12px;}}
.carousel-dot{{width:6px;height:6px;border-radius:50%;background:var(--text-tertiary);opacity:0.3;transition:all 0.25s;cursor:pointer;}}
.carousel-dot.active{{opacity:1;background:var(--accent-ember);width:22px;border-radius:3px;}}
.sig-card{{flex:0 0 340px;scroll-snap-align:start;background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius-lg);overflow:hidden;position:relative;transition:all 0.3s;cursor:pointer;}}
.sig-card:hover{{border-color:var(--border-hover);transform:translateY(-3px);box-shadow:var(--shadow-card);}}
.sig-accent{{position:absolute;top:0;left:0;right:0;height:3px;}}
.sig-accent.high{{background:linear-gradient(90deg,var(--accent-ember),var(--accent-amber));}}
.sig-accent.mid{{background:linear-gradient(90deg,var(--accent-amber),var(--accent-emerald));}}
.sig-body{{padding:22px;}}
.sig-top{{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;}}
.sig-level{{font-family:var(--font-mono);font-size:10px;font-weight:500;padding:3px 10px;border-radius:20px;}}
.lv-high{{background:var(--accent-ember-glow);color:var(--accent-ember);}}
.lv-mid{{background:var(--accent-amber-glow);color:var(--accent-amber);}}
.sig-pct{{font-family:var(--font-mono);font-size:12px;color:var(--text-tertiary);}}
.sig-game{{font-family:var(--font-display);font-size:18px;font-weight:700;margin-bottom:6px;}}
.sig-game a{{color:var(--text-primary);text-decoration:none;transition:color 0.2s;}}
.sig-game a:hover{{color:var(--accent-sky);}}
.sig-meta{{font-family:var(--font-mono);font-size:11px;color:var(--text-tertiary);margin-bottom:12px;}}
.sig-text{{font-size:14px;color:var(--text-secondary);line-height:1.6;margin-bottom:14px;}}
.sig-tags{{display:flex;gap:6px;flex-wrap:wrap;}}
.sig-tag{{font-family:var(--font-mono);font-size:10px;font-weight:500;padding:3px 8px;border-radius:4px;border:1px solid var(--border);color:var(--text-tertiary);}}
.sig-detail{{max-height:0;overflow:hidden;transition:max-height 0.4s ease;}}
.sig-card.open .sig-detail{{max-height:500px;}}
.sig-detail-inner{{padding:18px 22px;background:var(--bg-elevated);border-top:1px solid var(--border);}}
.sig-dl{{font-family:var(--font-mono);font-size:10px;font-weight:500;color:var(--accent-amber);text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;}}
.sig-dt{{font-size:13px;color:var(--text-secondary);line-height:1.7;margin-bottom:12px;}}
.sig-dt strong{{color:var(--text-primary);font-weight:600;}}
.sig-link{{display:inline-flex;align-items:center;gap:4px;font-family:var(--font-mono);font-size:11px;color:var(--accent-sky);text-decoration:none;padding:5px 12px;border:1px solid var(--accent-sky-glow);border-radius:6px;transition:all 0.2s;}}
.sig-link:hover{{background:var(--accent-sky-glow);}}
.buzz-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px;}}
.bz-card{{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius-md);padding:20px;display:flex;flex-direction:column;gap:10px;transition:all 0.3s;}}
.bz-card:hover{{border-color:var(--border-hover);transform:translateY(-2px);box-shadow:var(--shadow-card);}}
.bz-top{{display:flex;align-items:center;justify-content:space-between;}}
.bz-src{{font-family:var(--font-mono);font-size:10px;font-weight:500;color:var(--accent-violet);background:var(--accent-violet-glow);padding:3px 10px;border-radius:20px;}}
.bz-sub{{font-family:var(--font-mono);font-size:10px;color:var(--text-tertiary);}}
.bz-summary{{font-size:14px;font-weight:500;color:var(--text-primary);line-height:1.5;}}
.bz-insight{{font-size:12px;color:var(--accent-amber);background:var(--accent-amber-glow);padding:8px 12px;border-radius:var(--radius-sm);line-height:1.5;}}
.bz-link{{font-size:12px;color:var(--text-tertiary);text-decoration:none;display:flex;align-items:center;gap:4px;transition:color 0.2s;}}
.bz-link:hover{{color:var(--accent-sky);}}
.dtable-wrap{{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius-lg);overflow:hidden;}}
.dtable{{width:100%;border-collapse:collapse;}}
.dtable thead th{{font-family:var(--font-mono);font-size:10px;font-weight:500;color:var(--text-tertiary);text-transform:uppercase;letter-spacing:1px;padding:14px 16px;text-align:left;border-bottom:1px solid var(--border);background:var(--bg-elevated);}}
.dtable tbody tr{{border-bottom:1px solid var(--border);transition:background 0.15s;}}
.dtable tbody tr:last-child{{border-bottom:none;}}
.dtable tbody tr:hover{{background:var(--bg-card-hover);}}
.dtable td{{padding:13px 16px;font-size:13px;}}
.d-rank{{font-family:var(--font-mono);font-weight:600;color:var(--text-tertiary);width:40px;}}
.d-rank.top{{color:var(--accent-amber);}}
.d-name{{font-weight:600;}}.d-name a{{color:var(--text-primary);text-decoration:none;transition:color 0.2s;}}.d-name a:hover{{color:var(--accent-sky);}}
.d-num{{font-family:var(--font-mono);font-size:12px;text-align:right;color:var(--text-secondary);}}.d-pos{{color:var(--accent-emerald);}}
.d-score{{font-family:var(--font-mono);font-size:12px;font-weight:600;color:var(--accent-amber);text-align:right;}}
@media(max-width:768px){{.dtable-wrap{{overflow-x:auto;}}.dtable{{min-width:560px;}}}}
.col-tip{{position:relative;cursor:help;border-bottom:1px dashed var(--text-tertiary);}}
.col-tip::after{{content:attr(data-tip);position:absolute;bottom:calc(100% + 8px);left:50%;transform:translateX(-50%);background:var(--bg-card);border:1px solid var(--border-hover);color:var(--text-secondary);font-family:var(--font-body);font-size:11px;font-weight:400;letter-spacing:0;text-transform:none;padding:8px 12px;border-radius:8px;white-space:nowrap;pointer-events:none;opacity:0;transition:opacity 0.2s;z-index:50;box-shadow:0 4px 16px rgba(0,0,0,0.4);}}
.col-tip:hover::after{{opacity:1;}}
.col-tip-right::after{{left:auto;right:0;transform:none;}}
.gtabs{{display:flex;gap:6px;margin-bottom:24px;overflow-x:auto;padding-bottom:4px;-ms-overflow-style:none;scrollbar-width:none;}}
.gtabs::-webkit-scrollbar{{display:none;}}
.gtab{{font-family:var(--font-display);font-size:13px;font-weight:600;color:var(--text-tertiary);padding:8px 16px;border-radius:20px;border:1px solid var(--border);background:transparent;cursor:pointer;white-space:nowrap;transition:all 0.2s;}}
.gtab:hover{{color:var(--text-secondary);border-color:var(--border-hover);}}
.gtab.active{{color:var(--text-primary);background:rgba(255,255,255,0.06);border-color:var(--border-hover);}}
.gtab .tb{{font-family:var(--font-mono);font-size:9px;font-weight:600;margin-left:5px;padding:2px 5px;border-radius:3px;vertical-align:middle;}}
.tb-hot{{background:var(--accent-ember-glow);color:var(--accent-ember);}}
.tb-up{{background:var(--accent-emerald-glow);color:var(--accent-emerald);}}
.gpanel{{display:none;background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius-lg);padding:26px;animation:fadeUp 0.3s ease;}}
.gpanel.active{{display:block;}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(6px);}}to{{opacity:1;transform:translateY(0);}}}}
.gp-sum{{font-size:15px;color:var(--text-secondary);line-height:1.7;margin-bottom:22px;padding-bottom:18px;border-bottom:1px solid var(--border);}}
.gp-block{{margin-bottom:18px;}}
.gp-label{{font-family:var(--font-mono);font-size:10px;font-weight:500;color:var(--accent-amber);text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;}}
.gp-text{{font-size:13px;color:var(--text-secondary);line-height:1.8;}}
.gp-text strong{{color:var(--text-primary);font-weight:600;}}
.gp-chips{{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px;}}
.gp-chip{{font-size:12px;font-weight:500;padding:6px 14px;background:var(--bg-elevated);border:1px solid var(--border);border-radius:8px;color:var(--text-secondary);transition:all 0.2s;}}
.gp-chip:hover{{border-color:var(--accent-sky);color:var(--accent-sky);}}
.compact-grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px;}}
@media(max-width:768px){{.compact-grid{{grid-template-columns:1fr;}}}}
.clist{{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius-lg);overflow:hidden;}}
.clist-head{{padding:16px 20px;background:var(--bg-elevated);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;}}
.clist-title{{font-family:var(--font-display);font-size:14px;font-weight:700;display:flex;align-items:center;gap:8px;}}
.clist-cnt{{font-family:var(--font-mono);font-size:10px;color:var(--text-tertiary);padding:2px 8px;border:1px solid var(--border);border-radius:10px;}}
.ci{{display:flex;align-items:center;gap:12px;padding:11px 20px;border-bottom:1px solid var(--border);transition:background 0.15s;}}
.ci:last-child{{border-bottom:none;}}.ci:hover{{background:var(--bg-card-hover);}}
.ci-rank{{font-family:var(--font-mono);font-size:13px;font-weight:700;color:var(--text-tertiary);min-width:22px;text-align:center;}}.ci-rank.t3{{color:var(--accent-ember);}}
.ci-name{{flex:1;font-size:13px;font-weight:500;}}.ci-name a{{color:var(--text-primary);text-decoration:none;transition:color 0.2s;}}.ci-name a:hover{{color:var(--accent-sky);}}
.ci-dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0;}}.dot-new{{background:var(--accent-ember);box-shadow:0 0 8px var(--accent-ember-glow);}}
.ci-status{{font-family:var(--font-mono);font-size:10px;color:var(--text-tertiary);}}
.subnav{{position:sticky;top:var(--nav-h);z-index:100;background:var(--bg-glass);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border-bottom:1px solid var(--border);padding:0 24px;}}
.subnav-inner{{max-width:1200px;margin:0 auto;display:flex;gap:4px;overflow-x:auto;padding:10px 0;-ms-overflow-style:none;scrollbar-width:none;}}
.subnav-inner::-webkit-scrollbar{{display:none;}}
.subnav-link{{font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--text-tertiary);text-decoration:none;padding:6px 14px;border-radius:6px;white-space:nowrap;transition:all 0.2s;border:none;background:transparent;cursor:pointer;}}
.subnav-link:hover,.subnav-link.active{{color:var(--text-primary);background:rgba(255,255,255,0.06);}}
.site-footer{{padding:40px 0 36px;border-top:1px solid var(--border);margin-top:32px;}}
.ft-inner{{display:flex;justify-content:space-between;align-items:flex-start;gap:40px;flex-wrap:wrap;}}
.ft-brand{{font-family:var(--font-display);font-size:15px;font-weight:800;margin-bottom:6px;display:flex;align-items:center;gap:8px;}}
.ft-desc{{font-size:12px;color:var(--text-tertiary);max-width:300px;line-height:1.6;}}
.ft-meta{{font-family:var(--font-mono);font-size:11px;color:var(--text-tertiary);line-height:2;text-align:right;}}
.info-trigger{{display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;font-family:var(--font-mono);font-size:11px;font-weight:700;color:var(--text-tertiary);background:rgba(255,255,255,0.04);border:1px solid var(--border);border-radius:50%;cursor:pointer;transition:all 0.2s;margin-left:8px;vertical-align:middle;position:relative;flex-shrink:0;}}
.info-trigger:hover{{color:var(--accent-amber);border-color:var(--accent-amber);background:var(--accent-amber-glow);}}
.info-overlay{{display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.6);backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px);z-index:500;animation:fadeIn 0.2s ease;}}
.info-overlay.show{{display:flex;align-items:center;justify-content:center;padding:24px;}}
@keyframes fadeIn{{from{{opacity:0;}}to{{opacity:1;}}}}
.info-panel{{background:var(--bg-card);border:1px solid var(--border-hover);border-radius:var(--radius-lg);max-width:600px;width:100%;max-height:80vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,0.5);animation:slideUp 0.3s ease;}}
@keyframes slideUp{{from{{opacity:0;transform:translateY(16px);}}to{{opacity:1;transform:translateY(0);}}}}
.info-panel-header{{padding:20px 24px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;background:var(--bg-card);border-radius:var(--radius-lg) var(--radius-lg) 0 0;z-index:1;}}
.info-panel-title{{font-family:var(--font-display);font-size:16px;font-weight:700;display:flex;align-items:center;gap:8px;}}
.info-panel-close{{width:28px;height:28px;background:rgba(255,255,255,0.04);border:1px solid var(--border);border-radius:6px;color:var(--text-tertiary);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:14px;transition:all 0.2s;}}
.info-panel-close:hover{{color:var(--text-primary);background:rgba(255,255,255,0.08);}}
.info-panel-body{{padding:20px 24px 24px;}}
.info-block{{margin-bottom:18px;}}.info-block:last-child{{margin-bottom:0;}}
.info-block-label{{font-family:var(--font-mono);font-size:10px;font-weight:500;color:var(--accent-amber);text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;}}
.info-block-text{{font-size:13px;color:var(--text-secondary);line-height:1.8;}}
.info-block-text strong{{color:var(--text-primary);font-weight:600;}}
.info-formula{{font-family:var(--font-mono);font-size:12px;background:var(--bg-elevated);border:1px solid var(--border);border-radius:var(--radius-sm);padding:12px 16px;margin:8px 0;color:var(--accent-sky);line-height:1.8;overflow-x:auto;}}
.info-source-row{{display:flex;align-items:center;gap:8px;margin-top:6px;flex-wrap:wrap;}}
.info-source-chip{{font-family:var(--font-mono);font-size:10px;padding:3px 8px;border-radius:4px;border:1px solid var(--border);color:var(--text-tertiary);}}
.info-divider{{height:1px;background:var(--border);margin:16px 0;}}
</style>
</head>
<body>

<nav class="topnav">
  <div class="topnav-inner">
    <div class="topnav-brand" style="cursor:default;">
      <div class="topnav-brand-icon">🔥</div>
      Chance Sensor
    </div>
    <div class="primary-tabs" id="primaryTabs">
      <button class="primary-tab active" data-view="cardnews">📰 카드뉴스</button>
      <button class="primary-tab" data-view="dashboard">📊 대시보드</button>
    </div>
    <div class="topnav-issue">WEEKLY #{issue_number}</div>
  </div>
</nav>

<!-- ══════════ VIEW 1: 카드뉴스 ══════════ -->
<div class="view active" id="view-cardnews">

  <nav class="subnav">
    <div class="subnav-inner">
      <button class="subnav-link active" data-target="cn-signals" data-parent="cardnews">🔥 Signal Alert</button>
      <button class="subnav-link" data-target="cn-buzz" data-parent="cardnews">💬 Community Buzz</button>
    </div>
  </nav>

  <section class="hero">
    <div class="container">
      <div class="hero-eyebrow">{period}</div>
      <h1 class="hero-title">이번 주<br><span class="hero-gradient">신작 기획 힌트 {signal_count}건</span></h1>
      <div class="hero-brief">
        <div class="hero-brief-title">📌 이번 주 핵심 인사이트</div>
        <div class="hero-brief-body">
{brief_items_html}
        </div>
      </div>
      <div class="hero-stats">
        <div class="hero-stat" onclick="openInfo('signal')"><div class="hero-stat-value">{signal_count}<span class="info-trigger">!</span></div><div class="hero-stat-label">Signal Alerts</div></div>
        <div class="hero-stat" onclick="openInfo('genre')"><div class="hero-stat-value">{genre_count}<span class="info-trigger">!</span></div><div class="hero-stat-label">Genre Tracked</div></div>
        <div class="hero-stat" onclick="openInfo('watchlist')"><div class="hero-stat-value">{watchlist_count}<span class="info-trigger">!</span></div><div class="hero-stat-label">Watchlist</div></div>
        <div class="hero-stat" onclick="openInfo('buzz')"><div class="hero-stat-value">{buzz_count}<span class="info-trigger">!</span></div><div class="hero-stat-label">Community Buzz</div></div>
      </div>
    </div>
  </section>

  <div class="divider"></div>

  <section class="section" id="cn-signals">
    <div class="container">
      <div class="section-head">
        <div>
          <div class="section-label">Signal</div>
          <h2 class="section-title">🔥 Signal Alert <span class="info-trigger" onclick="openInfo('signal')">!</span></h2>
          <div class="section-sub">이번 주 포착된 주요 게임 시장 신호</div>
        </div>
        <div class="section-badge">{signal_count}건 포착</div>
      </div>
      <div class="carousel-wrap">
        <button class="carousel-arrow carousel-arrow-left disabled" id="sigArrowL" aria-label="이전">‹</button>
        <div class="carousel-track" id="sigTrack">
{signals_html}
        </div>
        <button class="carousel-arrow carousel-arrow-right" id="sigArrowR" aria-label="다음">›</button>
      </div>
      <div class="carousel-dots" id="sigDots"></div>
    </div>
  </section>

  <div class="divider"></div>

  <section class="section" id="cn-buzz">
    <div class="container">
      <div class="section-head">
        <div>
          <div class="section-label">Buzz</div>
          <h2 class="section-title">💬 Community Buzz <span class="info-trigger" onclick="openInfo('buzz')">!</span></h2>
          <div class="section-sub">Reddit 커뮤니티에서 포착된 이번 주 화제</div>
        </div>
        <div class="section-badge">{buzz_count}건</div>
      </div>
      <div class="buzz-grid">
{buzz_html}
      </div>
    </div>
  </section>
</div>

<!-- ══════════ VIEW 2: 대시보드 ══════════ -->
<div class="view" id="view-dashboard">

  <nav class="subnav">
    <div class="subnav-inner">
      <button class="subnav-link active" data-target="db-trending" data-parent="dashboard">📈 Trending</button>
      <button class="subnav-link" data-target="db-genres" data-parent="dashboard">🎯 Genre Watch</button>
      <button class="subnav-link" data-target="db-radar" data-parent="dashboard">📡 Radar</button>
    </div>
  </nav>

  <div style="height: calc(var(--nav-h) + 48px);"></div>

  <section class="section" id="db-trending">
    <div class="container">
      <div class="section-head">
        <div>
          <div class="section-label">Ranking</div>
          <h2 class="section-title">📈 Steam Trending <span class="info-trigger" onclick="openInfo('trending')">!</span></h2>
          <div class="section-sub">주간 인기 상승 타이틀 랭킹</div>
        </div>
        <div class="section-badge">TOP {trending_count}</div>
      </div>
      <div class="dtable-wrap">
        <table class="dtable">
          <thead><tr><th>#</th><th>게임명</th><th style="text-align:right"><span class="col-tip col-tip-right" data-tip="SteamSpy 추정 보유 계정 수">소유자</span></th><th style="text-align:right"><span class="col-tip col-tip-right" data-tip="Steam 유저 리뷰 총 개수">리뷰</span></th><th style="text-align:right"><span class="col-tip col-tip-right" data-tip="전체 리뷰 중 긍정 비율">긍정률</span></th><th style="text-align:right"><span class="col-tip col-tip-right" data-tip="베이지안 긍정률 + 리뷰수 가산 + 소규모 가산">점수</span></th></tr></thead>
          <tbody>
{trending_html}
          </tbody>
        </table>
      </div>
    </div>
  </section>

  <div class="divider"></div>

  <section class="section" id="db-genres">
    <div class="container">
      <div class="section-head">
        <div>
          <div class="section-label">Analysis</div>
          <h2 class="section-title">🎯 Genre Watch <span class="info-trigger" onclick="openInfo('genre')">!</span></h2>
          <div class="section-sub">장르별 트렌드 심층 분석</div>
        </div>
        <div class="section-badge">{genre_count}개 장르</div>
      </div>
      <div class="gtabs" id="gTabs">
        {genre_tabs_html}
      </div>
{genre_panels_html}
    </div>
  </section>

  <div class="divider"></div>

  <section class="section" id="db-radar">
    <div class="container">
      <div class="section-head">
        <div>
          <div class="section-label">Tracking</div>
          <h2 class="section-title">📡 Radar <span class="info-trigger" onclick="openInfo('radar')">!</span></h2>
          <div class="section-sub">위시리스트 트렌딩 & 지속 추적 리스트</div>
        </div>
      </div>
      <div class="compact-grid">
        <div class="clist">
          <div class="clist-head"><div class="clist-title">🔮 Wishlist Trending</div><span class="clist-cnt">{wishlist_count}건</span></div>
          {wishlist_html}
        </div>
        <div class="clist">
          <div class="clist-head"><div class="clist-title">📋 Watchlist</div><span class="clist-cnt">{watchlist_count}건</span></div>
          {watchlist_html}
        </div>
      </div>
    </div>
  </section>
</div>

<footer class="site-footer">
  <div class="container">
    <div class="ft-inner">
      <div>
        <div class="ft-brand">🔥 Chance Sensor</div>
        <div class="ft-desc">게임 시장의 기회 신호를 AI로 포착하고, 기획자에게 인사이트를 전달하는 위클리 인텔리전스 서비스.</div>
      </div>
      <div class="ft-meta">
        <strong>데이터:</strong> Steam API, SteamSpy, Reddit API<br>
        <strong>AI 분석:</strong> Claude API (Sonnet 4.6)<br>
        <strong>면책:</strong> 공개 데이터 기반 추정치이며 투자 근거로 사용 불가
      </div>
    </div>
  </div>
</footer>

<div class="info-overlay" id="infoOverlay" onclick="closeInfo(event)">
  <div class="info-panel" onclick="event.stopPropagation()">
    <div class="info-panel-header">
      <div class="info-panel-title" id="infoPanelTitle"></div>
      <button class="info-panel-close" onclick="closeInfo()">✕</button>
    </div>
    <div class="info-panel-body" id="infoPanelBody"></div>
  </div>
</div>

<script>
document.querySelectorAll('.primary-tab').forEach(tab => {{
  tab.addEventListener('click', () => {{
    document.querySelectorAll('.primary-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('view-' + tab.dataset.view).classList.add('active');
    window.scrollTo({{ top: 0, behavior: 'smooth' }});
  }});
}});
document.querySelectorAll('.gtab').forEach(tab => {{
  tab.addEventListener('click', () => {{
    document.querySelectorAll('.gtab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.gpanel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('gp-' + tab.dataset.g).classList.add('active');
  }});
}});
document.querySelectorAll('.subnav-link').forEach(link => {{
  link.addEventListener('click', (e) => {{
    e.preventDefault();
    const targetId = link.dataset.target;
    const target = document.getElementById(targetId);
    if (target) {{
      const offset = 120;
      const top = target.getBoundingClientRect().top + window.scrollY - offset;
      window.scrollTo({{ top, behavior: 'smooth' }});
    }}
  }});
}});
function updateSubnav(parentId) {{
  const links = document.querySelectorAll(`.subnav-link[data-parent="${{parentId}}"]`);
  const ids = Array.from(links).map(l => l.dataset.target);
  let current = ids[0];
  ids.forEach(id => {{
    const el = document.getElementById(id);
    if (el && window.scrollY >= el.offsetTop - 140) current = id;
  }});
  links.forEach(l => {{
    l.classList.toggle('active', l.dataset.target === current);
  }});
}}
window.addEventListener('scroll', () => {{
  const activeView = document.querySelector('.view.active');
  if (activeView) {{
    const parentId = activeView.id.replace('view-', '');
    updateSubnav(parentId);
  }}
}});
function initCarousel(trackId, dotsId, arrowLId, arrowRId) {{
  const track = document.getElementById(trackId);
  const dotsC = document.getElementById(dotsId);
  const arrowL = document.getElementById(arrowLId);
  const arrowR = document.getElementById(arrowRId);
  if (!track) return;
  const cards = track.querySelectorAll('.sig-card');
  if (!cards.length) return;
  const gap = 16;
  cards.forEach((_, i) => {{
    const dot = document.createElement('div');
    dot.className = 'carousel-dot' + (i === 0 ? ' active' : '');
    dot.addEventListener('click', () => {{
      cards[i].scrollIntoView({{ behavior: 'smooth', inline: 'start', block: 'nearest' }});
    }});
    dotsC.appendChild(dot);
  }});
  function getActiveIndex() {{
    const sl = track.scrollLeft;
    const cw = cards[0].offsetWidth + gap;
    return Math.round(sl / cw);
  }}
  function updateControls() {{
    const idx = getActiveIndex();
    const max = cards.length - 1;
    arrowL.classList.toggle('disabled', idx <= 0);
    arrowR.classList.toggle('disabled', idx >= max);
    dotsC.querySelectorAll('.carousel-dot').forEach((d, i) => {{
      d.classList.toggle('active', i === idx);
    }});
  }}
  arrowL.addEventListener('click', () => {{
    const idx = getActiveIndex();
    if (idx > 0) cards[idx - 1].scrollIntoView({{ behavior: 'smooth', inline: 'start', block: 'nearest' }});
  }});
  arrowR.addEventListener('click', () => {{
    const idx = getActiveIndex();
    if (idx < cards.length - 1) cards[idx + 1].scrollIntoView({{ behavior: 'smooth', inline: 'start', block: 'nearest' }});
  }});
  track.addEventListener('scroll', updateControls);
  updateControls();
}}
initCarousel('sigTrack', 'sigDots', 'sigArrowL', 'sigArrowR');
</script>
<script>
const infoData = {{
  signal: {{
    title: '🔥 Signal Alert — 감지 로직',
    body: `<div class="info-block"><div class="info-block-label">개요</div><div class="info-block-text">수집된 전체 게임 풀에서 <strong>"주목할 만한 시장 신호"</strong>를 자동 감지합니다. 대형 AAA 타이틀이 아닌 <strong>소규모 인디 게임</strong>에서 보이는 혁신적 게임플레이를 포착합니다.</div></div><div class="info-divider"></div><div class="info-block"><div class="info-block-label">필터링 기준</div><div class="info-block-text">• <strong>소유자 500만 미만</strong>만 대상<br>• <strong>리뷰 50개 이상</strong> (최소 신뢰도)</div></div><div class="info-divider"></div><div class="info-block"><div class="info-block-label">베이지안 보정</div><div class="info-formula">베이지안 긍정률 = (실제 긍정 + 100 × 0.75) / (총 리뷰 + 100)<br>리뷰수 가산 = min(log₁₀(총 리뷰) × 5, 20)<br><strong>최종 점수 = 베이지안 긍정률 + 리뷰수 가산</strong></div></div><div class="info-divider"></div><div class="info-block"><div class="info-block-label">데이터 소스</div><div class="info-source-row"><span class="info-source-chip">SteamSpy API</span><span class="info-source-chip">Steam Store API</span><span class="info-source-chip">Claude API</span></div></div>`
  }},
  trending: {{
    title: '📈 Steam Trending — 점수 산정',
    body: `<div class="info-block"><div class="info-block-label">개요</div><div class="info-block-text">소규모이면서 긍정률이 높은 <strong>숨은 강자</strong>를 찾아내는 복합 점수 랭킹입니다.</div></div><div class="info-divider"></div><div class="info-block"><div class="info-block-label">대상 필터</div><div class="info-block-text">• 소유자 <strong>5만 ~ 500만</strong><br>• 리뷰 <strong>500개 이상</strong></div></div><div class="info-divider"></div><div class="info-block"><div class="info-block-label">점수 공식</div><div class="info-formula">① 베이지안 긍정률<br>② 리뷰수 가산 = min(log₁₀(총 리뷰) × 5, 20)<br>③ 소규모 가산: 30만 미만 → +15, 100만 미만 → +8<br><strong>최종 = ① + ② + ③</strong></div></div><div class="info-divider"></div><div class="info-block"><div class="info-block-label">데이터 소스</div><div class="info-source-row"><span class="info-source-chip">SteamSpy API</span><span class="info-source-chip">자체 점수 로직</span></div></div>`
  }},
  buzz: {{
    title: '💬 Community Buzz — 수집 로직',
    body: `<div class="info-block"><div class="info-block-label">개요</div><div class="info-block-text">유저 커뮤니티 목소리에서 <strong>충족되지 않은 니즈</strong>와 <strong>떠오르는 트렌드</strong>를 추출합니다.</div></div><div class="info-divider"></div><div class="info-block"><div class="info-block-label">수집 대상 (6개 서브레딧)</div><div class="info-block-text">r/gaming, r/truegaming, r/JRPG, r/ShouldIbuythisgame, r/PatientGamers, r/gamingsuggestions</div></div><div class="info-divider"></div><div class="info-block"><div class="info-block-label">AI 분석</div><div class="info-block-text">Claude API가 상위 10개 포스트를 <strong>신작 기획 힌트</strong> 관점에서 분석합니다. 업계 뉴스는 자동 필터링됩니다.</div></div><div class="info-divider"></div><div class="info-block"><div class="info-block-label">데이터 소스</div><div class="info-source-row"><span class="info-source-chip">Reddit RSS</span><span class="info-source-chip">Google Apps Script</span><span class="info-source-chip">Claude API</span></div></div>`
  }},
  genre: {{
    title: '🎯 Genre Watch — 분석 로직',
    body: `<div class="info-block"><div class="info-block-label">개요</div><div class="info-block-text"><strong>10개 장르</strong>에 대해 SteamSpy 태그 API로 수집 후 Claude AI가 트렌드를 분석합니다.</div></div><div class="info-divider"></div><div class="info-block"><div class="info-block-label">추적 장르</div><div class="info-block-text">RPG, 슈터, 생존, 로그라이크, 시뮬레이션, 전략, 메트로배니아/플랫포머, 인디, 어드벤처, 퍼즐</div></div><div class="info-divider"></div><div class="info-block"><div class="info-block-label">트렌드 판정</div><div class="info-formula"><span style="color:var(--accent-ember);">🔥 HOT</span> — 강한 성장세<br><span style="color:var(--accent-emerald);">↑ UP</span> — 완만한 성장<br><span style="color:var(--text-tertiary);">→ FLAT</span> — 현상 유지<br><span style="color:var(--accent-ember);">↓ DOWN</span> — 하락세</div></div><div class="info-divider"></div><div class="info-block"><div class="info-block-label">데이터 소스</div><div class="info-source-row"><span class="info-source-chip">SteamSpy Tag API</span><span class="info-source-chip">Claude API</span></div></div>`
  }},
  watchlist: {{
    title: '📋 Watchlist — 추적 로직',
    body: `<div class="info-block"><div class="info-block-label">개요</div><div class="info-block-text">Signal 감지 게임을 자동 추가하여 <strong>주간 변화를 누적 추적</strong>합니다.</div></div><div class="info-divider"></div><div class="info-block"><div class="info-block-label">관리 규칙</div><div class="info-block-text">• 최대 <strong>30개</strong> 동시 추적<br>• watchlist.json은 GitHub 자동 커밋</div></div><div class="info-divider"></div><div class="info-block"><div class="info-block-label">성장률 계산</div><div class="info-formula">성장률 = (금주 소유자 - 전주 소유자) / 전주 소유자 × 100%</div><div class="info-block-text">2주차 이후 자동 계산. 30% 이상 → Rising Signal 승격.</div></div>`
  }},
  radar: {{
    title: '📡 Radar — Wishlist & Watchlist',
    body: `<div class="info-block"><div class="info-block-label">Wishlist Trending</div><div class="info-block-text">Steam Store의 <strong>인기 출시 예정</strong> API를 통해 Wishlist 기반 상위 10개를 수집합니다.</div></div><div class="info-divider"></div><div class="info-block"><div class="info-block-label">Watchlist</div><div class="info-block-text">Signal Alert 감지 게임이 자동 추가되어 <strong>최대 30개</strong>를 지속 추적합니다.</div></div><div class="info-divider"></div><div class="info-block"><div class="info-block-label">자동화</div><div class="info-formula">매주 월요일 10시 KST GitHub Actions 자동 실행<br>Steam 수집 → Reddit 수집 → Signal 감지 → Claude AI → HTML → Drive + Slack</div></div>`
  }}
}};
function openInfo(key) {{
  const data = infoData[key];
  if (!data) return;
  document.getElementById('infoPanelTitle').innerHTML = data.title;
  document.getElementById('infoPanelBody').innerHTML = data.body;
  document.getElementById('infoOverlay').classList.add('show');
  document.body.style.overflow = 'hidden';
}}
function closeInfo(e) {{
  if (e && e.target !== document.getElementById('infoOverlay')) return;
  document.getElementById('infoOverlay').classList.remove('show');
  document.body.style.overflow = '';
}}
document.addEventListener('keydown', (e) => {{
  if (e.key === 'Escape') {{
    document.getElementById('infoOverlay').classList.remove('show');
    document.body.style.overflow = '';
  }}
}});
</script>
</body>
</html>"""