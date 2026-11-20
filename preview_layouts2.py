# -*- coding: utf-8 -*-
"""
3 种真正差异化的布局（基于真实设计理念）：
1. 报纸晨报式（Ledger "Printed markets"）
2. 深色终端式（iOS Stocks）
3. 浅色极简式（Stocketa）
"""
import sys, base64, io
from datetime import datetime
from types import SimpleNamespace

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import fetch_data, analyze


def render_chart(sge_df, days=250, dark=False):
    if sge_df is None or sge_df.empty:
        return None
    df = sge_df.copy()
    df["close"] = pd.to_numeric(df["close"], errors="coerce").dropna()
    if df.empty:
        return None
    close = df["close"].iloc[-days:]
    dates = pd.to_datetime(df["date"]).iloc[-days:]
    # 均线用全量算
    ma20 = df["close"].rolling(20).mean().iloc[-days:]
    ma50 = df["close"].rolling(50).mean().iloc[-days:]
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(9, 3.6))
    bg = "#121212" if dark else "white"
    fg = "#e0e0e0" if dark else "#333333"
    fig.patch.set_facecolor(bg)
    ax.set_facecolor(bg)
    line_c = "#f5a623" if dark else "#c0392b"
    ax.plot(dates, close.values, label="Au99.99", color=line_c, linewidth=1.6)
    if ma20.dropna().size > 0:
        ax.plot(dates, ma20.values, label="MA20", color="#e67e22", linewidth=1.0, alpha=0.9)
    if ma50.dropna().size > 0:
        ax.plot(dates, ma50.values, label="MA50", color="#3498db", linewidth=1.0, alpha=0.9)
    ax.tick_params(colors=fg, labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color(fg)
    ax.spines["left"].set_color(fg)
    ax.grid(True, alpha=0.15, color=fg)
    ax.legend(loc="best", fontsize=7, facecolor=bg, labelcolor=fg)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight", facecolor=bg)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def _fmt(v, nd=2):
    return f"{float(v):.{nd}f}" if v is not None else "-"


def _pct(v):
    return f"{float(v):+.2f}%" if v is not None else "-"


def build():
    data = fetch_data.fetch_all()
    result = analyze.analyze(data)
    sge = result["sge"]; advice = result["advice"]; short = result["short_term"]
    macro = result["macro"]; pboc = result["pboc"]
    img_light = render_chart(data.get("sge"), dark=False)
    img_dark = render_chart(data.get("sge"), dark=True)
    action = advice["action"]
    if "加码" in action: color = "#27ae60"
    elif "减量" in action: color = "#e74c3c"
    else: color = "#2980b9"
    mp = []
    if macro.get("DXY"): mp.append(f"美元 {_fmt(macro['DXY'].get('value'))}")
    if macro.get("US10Y"): mp.append(f"美债10Y {_fmt(macro['US10Y'].get('value'))}%")
    macro_line = " · ".join(mp) if mp else "宏观缺失"
    pboc_line = f"央行储备环比 {_pct(pboc.get('mom'))}" if pboc.get("available") else "央行缺失"
    rsi = sge.get("rsi")
    rsi_txt = f"RSI {rsi:.0f} 超卖" if rsi and rsi < 30 else f"RSI {rsi:.0f}" if rsi else "RSI -"
    return SimpleNamespace(
        action=action, color=color, today=datetime.now().strftime("%Y-%m-%d"),
        latest=_fmt(sge.get('latest')), chg1=_pct(sge.get('change_1d')), chg5=_pct(sge.get('change_5d')),
        trend=advice['trend'], rsi_txt=rsi_txt, valuation=advice['valuation'],
        trend_note=advice['trend_note'], val_note=advice['val_note'], risk_note=advice['risk_note'],
        short_view=short.get('view','-'), short_note=short.get('note',''),
        macro_line=macro_line, pboc_line=pboc_line, img_light=img_light, img_dark=img_dark,
    )


def _wrap(body, css):
    return f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>预览</title><style>{css}</style></head><body>{body}</body></html>"""


# ============ 1. 报纸晨报式 ============
def newspaper(c):
    css = """
*{margin:0;padding:0;box-sizing:border-box}
body{background:#f6f1e7;color:#1a1a1a;font-family:"Georgia","Times New Roman","SimSun",serif;padding:26px 22px}
.wrap{max-width:600px;margin:0 auto}
.masthead{text-align:center;border-bottom:3px double #1a1a1a;padding-bottom:10px;margin-bottom:14px}
.masthead h1{font-size:26px;font-weight:700;letter-spacing:4px}
.masthead .sub{font-size:12px;color:#666;margin-top:4px;letter-spacing:1px}
.lead{border-bottom:1px solid #1a1a1a;padding-bottom:12px;margin-bottom:12px}
.lead .label{font-size:12px;color:#8a1f1f;letter-spacing:2px;font-weight:bold}
.lead .action{font-size:34px;font-weight:800;margin:4px 0}
.lead .reason{font-size:13px;color:#444;line-height:1.6}
.price-row{display:flex;align-items:baseline;justify-content:space-between;border-bottom:1px solid #1a1a1a;padding:14px 0}
.price-row .big{font-size:46px;font-weight:800;font-family:"Georgia",serif}
.price-row .unit{font-size:15px;color:#666}
.price-row .chg{font-size:15px;font-weight:bold}
.sec-title{font-size:13px;color:#8a1f1f;font-weight:bold;letter-spacing:2px;margin:16px 0 6px;border-bottom:1px solid #bbb;padding-bottom:4px}
.row{display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid #ddd;font-size:14px}
.row .k{color:#555}
.row .v{font-weight:bold}
.chart{margin:12px 0;border-top:1px solid #1a1a1a;padding-top:12px}
.chart img{width:100%;display:block}
.note{font-size:13px;color:#444;padding:8px 0;border-bottom:1px solid #1a1a1a;font-style:italic}
.up{color:#8a1f1f}.down{color:#1a6e1a}
.foot{text-align:center;font-size:11px;color:#999;margin-top:14px}
"""
    updown = "up" if c.chg1.startswith("-") else "down"  # 报纸用红涨绿跌? 这里红色表跌，绿色表涨（国内）
    body = f"""
<div class="wrap">
  <div class="masthead"><h1>黄金晨报</h1><div class="sub">GOLD DAILY · {c.today}</div></div>
  <div class="lead">
    <div class="label">今日定投建议</div>
    <div class="action">{c.action}</div>
    <div class="reason">{c.trend_note}；{c.val_note}</div>
  </div>
  <div class="price-row">
    <span class="big">{c.latest}</span>
    <span class="unit">元/克</span>
    <span class="chg {updown}">{c.chg1}</span>
  </div>
  <div class="sec-title">行情摘要</div>
  <div class="row"><span class="k">趋势</span><span class="v">{c.trend}</span></div>
  <div class="row"><span class="k">RSI</span><span class="v">{c.rsi_txt}</span></div>
  <div class="row"><span class="k">估值</span><span class="v">{c.valuation}</span></div>
  <div class="row"><span class="k">短期（1~2周）</span><span class="v">{c.short_view}</span></div>
  <div class="chart"><img src="data:image/png;base64,{c.img_light}"></div>
  <div class="note">{c.short_note}</div>
  <div class="sec-title">外围</div>
  <div class="row"><span class="k">宏观</span><span class="v">{c.macro_line}</span></div>
  <div class="row"><span class="k">央行</span><span class="v">{c.pboc_line}</span></div>
  <div class="foot">仅供学习研究，不构成投资建议</div>
</div>"""
    return _wrap(body, css)


# ============ 2. 深色终端式 ============
def terminal(c):
    css = """
*{margin:0;padding:0;box-sizing:border-box}
body{background:#000;color:#fff;font-family:"SF Mono","Consolas","Microsoft YaHei",monospace;padding:20px 18px}
.wrap{max-width:600px;margin:0 auto}
.topbar{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #2c2c2e;padding-bottom:10px;margin-bottom:14px}
.topbar .t{font-size:15px;font-weight:bold;letter-spacing:1px}
.topbar .d{font-size:12px;color:#8e8e93}
.advice{border-bottom:1px solid #2c2c2e;padding:16px 0}
.advice .a{font-size:28px;font-weight:bold;color:#0a84ff}
.advice .r{font-size:13px;color:#8e8e93;margin-top:6px}
.price{padding:18px 0;border-bottom:1px solid #2c2c2e}
.price .big{font-size:52px;font-weight:700;font-variant-numeric:tabular-nums}
.price .unit{font-size:14px;color:#8e8e93}
.price .chg{font-size:16px;font-weight:bold;margin-left:12px;font-variant-numeric:tabular-nums}
.metrics{border-bottom:1px solid #2c2c2e;padding:12px 0}
.metric{display:flex;justify-content:space-between;padding:6px 0;font-size:14px;font-variant-numeric:tabular-nums}
.metric .k{color:#8e8e93}
.metric .v{font-weight:bold}
.chart{padding:14px 0;border-bottom:1px solid #2c2c2e}
.chart img{width:100%;display:block}
.note{font-size:13px;color:#8e8e93;padding:10px 0;border-bottom:1px solid #2c2c2e}
.info{font-size:13px;color:#8e8e93;padding:8px 0}
.up{color:#30d158}.down{color:#ff453a}
.foot{text-align:center;font-size:11px;color:#48484a;margin-top:14px}
"""
    updown = "down" if c.chg1.startswith("-") else "up"  # 深色：绿涨红跌
    body = f"""
<div class="wrap">
  <div class="topbar"><span class="t">GOLD·定投</span><span class="d">{c.today}</span></div>
  <div class="advice"><div class="a">{c.action}</div><div class="r">{c.trend_note} · {c.val_note}</div></div>
  <div class="price"><span class="big">{c.latest}</span><span class="unit"> 元/克</span><span class="chg {updown}">{c.chg1}</span></div>
  <div class="metrics">
    <div class="metric"><span class="k">趋势</span><span class="v">{c.trend}</span></div>
    <div class="metric"><span class="k">RSI</span><span class="v">{c.rsi_txt}</span></div>
    <div class="metric"><span class="k">估值</span><span class="v">{c.valuation}</span></div>
    <div class="metric"><span class="k">短期</span><span class="v">{c.short_view}</span></div>
  </div>
  <div class="chart"><img src="data:image/png;base64,{c.img_dark}"></div>
  <div class="note">{c.short_note}</div>
  <div class="info">MACRO  {c.macro_line}</div>
  <div class="info">PBOC   {c.pboc_line}</div>
  <div class="foot">仅供学习研究，不构成投资建议</div>
</div>"""
    return _wrap(body, css)


# ============ 3. 浅色极简式 ============
def minimal(c):
    css = """
*{margin:0;padding:0;box-sizing:border-box}
body{background:linear-gradient(135deg,#e8e0f7 0%,#d8e4f2 45%,#f0e2ef 100%);min-height:100vh;color:#2d2a45;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;padding:34px 22px}
.wrap{max-width:560px;margin:0 auto}
.top{text-align:left;margin-bottom:20px}
.top h1{font-size:22px;font-weight:700;letter-spacing:-0.5px}
.top .d{font-size:13px;color:#8a86a3;margin-top:5px}
.glass{background:rgba(255,255,255,0.5);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,0.65);border-radius:20px;box-shadow:0 8px 32px rgba(76,58,150,0.10);padding:20px 22px;margin-bottom:16px}
.advice .pill{display:inline-block;background:linear-gradient(135deg,#7c3aed,#a855f7);color:#fff;font-size:12px;padding:5px 14px;border-radius:999px;margin-bottom:12px;letter-spacing:1px}
.advice .a{font-size:32px;font-weight:700;letter-spacing:-1px}
.advice .r{font-size:13px;color:#6a6580;margin-top:8px;line-height:1.7}
.price .big{font-size:54px;font-weight:700;letter-spacing:-2px}
.price .unit{font-size:15px;color:#8a86a3}
.price .chg{font-size:15px;font-weight:600;margin-top:8px}
.metrics .item{display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid rgba(0,0,0,0.05)}
.metrics .item:last-child{border-bottom:none}
.metrics .k{font-size:13px;color:#8a86a3}
.metrics .v{font-size:14px;font-weight:600}
.chart img{width:100%;display:block;border-radius:12px}
.risk{font-size:13px;color:#6a6580;line-height:1.7}
.risk b{color:#7c3aed}
.info .item{display:flex;justify-content:space-between;align-items:center;padding:8px 0;font-size:13px;color:#6a6580;border-bottom:1px solid rgba(0,0,0,0.05)}
.info .item:last-child{border-bottom:none}
.info .v{font-weight:600;color:#2d2a45}
.up{color:#7c3aed}.down{color:#ef4444}
.foot{text-align:center;font-size:11px;color:#a5a1b8;margin-top:18px}
"""
    updown = "down" if c.chg1.startswith("-") else "up"
    body = f"""
<div class="wrap">
  <div class="top"><h1>黄金定投日报</h1><div class="d">{c.today}</div></div>
  <div class="glass advice">
    <div class="pill">今日定投建议</div>
    <div class="a">{c.action}</div>
    <div class="r">{c.trend_note} · {c.val_note}</div>
  </div>
  <div class="glass price">
    <span class="big">{c.latest}</span><span class="unit"> 元/克</span>
    <div class="chg {updown}">{c.chg1} · 5日 {c.chg5}</div>
  </div>
  <div class="glass metrics">
    <div class="item"><span class="k">趋势</span><span class="v">{c.trend}</span></div>
    <div class="item"><span class="k">RSI</span><span class="v">{c.rsi_txt}</span></div>
    <div class="item"><span class="k">估值</span><span class="v">{c.valuation}</span></div>
    <div class="item"><span class="k">短期（1~2周）</span><span class="v">{c.short_view}</span></div>
  </div>
  <div class="glass chart"><img src="data:image/png;base64,{c.img_light}"></div>
  <div class="glass risk">⚠️ <b>风险提示</b>　{c.risk_note}</div>
  <div class="glass info">
    <div class="item"><span class="k">宏观</span><span class="v">{c.macro_line}</span></div>
    <div class="item"><span class="k">央行</span><span class="v">{c.pboc_line}</span></div>
  </div>
  <div class="foot">仅供学习研究，不构成投资建议</div>
</div>"""
    return _wrap(body, css)


def main():
    c = build()
    for name, fn in [("paper", newspaper), ("terminal", terminal), ("minimal", minimal)]:
        html = fn(c)
        with open(f"v2_{name}.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"v2_{name}.html 已生成")


if __name__ == "__main__":
    main()
