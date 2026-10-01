import pytest

from app.faq_data import build_entries
from app.knowledge_base import FAQEntry, KnowledgeBase


def test_default_knowledge_base_has_entries():
    kb = KnowledgeBase.default()

    assert len(kb.entries) == 25
    assert len(kb.questions()) == 25


def test_exact_question_match():
    kb = KnowledgeBase.default()

    match = kb.find("What is Python?")

    assert match is not None
    assert match.entry.id == "python"
    assert match.score == 1.0


def test_alias_match():
    kb = KnowledgeBase.default()

    match = kb.find("what is natural language processing")

    assert match is not None
    assert match.entry.id == "nlp"
    assert match.score == 1.0


def test_embedded_phrase_match():
    kb = KnowledgeBase.default()

    match = kb.find(
        "Can you tell me what is Python?"
    )

    assert match is not None
    assert match.entry.id == "python"
    assert match.score == 0.9


def test_keyword_match_for_explain_question():
    kb = KnowledgeBase.default()

    match = kb.find(
        "Explain Python to me"
    )

    assert match is not None
    assert match.entry.id == "python"
    assert match.score == 0.75


def test_contractions_are_normalized():
    kb = KnowledgeBase.default()

    match = kb.find(
        "What's an API?"
    )

    assert match is not None
    assert match.entry.id == "api"


def test_answer_returns_text():
    kb = KnowledgeBase.default()

    answer = kb.answer("What is SQLite?")

    assert answer is not None
    assert "lightweight database" in answer


def test_unknown_question_returns_none():
    kb = KnowledgeBase.default()

    assert kb.find(
        "What is quantum banana programming?"
    ) is None

    assert kb.answer(
        "What is quantum banana programming?"
    ) is None


def test_empty_input_returns_none():
    kb = KnowledgeBase.default()

    assert kb.find("") is None
    assert kb.find(None) is None
    assert kb.answer("") is None


def test_get_existing_and_missing_entry():
    kb = KnowledgeBase.default()

    assert kb.get("python") is not None
    assert kb.get("does_not_exist") is None


def test_duplicate_entry_id_is_rejected():
    entry = FAQEntry(
        id="same",
        question="What is X?",
        answer="X",
    )

    kb = KnowledgeBase([entry])

    with pytest.raises(
        ValueError,
        match="Duplicate FAQ id",
    ):
        kb.add_entry(
            FAQEntry(
                id="same",
                question="What is Y?",
                answer="Y",
            )
        )


def test_custom_entry_can_be_added():
    kb = KnowledgeBase()

    entry = FAQEntry(
        id="favorite_food",
        question="What is your favorite food?",
        aliases=(
            "what food do you like",
            "tell me your favorite food",
        ),
        keywords=("favorite food",),
        answer="I like pizza.",
    )

    kb.add_entry(entry)

    assert kb.get("favorite_food") == entry
    assert kb.answer(
        "What is your favorite food?"
    ) == "I like pizza."


def test_aliases_are_unique_across_default_entries():
    entries = build_entries()
    seen = {}

    for entry in entries:
        phrases = [
            entry.question,
            *entry.aliases,
        ]

        for phrase in phrases:
            key = " ".join(
                phrase.lower().split()
            )

            if key in seen:
                pytest.fail(
                    f"Duplicate FAQ phrase: {phrase!r} "
                    f"in {entry.id!r} and {seen[key]!r}"
                )

            seen[key] = entry.id


def test_all_default_entries_have_answers():
    for entry in build_entries():
        assert entry.id
        assert entry.question
        assert entry.answer
        assert entry.answer.strip()


def test_phrases_returns_entry_mappings():
    kb = KnowledgeBase.default()

    phrases = kb.phrases()

    assert phrases
    assert all(
        phrase and entry_id
        for phrase, entry_id in phrases
    )


def test_project_questions_match():
    kb = KnowledgeBase.default()

    assert kb.answer(
        "What is this project?"
    ) is not None

    assert kb.answer(
        "What technologies are used?"
    ) is not None

    assert kb.answer(
        "Who created you?"
    ) is not None
