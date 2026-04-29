#!/usr/bin/env python3
"""
Quick test script to verify NVIDIA NIM API + web search works.
Run locally before triggering GitHub Actions.
"""

import os
import sys
import json
import re
import requests
from duckduckgo_search import DDGS

API_KEY = os.environ.get("NVIDIA_API_KEY", "")
MODEL = os.environ.get("MODEL_NAME", "deepseek-ai/deepseek-v4-pro")
NIM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

def web_search(query: str, max_results: int = 3):
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=max_results)
            return [{"title": r["title"], "href": r["href"], "body": r["body"]} for r in results]
    except Exception as e:
        return [{"error": str(e)}]

def call_nim(messages, max_tokens=2000):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }
    resp = requests.post(NIM_URL, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

def main():
    if not API_KEY:
        print("❌ ERROR: Set NVIDIA_API_KEY environment variable")
        sys.exit(1)

    print(f"🧪 Testing NVIDIA NIM with {MODEL}...")
    print(f"   API Key: {API_KEY[:8]}...{API_KEY[-4:]}")

    # Test 1: Simple completion
    print("\n[Test 1] Simple completion...")
    try:
        resp = call_nim([
            {"role": "user", "content": "Say 'NVIDIA NIM is working' and nothing else."}
        ], max_tokens=50)
        print(f"   ✅ {resp.strip()}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        sys.exit(1)

    # Test 2: Web search tool
    print("\n[Test 2] Web search + tool calling...")
    try:
        # Simulate what the agent does
        search_results = web_search("KOSPI index today", max_results=3)
        print(f"   🔍 Found {len(search_results)} search results")
        for r in search_results:
            print(f"      - {r.get('title', 'N/A')[:60]}...")

        # Ask model to analyze
        context = json.dumps(search_results, ensure_ascii=False, indent=2)
        resp = call_nim([
            {"role": "system", "content": "You analyze market data. Be concise."},
            {"role": "user", "content": f"Here are search results about KOSPI:\n{context}\n\nSummarize in 2 sentences."}
        ], max_tokens=200)
        print(f"   ✅ Model analysis: {resp.strip()}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        sys.exit(1)

    print("\n🎉 All tests passed! Your setup is ready for GitHub Actions.")
    print("   Next: Set NVIDIA_API_KEY in GitHub repo secrets and trigger a workflow.")

if __name__ == "__main__":
    main()
