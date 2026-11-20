# -*- coding: utf-8 -*-
"""
黄金市场日报 —— 主入口（HTML 版）

用法：python main.py
功能：拉数据 → 分析 → 画图 → 生成 HTML 报告（内嵌图表 + 颜色标注）
输出：gold_report.html（用浏览器打开）
"""
import sys
import base64
import io
from datetime import datetime

# Windows 控制台 GBK 编码兼容
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import matplotlib
matplotlib.use("Agg")  # 无 GUI 后端
import matplotlib.pyplot as plt
import pandas as pd

import fetch_data
import analyze
from analyze import _extract_series, calc_ma, calc_rsi


# ---------------------------------------------------------------------------
# 格式化工具
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 图表生成
# ---------------------------------------------------------------------------

def _setup_font():
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False


def _fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def render_price_chart(close):
    """价格 + 均线图。"""
    _setup_font()
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(close.index, close.values, label="收盘价", color="#2c3e50", linewidth=1.4)
    for w, color, name in [(20, "#e67e22", "MA20"), (50, "#2980b9", "MA50"), (200, "#8e44ad", "MA200")]:
        ma = calc_ma(close, w)
        if ma is not None:
            ax.plot(ma.index, ma.values, label=name, color=color, linewidth=1.0, alpha=0.9)
    ax.set_title("国际金价走势（美元/盎司）")
    ax.legend(loc="best", fontsize=8)
    ax.grid(True, alpha=0.3)
    return _fig_to_base64(fig)


def render_rsi_chart(close):
    """RSI 图。"""
    rsi = calc_rsi(close, 14)
    if rsi is None:
        return None
    _setup_font()
    fig, ax = plt.subplots(figsize=(9, 2.4))
    ax.plot(rsi.index, rsi.values, color="#16a085", linewidth=1.2)
    ax.axhline(70, color="#e74c3c", linestyle="--", alpha=0.6)
    ax.axhline(30, color="#27ae60", linestyle="--", alpha=0.6)
    ax.fill_between(rsi.index, 30, 70, alpha=0.06, color="#95a5a6")
    ax.set_ylim(0, 100)
    ax.set_title("RSI(14) 相对强弱（>70 超买 / <30 超卖）")
    ax.grid(True, alpha=0.3)
    return _fig_to_base64(fig)


def render_sge_chart(sge_df, days=250):
    """国内金价 Au99.99 走势图（近 1 年）。均线用全量数据算，再截取显示。"""
    if sge_df is None or sge_df.empty:
        return None
    df = sge_df.copy()
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["close"])
    if df.empty:
        return None
    close_full = df["close"]
    dates_full = pd.to_datetime(df["date"])
    # 均线用全量数据算，再截取最近 N 天显示（避免 MA50 只有最后几天有值）
    ma20_full = close_full.rolling(20).mean()
    ma50_full = close_full.rolling(50).mean()
    close = close_full.iloc[-days:]
    dates = dates_full.iloc[-days:]
    ma20 = ma20_full.iloc[-days:]
    ma50 = ma50_full.iloc[-days:]
    _setup_font()
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(dates, close.values, label="Au99.99", color="#c0392b", linewidth=1.5)
    if ma20.dropna().size > 0:
        ax.plot(dates, ma20.values, label="MA20", color="#e67e22", linewidth=1.0, alpha=0.9)
    if ma50.dropna().size > 0:
        ax.plot(dates, ma50.values, label="MA50", color="#2980b9", linewidth=1.0, alpha=0.9)
    ax.set_title("国内金价 Au99.99 走势（近 1 年，元/克）")
    ax.legend(loc="best", fontsize=8)
    ax.grid(True, alpha=0.3)
    return _fig_to_base64(fig)


# ---------------------------------------------------------------------------
# HTML 渲染
# ---------------------------------------------------------------------------

def _bias_color(bias):
    if "偏空" in bias or bias == "利空":
        return "#e74c3c"
    if "偏多" in bias or bias == "利多":
        return "#27ae60"
    return "#95a5a6"


