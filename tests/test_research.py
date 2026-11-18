from types import SimpleNamespace


from app.agents.research import (
    NO_INFO,
    Doc,
    answer_question,
    load_documents,
    retrieve,
    rewrite_query,
)

DOCS = [
    Doc(
        "Bank of England lifts rate",
        "Bank of England lifts interest rate to fight inflation.",
        [("BBC", "http://bbc/1")],
        "story",
    ),
    Doc(
        "Ronaldo retires",
        "Ronaldo retires from Portugal duty.",
        [("BBC", "http://bbc/2")],
    ),
    Doc(
        "Solar devices",
        "RadianX promises solar powered devices that never need charging.",
        [("TechCrunch", "http://tc/3")],
    ),
]


class FakeModels:
    def __init__(self, rewrite, answer):
        self.rewrite = rewrite
        self.answer = answer
        self.last_contents = ""

    def generate_content(self, **kwargs):
        prompt = kwargs["config"].system_instruction
        if "search query" in prompt:
            return SimpleNamespace(text=self.rewrite)
        self.last_contents = kwargs["contents"]
        return SimpleNamespace(text=self.answer)


class FakeClient:
    def __init__(self, rewrite="interest rate inflation", answer="The Bank raised rates [1]."):
        self.models = FakeModels(rewrite, answer)


class BrokenModels:
    def generate_content(self, **kwargs):
        raise RuntimeError("boom")


class BrokenClient:
    def __init__(self):
        self.models = BrokenModels()


def test_retrieve_finds_relevant_doc():
    hits = retrieve("interest rate inflation", DOCS)
    assert hits[0][0].title == "Bank of England lifts rate"


def test_retrieve_unrelated_query_is_empty():
    assert retrieve("volcano eruption lava", DOCS) == []


def test_retrieve_empty_docs_or_query():
    assert retrieve("anything", []) == []
    assert retrieve("   ", DOCS) == []


def test_retrieve_respects_k():
    assert len(retrieve("rate Ronaldo solar", DOCS, k=2)) == 2


def test_load_documents_dedups_stories_and_articles():
    def stories_loader(limit):
        return [
            {"title": "Bank rate up", "summary": "s1", "sources": [{"source": "BBC", "link": "http://a"}]},
            {"title": "bank rate up", "summary": "older", "sources": [{"source": "BBC", "link": "http://a"}]},
            {"title": "Ronaldo", "summary": "s2", "sources": [{"source": "BBC", "link": "http://b"}]},
        ]

    def articles_loader(limit):
        return [
            {"title": "Bank rate up", "link": "http://a", "source": "BBC", "summary": "x"},
            {"title": "Solar", "link": "http://c", "source": "TC", "summary": "y"},
        ]

    docs = load_documents(stories_loader=stories_loader, articles_loader=articles_loader)
    assert [d.title for d in docs] == ["Bank rate up", "Ronaldo", "Solar"]
    assert [d.kind for d in docs] == ["story", "story", "article"]


def test_rewrite_query_cleans_output():
    client = FakeClient(rewrite='  "interest rate inflation"\n')
    assert rewrite_query("mehngai ki khabar?", client) == "interest rate inflation"


def test_rewrite_query_falls_back_on_error():
    assert rewrite_query("original sawal", BrokenClient()) == "original sawal"


def test_answer_returns_cited_sources_only():
    client = FakeClient()
    result = answer_question("Bank ne kya kiya?", client=client, docs=DOCS)
    assert "[1]" in result["answer"]
    assert result["query"] == "interest rate inflation"
    assert len(result["sources"]) == 1
    assert result["sources"][0]["title"] == "Bank of England lifts rate"
    assert result["sources"][0]["sources"] == [{"source": "BBC", "link": "http://bbc/1"}]
    assert "interest rate" in client.models.last_contents  # context model ko gaya


def test_answer_without_citations_returns_all_hits():
    client = FakeClient(rewrite="Ronaldo Portugal interest rate", answer="Jawab bina citation.")
    result = answer_question("sawal", client=client, docs=DOCS)
    assert len(result["sources"]) == 2


def test_answer_when_nothing_found():
    result = answer_question("volcano eruption lava", client=BrokenClient(), docs=DOCS, rewrite=False)
    assert result["answer"] == NO_INFO
    assert result["sources"] == []


def test_answer_empty_model_reply_returns_no_info():
    client = FakeClient(answer="")
    result = answer_question("Bank ne kya kiya?", client=client, docs=DOCS)
    assert result["answer"] == NO_INFO
    assert result["sources"] == []
