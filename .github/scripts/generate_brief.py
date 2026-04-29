#!/usr/bin/env python3
"""
KRX Morning Brief Generator — Agent with Web Search
Uses NVIDIA NIM API with DeepSeek V4 Pro/Flash.
Supports multiple models — output files include model slug.
"""

import os
import sys
import json
import re
import requests
from datetime import datetime, timezone, timedelta
from duckduckgo_search import DDGS
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────
MODEL_NAME = os.environ.get("MODEL_NAME", "deepseek-ai/deepseek-v4-pro")
API_KEY = os.environ["NVIDIA_API_KEY"]
NIM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

# Derive a short slug from model name for filenames
# e.g. "deepseek-ai/deepseek-v4-pro" → "dsv4pro"
MODEL_SLUG_MAP = {
    "deepseek-ai/deepseek-v4-pro": "dsv4pro",
    "deepseek-ai/deepseek-v4-flash": "dsv4flash",
}
MODEL_SLUG = MODEL_SLUG_MAP.get(MODEL_NAME, MODEL_NAME.replace("/", "-").replace(".", "")[:12])

# KRX 2026 holidays
KRX_HOLIDAYS = {
    "2026-01-01", "2026-01-02",
    "2026-02-16", "2026-02-17", "2026-02-18",
    "2026-03-01", "2026-05-01", "2026-05-05",
    "2026-06-06", "2026-08-15",
    "2026-09-28", "2026-09-29", "2026-09-30",
    "2026-10-03", "2026-10-05",
    "2026-12-25", "2026-12-31",
}

# ── Web Search Tool ─────────────────────────────────────────────────

def web_search(query: str, max_results: int = 5) -> list:
    """Search the web using DuckDuckGo."""
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=max_results)
            return [
                {"title": r["title"], "href": r["href"], "body": r["body"]}
                for r in results
            ]
    except Exception as e:
        return [{"error": str(e), "query": query}]

def web_fetch(url: str) -> str:
    """Fetch a webpage and return text content."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; KRX-Brief-Bot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        # Simple HTML-to-text (could use BeautifulSoup for better parsing)
        text = re.sub(r'<[^>]+>', ' ', resp.text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:8000]  # Limit length
    except Exception as e:
        return f"Error fetching {url}: {e}"

# ── NVIDIA NIM API ────────────────────────────────────────────────

def call_nim(messages: list, max_tokens: int = 8000, temperature: float = 0.3) -> str:
    """Call NVIDIA NIM chat completions API with retry."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    
    # Retry on errors (NIM sometimes has transient issues or connection resets)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"   → Calling NIM (attempt {attempt + 1}/{max_retries}, max_tokens={max_tokens})...")
            resp = requests.post(NIM_URL, headers=headers, json=payload, timeout=120)
            if resp.status_code in (500, 502, 503) and attempt < max_retries - 1:
                print(f"   ⚠ NIM returned {resp.status_code}, retrying...")
                import time
                time.sleep(10 * (attempt + 1))
                continue
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as e:
            status = getattr(getattr(e, 'response', None), 'status_code', 'ConnectionError')
            print(f"   ⚠ Error: {status}, retrying...")
            if attempt < max_retries - 1:
                import time
                time.sleep(10 * (attempt + 1))
                continue
            raise
    raise RuntimeError("Max retries exceeded for NIM API call")

# ── Agent Loop ──────────────────────────────────────────────────────

def run_agent_with_tools(system_prompt: str, user_prompt: str) -> str:
    """
    Run the model with tool-calling loop.
    The model can request web_search or web_fetch.
    We execute the tools and feed results back.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    # Tool definitions for the model
    tools_desc = """
You have access to web_search and web_fetch tools. 

IMPORTANT WORKFLOW:
1. First, call the tools you need by outputting JSON blocks
2. WAIT — I will execute the tools and return results
3. After receiving results, analyze the data and write the final brief
4. Do NOT output more tool calls after receiving results — write the brief instead

To use a tool, output ONLY a JSON block like this:

```tool
{"tool": "web_search", "query": "your search query"}
```

Available tools:
- web_search(query): Search DuckDuckGo. Returns results with title, URL, snippet.
- web_fetch(url): Fetch webpage content. Returns page text.

