# -*- coding: utf-8 -*-
"""
生成 4 种不同布局的预览图，供选择。
运行：python preview_layouts.py
输出：preview_layout1~4.png + layout1~4.html
"""
import sys
import base64
import io
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

import fetch_data
import analyze


def render_sge_chart(sge_df, days=250):
    if sge_df is None or sge_df.empty:
        return None
    df = sge_df.copy()
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["close"])
    if df.empty:
        return None
    close_full = df["close"]
    dates_full = pd.to_datetime(df["date"])
    ma20_full = close_full.rolling(20).mean()
    ma50_full = close_full.rolling(50).mean()
    close = close_full.iloc[-days:]
    dates = dates_full.iloc[-days:]
    ma20 = ma20_full.iloc[-days:]
    ma50 = ma50_full.iloc[-days:]
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(dates, close.values, label="Au99.99", color="#c0392b", linewidth=1.5)
    if ma20.dropna().size > 0:
        ax.plot(dates, ma20.values, label="MA20", color="#e67e22", linewidth=1.0, alpha=0.9)
    if ma50.dropna().size > 0:
        ax.plot(dates, ma50.values, label="MA50", color="#2980b9", linewidth=1.0, alpha=0.9)
    ax.set_title("国内金价 Au99.99 走势（近 1 年，元/克）")
    ax.legend(loc="best", fontsize=8)
    ax.grid(True, alpha=0.3)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def _fmt(v, nd=2):
    if v is None:
        return "-"
    try:
        return f"{float(v):.{nd}f}"
    except (TypeError, ValueError):
        return str(v)


def _pct(v):
    if v is None:
        return "-"
    return f"{float(v):+.2f}%"


def build_common():
    data = fetch_data.fetch_all()
    result = analyze.analyze(data)
    sge = result["sge"]
    advice = result["advice"]
    short = result["short_term"]
    macro = result["macro"]
    pboc = result["pboc"]
    img = render_sge_chart(data.get("sge"))

    action = advice["action"]
    if "加码" in action:
        color, color2 = "#27ae60", "#2ecc71"
    elif "减量" in action:
        color, color2 = "#e74c3c", "#c0392b"
    else:
        color, color2 = "#2980b9", "#3498db"

    macro_parts = []
    if macro.get("DXY"):
        macro_parts.append(f"美元 {_fmt(macro['DXY'].get('value'))}")
    if macro.get("US10Y"):
        macro_parts.append(f"美债10Y {_fmt(macro['US10Y'].get('value'))}%")
    if macro.get("SILVER"):
        macro_parts.append(f"白银 {_fmt(macro['SILVER'].get('value'))}")
    macro_line = " · ".join(macro_parts) if macro_parts else "宏观缺失"
    pboc_line = f"央行储备 {pboc.get('month','')} 环比 {_pct(pboc.get('mom'))}" if pboc.get("available") else "央行储备缺失"

    trend = advice["trend"]
    rsi = sge.get("rsi")
    rsi_txt = f"RSI {rsi:.0f} 超卖" if rsi is not None and rsi < 30 else f"RSI {rsi:.0f} 超买" if rsi is not None and rsi > 70 else f"RSI {rsi:.0f}" if rsi is not None else "RSI -"
    valuation = advice["valuation"]

    return SimpleNamespace(
        action=action, color=color, color2=color2, today=datetime.now().strftime("%Y-%m-%d"),
        latest=_fmt(sge.get('latest')), chg1=_pct(sge.get('change_1d')), chg5=_pct(sge.get('change_5d')),
        trend=trend, rsi_txt=rsi_txt, valuation=valuation,
        trend_note=advice['trend_note'], val_note=advice['val_note'],
        short_view=short.get('view','-'), short_note=short.get('note',''),
        macro_line=macro_line, pboc_line=pboc_line, img=img,
    )


def _wrap(t, body, color, color2):
    t = t.replace("__COLOR__", color).replace("__COLOR2__", color2)
    return f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>布局预览</title>
