# 黄金市场日报（gold report）

每天自动拉取黄金相关数据，跑五层分析，生成一份 markdown 日报。

## 项目结构

```
D:\gold\
├── main.py           # 主入口：拉数据 → 分析 → 生成报告
├── fetch_data.py     # 数据获取（akshare 国内 + yfinance 国际，带重试容错）
├── analyze.py        # 指标计算 + 五层判断
├── requirements.txt  # 依赖
└── report_YYYY-MM-DD.md  # 每日生成的报告（自动）
```

## 用法

```bash
# 安装依赖（国内建议用镜像）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 运行
python main.py
```

运行后：
- 控制台打印报告
- 同目录生成 `report_2026-11-20.md` 文件

## 数据源

| 数据 | 来源 |
|------|------|
| 国内金价 Au99.99 | akshare（上海黄金交易所） |
| 中国央行黄金储备 | akshare |
| 国际金价 GC=F | yfinance |
| 美元指数 / 美债收益率 / 白银 | yfinance |

> 注意：yfinance 偶发网络抖动（报 "delisted" 或 SSL 错误），脚本已带重试逻辑，多试几次通常能拿到。

## 五层分析逻辑

1. **宏观**：美元指数、美债收益率 → 判断大方向
2. **趋势**：价格 vs MA20/MA50、是否创新低
3. **信号**：RSI 超卖/超买
4. **资金**：央行黄金储备环比
5. **综合**：加权给倾向 + 建议

## 下一步（待开发）

- [ ] 邮件 / 企业微信推送
- [ ] GitHub Actions 定时任务
- [ ] 报告可视化（K 线图）
