# -*- coding: utf-8 -*-
"""
分析模块
- 指标计算：MA20/MA50/RSI、涨跌幅、回撤
- 五层判断：宏观 / 趋势 / 信号 / 资金 / 综合

判断结果统一用 bias 表达：
    "利空" / "偏空" / "中性" / "偏多" / "利多"
"""
import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------

def _extract_series(df, col="Close"):
    """从 yfinance DataFrame 稳健提取某一列，返回干净的 Series（去掉 NaN）。"""
    if df is None or df.empty:
        return None
    try:
        s = df[col]
    except KeyError:
        if isinstance(df.columns, pd.MultiIndex):
            try:
                s = df.xs(col, axis=1, level=0)
            except Exception:
                return None
        else:
            return None
    if isinstance(s, pd.DataFrame):
        s = s.iloc[:, 0]
    s = pd.to_numeric(s, errors="coerce")
    return s.dropna()


def _last(s):
    """取 Series 最后一个有效值。"""
    if s is None or len(s) == 0:
        return None
    return float(s.iloc[-1])


def calc_ma(close, window):
    """移动平均。"""
    if close is None or len(close) < window:
        return None
    return close.rolling(window).mean()


def calc_rsi(close, window=14):
    """RSI 相对强弱指标。"""
    if close is None or len(close) < window + 1:
        return None
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def pct_change(close, n):
    """近 n 日涨跌幅（%）。"""
    if close is None or len(close) <= n:
        return None
    return (close.iloc[-1] / close.iloc[-1 - n] - 1) * 100


# ---------------------------------------------------------------------------
# 各层分析
# ---------------------------------------------------------------------------

def analyze_price(close):
    """通用价格分析（MA/RSI/动量/估值/回撤），close 是价格 Series。"""
    if close is None or len(close) < 30:
        return {"available": False}

    ma20 = calc_ma(close, 20)
    ma50 = calc_ma(close, 50)
    ma200 = calc_ma(close, 200)
    rsi = calc_rsi(close, 14)

    price = _last(close)
    m20 = _last(ma20) if ma20 is not None else None
    m50 = _last(ma50) if ma50 is not None else None
    m200 = _last(ma200) if ma200 is not None else None
    r = _last(rsi) if rsi is not None else None

    # 回撤（数据范围内高点）
    drawdown = None
    peak = float(close.max())
    drawdown = (price / peak - 1) * 100 if peak else None

    # 动量（中长期趋势信号，回测证明短期反向、中长期有效）
    mom120 = pct_change(close, 120)
    mom250 = pct_change(close, 250)

    # 估值分位（当前价在近5年中的位置，0=最低，100=最高）
    pct_5y = None
    if len(close) > 60:
        window = close.iloc[-1260:] if len(close) > 1260 else close
        pct_5y = float((close.iloc[-1] <= window).mean() * 100)

    # 历史最大回撤（用全部可用数据）
    max_dd = None
    if len(close) > 60:
        cum = (1 + close.pct_change()).cumprod()
        max_dd = float((cum / cum.cummax() - 1).min())

    # 年化波动率
    vol = None
    if len(close) > 60:
        vol = float(close.pct_change().std() * np.sqrt(252))

    return {
        "available": True,
        "price": price,
        "ma20": m20,
        "ma50": m50,
        "ma200": m200,
        "rsi": r,
        "change_1d": pct_change(close, 1),
        "change_5d": pct_change(close, 5),
        "change_20d": pct_change(close, 20),
        "drawdown": drawdown,
        "mom120": mom120,
        "mom250": mom250,
        "pct_5y": pct_5y,
        "max_dd": max_dd,
        "vol": vol,
        "above_ma20": (price > m20) if (price is not None and m20 is not None) else None,
        "above_ma50": (price > m50) if (price is not None and m50 is not None) else None,
        "above_ma200": (price > m200) if (price is not None and m200 is not None) else None,
    }


def analyze_macro(macro_dict):
    """宏观：美元指数 + 美债收益率。"""
    result = {}
    if not macro_dict:
        return result

    # 美元指数
    dxy = _extract_series(macro_dict.get("DXY"))
    if dxy is not None:
        dxy_last = _last(dxy)
        dxy_chg = pct_change(dxy, 20)
        # 美元走强(20日涨) -> 利空黄金
        bias = "中性"
        if dxy_chg is not None:
            if dxy_chg > 1.0:
                bias = "利空"
            elif dxy_chg < -1.0:
                bias = "利多"
            else:
                bias = "中性"
        result["DXY"] = {"value": dxy_last, "change_20d": dxy_chg, "bias": bias}

    # 美债10年期
    us10y = _extract_series(macro_dict.get("US10Y"))
    if us10y is not None:
        v = _last(us10y)
        bias = "中性"
        if v is not None:
            if v > 4.5:
                bias = "利空"   # 高利率压制黄金
            elif v < 3.0:
                bias = "利多"
        result["US10Y"] = {"value": v, "bias": bias}

    # 美债2年期
    us02y = _extract_series(macro_dict.get("US02Y"))
    if us02y is not None:
        result["US02Y"] = {"value": _last(us02y)}

    # 白银
    silver = _extract_series(macro_dict.get("SILVER"))
    if silver is not None:
        result["SILVER"] = {"value": _last(silver), "change_5d": pct_change(silver, 5)}

    return result


