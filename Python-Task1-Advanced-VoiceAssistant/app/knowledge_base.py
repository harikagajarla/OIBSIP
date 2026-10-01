"""A small local FAQ / knowledge base.

This is local knowledge only. It answers questions stored in app/faq_data.py.
"""

import re
from dataclasses import dataclass

from app.utils import normalize_text

_MIN_SCORE = 0.7

_CONTRACTIONS = (
    (re.compile(r"\bwhat'?s\b"), "what is"),
    (re.compile(r"\bwho'?s\b"), "who is"),
    (re.compile(r"\bhow'?s\b"), "how is"),
    (re.compile(r"\bthat'?s\b"), "that is"),
)

_ARTICLES = re.compile(r"\b(?:a|an|the)\b")

_QUESTION_FRAME = re.compile(
    r"\b(?:what|explain|define|definition|meaning|describe|about|overview)\b"
)


def _canonical(text):
    """Normalize a question so equivalent phrasings can match."""
    cleaned = normalize_text(text)

    for pattern, replacement in _CONTRACTIONS:
        cleaned = pattern.sub(replacement, cleaned)

    cleaned = re.sub(r"[^a-z0-9 ]+", " ", cleaned)
    cleaned = _ARTICLES.sub(" ", cleaned)

    return re.sub(r"\s+", " ", cleaned).strip()


def _contains(text, phrase):
    """Return True when phrase appears as whole words."""
    return f" {phrase} " in f" {text} "


@dataclass(frozen=True)
class FAQEntry:
    """One local FAQ question and answer."""

    id: str
    question: str
    answer: str
    aliases: tuple = ()
    keywords: tuple = ()


@dataclass(frozen=True)
class FAQMatch:
    """A matched FAQ entry and its confidence score."""

    entry: FAQEntry
    score: float


class KnowledgeBase:
    """Looks up answers from a collection of FAQEntry objects."""

    def __init__(self, entries=None):
        self._items = []

        for entry in entries or ():
            self.add_entry(entry)

    @classmethod
    def default(cls):
        """Load the built-in FAQ entries."""
        from app.faq_data import build_entries

        return cls(build_entries())

    def add_entry(self, entry):
        """Add an FAQ entry and reject duplicate IDs."""
        if any(
            existing.id == entry.id
            for existing, _, _ in self._items
        ):
            raise ValueError(
                f"Duplicate FAQ id: {entry.id}"
            )

        phrases = {_canonical(entry.question)}
        phrases.update(
            _canonical(alias)
            for alias in entry.aliases
        )
        phrases.discard("")

        keywords = [
            keyword
            for keyword in (
                _canonical(word)
                for word in entry.keywords
            )
            if keyword
        ]

        self._items.append(
            (entry, phrases, keywords)
        )

    @property
    def entries(self):
        return [
            entry
            for entry, _, _ in self._items
        ]

    def get(self, entry_id):
        """Return an entry by ID or None."""
        for entry, _, _ in self._items:
            if entry.id == entry_id:
                return entry

        return None

    def questions(self):
        """Return the main question for every entry."""
        return [
            entry.question
            for entry in self.entries
        ]

    def phrases(self):
        """Return canonical phrases and their entry IDs."""
        return [
            (phrase, entry.id)
            for entry, phrases, _ in self._items
            for phrase in phrases
        ]

    def find(self, text):
        """Return the best FAQ match or None."""
        query = _canonical(text)

        if not query:
            return None

        has_frame = bool(
            _QUESTION_FRAME.search(query)
        )

        best = None

        for entry, phrases, keywords in self._items:
            score = 0.0
            specificity = 0

            for phrase in phrases:
                if query == phrase:
                    candidate = (
                        1.0,
                        len(phrase),
                    )
                elif (
                    len(phrase.split()) >= 2
                    and _contains(query, phrase)
                ):
                    candidate = (
                        0.9,
                        len(phrase),
                    )
                else:
                    continue

                if candidate > (
                    score,
                    specificity,
                ):
                    score, specificity = candidate

            if score == 0.0 and has_frame:
                for keyword in keywords:
                    if (
                        _contains(query, keyword)
                        and len(keyword) > specificity
                    ):
                        score = 0.75
                        specificity = len(keyword)

            if score and (
                best is None
                or (score, specificity) > best[:2]
            ):
                best = (
                    score,
                    specificity,
                    entry,
                )

        if best is not None and best[0] >= _MIN_SCORE:
            return FAQMatch(
                entry=best[2],
                score=best[0],
            )

        return None

    def answer(self, text):
        """Return the FAQ answer text or None."""
        match = self.find(text)

        return (
            match.entry.answer
            if match
            else None
        )
