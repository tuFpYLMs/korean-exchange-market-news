# KRX Morning Brief Prompt

## Overview
Generates the PRO KRX Morning Intelligence Brief for the next trading day in Seoul (KST).

## Schedule
- **Cron:** `0 23 * * *` (23:00 UTC = 08:00 KST next day)
- **Trigger:** GitHub Actions scheduled workflow
- **Model:** `deepseek-ai/deepseek-v4-pro` via NVIDIA NIM API

## Tasks

### 1. Gather Overnight Market Data (Web Search)
Search for the following data points relevant to Korea:

- **US Equities:** S&P500, Nasdaq, Russell 2000 closes
- **Semiconductors:** SOX (Philadelphia Semiconductor Index)
- **AI Stocks:** Nvidia and major AI stocks performance
- **Bonds:** US Treasury yields (10Y, 2Y)
- **FX:** DXY (USD Index), USDKRW rate
- **Commodities:** Oil, LNG, Copper prices
- **China:** CSI 300, Hang Seng
- **Japan:** Nikkei 225
- **Policy:** Any Fed/BOJ/PBOC comments or policy news
- **Geopolitics:** Developments affecting markets

### 2. Gather Korea-Specific News (Web Search)
Search for:

- KRX opening expectations / pre-market sentiment
- Foreign investor flow trends
- Institution and retail behavior signals
- Government policy announcements
- Export/import data releases
- BOK (Bank of Korea) policy signals
- CPI/inflation data
- Major earnings releases (Samsung, SK Hynix, Hyundai, LG, Naver, Kakao, etc.)
- Regulatory changes
- Domestic headlines from Korean financial news (Korean Economic Daily, Maeil Business, Chosun Ilbo business, etc.)

### 3. Generate Brief Format

```
📈 PRO KRX Morning Brief | {DATE} | 8:00 AM KST

## 1. Opening Call
- Expected Open: Bullish / Neutral / Bearish
- Gap Estimate
- Confidence: 1–10
- Main catalyst:

## 2. Market Regime Today
(Trend Day Up / Trend Day Down / Range Day / Reversal Day / News Volatility Day)

## 3. Foreign Money Flow Radar
- Foreigners: Net Buy / Sell Likely
- Institutions: Buy / Sell Likely
- Retail: Chasing / Defensive

## 4. Sector Heatmap (Rank Top Opportunities)
🔥 Strongest Likely:
❄ Weakest Likely:

## 5. Key Stocks In Play Today
(Samsung Electronics, SK Hynix, Hyundai Motor, LG Energy Solution, Hanwha Aerospace, Naver, Kakao, Posco Holdings, etc.)
For each: Bullish / Bearish / Watch + Why

## 6. Macro Risk Dashboard
Score 1–10 each: FX Risk, Yield Risk, China Risk, Geopolitical Risk, Earnings Risk

## 7. Intraday Playbook
(Best tactical approach for the day)

## 8. Key Levels
KOSPI support/resistance, KOSDAQ support/resistance, USDKRW key zone

## 9. Today's Edge (Most Important)
One concise paragraph on what likely happens and how to trade it.

## BONUS EDGE (when confidence high)
🎯 Highest Probability Trade Today
⚠ Avoid
```

### 4. Commit to GitHub
Save the brief as `briefs/YYYY-MM-DD.md` in the repo and push to `main`.

## Rules
- Only KRX-relevant information
- No generic global news fluff
- Dense, concise, actionable (5-minute read max)
- Think like a professional macro + equity trading desk
- If conviction is low, state it clearly
- Convert all times to KST
- Use overnight data heavily

## Output
- Save to: `briefs/{DATE}.md`
- Commit message: `Morning Brief: {DATE}`
- Do NOT send Telegram messages