<style>{t}</style></head><body>{body}</body></html>"""


# ============ 布局1：渐变卡片 ============
def layout1(c):
    css = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Microsoft YaHei",sans-serif;background:#f0f2f5;color:#2c3e50;padding:24px 20px}
.container{max-width:620px;margin:0 auto}
.header{text-align:center;margin-bottom:20px}
.header h1{font-size:20px;color:#34495e}
.header .date{font-size:13px;color:#95a5a6;margin-top:4px}
.advice{background:linear-gradient(135deg,__COLOR__,__COLOR2__);border-radius:16px;padding:26px;color:#fff;text-align:center;margin-bottom:16px;box-shadow:0 6px 18px rgba(0,0,0,.14)}
.advice .l{font-size:14px;opacity:.92}
.advice .a{font-size:30px;font-weight:bold;margin:8px 0 6px}
.advice .r{font-size:14px;opacity:.92}
.price{background:#fff;border-radius:14px;padding:22px;text-align:center;margin-bottom:12px;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.price .l{font-size:13px;color:#7f8c8d}
.price .v{font-size:52px;font-weight:bold;margin:6px 0 2px}
.price .u{font-size:15px;color:#7f8c8d}
.price .d{font-size:16px;font-weight:bold;margin-top:8px}
.badges{display:flex;gap:10px;justify-content:center;margin-bottom:12px;flex-wrap:wrap}
.badge{padding:8px 16px;border-radius:20px;font-size:14px;font-weight:bold;background:#fff;box-shadow:0 2px 6px rgba(0,0,0,.05)}
.badge b{color:__COLOR__}
.chart{background:#fff;border-radius:14px;padding:14px;margin-bottom:12px;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.chart img{width:100%;border-radius:8px;display:block}
.short{background:#fff;border-radius:12px;padding:14px 18px;margin-bottom:10px;font-size:14px;box-shadow:0 2px 8px rgba(0,0,0,.04)}
.info{background:#fff;border-radius:12px;padding:12px 18px;margin-bottom:10px;font-size:13px;color:#5d6d7e;box-shadow:0 2px 8px rgba(0,0,0,.04)}
.up{color:#27ae60}.down{color:#e74c3c}
.disclaimer{text-align:center;color:#bdc3c7;font-size:11px;margin-top:12px}
"""
    body = f"""
<div class="container">
  <div class="header"><h1>黄金定投日报</h1><div class="date">{c.today}</div></div>
  <div class="advice"><div class="l">今日定投建议</div><div class="a">{c.action}</div><div class="r">{c.trend_note} · {c.val_note}</div></div>
  <div class="price"><div class="l">国内金价 Au99.99</div><div class="v">{c.latest}</div><div class="u">元/克</div><div class="d {'down' if c.chg1.startswith('-') else 'up'}">日 {c.chg1} · 5日 {c.chg5}</div></div>
  <div class="badges"><span class="badge">趋势：<b>{c.trend}</b></span><span class="badge"><b>{c.rsi_txt}</b></span><span class="badge">估值：<b>{c.valuation}</b></span></div>
  <div class="chart"><img src="data:image/png;base64,{c.img}"></div>
  <div class="short"><b>短期（1~2周）：{c.short_view}</b> — {c.short_note}</div>
  <div class="info">📊 {c.macro_line}</div>
  <div class="info">🏦 {c.pboc_line}</div>
  <div class="disclaimer">仅供学习研究，不构成投资建议</div>
</div>"""
    return _wrap(css, body, c.color, c.color2)


# ============ 布局2：深色科技 ============
def layout2(c):
    css = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Microsoft YaHei",sans-serif;background:#0f1626;color:#e0e6ed;padding:24px 20px}
