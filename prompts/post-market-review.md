# KRX Post-Market Review Prompt

## Overview
Evaluates the morning brief against actual market outcomes after KRX market close.

## Schedule
- **Cron:** `30 6 * * *` (06:30 UTC = 15:30 KST)
- **Trigger:** GitHub Actions scheduled workflow
- **Model:** `deepseek-ai/deepseek-v4-pro` via NVIDIA NIM API

## Critical Rules

1. **NEVER generate a review before KRX market close.** The review can ONLY be produced after 15:30 KST / 06:30 UTC.
2. **NEVER guess, infer, or hallucinate market data.** If you cannot find the actual closing price, foreign flow, or stock performance, mark it 🔮 UNTESTABLE and explain why.
3. **ONLY use data from explicit web sources.** Every number in the review MUST be traceable to a search result or web extraction.
4. **If data is missing, STOP.** Do not fill gaps with assumptions.

## Steps

### Step 1: Run the Strict Date Gate
Execute: `python3 scripts/review_gate.py`
- If output contains `STATUS=BLOCK`, output exactly: `SKIP: {REASON}` as your final response and STOP.
- If output contains `STATUS=PASS`, note BRIEF_PATH, REVIEW_PATH, KST_DATE.

### Step 2: Read the Morning Brief
Use `read_file` to read the brief at BRIEF_PATH.

### Step 3: Gather ACTUAL Market Data (Mandatory Web Search)

**Required searches:**
1. "KOSPI {KST_DATE} close price open high low" — must return exact numbers
2. "KOSDAQ {KST_DATE} close price" — must return exact numbers
3. "KRX foreign investor net buy sell {KST_DATE}" — must return billion KRW figure
4. "KOSPI money flow institutional retail foreign {KST_DATE}" — must return figures
5. "Samsung Electronics 005930 stock price {KST_DATE}" — must return exact close
6. "SK Hynix 000660 stock price {KST_DATE}" — must return exact close
7. "Hyundai Motor 005380 Hanwha Aerospace 012450 POSCO 005490 stock price {KST_DATE}"
8. "Naver 035420 Kakao 035720 stock price {KST_DATE}"
9. "LG Energy Solution 373220 stock price {KST_DATE}"
10. "KOSPI sector performance top losers gainers {KST_DATE}"
11. "USDKRW exchange rate {KST_DATE}"

**If ANY search returns NO specific numbers**, mark that section 🔮 UNTESTABLE. Do not invent figures.

### Step 4: Write the Review (DATA-ONLY)

Create the review at REVIEW_PATH. Every cell must contain either:
- A specific number from searches
- The exact quote from the brief
- A verdict marker (✅/⚠️/❌/🔮)
- "N/A — data not found" (if search yielded nothing)

**Structure:**

