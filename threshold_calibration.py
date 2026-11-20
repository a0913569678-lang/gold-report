# -*- coding: utf-8 -*-
"""
阈值标定：用历史数据统计「信号 → 未来收益」的真实关系，找到最优分界点。

标定对象：
1. 估值分位（近5年）→ 多少算"低位"/"高位"
2. 250日动量 → 多少算"上涨"/"下跌"
3. RSI → 验证 30/70 是否合理
"""
import sys
import time

import pandas as pd
import numpy as np
import yfinance as yf

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def load_close():
    for t in ("GLD", "GC=F"):
        for i in range(4):
            try:
                df = yf.download(t, period="max", interval="1d", progress=False)
                c = df["Close"]
                if isinstance(c, pd.DataFrame):
                    c = c.iloc[:, 0]
                c = pd.to_numeric(c, errors="coerce").dropna()
                if len(c) > 2000:
                    return c, t
            except Exception:
                pass
            time.sleep(2)
    return None, None


def rolling_percentile(close, window=1260):
    """滚动计算：当前价在近 window 天中的分位（0~100）。"""
    result = pd.Series(index=close.index, dtype=float)
    arr = close.values
    for i in range(window, len(close)):
        win = arr[i - window:i]
        result.iloc[i] = (arr[i] <= win).mean() * 100
    return result


def calc_rsi(close, window=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(window).mean() / loss.rolling(window).mean()
    return 100 - 100 / (1 + rs)


def bin_stats(signal, fwd, bins, name):
    """把信号分成 bins 档，统计每档未来收益。"""
    print(f"\n--- {name} ---")
    print(f"{'区间':<24}{'样本':>7}{'未来60日均收益':>15}{'未来120日均收益':>16}")
    for i in range(len(bins) - 1):
        lo, hi = bins[i], bins[i + 1]
        mask = (signal >= lo) & (signal < hi) if i < len(bins) - 2 else (signal >= lo)
        if mask.sum() < 50:
            continue
        f60 = fwd["fwd60"][mask].mean() * 100
        f120 = fwd["fwd120"][mask].mean() * 100
        print(f"  {lo:>6.1f} ~ {hi:<6.1f}  {mask.sum():>7d}  {f60:>+12.2f}%  {f120:>+13.2f}%")


def main():
    close, ticker = load_close()
    if close is None:
        print("数据加载失败")
        return
    print(f"数据源: {ticker}, {len(close)} 交易日, {close.index[0].date()} ~ {close.index[-1].date()}")

    print(">>> 计算信号 ...")
    pct_5y = rolling_percentile(close, 1260)   # 估值分位
    mom250 = close.pct_change(250)              # 250日动量
    rsi = calc_rsi(close, 14)                   # RSI

    fwd = pd.DataFrame({
        "fwd60": close.shift(-60) / close - 1,
        "fwd120": close.shift(-120) / close - 1,
    })

    # 1. 估值分位标定
    bin_stats(pct_5y, fwd, [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100], "估值分位（近5年）")

    # 2. 250日动量标定
    bin_stats(mom250, fwd, [-1.0, -0.5, -0.2, -0.1, 0, 0.1, 0.2, 0.5, 1.0, 5.0], "250日动量")

    # 3. RSI 标定（验证 30/70）
    bin_stats(rsi, fwd, [0, 20, 30, 40, 50, 60, 70, 80, 100], "RSI(14)")


if __name__ == "__main__":
    main()
