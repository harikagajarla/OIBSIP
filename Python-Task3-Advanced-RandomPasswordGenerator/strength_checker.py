"""
strength_checker.py

A simple, transparent password-strength estimator for the Secure
Password Generator project.

IMPORTANT LIMITATION (read this before trusting the output):
    This is a teaching-friendly, rule-of-thumb estimator. It looks at
    password length and how many different character categories are
    used. It is NOT a cryptographic entropy calculator and it does NOT
    check the password against real-world leaked-password databases or
    common-pattern dictionaries the way professional tools such as
    zxcvbn do. Treat the Weak/Medium/Strong label as a helpful hint,
    not a security guarantee.

This module has no GUI dependencies so it can be tested and reused
independently of app.py.
"""

from __future__ import annotations

STRONG_LENGTH_THRESHOLD = 12
MEDIUM_LENGTH_THRESHOLD = 8


def _character_category_count(password: str) -> int:
    """
    Count how many distinct character categories actually appear in
    the password itself (upper, lower, digit, symbol).

    We check the ACTUAL password rather than trusting the caller's
    stated selections, so this function gives an honest answer even
    if it's ever called with a password from elsewhere.
    """
    has_upper = any(ch.isupper() for ch in password)
    has_lower = any(ch.islower() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)
    has_symbol = any(not ch.isalnum() for ch in password)
    return sum([has_upper, has_lower, has_digit, has_symbol])


def calculate_strength(password: str) -> str:
    """
    Estimate password strength as "Weak", "Medium", or "Strong".

    The scoring logic (simple and transparent on purpose):
        - Start with points based on length.
        - Add points based on how many character categories are present.
        - Map the total score to a Weak / Medium / Strong label.

    Args:
        password: the generated password to evaluate.

    Returns:
        One of "Weak", "Medium", "Strong".
    """
    if not password:
        return "Weak"

    length = len(password)
    category_count = _character_category_count(password)

    score = 0

    # --- Length points ---
    if length >= STRONG_LENGTH_THRESHOLD:
        score += 2
    elif length >= MEDIUM_LENGTH_THRESHOLD:
        score += 1

    # --- Diversity points ---
    if category_count >= 4:
        score += 2
    elif category_count >= 3:
        score += 1

    # --- Final mapping ---
    # Max possible score is 4 (2 length + 2 diversity).
    if score >= 3:
        return "Strong"
    elif score >= 2:
        return "Medium"
    else:
        return "Weak"
