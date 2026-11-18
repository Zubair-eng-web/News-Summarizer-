from google import genai
from google.genai import errors, types

from app.collectors.rss import Article
from app.core.config import settings

SYSTEM_PROMPT = (
    "You are a news summarizer. Summarize the given news item in 2-3 short, "
    "factual sentences. Do not add opinions or information that is not in "
    "the text. If the text is too short, summarize only what is given. "
    "Reply with the summary only."
)


def get_client():
    """One key: a plain genai.Client. Several keys: a client that switches key on quota errors."""
    from app.core import api_keys

    keys = api_keys.candidate_keys()
    if not keys:
        raise ValueError(
            "GEMINI_API_KEY .env file me set nahi hai (ya dashboard ke API Keys page se key add karein)"
        )
    if len(keys) == 1:
        return genai.Client(api_key=keys[0])
    return api_keys.RotatingClient(keys, genai.Client)


def summarize_article(article: Article, client=None) -> str:
    """Ek article ki short summary return karta hai."""
    client = client or get_client()
    content = (
        f"Source: {article.source}\n"
        f"Title: {article.title}\n"
        f"Text: {article.summary[:1500]}"
    )
    try:
        response = client.models.generate_content(
            model=settings.llm_model,
            contents=content,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=300,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        text = (response.text or "").strip()
        return text or article.summary[:200]
    except errors.APIError as e:
        print(f"[ERROR] Summary fail ({article.source}): {e}")
        return article.summary[:200]  # fallback: original text


def summarize_articles(articles: list[Article], client=None) -> list[tuple[Article, str]]:
    client = client or get_client()
    return [(a, summarize_article(a, client)) for a in articles]


if __name__ == "__main__":
    from app.collectors.rss import collect_all

    for article, summary in summarize_articles(collect_all(1)[:3]):
        print(f"[{article.source}] {article.title}")
        print(f"   Summary: {summary}\n")
