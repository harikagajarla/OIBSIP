"""
password_generator.py

Pure password-generation logic for the Secure Password Generator project.

This module has NO knowledge of Tkinter or any GUI framework. It only
knows how to:
    1. Build a pool of allowed characters based on user selections.
    2. Validate that the user's request is actually possible.
    3. Generate a cryptographically secure password that is guaranteed
       to contain at least one character from every selected category.

Keeping this module free of GUI code means it can be tested and reused
on its own -- for example from a plain Python shell, a unit test file,
or a completely different interface (web, CLI, etc.) in the future.

Security note:
    We use Python's `secrets` module instead of `random` because `secrets`
    is built for cryptographic / security-sensitive use cases. `random`
    uses a Mersenne Twister PRNG that is fast but predictable if an
    attacker learns enough of its output -- that makes it unsafe for
    anything like passwords, tokens, or security keys. `secrets` pulls
    randomness from the operating system's cryptographically secure
    source (os.urandom), which does not have this weakness.
"""

from __future__ import annotations

import secrets
import string
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Character set constants
# ---------------------------------------------------------------------------

UPPERCASE_CHARS = string.ascii_uppercase          # 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
LOWERCASE_CHARS = string.ascii_lowercase          # 'abcdefghijklmnopqrstuvwxyz'
DIGIT_CHARS = string.digits                       # '0123456789'
SYMBOL_CHARS = "!@#$%^&*()-_=+[]{};:,.<>?/"       # curated, no ambiguous-looking symbols

# Characters that are easy to visually confuse with one another
# (zero vs capital O, lowercase L vs digit 1, etc.)
AMBIGUOUS_CHARS = "0Ol1I"

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
MIN_SELECTED_CATEGORIES = 2


class PasswordGeneratorError(ValueError):
    """
    Raised when the user's request cannot be fulfilled.

    We use a dedicated exception class (instead of a generic ValueError)
    so that the GUI layer (app.py) can catch *specifically* this error
    and show a friendly message, while still letting truly unexpected
    errors (bugs) surface differently during development.
    """


@dataclass
class PasswordOptions:
    """
    A small container that groups all the settings a user can choose.

    Using a dataclass here (instead of passing five separate arguments
    everywhere) keeps function signatures clean and makes it obvious
    which settings belong together.
    """
    length: int
    use_upper: bool = False
    use_lower: bool = False
    use_digits: bool = False
    use_symbols: bool = False
    exclude_ambiguous: bool = False

    def selected_category_count(self) -> int:
        """Return how many character-type checkboxes are turned on."""
        return sum([self.use_upper, self.use_lower, self.use_digits, self.use_symbols])


def _strip_ambiguous(characters: str) -> str:
    """Remove any ambiguous characters (0, O, l, 1, I) from a character set."""
    return "".join(ch for ch in characters if ch not in AMBIGUOUS_CHARS)


def _build_category_pools(options: PasswordOptions) -> dict[str, str]:
    """
    Build a dictionary mapping each SELECTED category name to its
    character pool (after ambiguous-character exclusion, if requested).

    Only categories the user actually selected are included in the
    returned dictionary. This dictionary is the single source of truth
    used both for building the full pool and for guaranteeing that each
    selected category is represented in the final password.
    """
    pools: dict[str, str] = {}

    if options.use_upper:
        pools["upper"] = UPPERCASE_CHARS
    if options.use_lower:
        pools["lower"] = LOWERCASE_CHARS
    if options.use_digits:
        pools["digits"] = DIGIT_CHARS
    if options.use_symbols:
        pools["symbols"] = SYMBOL_CHARS

    if options.exclude_ambiguous:
        pools = {name: _strip_ambiguous(chars) for name, chars in pools.items()}

    return pools


def validate_options(options: PasswordOptions) -> None:
    """
    Validate a PasswordOptions object and raise PasswordGeneratorError
    with a clear, user-friendly message if anything is invalid.

    This function does not return anything -- if it doesn't raise,
    the options are considered valid.
    """
    if not isinstance(options.length, int):
        raise PasswordGeneratorError("Password length must be a whole number.")

    if options.length < MIN_PASSWORD_LENGTH:
        raise PasswordGeneratorError(
            f"Password length must be at least {MIN_PASSWORD_LENGTH} characters."
        )

    if options.length > MAX_PASSWORD_LENGTH:
        raise PasswordGeneratorError(
            f"Password length must not exceed {MAX_PASSWORD_LENGTH} characters."
        )

    selected_count = options.selected_category_count()

    if selected_count == 0:
        raise PasswordGeneratorError("Select at least two character types.")

    if selected_count < MIN_SELECTED_CATEGORIES:
        raise PasswordGeneratorError("Please select at least two character types.")

    if options.length < selected_count:
        raise PasswordGeneratorError(
            "Password length must be at least the number of selected character types."
        )

    # After building pools (and possibly excluding ambiguous characters),
    # make sure every selected category still has at least one usable
    # character left. This protects against an edge case where a category
    # pool becomes empty after exclusion (not possible with our current
    # character sets, but this keeps the code robust if pools change later).
    pools = _build_category_pools(options)
    for name, chars in pools.items():
        if not chars:
            raise PasswordGeneratorError(
                f"No usable characters remain for the '{name}' category "
                "after excluding ambiguous characters."
            )


def generate_password(options: PasswordOptions) -> str:
    """
    Generate a cryptographically secure password matching `options`.

    Guarantees:
        - The password length exactly matches `options.length`.
        - The password contains AT LEAST ONE character from every
          selected category (upper/lower/digits/symbols).
        - All randomness comes from the `secrets` module.

    How the guarantee is implemented (read this if you're learning):
        1. We pick ONE guaranteed character from each selected category's
           pool. This immediately satisfies "at least one from every
           selected category" -- it is guaranteed by construction, not by
           chance, and not by re-generating passwords until one happens
           to qualify.
        2. We fill the remaining length by choosing randomly from the
           COMBINED pool of all selected categories.
        3. We shuffle the final list of characters using
           `secrets.SystemRandom().shuffle()` so the guaranteed
           characters aren't predictably placed at the start of the
           password.

    Raises:
        PasswordGeneratorError: if `options` is invalid.
    """
    # Always validate first -- never generate from bad input.
    validate_options(options)

    pools = _build_category_pools(options)
    combined_pool = "".join(pools.values())

    # Step 1: guarantee one character from each selected category.
    guaranteed_chars = [secrets.choice(chars) for chars in pools.values()]

    # Step 2: fill the rest of the length from the combined pool.
    remaining_length = options.length - len(guaranteed_chars)
    random_fill = [secrets.choice(combined_pool) for _ in range(remaining_length)]

    password_chars = guaranteed_chars + random_fill

    # Step 3: shuffle securely so guaranteed characters aren't always first.
    secrets.SystemRandom().shuffle(password_chars)

    return "".join(password_chars)
