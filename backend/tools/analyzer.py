import os
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

# Explicitly load .env from project root
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GROQ_API_KEY")


if not api_key:
    raise RuntimeError("❌ GROQ_API_KEY is not set. Check your .env file.")

client = Groq(api_key=api_key)

_ANALYSIS_PROMPT = """
Act as a Consumer Protection AI. Analyze this Terms of Service / Privacy Policy.
Extract harmful clauses. Output ONLY a valid JSON object with no markdown.

Required JSON format:
{
  "score": <int 0-100>,
  "grade": "<A, B, C, D, or F>",
  "summary": "<1 sentence summary>",
  "findings": [
    {
      "category": "<Privacy|Legal|Financial|Data>",
      "severity": "<Critical|High|Medium|Low>",
      "finding": "<Plain English explanation>"
    }
  ]
}

Text to analyze:
{text}
"""

def analyze_legal_text(markdown: str) -> dict:
    prompt = _ANALYSIS_PROMPT.format(text=markdown)

    response = client.chat.completions.create(
        model="deepseek-r1-distill-llama-70b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    raw_text = response.choices[0].message.content

    # Remove <think> tags
    clean_text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()

    # Remove markdown fences
    clean_text = clean_text.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(clean_text)
    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON from LLM: {clean_text[:300]}")

    return parsed