After I return tool results, write the final brief using that data.
"""

    # Add tools description to system prompt
    messages[0]["content"] += "\n\n" + tools_desc

    max_iterations = 12
    for iteration in range(max_iterations):
        print(f"  → Agent iteration {iteration + 1}...")
        response = call_nim(messages, max_tokens=4000, temperature=0.3)

        # Check if model wants to use tools — find ALL tool blocks
        tool_matches = re.findall(r'```tool\s*\n(\{.*?\})\n\s*```', response, re.DOTALL)
        if not tool_matches:
            # No tool call — this is the final output
            print("  ✓ Final response received (no more tool calls)")
            return response

        print(f"  🔧 Found {len(tool_matches)} tool call(s)")

        # Execute all tool calls
        tool_results = []
        for tool_json in tool_matches:
            try:
                tool_call = json.loads(tool_json)
            except json.JSONDecodeError:
                tool_results.append({"error": "Invalid JSON", "raw": tool_json})
                continue

            tool_name = tool_call.get("tool")
            print(f"     → Executing: {tool_name}")

            if tool_name == "web_search":
                query = tool_call.get("query", "")
                results = web_search(query)
                tool_results.append({"tool": tool_name, "query": query, "results": results})
            elif tool_name == "web_fetch":
                url = tool_call.get("url", "")
                content = web_fetch(url)
                tool_results.append({"tool": tool_name, "url": url, "content": content[:4000]})
            else:
                tool_results.append({"error": f"Unknown tool: {tool_name}"})

        # Add assistant message + all tool results to conversation
        messages.append({"role": "assistant", "content": response})
        combined_results = json.dumps(tool_results, ensure_ascii=False, indent=2)
        messages.append({"role": "user", "content": f"Tool results:\n{combined_results}\n\nContinue your analysis using the above data."})

    print("  ⚠ Max iterations reached. Returning last response.")
    return response

# ── Main ────────────────────────────────────────────────────────────

def main():
    # Get KST date (next trading day)
    kst_now = datetime.now(timezone.utc) + timedelta(hours=9)
    kst_date = kst_now.strftime("%Y-%m-%d")
    kst_weekday = kst_now.weekday()

    # Skip weekends and holidays
    if kst_weekday >= 5:
        print(f"SKIP: Weekend ({kst_date})")
        sys.exit(0)
    if kst_date in KRX_HOLIDAYS:
        print(f"SKIP: Holiday ({kst_date})")
        sys.exit(0)

    # Read the prompt template
    prompt_path = "prompts/morning-brief.md"
    if not os.path.exists(prompt_path):
        print(f"ERROR: Prompt file not found: {prompt_path}")
        sys.exit(1)

    with open(prompt_path, "r") as f:
        prompt_template = f.read()

    # Build user prompt with date context
    user_prompt = prompt_template + f"\n\n---\n**Today's date (KST):** {kst_date}\n**Target trading day:** {kst_date}\n**Model:** {MODEL_NAME}\n\nGenerate the brief now. Use web_search to gather current data."

    system_prompt = (
        "You are a professional macro and equity trading desk analyst specializing in the Korean stock market (KRX). "
        "Generate dense, actionable market intelligence briefs. "
        "You can use web_search and web_fetch tools to gather real-time data. "
        "Always cite your sources. Be concise and data-driven."
    )

    print(f"🚀 Generating Morning Brief for {kst_date} using {MODEL_NAME}...")
    brief_content = run_agent_with_tools(system_prompt, user_prompt)

    # Add model metadata header
    brief_with_meta = f"""<!--
model: {MODEL_NAME}
model_slug: {MODEL_SLUG}
generated_at: {datetime.now(timezone.utc).isoformat()}
prompt_file: prompts/morning-brief.md
-->

{brief_content}
"""

    # Save brief with model-specific filename
    os.makedirs("briefs", exist_ok=True)
    brief_path = f"briefs/{kst_date}-{MODEL_SLUG}.md"
    with open(brief_path, "w") as f:
        f.write(brief_with_meta)

    print(f"✅ Brief saved to {brief_path} ({len(brief_with_meta)} chars)")
    print(f"   Model: {MODEL_NAME} ({MODEL_SLUG})")

if __name__ == "__main__":
    main()
