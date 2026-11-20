# -*- coding: utf-8 -*-
"""
全面回测：黄金信号的有效性检验

覆盖：
1. 动量信号 × 未来 horizon 的分组收益差（含 t 检验显著性）
2. 分段稳定性（防过拟合：信号是否随时间稳定）
3. RSI 分位数分析（均值回归信号）
4. 250日动量策略的完整回测（累计收益 / 夏普 / 最大回撤）
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


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------

def load_close():
    for t in ("GLD", "GC=F"):
        for i in range(4):
            try:
                df = yf.download(t, period="max", interval="1d", progress=False)
                c = df["Close"]
                if isinstance(c, pd.DataFrame):
                    c = c.iloc[:, 0]
                c = pd.to_numeric(c, errors="coerce").dropna()
                if len(c) > 1000:
                    return c, t
            except Exception:
                pass
            time.sleep(2)
    return None, None


def t_stat(x):
    """均值显著性 t 统计量（|t|>2 大致对应 5% 显著）。"""
    x = x.dropna()
    n = len(x)
    if n < 3:
        return 0.0
    se = x.std(ddof=1) / np.sqrt(n)
    return x.mean() / se if se > 0 else 0.0


def group_diff_t(mom, fwd, sign):
    """正组 vs 负组收益差 + t 检验。"""
    v = mom.notna() & fwd.notna()
    pos = fwd[(mom > 0) & v]
    neg = fwd[(mom < 0) & v]
    if len(pos) < 30 or len(neg) < 30:
        return None, None, None, None, None
    diff = pos.mean() - neg.mean()
    # 合并标准差做 t 检验（近似）
    pooled_se = np.sqrt(pos.var(ddof=1) / len(pos) + neg.var(ddof=1) / len(neg))
    t = diff / pooled_se if pooled_se > 0 else 0.0
    return diff, t, pos.mean(), neg.mean(), (len(pos), len(neg))


def calc_rsi(close, window=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(window).mean() / loss.rolling(window).mean()
    return 100 - 100 / (1 + rs)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    close, ticker = load_close()
    if close is None:
        print("数据加载失败")
        return
    print(f"数据源: {ticker}，{len(close)} 个交易日，{close.index[0].date()} ~ {close.index[-1].date()}\n")

    # ========== Part 1: 动量 × horizon 分组收益差 ==========
    mom_periods = [5, 10, 20, 60, 120, 250]
    horizons = [5, 20, 60, 120, 250]

    print("=" * 92)
    print("【Part 1】动量信号(过去N日涨跌) → 未来M日收益差（正组 - 负组）")
    print("  差值>0=趋势(强者恒强)  差值<0=均值回归(跌多反弹)  t>2 显著")
    print("=" * 92)
    print("信号\\未来".ljust(10) + "".join(f"{'':>4}{m:>4}日{'':>3}" for m in horizons))
    print("-" * 92)

    momentum_cache = {n: close.pct_change(n) for n in mom_periods}
    fwd_cache = {m: close.shift(-m) / close - 1 for m in horizons}

    for n in mom_periods:
        row = f"过去{n:>3}日{'':<3}"
        for m in horizons:
            diff, t, pm, nm, cnt = group_diff_t(momentum_cache[n], fwd_cache[m], n)
            if diff is None:
                row += f"{'--':>12}"
            else:
                star = "★" if abs(t) > 2 else ""
                row += f"  {diff*100:+5.2f}%{star:>2}"
        print(row)
    print("  (★ 表示 t>2，统计显著)\n")

    # ========== Part 2: 分段稳定性 ==========
    print("=" * 92)
    print("【Part 2】分段稳定性：核心信号(250日动量→未来120日) 在各时间段的差值")
    print("  如果各段差值同号且接近 → 信号稳健；忽正忽负 → 过拟合/不稳定")
    print("=" * 92)
    mom250 = momentum_cache[250]
    fwd120 = fwd_cache[120]
    valid = mom250.notna() & fwd120.notna()
    idx = close.index[valid]
    mv = mom250[valid].values
    fv = fwd120[valid].values
    n_total = len(mv)
    n_split = 6
    chunk = n_total // n_split
    for i in range(n_split):
        a = i * chunk
        b = (i + 1) * chunk if i < n_split - 1 else n_total
        pos = fv[a:b][mv[a:b] > 0]
        neg = fv[a:b][mv[a:b] < 0]
        d = pos.mean() - neg.mean() if len(pos) and len(neg) else float("nan")
        print(f"  段{i+1} ({idx[a].date()}~{idx[b-1].date()})  正组{len(pos):4d}  负组{len(neg):4d}  差值{d*100:+5.2f}%")
    print()

    # ========== Part 3: RSI 分位数 ==========
    print("=" * 92)
    print("【Part 3】RSI(14) 分位数 → 未来收益（检验均值回归强度）")
    print("=" * 92)
    rsi = calc_rsi(close, 14)
    fwd20 = fwd_cache[20]
    v = rsi.notna() & fwd20.notna()
    r = rsi[v].values
    f = fwd20[v].values
    quantiles = [0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9, 1.0]
    print(f"  {'RSI区间':<16}{'样本':>6}{'未来20日均收益':>16}{'未来60日均收益':>16}")
    fwd60 = fwd_cache[60]
    f60 = fwd60[v].values
    for i in range(len(quantiles) - 1):
        lo, hi = np.quantile(r, quantiles[i]), np.quantile(r, quantiles[i+1])
        mask = (r >= lo) & (r < hi) if i < len(quantiles) - 2 else (r >= lo)
        if mask.sum() < 30:
            continue
        m20 = f[mask].mean() * 100
        m60 = f60[mask].mean() * 100
        print(f"  RSI {lo:>5.1f}~{hi:>5.1f}{mask.sum():>6d}{m20:>+14.2f}%{m60:>+14.2f}%")
    print()

    # ========== Part 4: 250日动量策略回测 ==========
    print("=" * 92)
    print("【Part 4】策略回测：250日动量 >0 持有 / <0 空仓（未来20日滚动再平衡）")
    print("=" * 92)
    mom250s = momentum_cache[250]
    # 信号：250日动量 > 0 持有（做多），< 0 空仓
    signal = (mom250s > 0).astype(float)
    signal = signal.shift(1)  # 避免前视偏差，用昨天的信号决定今天
    daily_ret = close.pct_change()
    strat_ret = (signal * daily_ret).dropna()
    bench_ret = daily_ret.reindex(strat_ret.index).dropna()

    def sharpe(r):
        return r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else 0.0

    def max_drawdown(r):
        cum = (1 + r).cumprod()
        dd = cum / cum.cummax() - 1
        return dd.min()

    print(f"  策略年化收益: {strat_ret.mean()*252*100:+.2f}%")
    print(f"  基准(买入持有)年化: {bench_ret.mean()*252*100:+.2f}%")
    print(f"  策略夏普: {sharpe(strat_ret):.2f}   基准夏普: {sharpe(bench_ret):.2f}")
    print(f"  策略最大回撤: {max_drawdown(strat_ret)*100:.1f}%   基准最大回撤: {max_drawdown(bench_ret)*100:.1f}%")
    print(f"  参与市场时间比例(信号>0): {signal.mean()*100:.1f}%")
    print(f"  累计收益 策略: {((1+strat_ret).cumprod().iloc[-1]-1)*100:+.0f}%  基准: {((1+bench_ret).cumprod().iloc[-1]-1)*100:+.0f}%")


if __name__ == "__main__":
    main()
