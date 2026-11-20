# -*- coding: utf-8 -*-
"""
回测标定模块

目的：用历史数据验证「信号 → 未来收益」的关系，用历史频率标定概率，而非拍脑袋。
方法：时间序列动量 + 均线 + RSI 信号，统计「未来 20 日收益」的历史频率。
防过拟合：分段稳定性验证（前 50% vs 后 50%，以及滚动 5 段）。

依据（权威文献）：
- 时间序列动量：Moskowitz/Ooi/Pedersen (2012, JFE)、Hurst et al. (2017, JPM)
- 点位预测难打败随机游走 → 本模块只做「方向 + 概率」，不预测点位
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

HORIZON = 20  # 未来多少个交易日


# ---------------------------------------------------------------------------
# 数据加载
# ---------------------------------------------------------------------------

def _extract_close(df):
    try:
        s = df["Close"]
    except KeyError:
        if isinstance(df.columns, pd.MultiIndex):
            s = df.xs("Close", axis=1, level=0)
        else:
            return None
    if isinstance(s, pd.DataFrame):
        s = s.iloc[:, 0]
    return pd.to_numeric(s, errors="coerce").dropna()


def load_gold_data(min_bars=1000):
    """加载尽量长的黄金日线。优先 GLD（2004至今，数据最全）。"""
    for ticker in ("GLD", "GC=F"):
        for attempt in range(3):
            try:
                df = yf.download(ticker, period="max", interval="1d", progress=False)
                close = _extract_close(df)
                if close is not None and len(close) > min_bars:
                    return close, ticker
            except Exception:
                pass
            time.sleep(2)
    return None, None


# ---------------------------------------------------------------------------
# 信号计算
# ---------------------------------------------------------------------------

def calc_rsi(close, window=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def compute_signals(close):
    """计算技术信号 + 未来收益标签。"""
    sig = pd.DataFrame(index=close.index)
    sig["close"] = close
    sig["ma20"] = close.rolling(20).mean()
    sig["ma50"] = close.rolling(50).mean()
    sig["ma200"] = close.rolling(200).mean()
    sig["mom20"] = close.pct_change(20)
    sig["mom60"] = close.pct_change(60)
    sig["mom120"] = close.pct_change(120)
    sig["rsi"] = calc_rsi(close, 14)
    # 未来 HORIZON 日收益（标签）
    sig["fwd"] = close.shift(-HORIZON) / close - 1
    return sig


def build_score(sig):
    """复现 analyze.py 的 score 打分逻辑（技术部分），保持一致性。"""
    p = sig["close"]
    m20 = sig["ma20"]
    m50 = sig["ma50"]
    m200 = sig["ma200"]
    score = pd.Series(0.0, index=sig.index)

    bearish = (p < m20) & (m20 < m50)   # 空头排列
    bullish = (p > m20) & (m20 > m50)   # 多头排列
    below20 = (p < m20) & ~bearish
    above20 = (p > m20) & ~bullish

    score[bearish] = -3
    score[bullish] = 3
    score[below20] = -2
    score[above20] = 2

    v200 = m200.notna()
    score[v200 & (p < m200)] -= 1
    score[v200 & (p > m200)] += 1

    vrsi = sig["rsi"].notna()
    score[vrsi & (sig["rsi"] < 30)] += 1
    score[vrsi & (sig["rsi"] > 70)] -= 1

    return score


# ---------------------------------------------------------------------------
# 回测 + 概率标定
# ---------------------------------------------------------------------------

def calibrate(sig, score):
    """按 score 分组，统计未来收益的历史频率。"""
    df = pd.DataFrame({"score": score, "fwd": sig["fwd"]})
    df = df.dropna(subset=["fwd"])

    table = df.groupby("score")["fwd"].agg(
        样本数="count",
        上涨概率="mean",  # 占位，下面替换
        平均收益="mean",
        中位收益="median",
    )
    table["上涨概率"] = df.groupby("score")["fwd"].apply(lambda x: (x > 0).mean())
    return df, table


def stability_check(df, n_splits=5):
    """分段稳定性验证：把历史切成 n 段，看每段「score=-3 时上涨概率」是否稳定。"""
    df = df.dropna(subset=["fwd"]).sort_index()
    rows = []
    chunk = len(df) // n_splits
    for i in range(n_splits):
        sub = df.iloc[i * chunk:(i + 1) * chunk]
        if sub.empty:
            continue
        neg = sub[sub["score"] < 0]
        pos = sub[sub["score"] > 0]
        rows.append({
            "分段": i + 1,
            "起始日期": str(sub.index[0].date()),
            "样本数": len(sub),
            "空头score上涨概率": (neg["fwd"] > 0).mean() if len(neg) else None,
            "多头score上涨概率": (pos["fwd"] > 0).mean() if len(pos) else None,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    print(">>> 加载历史黄金数据 ...")
    close, ticker = load_gold_data()
    if close is None:
        print("[错误] 无法加载黄金数据")
        return
    print(f">>> 数据源: {ticker}，{len(close)} 个交易日，{close.index[0].date()} ~ {close.index[-1].date()}")

    print(">>> 计算信号 ...")
    sig = compute_signals(close)
    score = build_score(sig)

    print(f">>> 回测（未来 {HORIZON} 日收益）...")
    df, table = calibrate(sig, score)

    print("\n" + "=" * 70)
    print(f"【概率标定表】score → 未来{HORIZON}日收益（{ticker}）")
    print("=" * 70)
    for s, row in table.iterrows():
        print(f"  score={s:+.0f}  样本={int(row['样本数']):4d}  上涨概率={row['上涨概率']*100:5.1f}%  "
              f"平均收益={row['平均收益']*100:+.2f}%  中位={row['中位收益']*100:+.2f}%")

    print("\n" + "=" * 70)
    print(f"【分段稳定性验证】（前到后 {5} 段）")
    print("=" * 70)
    stab = stability_check(df, n_splits=5)
    for _, row in stab.iterrows():
        neg = row["空头score上涨概率"]
        pos = row["多头score上涨概率"]
        neg_s = f"{neg*100:.1f}%" if neg is not None else "无样本"
        pos_s = f"{pos*100:.1f}%" if pos is not None else "无样本"
        print(f"  分段{int(row['分段'])} ({row['起始日期']})  样本={int(row['样本数'])}  "
              f"空头上涨={neg_s}  多头上涨={pos_s}")

    # 总体统计
    overall = df["fwd"]
    print("\n" + "=" * 70)
    print("【基准】")
    print("=" * 70)
    print(f"  无信号随机持有 {HORIZON} 日的上涨概率: {(overall > 0).mean()*100:.1f}%")
    print(f"  平均收益: {overall.mean()*100:+.2f}%")
    neg_all = df[df["score"] < 0]["fwd"]
    pos_all = df[df["score"] > 0]["fwd"]
    print(f"  score<0 时上涨概率: {(neg_all > 0).mean()*100:.1f}%（样本 {len(neg_all)}）")
    print(f"  score>0 时上涨概率: {(pos_all > 0).mean()*100:.1f}%（样本 {len(pos_all)}）")


if __name__ == "__main__":
    main()