.container{max-width:620px;margin:0 auto}
.header{text-align:center;margin-bottom:20px}
.header h1{font-size:20px;color:#fff}
.header .date{font-size:13px;color:#5c6b7e;margin-top:4px}
.advice{background:linear-gradient(135deg,__COLOR__,__COLOR2__);border-radius:16px;padding:26px;color:#fff;text-align:center;margin-bottom:16px;box-shadow:0 6px 24px rgba(0,0,0,.4)}
.advice .l{font-size:14px;opacity:.9}
.advice .a{font-size:30px;font-weight:bold;margin:8px 0 6px}
.advice .r{font-size:14px;opacity:.9}
.price{background:#1a2332;border:1px solid #253144;border-radius:14px;padding:22px;text-align:center;margin-bottom:12px}
.price .l{font-size:13px;color:#5c6b7e}
.price .v{font-size:52px;font-weight:bold;margin:6px 0 2px;color:#fff}
.price .u{font-size:15px;color:#5c6b7e}
.price .d{font-size:16px;font-weight:bold;margin-top:8px}
.badges{display:flex;gap:10px;justify-content:center;margin-bottom:12px;flex-wrap:wrap}
.badge{padding:8px 16px;border-radius:20px;font-size:14px;font-weight:bold;background:#1a2332;border:1px solid #253144}
.badge b{color:__COLOR2__}
.chart{background:#1a2332;border:1px solid #253144;border-radius:14px;padding:14px;margin-bottom:12px}
.chart img{width:100%;border-radius:8px;display:block}
.short{background:#1a2332;border:1px solid #253144;border-radius:12px;padding:14px 18px;margin-bottom:10px;font-size:14px}
.info{background:#1a2332;border:1px solid #253144;border-radius:12px;padding:12px 18px;margin-bottom:10px;font-size:13px;color:#8b9bb0}
.up{color:#2ecc71}.down{color:#e74c3c}
.disclaimer{text-align:center;color:#3d4c60;font-size:11px;margin-top:12px}
"""
    body = f"""
<div class="container">
  <div class="header"><h1>黄金定投日报</h1><div class="date">{c.today}</div></div>
  <div class="advice"><div class="l">今日定投建议</div><div class="a">{c.action}</div><div class="r">{c.trend_note} · {c.val_note}</div></div>
  <div class="price"><div class="l">国内金价 Au99.99</div><div class="v">{c.latest}</div><div class="u">元/克</div><div class="d {'down' if c.chg1.startswith('-') else 'up'}">日 {c.chg1} · 5日 {c.chg5}</div></div>
  <div class="badges"><span class="badge">趋势：<b>{c.trend}</b></span><span class="badge"><b>{c.rsi_txt}</b></span><span class="badge">估值：<b>{c.valuation}</b></span></div>
  <div class="chart"><img src="data:image/png;base64,{c.img}"></div>
  <div class="short"><b>短期（1~2周）：{c.short_view}</b> — {c.short_note}</div>
  <div class="info">📊 {c.macro_line}</div>
  <div class="info">🏦 {c.pboc_line}</div>
  <div class="disclaimer">仅供学习研究，不构成投资建议</div>
</div>"""
    return _wrap(css, body, c.color, c.color2)


# ============ 布局3：极简清单 ============
def layout3(c):
    css = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Microsoft YaHei",sans-serif;background:#fff;color:#1a1a1a;padding:30px 24px}
.container{max-width:600px;margin:0 auto}
.header{margin-bottom:28px}
.header h1{font-size:26px;font-weight:700;letter-spacing:1px}
.header .date{font-size:13px;color:#999;margin-top:6px}
.advice{margin-bottom:28px}
.advice .l{font-size:13px;color:#999;letter-spacing:2px}
.advice .a{font-size:36px;font-weight:800;margin:6px 0;color:__COLOR__}
.advice .r{font-size:14px;color:#666;line-height:1.6}
.price{border-top:1px solid #eee;padding:22px 0}
.price .row{display:flex;justify-content:space-between;align-items:baseline}
.price .l{font-size:14px;color:#999}
.price .v{font-size:44px;font-weight:800}
.price .u{font-size:14px;color:#999}
.price .d{font-size:14px;font-weight:600}
.chart{padding:16px 0;border-top:1px solid #eee}
.chart img{width:100%;display:block}
.row-line{display:flex;justify-content:space-between;padding:14px 0;border-top:1px solid #eee;font-size:15px}
.row-line .k{color:#666}
.row-line .v{font-weight:600}
.up{color:#27ae60}.down{color:#e74c3c}
.disclaimer{text-align:center;color:#ccc;font-size:11px;margin-top:20px;padding-top:16px;border-top:1px solid #eee}
"""
    body = f"""
<div class="container">
  <div class="header"><h1>黄金定投日报</h1><div class="date">{c.today}</div></div>
  <div class="advice"><div class="l">今日定投建议</div><div class="a">{c.action}</div><div class="r">{c.trend_note}<br>{c.val_note}</div></div>
  <div class="price">
    <div class="row"><span class="l">国内金价 Au99.99</span><span class="d {'down' if c.chg1.startswith('-') else 'up'}">{c.chg1}</span></div>
    <div class="row"><span class="v">{c.latest}</span><span class="u">元/克</span></div>
  </div>
  <div class="row-line"><span class="k">趋势</span><span class="v">{c.trend}</span></div>
  <div class="row-line"><span class="k">RSI</span><span class="v">{c.rsi_txt}</span></div>
  <div class="row-line"><span class="k">估值</span><span class="v">{c.valuation}</span></div>
  <div class="row-line"><span class="k">短期（1~2周）</span><span class="v">{c.short_view}</span></div>
  <div class="chart"><img src="data:image/png;base64,{c.img}"></div>
  <div class="row-line"><span class="k">宏观</span><span class="v">{c.macro_line}</span></div>
  <div class="row-line"><span class="k">央行</span><span class="v">{c.pboc_line}</span></div>
  <div class="disclaimer">仅供学习研究，不构成投资建议</div>
</div>"""
    return _wrap(css, body, c.color, c.color2)


# ============ 布局4：网格仪表盘 ============
def layout4(c):
    css = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Microsoft YaHei",sans-serif;background:#eef1f5;color:#2c3e50;padding:24px 20px}
.container{max-width:620px;margin:0 auto}
.header{margin-bottom:18px;text-align:center}
.header h1{font-size:20px;color:#34495e}
.header .date{font-size:13px;color:#95a5a6;margin-top:4px}
.advice{background:__COLOR__;border-radius:14px;padding:20px;color:#fff;text-align:center;margin-bottom:14px}
.advice .a{font-size:26px;font-weight:bold}
.advice .r{font-size:13px;opacity:.9;margin-top:4px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px}
.cell{background:#fff;border-radius:12px;padding:16px;text-align:center;box-shadow:0 2px 6px rgba(0,0,0,.05)}
.cell .l{font-size:12px;color:#95a5a6}
.cell .v{font-size:24px;font-weight:bold;margin-top:6px}
.cell .v.small{font-size:18px}
.cell .d{font-size:12px;margin-top:4px}
.chart{background:#fff;border-radius:12px;padding:12px;margin-bottom:12px;box-shadow:0 2px 6px rgba(0,0,0,.05)}
.chart img{width:100%;border-radius:8px;display:block}
.short{background:#fff;border-radius:12px;padding:13px 16px;margin-bottom:10px;font-size:14px;box-shadow:0 2px 6px rgba(0,0,0,.05)}
.info{background:#fff;border-radius:12px;padding:11px 16px;margin-bottom:10px;font-size:13px;color:#5d6d7e;box-shadow:0 2px 6px rgba(0,0,0,.05)}
.up{color:#27ae60}.down{color:#e74c3c}
.disclaimer{text-align:center;color:#bdc3c7;font-size:11px;margin-top:12px}
"""
    body = f"""
<div class="container">
  <div class="header"><h1>黄金定投日报</h1><div class="date">{c.today}</div></div>
  <div class="advice"><div class="a">{c.action}</div><div class="r">{c.trend_note} · {c.val_note}</div></div>
  <div class="grid">
    <div class="cell"><div class="l">国内金价</div><div class="v">{c.latest}</div><div class="d {'down' if c.chg1.startswith('-') else 'up'}">{c.chg1}</div></div>
    <div class="cell"><div class="l">RSI</div><div class="v small">{c.rsi_txt}</div><div class="d">{c.short_view}</div></div>
    <div class="cell"><div class="l">趋势</div><div class="v small">{c.trend}</div><div class="d">近1年</div></div>
    <div class="cell"><div class="l">估值</div><div class="v small">{c.valuation}</div><div class="d">近5年分位</div></div>
  </div>
  <div class="chart"><img src="data:image/png;base64,{c.img}"></div>
  <div class="short"><b>短期（1~2周）：{c.short_view}</b> — {c.short_note}</div>
  <div class="info">📊 {c.macro_line}</div>
  <div class="info">🏦 {c.pboc_line}</div>
  <div class="disclaimer">仅供学习研究，不构成投资建议</div>
</div>"""
    return _wrap(css, body, c.color, c.color2)


def main():
    c = build_common()
    layouts = [layout1, layout2, layout3, layout4]
    for i, fn in enumerate(layouts, 1):
        html = fn(c)
        with open(f"layout{i}.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"layout{i}.html 已生成")


if __name__ == "__main__":
    main()
