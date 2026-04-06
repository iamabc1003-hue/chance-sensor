"""
Chance Sensor - Web Dashboard
브라우저에서 접속하여 리포트 조회, 수동 실행, 이력 관리
"""

import glob
import os
import subprocess
import threading
import time
from datetime import datetime

from flask import Flask, render_template_string, send_from_directory, redirect, url_for, jsonify, request
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# 프록시 경로 자동 감지: SCRIPT_NAME이 없으면 Referer에서 추출
@app.before_request
def detect_proxy_prefix():
    if not request.environ.get("SCRIPT_NAME"):
        referer = request.headers.get("Referer", "")
        # /api/v1/ai-tools/XX/proxy 패턴 감지
        import re
        m = re.search(r"(/api/v1/ai-tools/\d+/proxy)", referer)
        if m:
            request.environ["SCRIPT_NAME"] = m.group(1)

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# 실행 상태 관리
run_status = {"running": False, "last_run": None, "last_result": None, "log": ""}


def get_reports():
    """생성된 리포트 목록 (최신순)"""
    files = glob.glob(os.path.join(REPORTS_DIR, "chance_sensor_*.html"))
    reports = []
    for f in files:
        name = os.path.basename(f)
        # chance_sensor_20260407.html → 2026.04.07
        try:
            date_str = name.replace("chance_sensor_", "").replace(".html", "")
            date = datetime.strptime(date_str, "%Y%m%d")
            display = date.strftime("%Y.%m.%d")
        except ValueError:
            display = name
        reports.append({"filename": name, "display": display, "path": f, "size": os.path.getsize(f)})
    reports.sort(key=lambda x: x["filename"], reverse=True)
    return reports