def analyze_pboc(pboc_df):
    """央行黄金储备：环比变化。"""
    if pboc_df is None or pboc_df.empty:
        return {"available": False}
    try:
        col = "黄金储备-环比"
        if col not in pboc_df.columns:
            # 尝试模糊匹配
            col = [c for c in pboc_df.columns if "环比" in str(c) and "黄金" in str(c)]
            if not col:
                return {"available": False}
            col = col[0]
        latest = float(pboc_df.iloc[-1][col])
        prev = float(pboc_df.iloc[-2][col]) if len(pboc_df) >= 2 else None
        mom = latest
        bias = "中性"
        if mom is not None:
            if mom > 1:
                bias = "利多"   # 央行增持
            elif mom < -1:
                bias = "利空"   # 央行减持
        month = str(pboc_df.iloc[-1].get("月份", ""))
        return {"available": True, "month": month, "mom": mom, "bias": bias}
    except Exception as e:
        return {"available": False, "error": str(e)}


def analyze_sge(sge_df):
    """国内金价 Au99.99：完整分析（趋势/估值/RSI/回撤）。"""
    if sge_df is None or sge_df.empty:
        return {"available": False}
    close = pd.to_numeric(sge_df["close"], errors="coerce").dropna()
    if len(close) == 0:
        return {"available": False}
    result = analyze_price(close)
    result["latest"] = float(close.iloc[-1])
    return result


# ---------------------------------------------------------------------------
# 综合判断
# ---------------------------------------------------------------------------

def make_advice(intl, macro, pboc, sge):
    """定投建议（替代方向预测）。阈值经回测标定（threshold_calibration.py）。"""
    reasons = []

    # 1. 趋势背景（250日动量，标定：0为正负分界，>50%过热）
    mom250 = intl.get("mom250")
    if mom250 is not None:
        if mom250 > 50:
            trend = "过热"
            trend_note = f"过去250日涨 {mom250:+.0f}%，已过热，历史上有回调风险"
        elif mom250 > 0:
            trend = "上涨"
            trend_note = f"长期趋势上涨（过去250日 {mom250:+.1f}%）"
        elif mom250 < -10:
            trend = "下跌"
            trend_note = f"长期趋势下跌（过去250日 {mom250:+.1f}%）"
        else:
            trend = "震荡"
            trend_note = f"长期趋势震荡（过去250日 {mom250:+.1f}%）"
    else:
        trend = "未知"
        trend_note = "长期趋势数据不足"

    # 2. 估值位置（标定：<20% 低位才有优势，高位不减量）
    pct = intl.get("pct_5y")
    if pct is not None:
        if pct < 20:
            valuation = "低位"
        elif pct > 80:
            valuation = "高位"
        else:
            valuation = "中等"
        val_note = f"当前处于近5年 {pct:.0f}% 分位（{valuation}）"
    else:
        valuation = "未知"
        val_note = "估值数据不足"

    # 3. 定投建议（核心输出，标定后：只用估值+趋势，RSI 不参与）
    if valuation == "低位":
        action = "可加码定投"
        reasons.append(f"估值处于近5年低位（{pct:.0f}% 分位），回测显示低位买入未来收益显著更高")
    elif trend == "过热":
        action = "建议减量定投"
        reasons.append("过去250日涨幅过大（>50%），回测显示过热后易回调")
    else:
        action = "正常定投"

    # 4. 风险提示
    max_dd = intl.get("max_dd")
    vol = intl.get("vol")
    risk_note = ""
    if max_dd is not None and vol is not None:
        risk_note = f"历史最大回撤约 {max_dd*100:.0f}%，年化波动率 {vol*100:.0f}%。定投核心是坚持，跌了正是摊低成本的机会。"

    return {
        "action": action,
        "trend": trend,
        "trend_note": trend_note,
        "valuation": valuation,
        "val_note": val_note,
        "reasons": reasons,
        "risk_note": risk_note,
    }


def short_term_view(intl):
    """短期参考（未来 1~2 周）：基于均值回归，仅作参考。"""
    rsi = intl.get("rsi")
    mom5 = intl.get("change_5d")

    if rsi is not None and rsi < 30:
        view = "偏反弹"
        note = f"RSI={rsi:.0f} 超卖，短期跌过头有反弹倾向（仅供参考）"
    elif rsi is not None and rsi > 70:
        view = "偏回调"
        note = f"RSI={rsi:.0f} 超买，短期涨过头有回调倾向（仅供参考）"
    elif mom5 is not None and mom5 < -3:
        view = "偏反弹"
        note = f"近5日急跌 {mom5:.1f}%，短期有技术性反弹倾向（仅供参考）"
    elif mom5 is not None and mom5 > 3:
        view = "偏回调"
        note = f"近5日急涨 {mom5:.1f}%，短期有技术性回调倾向（仅供参考）"
    else:
        view = "震荡"
        note = "短期方向不明确（仅供参考）"

    return {"view": view, "note": note}


def analyze(data):
    """总入口：以国内金价为主分析。"""
    sge = analyze_sge(data.get("sge"))
    macro = analyze_macro(data.get("macro"))
    pboc = analyze_pboc(data.get("pboc"))
    advice = make_advice(sge, macro, pboc, sge)
    short_term = short_term_view(sge)
    return {
        "sge": sge,
        "macro": macro,
        "pboc": pboc,
        "advice": advice,
        "short_term": short_term,
    }
