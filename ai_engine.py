"""
AI Response Engine for PESCE Campus Info Bot
=============================================
Uses Groq (primary) and Google Gemini (fallback) LLMs to generate
natural, conversational responses using gathered context from:
  - Local JSON knowledge base
  - Semantic search results
  - Live web-scraped data from pesce.ac.in

The LLM receives PESCE-specific context and the user's question,
then produces a helpful, accurate, college-specific response.
"""

import streamlit as st
import json
import requests
import time

# ==========================================
# API KEY LOADING
# ==========================================
def _get_key(name):
    """Load API key from Streamlit secrets or environment."""
    try:
        return st.secrets.get(name, "")
    except Exception:
        import os
        return os.environ.get(name, "")


# ==========================================
# SYSTEM PROMPT (shared across all LLMs)
# ==========================================
SYSTEM_PROMPT = """You are the official AI assistant for PES College of Engineering (PESCE), Mandya, Karnataka, India.

Your role:
- Answer questions about PESCE accurately using ONLY the provided context data.
- Be friendly, professional, and helpful — like a knowledgeable campus guide.
- If the context contains the answer, provide it clearly with relevant details.
- If the context does NOT contain enough information, say so honestly and suggest contacting admissions@pesce.ac.in or calling +91 94482 82588.
- Format responses with markdown: use **bold** for key facts, bullet points for lists, and emojis sparingly for warmth.
- Keep responses concise but complete (2-4 paragraphs max).
- NEVER fabricate information not present in the context.
- When mentioning departments, use full official names.
- Always be proud of PESCE's heritage (established 1962, autonomous since 2008, NAAC A grade).

CRITICAL DATA FRESHNESS RULES:
- For personnel queries (principal, warden, HOD, faculty, dean, vice principal):
  ALWAYS prefer the "LIVE DATA FROM PESCE WEBSITE" section over the "KNOWLEDGE BASE" section.
  The website data is scraped in real-time and is more current. The knowledge base may have outdated names.
- If the live data and knowledge base conflict on a person's name/role, USE THE LIVE DATA and mention it is from the official website.
- When listing faculty, include ALL names found in the live data with their designations.

Response language: Respond in the same language the user asks in (English, Hindi, or Kannada)."""


# ==========================================
# CONTEXT BUILDER
# ==========================================
def build_context(query, json_data=None, semantic_result=None, scraped_text=None):
    """
    Assembles all available data sources into a single context string
    that the LLM can use to answer the query.
    """
    parts = []

    # 1. Full JSON knowledge base (compact)
    if json_data:
        parts.append("=== PESCE KNOWLEDGE BASE (Static Data — may be outdated for personnel) ===")
        parts.append(json.dumps(json_data, indent=2, ensure_ascii=False))

    # 2. Semantic search result (if available)
    if semantic_result:
        parts.append("\n=== SEMANTIC SEARCH MATCH ===")
        if isinstance(semantic_result, dict):
            parts.append(json.dumps(semantic_result, indent=2, ensure_ascii=False))
        else:
            parts.append(str(semantic_result))

    # 3. Web-scraped content (if available) — MOST AUTHORITATIVE for live data
    if scraped_text:
        parts.append("\n=== LIVE DATA FROM PESCE WEBSITE (pesce.ac.in) — USE THIS FOR PERSONNEL INFO ===")
        parts.append(str(scraped_text)[:5000])  # Increased cap for faculty lists

    return "\n".join(parts)


