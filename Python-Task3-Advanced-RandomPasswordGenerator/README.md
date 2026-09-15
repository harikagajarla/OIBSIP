# Random Password Generator

## Overview

A desktop password generator built with Python and Tkinter, developed as **Task 3 (Advanced Tier)** of the **Oasis Infobyte Python Programming Internship**. It generates cryptographically secure passwords based on user-selected rules, guarantees representation of every selected character category, shows a transparent strength estimate, and keeps a temporary in-memory history of recent passwords — with no data ever written to disk.

## Internship Context

- **Internship:** Oasis Infobyte — Python Programming Internship
- **Task:** Task 3 — Random Password Generator
- **Tier completed:** Advanced
- **Author:** Gajarla Harika

## Features

### Beginner-tier
- User-specified password length, with a minimum of 8 characters.
- Selectable character categories: uppercase, lowercase, numbers, symbols.
- At least 2 categories must be selected before a password can be generated.
- Clear, specific validation messages for invalid input.
- Generate as many passwords as you like without restarting the app.

### Advanced-tier
- Desktop GUI built with Tkinter (slider **and** spinbox for length, checkboxes for character types).
- Passwords generated using Python's `secrets` module (not `random`) — see [Security Considerations](#security-considerations).
- Every selected character category is **guaranteed** to appear at least once in the generated password (by construction, not by chance).
- Password-strength indicator: **Weak / Medium / Strong** — see [Password Strength Logic](#password-strength-logic).
- "Copy to Clipboard" button, plus automatic clipboard copy immediately after generation, using `pyperclip`.
- Optional exclusion of visually ambiguous characters: `0`, `O`, `l`, `1`, `I`.
- Session history showing the last 5 generated passwords, masked by default with a "Show/Hide History" toggle (see [Security Considerations](#security-considerations)).
- Friendly, in-GUI error handling — no raw Python tracebacks are ever shown to the user.

## Technologies Used

| Technology | Purpose |
|---|---|
| Python 3.12 | Core language |
| Tkinter | GUI (bundled with standard Python installs) |
| `secrets` | Cryptographically secure random selection |
| `string` | Base character set constants |
| `pyperclip` | Clipboard read/write |
| `unittest` | Automated tests for the logic layer |

## Architecture

The project separates business logic from the GUI:

- **`password_generator.py`** — pure logic: builds character pools, validates input, guarantees category inclusion, generates the password with `secrets`. Contains no Tkinter code.
- **`strength_checker.py`** — pure logic: scores a password's length and character diversity into Weak/Medium/Strong. Contains no Tkinter code.
- **`app.py`** — the only file that imports Tkinter. Builds the window, reads user input, calls into the two logic modules, and manages clipboard + in-memory history.

This separation means the generation and scoring logic can be tested directly (see `tests/`) without ever opening a GUI window.

## Project Structure

```
Python-Task3-Advanced-RandomPasswordGenerator/
├── app.py                       # Tkinter GUI (orchestration only)
├── password_generator.py        # Secure generation logic
├── strength_checker.py          # Strength-scoring logic
├── requirements.txt             # External dependencies (pyperclip only)
├── README.md
├── .gitignore
├── screenshots/
│   ├── main_window.png
│   └── validation_error.png
└── tests/
    ├── __init__.py
    ├── test_password_generator.py
    └── test_strength_checker.py
```

## Installation

### 1. Check Python is installed
```powershell
python --version
```

### 2. Create a virtual environment
```powershell
python -m venv venv
```

### 3. Activate it (PowerShell)
```powershell
venv\Scripts\Activate.ps1
```

> **PowerShell execution policy note:** if activation is blocked with a message about running scripts being disabled, avoid changing your system-wide policy. Instead, run this for the *current PowerShell session only*:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> ```
> This reverts automatically once you close that PowerShell window.

### 4. Install dependencies
```powershell
pip install -r requirements.txt
```

## How to Run

```powershell
python app.py
```

To deactivate the virtual environment when finished:
```powershell
deactivate
```

## How It Works

1. You choose a password length (8–128) using the slider or spinbox, and tick at least two character-type checkboxes.
2. On clicking **Generate Password**, `app.py` packages your choices into a `PasswordOptions` object and passes it to `password_generator.generate_password()`.
3. That function:
   - Validates the request (length range, minimum categories, etc.) and raises a clear error if something is wrong.
   - Builds a character pool for each *selected* category (applying ambiguous-character exclusion first, if enabled).
   - Picks **one guaranteed character from each selected category** using `secrets.choice()` — this is what guarantees every category appears, regardless of randomness.
   - Fills the remaining length by choosing randomly from the combined pool of all selected categories.
   - Shuffles the final character list with `secrets.SystemRandom().shuffle()` so the guaranteed characters aren't predictably placed at the start.
4. The result is displayed, scored for strength, copied to the clipboard automatically, and added to the in-memory session history.

## Security Considerations

- **Why `secrets` instead of `random`:** Python's `random` module uses a Mersenne Twister pseudo-random number generator. It's fast and fine for simulations or games, but it is *not* cryptographically secure — someone who observes enough of its output can, in principle, predict future values. `secrets` draws from the operating system's cryptographically secure randomness source (`os.urandom`), which is the appropriate choice for anything security-sensitive, including password generation.
- **No persistence, ever:** generated passwords and the session history live only in this running process's memory (plain Python variables/lists). Nothing is written to a file, log, or database at any point. Closing the app permanently discards the history.
- **No logging of real passwords:** the only `print()` statements in the code are debug messages for *unexpected* errors, and they intentionally print the exception, never the password.
- **Clipboard behavior:** clicking Generate automatically copies the new password to your system clipboard via `pyperclip`, and you can also click "Copy to Clipboard" manually at any time. If the clipboard mechanism isn't available on your system, the app shows a friendly message instead of crashing — it does not silently fail.
- **History masking:** the "Recent Session Passwords" list is masked by default (e.g. `Xk•••••••Wj`) with a "Show/Hide History" toggle, so a generated password isn't left visible on-screen by default during screenshots, demos, or someone glancing at your monitor. This satisfies the requirement to display the last 5 passwords while defaulting to a safer view.

## Password Strength Logic

The strength indicator uses a simple, transparent scoring system — **not** a cryptographic entropy calculator:

- **+2 points** if length ≥ 12, **+1 point** if length ≥ 8.
- **+2 points** if the password contains characters from 4 categories, **+1 point** if from 3.
- Total score of 3–4 → **Strong**, 2 → **Medium**, 0–1 → **Weak**.

### Limitations
This is a teaching-friendly heuristic, not an enterprise-grade estimator. It does **not** check against leaked-password databases, common patterns/dictionary words, or keyboard-walk sequences the way tools like `zxcvbn` do. Treat the label as a helpful hint, not a security guarantee.

## Validation

| Condition | Message shown |
|---|---|
| Length < 8 | "Password length must be at least 8 characters." |
| Length > 128 | "Password length must not exceed 128 characters." |
| 0 categories selected | "Select at least two character types." |
| 1 category selected | "Please select at least two character types." |
| Length smaller than number of selected categories | "Password length must be at least the number of selected character types." (Note: unreachable in the real GUI today since the minimum length of 8 already exceeds the maximum of 4 categories — the check exists defensively and is covered by a dedicated unit test.) |

## Testing

### Automated tests
Run from the project root:
```powershell
python -m unittest discover -s tests -v
```
15 automated tests cover the logic layer (`password_generator.py`, `strength_checker.py`): minimum/maximum length, rejection of invalid lengths, single/zero category rejection, category-guarantee correctness (checked statistically across hundreds of generations), ambiguous-character exclusion, and strength-label boundaries. **All 15 currently pass.**

### Manual GUI test checklist
| # | Test | Result |
|---|---|---|
| 1 | Minimum length (8) | Passed |
| 2 | Maximum reasonable length (128) | Passed |
| 3 | Uppercase only (rejected — single category) | Passed |
| 4 | Lowercase only (rejected — single category) | Passed |
| 5 | Numbers only (rejected — single category) | Passed |
| 6 | Symbols only (rejected — single category) | Passed |
| 7 | Two selected categories | Passed |
| 8 | All four categories | Passed |
| 9 | Ambiguous-character exclusion | Passed (checked programmatically over 100 generations) |
| 10 | Clipboard copying | Passed (verified via `pyperclip.paste()`) |
| 11 | Strength indicator | Passed |
| 12 | Five-password session history cap | Passed |
| 13 | Invalid input (length below 8, no categories) | Passed |
| 14 | Length smaller than mandatory categories | Passed (via temporary unit-test override — see note above) |
| 15 | App restart clears session history | Not independently re-verified in this session, but guaranteed by design: history is a plain in-memory Python list created fresh in `PasswordGeneratorApp.__init__`, with no file or database read on startup. |

**How to manually verify every selected category is present:** click "Show History" to reveal the last 5 passwords, then visually check each one contains at least one character from every category you selected (e.g. if you selected Uppercase + Numbers + Symbols, confirm each password has at least one uppercase letter, one digit, and one symbol).

## Screenshots

Screenshots use placeholder password text (not real generated secrets) to avoid publishing a working password in a public repository.

- `screenshots/main_window.png` — main interface after generating a password
- `screenshots/validation_error.png` — validation error shown when fewer than 2 categories are selected

## Limitations

- The strength estimator is a simple heuristic (see [Password Strength Logic](#password-strength-logic)), not a full entropy/leak-database check.
- The "length smaller than selected categories" validation path cannot currently be triggered through the GUI, since the minimum length (8) already exceeds the maximum possible category count (4). It remains in the code for correctness and is covered by a unit test that temporarily lowers the minimum to prove the logic works.
- Clipboard support depends on the underlying OS having a working clipboard mechanism (on Linux this requires `xclip` or `xsel` to be installed); the app handles the absence of this gracefully with an on-screen message rather than crashing.

## Future Improvements

- Optional passphrase-style generation (word-based instead of character-based).
- Adjustable strength-scoring weights exposed in the UI.
- Dark/light theme toggle.

## Author

**Gajarla Harika**
MCA Candidate, Aurora's PG College (Uppal), Hyderabad
Oasis Infobyte Python Programming Internship