def run_pipeline():
    """파이프라인 실행 (백그라운드)"""
    global run_status
    run_status["running"] = True
    run_status["log"] = ""

    try:
        # main.py의 generate_report output_path를 reports/ 디렉토리로 변경
        env = os.environ.copy()
        env["CHANCE_SENSOR_OUTPUT_DIR"] = REPORTS_DIR

        result = subprocess.run(
            ["python", "main.py"],
            capture_output=True, text=True, timeout=600,
            cwd=os.path.dirname(__file__),
            env=env,
        )
        run_status["log"] = result.stdout + result.stderr
        run_status["last_result"] = "성공" if result.returncode == 0 else f"실패 (코드: {result.returncode})"

        # main.py가 현재 디렉토리에 생성한 HTML을 reports/로 이동
        for f in glob.glob(os.path.join(os.path.dirname(__file__), "chance_sensor_*.html")):
            dest = os.path.join(REPORTS_DIR, os.path.basename(f))
            os.rename(f, dest)

    except subprocess.TimeoutExpired:
        run_status["last_result"] = "타임아웃 (10분 초과)"
    except Exception as e:
        run_status["last_result"] = f"오류: {e}"

    run_status["running"] = False
    run_status["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Chance Sensor</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #0a0a0f;
  --bg-card: #12121a;
  --bg-card-hover: #1a1a26;
  --border: #1e1e2e;
  --text: #e0e0e8;
  --text-dim: #8888a0;
  --text-muted: #55556a;
  --accent-fire: #ff4d2e;
  --accent-fire-dim: #ff4d2e33;
  --accent-gold: #ffb800;
  --accent-green: #22c55e;
  --accent-blue: #3b82f6;
  --radius: 12px;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Noto Sans KR', sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }

.container { max-width: 960px; margin: 0 auto; padding: 40px 24px; }

.header { text-align: center; margin-bottom: 48px; }
.header-logo { width: 48px; height: 48px; background: linear-gradient(135deg, var(--accent-fire), var(--accent-gold));
  border-radius: 10px; display: inline-flex; align-items: center; justify-content: center; font-size: 22px; margin-bottom: 16px; }
.header h1 { font-size: 32px; font-weight: 900; background: linear-gradient(135deg, var(--accent-fire), var(--accent-gold));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.header p { color: var(--text-dim); font-size: 14px; margin-top: 8px; }

.status-bar { display: flex; gap: 16px; margin-bottom: 32px; flex-wrap: wrap; }
.status-card { flex: 1; min-width: 200px; background: var(--bg-card); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 20px; }
.status-label { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: var(--text-muted); margin-bottom: 8px; }
.status-value { font-family: 'JetBrains Mono', monospace; font-size: 18px; font-weight: 600; }
.status-value.running { color: var(--accent-gold); }
.status-value.success { color: var(--accent-green); }
.status-value.idle { color: var(--text-dim); }

.actions { margin-bottom: 32px; text-align: center; }
.btn { display: inline-block; padding: 14px 32px; border-radius: 8px; font-size: 15px; font-weight: 600;
  text-decoration: none; cursor: pointer; border: none; transition: all 0.2s; }
.btn-primary { background: linear-gradient(135deg, var(--accent-fire), var(--accent-gold)); color: #000; }
.btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 20px var(--accent-fire-dim); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; transform: none; box-shadow: none; }
.btn-secondary { background: var(--bg-card); color: var(--text); border: 1px solid var(--border); margin-left: 12px; }
.btn-secondary:hover { background: var(--bg-card-hover); }

.section-title { font-size: 16px; font-weight: 700; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
.section-title span { font-size: 20px; }

.report-list { display: flex; flex-direction: column; gap: 8px; }
.report-item { display: flex; align-items: center; justify-content: space-between;
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px;
  padding: 16px 20px; transition: all 0.2s; }
.report-item:hover { background: var(--bg-card-hover); border-color: var(--accent-fire); }
.report-info { display: flex; align-items: center; gap: 12px; }
.report-icon { font-size: 20px; }
.report-date { font-weight: 600; font-size: 15px; }
.report-name { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--text-muted); }
.report-actions { display: flex; gap: 8px; }
.report-btn { padding: 6px 14px; border-radius: 6px; font-size: 12px; font-weight: 600;
  text-decoration: none; border: 1px solid var(--border); color: var(--text-dim); transition: all 0.2s; }
.report-btn:hover { color: var(--text); border-color: var(--accent-blue); }
.report-btn.view { background: var(--accent-blue); color: #fff; border-color: var(--accent-blue); }
.report-btn.view:hover { opacity: 0.9; }

.empty { text-align: center; padding: 60px; color: var(--text-muted); }
.empty-icon { font-size: 48px; margin-bottom: 12px; }

.log-box { background: #0d0d12; border: 1px solid var(--border); border-radius: 8px;
  padding: 16px; margin-top: 16px; max-height: 300px; overflow-y: auto;
  font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--text-dim);
  white-space: pre-wrap; word-break: break-all; display: none; }

.footer { text-align: center; margin-top: 48px; padding-top: 24px; border-top: 1px solid var(--border);
  font-size: 12px; color: var(--text-muted); }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="header-logo">🔥</div>
    <h1>Chance Sensor</h1>
    <p>게임 시장 주간 모니터링 · 신작 기획 아이디어 발굴</p>
  </div>

  <div class="status-bar">
    <div class="status-card">
      <div class="status-label">상태</div>
      <div class="status-value {{ 'running' if status.running else 'idle' }}">
        {{ '🔄 실행 중...' if status.running else '✅ 대기' }}
      </div>
    </div>
    <div class="status-card">
      <div class="status-label">마지막 실행</div>
      <div class="status-value">{{ status.last_run or '—' }}</div>
    </div>
    <div class="status-card">
      <div class="status-label">결과</div>
      <div class="status-value {{ 'success' if status.last_result and '성공' in status.last_result else '' }}">
        {{ status.last_result or '—' }}
      </div>
    </div>
    <div class="status-card">
      <div class="status-label">리포트 수</div>
      <div class="status-value">{{ reports|length }}건</div>
    </div>
  </div>

  <div class="actions">
    <form action="{{ url_for('run') }}" method="post" style="display: inline;">
      <button type="submit" class="btn btn-primary" {{ 'disabled' if status.running }}>
        {{ '실행 중...' if status.running else '🚀 리포트 생성' }}
      </button>
    </form>
    {% if status.log %}
    <button class="btn btn-secondary" onclick="document.getElementById('log').style.display = document.getElementById('log').style.display === 'none' ? 'block' : 'none'">
      📋 실행 로그
    </button>
    {% endif %}
  </div>

  {% if status.log %}
  <div id="log" class="log-box">{{ status.log }}</div>
  {% endif %}

  <div class="section-title"><span>📊</span> 리포트 이력</div>

  {% if reports %}
  <div class="report-list">
    {% for r in reports %}
    <div class="report-item">
      <div class="report-info">
        <div class="report-icon">📄</div>
        <div>
          <div class="report-date">{{ r.display }}</div>
          <div class="report-name">{{ r.filename }} · {{ (r.size / 1024)|round(0)|int }}KB</div>
        </div>
      </div>
      <div class="report-actions">
        <a href="{{ url_for('view_report', filename=r.filename) }}" class="report-btn view" target="_blank">열기</a>
        <a href="{{ url_for('download_report', filename=r.filename) }}" class="report-btn">다운로드</a>
      </div>
    </div>
    {% endfor %}
  </div>
  {% else %}
  <div class="empty">
    <div class="empty-icon">📭</div>
    <p>아직 생성된 리포트가 없습니다.</p>
    <p style="margin-top: 8px;">위의 "리포트 생성" 버튼을 클릭하세요.</p>
  </div>
  {% endif %}

  <div class="footer">
    Chance Sensor v29 · RisingWings (Aetnite) · Powered by SteamSpy, Reddit, Claude AI
  </div>
</div>

{% if status.running %}
<script>setTimeout(() => location.reload(), 5000);</script>
{% endif %}
</body>
</html>"""


@app.route("/")
def index():
    reports = get_reports()
    return render_template_string(DASHBOARD_HTML, reports=reports, status=run_status)


@app.route("/run", methods=["POST"])
def run():
    if not run_status["running"]:
        thread = threading.Thread(target=run_pipeline, daemon=True)
        thread.start()
    return redirect(url_for("index"))


@app.route("/report/<filename>")
def view_report(filename):
    return send_from_directory(REPORTS_DIR, filename)


@app.route("/download/<filename>")
def download_report(filename):
    return send_from_directory(REPORTS_DIR, filename, as_attachment=True)


@app.route("/api/status")
def api_status():
    return jsonify(run_status)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)