def render_html(result, sge_img):
    macro = result["macro"]
    pboc = result["pboc"]
    sge = result["sge"]
    advice = result["advice"]
    short_term = result.get("short_term", {})

    action = advice["action"]
    trend = advice["trend"]
    valuation = advice["valuation"]
    trend_note = advice["trend_note"]
    val_note = advice["val_note"]
    risk_note = advice.get("risk_note", "")
    short_view = short_term.get("view", "-")
    short_note = short_term.get("note", "")
    today = datetime.now().strftime("%Y-%m-%d")

    # RSI 文本
    rsi = sge.get("rsi")
    if rsi is not None and rsi < 30:
        rsi_txt = f"RSI {rsi:.0f} 超卖"
    elif rsi is not None and rsi > 70:
        rsi_txt = f"RSI {rsi:.0f} 超买"
    else:
        rsi_txt = f"RSI {rsi:.0f}" if rsi is not None else "RSI -"

    # 宏观一行
    macro_parts = []
    if macro.get("DXY"):
        macro_parts.append(f"美元 {_fmt(macro['DXY'].get('value'))}")
    if macro.get("US10Y"):
        macro_parts.append(f"美债10Y {_fmt(macro['US10Y'].get('value'))}%")
    if macro.get("SILVER"):
        macro_parts.append(f"白银 {_fmt(macro['SILVER'].get('value'))}")
    macro_line = " · ".join(macro_parts) if macro_parts else "宏观数据缺失"

    # 央行一行
    if pboc.get("available"):
        pboc_line = f"央行黄金储备 {pboc.get('month','')} 环比 {_pct(pboc.get('mom'))}"
    else:
        pboc_line = "央行黄金储备数据缺失"

    updown = "down" if (sge.get("change_1d") or 0) < 0 else "up"

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>黄金定投日报 {today}</title>
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{background:linear-gradient(135deg,#e8e0f7 0%,#d8e4f2 45%,#f0e2ef 100%);min-height:100vh;color:#2d2a45;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;padding:34px 22px}}
  .wrap{{max-width:560px;margin:0 auto}}
  .top{{text-align:left;margin-bottom:20px}}
  .top h1{{font-size:22px;font-weight:700;letter-spacing:-0.5px}}
  .top .d{{font-size:13px;color:#8a86a3;margin-top:5px}}
  .glass{{background:rgba(255,255,255,0.5);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,0.65);border-radius:20px;box-shadow:0 8px 32px rgba(76,58,150,0.10);padding:20px 22px;margin-bottom:16px}}
  .advice .pill{{display:inline-block;background:linear-gradient(135deg,#7c3aed,#a855f7);color:#fff;font-size:12px;padding:5px 14px;border-radius:999px;margin-bottom:12px;letter-spacing:1px}}
  .advice .a{{font-size:32px;font-weight:700;letter-spacing:-1px}}
  .advice .r{{font-size:13px;color:#6a6580;margin-top:8px;line-height:1.7}}
  .price .big{{font-size:54px;font-weight:700;letter-spacing:-2px}}
  .price .unit{{font-size:15px;color:#8a86a3}}
  .price .chg{{font-size:15px;font-weight:600;margin-top:8px}}
  .metrics .item{{display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid rgba(0,0,0,0.05)}}
  .metrics .item:last-child{{border-bottom:none}}
  .metrics .k{{font-size:13px;color:#8a86a3}}
  .metrics .v{{font-size:14px;font-weight:600}}
  .chart img{{width:100%;display:block;border-radius:12px}}
  .risk{{font-size:13px;color:#6a6580;line-height:1.7}}
  .risk b{{color:#7c3aed}}
  .info .item{{display:flex;justify-content:space-between;align-items:center;padding:8px 0;font-size:13px;color:#6a6580;border-bottom:1px solid rgba(0,0,0,0.05)}}
  .info .item:last-child{{border-bottom:none}}
  .info .v{{font-weight:600;color:#2d2a45}}
  .up{{color:#7c3aed}}.down{{color:#ef4444}}
  .foot{{text-align:center;font-size:11px;color:#a5a1b8;margin-top:18px}}
</style>
</head>
<body>
<div class="wrap">
  <div class="top"><h1>黄金定投日报</h1><div class="d">{today}</div></div>
  <div class="glass advice">
    <div class="pill">今日定投建议</div>
    <div class="a">{action}</div>
    <div class="r">{trend_note} · {val_note}</div>
  </div>
  <div class="glass price">
    <span class="big">{_fmt(sge.get('latest'))}</span><span class="unit"> 元/克</span>
    <div class="chg {updown}">{_pct(sge.get('change_1d'))} · 5日 {_pct(sge.get('change_5d'))}</div>
  </div>
  <div class="glass metrics">
    <div class="item"><span class="k">趋势</span><span class="v">{trend}</span></div>
    <div class="item"><span class="k">RSI</span><span class="v">{rsi_txt}</span></div>
    <div class="item"><span class="k">估值</span><span class="v">{valuation}</span></div>
    <div class="item"><span class="k">短期（1~2周）</span><span class="v">{short_view}</span></div>
  </div>
  <div class="glass chart"><img src="data:image/png;base64,{sge_img}"></div>
  <div class="glass risk">⚠️ <b>风险提示</b>　{risk_note}</div>
  <div class="glass info">
    <div class="item"><span class="k">宏观</span><span class="v">{macro_line}</span></div>
    <div class="item"><span class="k">央行</span><span class="v">{pboc_line}</span></div>
  </div>
  <div class="foot">仅供学习研究，不构成投资建议</div>
</div>
</body>
</html>"""
    return html


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def html_to_png(html_path, png_path, width=620):
    """用 Playwright 把 HTML 截图成长图 PNG（2倍清晰度，适合推送）。"""
    import pathlib
    from playwright.sync_api import sync_playwright
    html_path = str(pathlib.Path(html_path).resolve())
    png_path = str(pathlib.Path(png_path).resolve())
    uri = pathlib.Path(html_path).as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": 900}, device_scale_factor=2)
        page.goto(uri)
        page.wait_for_timeout(800)  # 等 base64 图表渲染完成
        page.screenshot(path=png_path, full_page=True)
        browser.close()


def main():
    print(">>> 正在拉取数据 ...")
    data = fetch_data.fetch_all()
    print(">>> 正在分析 ...")
    result = analyze.analyze(data)

    print(">>> 正在生成图表 ...")
    sge_img = render_sge_chart(data.get("sge"))

    print(">>> 正在渲染 HTML ...")
    html = render_html(result, sge_img)

    filename = "gold_report.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)

    print(">>> 正在生成长图 ...")
    try:
        html_to_png(filename, "gold_report.png")
        print(">>> 长图已生成: gold_report.png")
    except Exception as e:
        print(f">>> 长图生成失败: {e}")

    print(f"\n>>> 报告已生成: {filename}")
    print(f">>> 定投建议: {result['advice']['action']}")


if __name__ == "__main__":
    main()
