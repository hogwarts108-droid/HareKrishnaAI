import json

from app import knowledge


def test_find_answer_returns_normalized_chapter_and_verse():
    result = knowledge.find_answer("Bhagavad Gita 18.66")
    assert result is not None
    assert result["source"] == "Bhagavad Gita"
    assert "chapter" in result
    assert result["verse"] == "18.66"


def test_generate_answer_text_mentions_chapter_and_verse():
    result = knowledge.find_answer("Yoga Sutra 1.2")
    assert result is not None
    text = knowledge.generate_answer_text("Yoga Sutra 1.2", result, lang="de")
    assert "Kapitel" in text or "Vers" in text
    assert "1.2" in text