# ==========================================
# GROQ LLM (Primary — Fast, Free Tier)
# ==========================================
def query_groq(query, context, lang="English"):
    """
    Send query to Groq API (Llama 3.3 70B) for response generation.
    Groq offers extremely fast inference. Retries on 429 rate limiting.
    """
    api_key = _get_key("GROQ_API_KEY")
    if not api_key:
        return None

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Context Data:\n{context}\n\n---\nStudent's Question: {query}\n\nRespond in {lang}."}
    ]

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": 1024,
        "top_p": 0.9,
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=15)
            if resp.status_code == 429:
                wait_time = min(2 ** attempt * 2, 10)  # 2s, 4s, 8s (capped at 10s)
                print(f"[AI Engine] Groq rate limited, retrying in {wait_time}s (attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
                continue
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except requests.exceptions.HTTPError as e:
            if resp.status_code != 429:
                print(f"[AI Engine] Groq API error: {e}")
                return None
        except Exception as e:
            print(f"[AI Engine] Groq API error: {e}")
            return None
    
    print("[AI Engine] Groq: all retries exhausted")
    return None


# ==========================================
# GEMINI LLM (Fallback)
# ==========================================
def query_gemini(query, context, lang="English"):
    """
    Send query to Google Gemini API as a fallback.
    Tries primary key first, then secondary key. Retries on 429.
    """
    keys = [_get_key("GEMINI_API_KEY"), _get_key("GEMINI_API_KEY_2")]
    keys = [k for k in keys if k]  # Filter empty

    if not keys:
        return None

    prompt = f"""{SYSTEM_PROMPT}

Context Data:
{context}

---
Student's Question: {query}

Respond in {lang}."""

    for api_key in keys:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 1024,
                "topP": 0.9
            }
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = requests.post(url, json=payload, timeout=15)
                if resp.status_code == 429:
                    wait_time = min(2 ** attempt * 2, 10)
                    print(f"[AI Engine] Gemini rate limited (key ...{api_key[-6:]}), retrying in {wait_time}s (attempt {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                resp.raise_for_status()
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            except requests.exceptions.HTTPError as e:
                if resp.status_code != 429:
                    print(f"[AI Engine] Gemini API error with key ...{api_key[-6:]}: {e}")
                    break  # Try next key
            except Exception as e:
                print(f"[AI Engine] Gemini API error with key ...{api_key[-6:]}: {e}")
                break  # Try next key
        
        print(f"[AI Engine] Gemini: retries exhausted for key ...{api_key[-6:]}")

    return None


# ==========================================
# SERPAPI WEB SEARCH (Extended Knowledge)
# ==========================================
def search_serpapi(query):
    """
    Search Google via SerpAPI for PESCE-related information.
    Used when local data + scraping aren't sufficient.
    """
    api_key = _get_key("SERPAPI_API_KEY")
    if not api_key:
        return None

    try:
        url = "https://serpapi.com/search.json"
        params = {
            "q": f"PESCE Mandya {query}",
            "api_key": api_key,
            "num": 5,
            "engine": "google"
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # Extract organic results
        results = []
        for item in data.get("organic_results", [])[:3]:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            link = item.get("link", "")
            results.append(f"**{title}**\n{snippet}\n🔗 {link}")

        # Also check answer box
        if "answer_box" in data:
            ab = data["answer_box"]
            answer = ab.get("answer", ab.get("snippet", ""))
            if answer:
                results.insert(0, f"**Quick Answer:** {answer}")

        return "\n\n".join(results) if results else None
    except Exception as e:
        print(f"[AI Engine] SerpAPI error: {e}")
        return None


# ==========================================
# WEATHER FOR MANDYA (Bonus Feature)
# ==========================================
def get_mandya_weather():
    """Fetch current weather in Mandya using Weatherstack API."""
    api_key = _get_key("WEATHERSTACK_API_KEY")
    if not api_key:
        return None

    try:
        url = f"http://api.weatherstack.com/current?access_key={api_key}&query=Mandya,Karnataka,India&units=m"
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        data = resp.json()

        if "current" in data:
            current = data["current"]
            weather_info = {
                "temperature": f"{current.get('temperature', 'N/A')}°C",
                "description": current.get("weather_descriptions", ["N/A"])[0],
                "humidity": f"{current.get('humidity', 'N/A')}%",
                "wind_speed": f"{current.get('wind_speed', 'N/A')} km/h",
                "feels_like": f"{current.get('feelslike', 'N/A')}°C",
            }
            return weather_info
    except Exception as e:
        print(f"[AI Engine] Weather API error: {e}")
    return None


# ==========================================
# MASTER AI RESPONSE FUNCTION
# ==========================================
def generate_ai_response(query, json_data=None, semantic_result=None, scraped_text=None, lang="English"):
    """
    Master function that orchestrates the full AI pipeline:
    1. Build context from all data sources
    2. If query is weather-related, inject live weather
    3. Try Groq LLM first (fast)
    4. Fallback to Gemini if Groq fails
    5. Return (response_text, source_label)
    
    Returns:
        tuple: (ai_response_text, "AI Engine") or (None, None) if all LLMs fail
    """
    # Check if weather-related
    weather_data = None
    q_lower = query.lower()
    if any(w in q_lower for w in ["weather", "climate", "temperature", "rain", "hot", "cold", "mausam"]):
        weather_data = get_mandya_weather()

    # Build unified context
    context = build_context(query, json_data, semantic_result, scraped_text)

    if weather_data:
        context += f"\n\n=== LIVE WEATHER IN MANDYA ===\n{json.dumps(weather_data, indent=2)}"

    # Try Groq first (fastest)
    response = query_groq(query, context, lang)
    if response:
        source = "🤖 AI (Groq Llama 3.3)"
        if weather_data:
            source += " + 🌤️ Live Weather"
        return response, source

    # Fallback to Gemini
    response = query_gemini(query, context, lang)
    if response:
        source = "🤖 AI (Google Gemini)"
        if weather_data:
            source += " + 🌤️ Live Weather"
        return response, source

    return None, None


# ==========================================
# STANDALONE TEST
# ==========================================
if __name__ == "__main__":
    print("=" * 60)
    print("AI Engine - Standalone Test (without Streamlit)")
    print("=" * 60)

    # Test Groq
    test_context = "PESCE is an engineering college in Mandya, established in 1962. It offers B.E., M.Tech, MCA, MBA and Ph.D programs."
    print("\nTesting Groq...")
    result = query_groq("Tell me about PESCE", test_context)
    if result:
        print(f"✅ Groq Response: {result[:200]}...")
    else:
        print("❌ Groq failed")

    print("\nTesting Gemini...")
    result = query_gemini("Tell me about PESCE", test_context)
    if result:
        print(f"✅ Gemini Response: {result[:200]}...")
    else:
        print("❌ Gemini failed")
