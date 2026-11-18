from app.agents import user_digest

STORIES = [
    {"title": "Budget talks", "summary": "", "priority": "Medium", "sources": []},
    {"title": "Cricket final", "summary": "", "priority": "Medium", "sources": []},
    {"title": "Quake", "summary": "", "priority": "Critical", "sources": []},
]


def user(uid, email, interests=()):
    return {"id": uid, "email": email, "interests": list(interests)}


def run(recipients, stories=STORIES, marks=None, fail_for=()):
    sent = []
    marks = [] if marks is None else marks

    def sender(items, email):
        if email in fail_for:
            raise RuntimeError("smtp down")
        sent.append((email, [s.title for s in items]))

    result = user_digest.send_user_digests(
        recipients=recipients,
        stories=stories,
        sender=sender,
        already_sent=lambda uid, day: (uid, day) in marks,
        mark_sent=lambda uid, day: marks.append((uid, day)),
        today="2026-11-17",
    )
    return result, sent, marks


def test_each_user_gets_own_order():
    result, sent, marks = run([user(1, "a@x.com", ["cricket"]), user(2, "b@x.com")])
    assert result == {"sent": 2, "skipped": 0, "failed": 0}
    assert sent[0] == ("a@x.com", ["Quake", "Cricket final", "Budget talks"])
    assert sent[1] == ("b@x.com", ["Quake", "Budget talks", "Cricket final"])
    assert marks == [(1, "2026-11-17"), (2, "2026-11-17")]


def test_not_sent_twice_in_one_day():
    result, sent, _ = run([user(1, "a@x.com"), user(2, "b@x.com")], marks=[(1, "2026-11-17")])
    assert result == {"sent": 1, "skipped": 1, "failed": 0}
    assert [email for email, _ in sent] == ["b@x.com"]


def test_one_failure_does_not_block_others():
    result, sent, marks = run([user(1, "bad@x.com"), user(2, "b@x.com")], fail_for=("bad@x.com",))
    assert result == {"sent": 1, "skipped": 0, "failed": 1}
    assert [email for email, _ in sent] == ["b@x.com"]
    assert marks == [(2, "2026-11-17")]


def test_no_stories_or_no_recipients_sends_nothing():
    result, sent, _ = run([user(1, "a@x.com")], stories=[])
    assert result == {"sent": 0, "skipped": 1, "failed": 0} and sent == []
    result, sent, _ = run([])
    assert result == {"sent": 0, "skipped": 0, "failed": 0} and sent == []


def test_dict_to_story_keeps_fields():
    story = user_digest.dict_to_story(
        {
            "title": "T",
            "summary": "S",
            "priority": "High",
            "sentiment": "negative",
            "credibility": "Confirmed by 2 sources",
            "sources": [{"source": "BBC", "link": "https://b.example"}],
        }
    )
    assert story.sources == [("BBC", "https://b.example")]
    assert (story.priority, story.sentiment) == ("High", "negative")
    assert story.credibility == "Confirmed by 2 sources"


def test_dict_to_story_keeps_claims():
    claims = [{"claim": "X", "supported_by": ["BBC"], "contradicted_by": [], "status": "single"}]
    assert user_digest.dict_to_story({"title": "T", "claims": claims}).claims == claims
