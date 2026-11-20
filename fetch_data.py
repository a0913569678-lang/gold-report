# -*- coding: utf-8 -*-
"""
数据获取模块
- akshare: 国内金价(Au99.99)、中国央行黄金储备
- yfinance: 国际金价(GC=F)、美元指数、美债收益率、白银

所有函数都带容错，失败返回 None，由上层决定如何处理。
"""
import time

import pandas as pd
import yfinance as yf


# ---------------------------------------------------------------------------
# akshare 国内数据
# ---------------------------------------------------------------------------

def fetch_sge_gold(symbol="Au99.99"):
    """上海黄金交易所现货黄金历史价格。返回 DataFrame[date, open, close, low, high]。"""
    try:
        import akshare as ak
        df = ak.spot_hist_sge(symbol=symbol)
        if df is None or df.empty:
            return None
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        return df
    except Exception as e:
        print(f"[warn] 拉取国内金价失败: {e}")
        return None


def fetch_pboc_gold():
    """中国央行黄金储备（月度）。返回 DataFrame，含 月份/黄金储备-数值/黄金储备-环比 等。"""
    try:
        import akshare as ak
        df = ak.macro_china_fx_gold()
        if df is None or df.empty:
            return None
        return df.copy()
    except Exception as e:
        print(f"[warn] 拉取央行黄金储备失败: {e}")
        return None


# ---------------------------------------------------------------------------
# yfinance 国际数据
# ---------------------------------------------------------------------------

def fetch_yf(ticker, period="6mo", interval="1d", retries=3):
    """通用 yfinance 下载（带重试），返回 DataFrame（可能带 MultiIndex 列）。"""
    for i in range(retries):
        try:
            df = yf.download(ticker, period=period, interval=interval, progress=False)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            print(f"[warn] yfinance 拉取 {ticker} 第{i+1}次失败: {e}")
        if i < retries - 1:
            time.sleep(2)
    print(f"[warn] yfinance 拉取 {ticker} 最终失败（已重试{retries}次）")
    return None


def fetch_intl_gold():
    """国际金价日线。优先 GC=F，失败 fallback 到 GLD（×10 近似金价）。
    返回 (df, source)，source 用于报告标注数据来源。"""
    for period in ("1y", "6mo", "3mo"):
        df = fetch_yf("GC=F", period=period, interval="1d", retries=2)
        if df is not None and not df.empty:
            return df, "GC=F"
    # fallback 到 GLD（SPDR 黄金 ETF，1 股约 0.1 盎司，价格×10 近似金价）
    for period in ("1y", "6mo", "3mo"):
        df = fetch_yf("GLD", period=period, interval="1d", retries=2)
        if df is not None and not df.empty:
            df = df.copy()
            for col in df.columns:
                try:
                    df[col] = df[col] * 10.0
                except Exception:
                    pass
            return df, "GLD(近似)"
    return None, None


def fetch_macro():
    """宏观数据：美元指数、美债10Y/2Y、白银。返回 {name: DataFrame or None}。"""
    targets = [
        ("DXY", "DX-Y.NYB"),   # 美元指数
        ("US10Y", "^TNX"),     # 美债10年期收益率
        ("US02Y", "^IRX"),     # 美债2年期收益率
        ("SILVER", "SI=F"),    # 白银
    ]
    result = {}
    for name, ticker in targets:
        result[name] = fetch_yf(ticker, period="3mo", interval="1d")
    return result


def fetch_all():
    """一次拉取全部数据。返回 dict，值为 DataFrame 或 None。"""
    intl_df, intl_source = fetch_intl_gold()
    return {
        "sge": fetch_sge_gold(),
        "pboc": fetch_pboc_gold(),
        "intl_gold": intl_df,
        "intl_source": intl_source,
        "macro": fetch_macro(),
    }
