"""
All Claude API calls for the Command Agent.
Handles: situation brief (auto), conversational Q&A, multi-turn history.
"""
import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

def get_client():
    return anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL = "claude-sonnet-4-5"
MAX_TOKENS = 1000

SYSTEM_PROMPT = """You are the business intelligence advisor for TIDEPOOL, a glutathione and electrolyte recovery drink mix brand based in Atlanta. Founded January 2026. Two founders: Kolton Green and Cameron Kopp.

You have access to real-time business data provided in each message as a JSON context object. Always ground your answers in the actual numbers provided. Never give generic advice. Never use em dashes.

TIDEPOOL context:
DTC price: $24.99
B2B landed cost: $11.31
Wholesale tiers:
  Starter: 12 bags @ $18.99
  Growth: 18 bags @ $17.49
  Partner: 24 bags @ $15.99
Monthly burn: dynamic from Finance Agent
Production COGS: $9,531.45 (sunk)

Founder personas:
Kolton Green: science/creative/founder story, medically adjacent venues, marketing/branding
Cameron Kopp: relationship/practical/sales, community venues, finances/operations

When answering questions:
- Lead with the most important number
- Be specific: name venues, SKUs, amounts
- Give a recommendation, not just analysis
- Flag anything that requires urgent action
- Keep answers concise — founders are busy"""

BRIEF_PROMPT = """Using the business data in the context JSON, generate a 3-sentence situation brief for the TIDEPOOL founders. This appears at the top of their Command Agent dashboard every morning.

Rules:
- Sentence 1: cash or runway situation (the most urgent financial signal)
- Sentence 2: the most pressing inventory or ops issue
- Sentence 3: the highest-priority sales action to take today

Be direct and specific. Use actual numbers from the data. No filler phrases. No em dashes."""


def generate_situation_brief(data_context: dict) -> str:
    try:
        context_str = json.dumps(data_context, indent=2, default=str)
        message = get_client().messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"{BRIEF_PROMPT}\n\nData context:\n{context_str}",
                }
            ],
        )
        return message.content[0].text.strip()
    except Exception as e:
        return f"Unable to generate brief: {e}"


def chat(question: str, data_context: dict, conversation_history: list) -> str:
    try:
        context_str = json.dumps(data_context, indent=2, default=str)
        messages = []
        for turn in conversation_history:
            messages.append({"role": turn["role"], "content": turn["content"]})
        messages.append(
            {
                "role": "user",
                "content": f"Current business data:\n{context_str}\n\nQuestion: {question}",
            }
        )
        response = get_client().messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"Error generating response: {e}"
