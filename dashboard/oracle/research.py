"""AI Research and Research Chat pages (existing /research, /research/web, /chat, plus /related)."""
import streamlit as st

from dashboard import api_client, utils
from dashboard.oracle import components as ui
from dashboard.oracle import data, logic

DEFAULT_SUGGESTED = [
    "What are the critical stories today?",
    "Aaj ki sabse badi khabar kya hai?",
]


def research() -> None:
    ui.page_header("AI Research", "Multi-step research with citations and web verification.")
    topic = st.text_input("Topic", placeholder="Egypt train collision", key="research_topic")
    if st.button("Run research", key="research_go"):
        if len(topic.strip()) < 3:
            st.warning("Write at least 3 characters.")
        else:
            try:
                with st.spinner("Researching (10-30 seconds)..."):
                    st.session_state.research_result = api_client.research(topic.strip())
            except api_client.ApiError as e:
                st.warning(f"Research failed: {e}")
    result = st.session_state.get("research_result")
    if result:
        coverage = result.get("coverage", [])
        st.caption("Sub-questions: " + " | ".join(f"{c['question']} ({c['hits']})" for c in coverage))
        followups = [c for c in coverage if c.get("followup")]
        if followups:
            st.caption("Follow-up searches: " + " | ".join(
                f"{c['question']} -> {c['followup']}" for c in followups))
        main, not_covered = logic.split_report(result["report"])
        with st.container(key="card_report"):
            st.markdown(utils.md_safe(main))
        if not_covered:
            with st.container(key="card_not_covered"):
                st.markdown(utils.md_safe(not_covered))
        ui.render_sources(result.get("sources"))
        st.download_button("Download report (.md)", logic.research_markdown(result),
                           file_name="oracle_research.md", key="research_dl")
        web = result.get("web")
        if web:
            st.markdown("**Web sources**")
            st.markdown(utils.md_safe(web["answer"]))
            for s in web.get("sources", []):
                st.markdown("- " + utils.link_markdown(s["title"], s["link"]))

    st.divider()
    st.markdown("### Web verification")
    st.caption("Checks a claim with Google Search (uses Gemini quota, needs a billed key).")
    text = st.text_input("Claim or topic", key="web_text")
    if st.button("Check on the web", key="web_go"):
        if len(text.strip()) < 3:
            st.warning("Write at least 3 characters.")
        else:
            try:
                with st.spinner("Searching the web..."):
                    st.session_state.web_result = api_client.web_check(text.strip())
            except api_client.ApiError as e:
                st.warning(f"Web check failed: {e}")
    web_result = st.session_state.get("web_result")
    if web_result:
        st.markdown(utils.md_safe(web_result["answer"]))
        for s in web_result.get("sources", []):
            st.markdown("- " + utils.link_markdown(s["title"], s["link"]))


def _suggestions() -> list[str]:
    items = list(DEFAULT_SUGGESTED)
    try:
        critical = data.stories(2, "Critical")
    except api_client.ApiError:
        critical = []
    if critical:
        items.append("Tell me more: " + critical[0]["title"][:90])
    return items


def _related(question: str, result: dict) -> tuple[list, list]:
    """Related articles (not already cited) and videos. Skipped when the answer was a refusal."""
    if not result.get("sources"):
        return [], []
    try:
        found = api_client.related(result.get("query") or question)
    except api_client.ApiError:
        return [], []
    cited = {x["link"] for s in result["sources"] for x in s.get("sources", [])}
    articles = [a for a in found.get("articles", [])
                if not any(x["link"] in cited for x in a.get("sources", []))]
    return articles, found.get("videos", [])


def _extras(m: dict) -> None:
    ui.render_sources(m.get("sources"))
    if not m.get("sources") and not m.get("failed"):
        st.info("The collected news does not support an answer to this question.")
    if m.get("related"):
        with st.expander("Related articles"):
            for a in m["related"]:
                st.markdown("- **" + utils.md_safe(a["title"]) + "**  \n"
                            + utils.sources_markdown(a.get("sources", [])))
    if m.get("videos"):
        with st.expander("Related videos"):
            for v in m["videos"]:
                st.markdown("- " + utils.link_markdown(v["title"], v["link"])
                            + f" ({utils.md_safe(v.get('channel', ''))})")


def chat() -> None:
    ui.page_header("Research Chat", "Ask about collected news in English or Roman Urdu.")
    st.session_state.setdefault("messages", [])
    messages = st.session_state.messages
    if not messages:
        st.caption("Suggested questions")
        options = _suggestions()
        for i, (col, q) in enumerate(zip(st.columns(len(options)), options)):
            if col.button(q, key=f"sugg_{i}"):
                st.session_state["chat_pending"] = q
                st.rerun()
    for m in messages:
        with st.chat_message(m["role"]):
            st.markdown(utils.md_safe(m["content"]))
            if m["role"] == "assistant":
                _extras(m)
    if messages:
        st.download_button("Download chat (.md)", logic.chat_markdown(messages),
                           file_name="oracle_chat.md", key="chat_dl")
    typed = st.chat_input("Ask about the news...")
    question = typed or st.session_state.pop("chat_pending", None)
    if not question:
        return
    messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(utils.md_safe(question))
    with st.chat_message("assistant"):
        reply = {"role": "assistant", "content": "", "sources": [], "related": [],
                 "videos": [], "failed": False}
        try:
            with st.spinner("Searching the news..."):
                result = api_client.ask(question)
            reply["content"] = result["answer"]
            reply["sources"] = result.get("sources", [])
            reply["related"], reply["videos"] = _related(question, result)
        except api_client.ApiError as e:
            reply["content"], reply["failed"] = f"Could not answer: {e}", True
        st.markdown(utils.md_safe(reply["content"]))
        _extras(reply)
    messages.append(reply)