import json
import re

from google.genai import errors, types

from app.agents.summarizer import get_client
from app.core.config import settings
from app.core.story import PRIORITIES, SENTIMENTS, Story

SYSTEM_PROMPT = (
    "You are a news editor. You receive a numbered list of news stories. "
    "For EACH story decide:\n"
    "- priority: Critical ONLY for events happening right now that threaten many lives "
    "or national security (active war or major attack, large disaster, mass-casualty "
    "accident, national emergency). Court verdicts, sentencing, election results and "
    "ongoing investigations are NOT Critical. At most 1 in 5 stories may be Critical. "
    "High (important politics, economy, policy, major crime), "
    "Medium (general news, technology, business and product news, education, and local "
    "civic or infrastructure news such as new public facilities, roads, transport or "
    "council decisions), "
    "Low (sports, entertainment, celebrity, lifestyle, festivals and social events).\n"
    "- sentiment: positive, negative or neutral (the tone of the news itself).\n"
    'Reply ONLY with a JSON array like: '
    '[{"id": 1, "priority": "High", "sentiment": "negative"}]. '
    "Include every story id exactly once."
)


def parse_analysis(text: str) -> dict[int, tuple[str, str]]:
    """Model ka JSON jawab parse karta hai. Ghalat values ko safe default me badalta hai."""
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        data = json.loads(text)
    except ValueError:
        return {}
    if not isinstance(data, list):
        return {}

    result: dict[int, tuple[str, str]] = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("id"))
        except (TypeError, ValueError):
            continue
        priority = str(item.get("priority", "")).strip().capitalize()
        sentiment = str(item.get("sentiment", "")).strip().lower()
        result[idx] = (
            priority if priority in PRIORITIES else "Medium",
            sentiment if sentiment in SENTIMENTS else "neutral",
        )
    return result


def analyze_stories(stories: list[Story], client=None) -> list[Story]:
    """Saari stories ka priority aur sentiment ek hi API call me nikalta hai."""
    if not stories:
        return stories

    client = client or get_client()
    items = "\n".join(f"{i}. {s.title} - {s.summary}" for i, s in enumerate(stories, 1))

    results: dict[int, tuple[str, str]] = {}
    try:
        response = client.models.generate_content(
            model=settings.llm_model,
            contents=items,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0,
                max_output_tokens=2000,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        results = parse_analysis(response.text)
    except errors.APIError as e:
        print(f"[ERROR] Analysis fail: {e}")

    if not results:
        print("[WARN] Analysis result nahi mila, default Medium/neutral lagaya gaya")

    for i, story in enumerate(stories, 1):
        if i in results:
            story.priority, story.sentiment = results[i]
    return stories
