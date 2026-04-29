#!/usr/bin/env python3
"""
KRX Post-Market Review Generator — Agent with Web Search
Uses NVIDIA NIM API with DeepSeek V4 Pro/Flash.
Supports multiple models — output files include model slug.
"""

import os
import sys
import json
import re
import subprocess
import requests
from datetime import datetime, timezone, timedelta
from duckduckgo_search import DDGS
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────
MODEL_NAME = os.environ.get("MODEL_NAME", "deepseek-ai/deepseek-v4-pro")
API_KEY = os.environ["NVIDIA_API_KEY"]
NIM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

MODEL_SLUG_MAP = {
    "deepseek-ai/deepseek-v4-pro": "dsv4pro",
    "deepseek-ai/deepseek-v4-flash": "dsv4flash",
}
MODEL_SLUG = MODEL_SLUG_MAP.get(MODEL_NAME, MODEL_NAME.replace("/", "-").replace(".", "")[:12])

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
        headers = {"User-Agent": "Mozilla/5.0 (compatible; KRX-Review-Bot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        text = re.sub(r'<[^>]+>', ' ', resp.text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:8000]
    except Exception as e:
        return f"Error fetching {url}: {e}"

# ── NVIDIA NIM API ────────────────────────────────────────────────

def call_nim(messages: list, max_tokens: int = 12000, temperature: float = 0.2) -> str:
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
    """Run the model with tool-calling loop."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    tools_desc = """
You have access to web_search and web_fetch tools. 

IMPORTANT WORKFLOW:
1. First, call the tools you need by outputting JSON blocks
2. WAIT — I will execute the tools and return results
3. After receiving results, analyze the data and write the final review
4. Do NOT output more tool calls after receiving results — write the review instead

To use a tool, output ONLY a JSON block like this:

```tool
{"tool": "web_search", "query": "your search query"}
```

Available tools:
- web_search(query): Search DuckDuckGo. Returns results with title, URL, snippet.
- web_fetch(url): Fetch webpage content. Returns page text.

After I return tool results, write the final review using that data.
"""

    messages[0]["content"] += "\n\n" + tools_desc

    max_iterations = 12
    for iteration in range(max_iterations):
        print(f"  → Agent iteration {iteration + 1}...")
        response = call_nim(messages, max_tokens=6000, temperature=0.2)

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

    print("  ⚠ Max iterations reached.")
    return response

# ── Main ────────────────────────────────────────────────────────────

def main():
    # Run date gate
    gate_result = subprocess.run(
        ["python3", "scripts/review_gate.py"],
        capture_output=True, text=True
    )

    if gate_result.returncode != 0:
        print(f"SKIP: {gate_result.stdout.strip()}")
        sys.exit(0)

    # Parse gate output
    brief_path = None
    review_path = None
    kst_date = None
    for line in gate_result.stdout.strip().split("\n"):
        if line.startswith("BRIEF_PATH="):
            brief_path = line.split("=", 1)[1]
        elif line.startswith("REVIEW_PATH="):
            review_path = line.split("=", 1)[1]
        elif line.startswith("KST_DATE="):
            kst_date = line.split("=", 1)[1]

    # Adjust review path to include model slug
    if review_path:
        review_path = review_path.replace(".md", f"-{MODEL_SLUG}.md")

    if not brief_path or not os.path.exists(brief_path):
        print(f"SKIP: Brief not found at {brief_path}")
        sys.exit(0)

    # Read brief
    with open(brief_path, "r") as f:
        brief_content = f.read()

    # Read review prompt template
    prompt_path = "prompts/post-market-review.md"
    if not os.path.exists(prompt_path):
        print(f"ERROR: Prompt file not found: {prompt_path}")
        sys.exit(1)

    with open(prompt_path, "r") as f:
        prompt_template = f.read()

    # Build user prompt
    user_prompt = (
        prompt_template +
        f"\n\n---\n**BRIEF_PATH={brief_path}\nREVIEW_PATH={review_path}\nKST_DATE={kst_date}\nMODEL={MODEL_NAME}**\n\n"
        f"MORNING BRIEF CONTENT:\n{brief_content}\n\n"
        "Generate the review now. Use web_search to gather actual market data. STRICTLY verify every number."
    )

    system_prompt = (
        "You are a quantitative trading desk analyst. You evaluate market predictions with strict data discipline. "
        "NEVER hallucinate numbers. If data is missing, mark it UNTESTABLE. "
        "You can use web_search and web_fetch tools to gather actual market data. "
        "Every number must be traceable to a source."
    )

    print(f"🚀 Generating Post-Market Review for {kst_date} using {MODEL_NAME}...")
    print(f"   Brief: {brief_path}")
    print(f"   Review will be saved to: {review_path}")

    review_content = run_agent_with_tools(system_prompt, user_prompt)

    # Check for SKIP
    if review_content.strip().startswith("SKIP:"):
        print(review_content.strip())
        sys.exit(0)

    # Add model metadata header
    review_with_meta = f"""<!--
model: {MODEL_NAME}
model_slug: {MODEL_SLUG}
generated_at: {datetime.now(timezone.utc).isoformat()}
prompt_file: prompts/post-market-review.md
brief_file: {brief_path}
-->

{review_content}
"""

    # Save review
    os.makedirs("reviews", exist_ok=True)
    with open(review_path, "w") as f:
        f.write(review_with_meta)

    print(f"✅ Review saved to {review_path} ({len(review_with_meta)} chars)")
    print(f"   Model: {MODEL_NAME} ({MODEL_SLUG})")

if __name__ == "__main__":
    main()
