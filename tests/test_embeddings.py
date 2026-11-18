from types import SimpleNamespace

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.research import Doc, answer_question, retrieve, retrieve_semantic
from app.core import embeddings, models  # noqa: F401
from app.core.database import Base

# Fake "matlab": har theme ke lafz ek hi dimension par jate hain
THEMES = [
    ("rate", "inflation", "borrowing", "price", "bank"),  # finance
    ("ronaldo", "football", "portugal"),  # sports
    ("solar", "chip", "charging"),  # tech
]

DOCS = [
    Doc(
        "Bank of England lifts rate",
        "Bank of England lifts interest rate to fight inflation.",
        [("BBC", "http://bbc/1")],
        "story",
    ),
    Doc("Ronaldo retires", "Ronaldo retires from Portugal duty.", [("BBC", "http://bbc/2")]),
    Doc(
        "Solar devices",
        "RadianX promises solar powered devices that never need charging.",
        [("TechCrunch", "http://tc/3")],
    ),
]


def fake_vector(text):
    t = text.lower()
    return [float(sum(t.count(w) for w in words)) for words in THEMES]


class FakeModels:
    def __init__(self, rewrite="borrowing costs price rises", fail_embeddings=False):
        self.rewrite = rewrite
        self.fail_embeddings = fail_embeddings
        self.embed_calls = []

    def embed_content(self, model, contents, config):
        if self.fail_embeddings:
            raise RuntimeError("quota")
        self.embed_calls.append((list(contents), config.task_type))
        return SimpleNamespace(embeddings=[SimpleNamespace(values=fake_vector(t)) for t in contents])

    def generate_content(self, **kwargs):
        if "search query" in kwargs["config"].system_instruction:
            return SimpleNamespace(text=self.rewrite)
        return SimpleNamespace(text="The Bank raised rates [1].")


class FakeClient:
    def __init__(self, **kwargs):
        self.models = FakeModels(**kwargs)


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(embeddings, "SessionLocal", sessionmaker(bind=engine))
    monkeypatch.setattr(embeddings, "init_db", lambda: None)
    yield
    engine.dispose()


def test_embed_batch_splits_into_batches():
    client = FakeClient()
    vectors = embeddings.embed_batch(
        ["rate", "ronaldo", "solar", "bank", "chip"], client, "RETRIEVAL_DOCUMENT", batch_size=2
    )
    assert len(vectors) == 5
    assert len(client.models.embed_calls) == 3
    assert client.models.embed_calls[0][1] == "RETRIEVAL_DOCUMENT"


def test_embed_batch_length_mismatch_raises():
    class ShortModels:
        def embed_content(self, model, contents, config):
            return SimpleNamespace(embeddings=[SimpleNamespace(values=[1.0, 0.0])])

    client = SimpleNamespace(models=ShortModels())
    with pytest.raises(ValueError):
        embeddings.embed_batch(["a", "b"], client, "RETRIEVAL_DOCUMENT")


def test_documents_are_cached(temp_db):
    client = FakeClient()
    embeddings.embed_documents_cached(["rate inflation", "ronaldo football"], client, delay=0)
    assert len(client.models.embed_calls) == 1

    embeddings.embed_documents_cached(["rate inflation", "ronaldo football"], client, delay=0)
    assert len(client.models.embed_calls) == 1  # cache se aaya, API call nahi hui

    embeddings.embed_documents_cached(["rate inflation", "solar chip"], client, delay=0)
    assert len(client.models.embed_calls) == 2
    assert client.models.embed_calls[1][0] == ["solar chip"]  # sirf naya text embed hua


def test_document_vectors_are_normalized(temp_db):
    vectors = embeddings.embed_documents_cached(
        ["rate inflation bank", "ronaldo football", "nothing relevant"], FakeClient(), delay=0
    )
    norms = np.linalg.norm(vectors, axis=1)
    assert norms[0] == pytest.approx(1.0)
    assert norms[1] == pytest.approx(1.0)
    assert norms[2] == pytest.approx(0.0)  # zero vector zero hi rehta hai


def test_query_embedding_is_unit_vector():
    vec = embeddings.embed_query("borrowing costs price rises", FakeClient())
    assert np.linalg.norm(vec) == pytest.approx(1.0)


def test_semantic_finds_meaning_without_shared_words(temp_db):
    query = "borrowing costs price rises"
    assert retrieve(query, DOCS) == []  # keyword search ko kuch nahi milta
    hits = retrieve_semantic(query, DOCS, FakeClient(), k=3, min_score=0.5)
    assert hits[0][0].title == "Bank of England lifts rate"
    assert hits[0][1] == pytest.approx(1.0)


def test_semantic_threshold_filters_unrelated(temp_db):
    assert retrieve_semantic("volcano lava eruption", DOCS, FakeClient(), min_score=0.5) == []


def test_semantic_empty_inputs():
    assert retrieve_semantic("anything", [], FakeClient()) == []
    assert retrieve_semantic("   ", DOCS, FakeClient()) == []


def test_answer_uses_semantic_retrieval(temp_db):
    result = answer_question("Mehngai ki kya khabar hai?", client=FakeClient(), docs=DOCS, semantic=True)
    assert result["retrieval"] == "semantic"
    assert "[1]" in result["answer"]
    assert result["sources"][0]["title"] == "Bank of England lifts rate"


def test_answer_falls_back_to_tfidf_when_embeddings_fail(temp_db):
    client = FakeClient(rewrite="interest rate inflation", fail_embeddings=True)
    result = answer_question("sawal", client=client, docs=DOCS, semantic=True)
    assert result["retrieval"] == "tfidf"
    assert result["sources"][0]["title"] == "Bank of England lifts rate"