```markdown
# 📊 KRX Post-Market Review | {KST_DATE} | Hedge Fund Assessment

**Morning Brief:** briefs/{KST_DATE}.md
**Reviewer:** Hermes Alpha System
**Review Date:** {KST_DATE} 15:30 KST
**Overall Score:** {X}/100 — {Grade}

---

## 1. Executive Summary
[2-3 sentences ONLY. Was the core thesis validated?]

---

## 2. Actual Market Outcomes

### Index Performance
| Index | Open | High | Low | Close | Change % | vs Brief Call |
|-------|------|------|-----|-------|----------|---------------|
| KOSPI | [number or N/A] | [number or N/A] | [number or N/A] | [number or N/A] | [number or N/A] | [✅/⚠️/❌/🔮] |
| KOSDAQ | [number or N/A] | [number or N/A] | [number or N/A] | [number or N/A] | [number or N/A] | [✅/⚠️/❌/🔮] |

### Money Flow (Billion KRW)
| Player | Actual | Brief Prediction | Verdict |
|--------|--------|------------------|---------|
| Foreign | [number or N/A] | [brief quote] | [✅/⚠️/❌/🔮] |
| Institutional | [number or N/A] | [brief quote] | [✅/⚠️/❌/🔮] |
| Retail | [number or N/A] | [brief quote] | [✅/⚠️/❌/🔮] |

### Key Stocks Actual vs Predicted
| Stock | Brief Signal | Actual Close | Actual Change % | Verdict |
|-------|-------------|--------------|-----------------|---------|
| Samsung Electronics | [brief signal] | [number or N/A] | [number or N/A] | [✅/⚠️/❌/🔮] |
| SK Hynix | [brief signal] | [number or N/A] | [number or N/A] | [✅/⚠️/❌/🔮] |
| Hyundai Motor | [brief signal] | [number or N/A] | [number or N/A] | [✅/⚠️/❌/🔮] |
| LG Energy Solution | [brief signal] | [number or N/A] | [number or N/A] | [✅/⚠️/❌/🔮] |
| Hanwha Aerospace | [brief signal] | [number or N/A] | [number or N/A] | [✅/⚠️/❌/🔮] |
| Naver | [brief signal] | [number or N/A] | [number or N/A] | [✅/⚠️/❌/🔮] |
| Kakao | [brief signal] | [number or N/A] | [number or N/A] | [✅/⚠️/❌/🔮] |
| POSCO Holdings | [brief signal] | [number or N/A] | [number or N/A] | [✅/⚠️/❌/🔮] |

### FX
| Metric | Brief Level | Actual | Verdict |
|--------|-------------|--------|---------|
| USDKRW | [brief quote] | [number or N/A] | [✅/⚠️/❌/🔮] |

---

## 3. Prediction-by-Prediction Audit

### Directional Call
- **Brief said:** [exact quote]
- **Actual:** [data from search or "N/A — data not found"]
- **Verdict:** [✅/⚠️/❌/🔮] — [explanation]

[Repeat for each major prediction. If actual data missing, say "Data not found in search results" and verdict 🔮]

---

## 4. What the Brief Got Right
[Bullets with sourced numbers]

---

## 5. What the Brief Got Wrong
[Bullets with sourced numbers — explain WHY]

---

## 6. Missed Opportunities
[What happened that brief missed? Only if data available.]

---

## 7. Grade Breakdown

| Dimension | Weight | Score | Notes |
|-----------|--------|-------|-------|
| Directional Call | 25% | X/100 | ... |
| Sector Rotation | 20% | X/100 | ... |
| Stock Picks | 20% | X/100 | ... |
| Flow Prediction | 15% | X/100 | ... |
| Levels & Timing | 10% | X/100 | ... |
| Macro Context | 10% | X/100 | ... |
| **TOTAL** | **100%** | **X/100** | **...** |

---

## 8. Trader's Takeaway
[1 paragraph]

---

## 9. Data Sources
[List EVERY URL used for actual market data. If a number came from a search result, cite it.]

---

*Review generated at {timestamp} KST*
*Data sources: [list all URLs]*
```

### Step 5: Commit and Push
```bash
git add reviews/{KST_DATE}.md
git commit -m "Post-market review: {KST_DATE} — Score: {X}/100"
git push origin main
```

## Absolute Prohibitions
- ❌ NEVER write a review before 06:30 UTC / 15:30 KST
- ❌ NEVER invent a stock price, index level, or flow number
- ❌ NEVER say "likely" or "probably" in the Actual Market Outcomes section
- ❌ NEVER fill missing data with "estimated" or "approximate" values
- ❌ If data is missing, the review MUST say so explicitly

## Final Check
Before finishing, verify:
1. Every number in Section 2 came from a web_search result
2. No section contains guessed data
3. The date gate script returned STATUS=PASS
4. All sources are listed in Section 9
5. Git push succeeded

If any check fails, output `[SILENT]` and stop.

## Output
- Save to: `reviews/{DATE}.md`
- Commit message: `Post-market review: {DATE} — Score: {X}/100`
