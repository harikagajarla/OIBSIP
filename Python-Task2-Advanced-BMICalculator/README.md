# BMI Tracker

A desktop BMI calculator built with Python and tkinter. It supports multiple named users, saves every measurement to a local SQLite database and draws each user's BMI trend with matplotlib.

Built as **Task 2 (Advanced)** of the Oasis Infobyte Python Programming Internship.

## Overview

Enter a weight (kg) and height (m), click **Calculate BMI**, and the app shows your BMI rounded to 2 decimals with a colour-coded category. Each result is saved to the selected user's history, and the **View Trend Graph** button plots how that user's BMI changed over time.

The project separates business logic, storage, services and UI into different layers so that each part can be tested on its own.

## Features

- BMI = weight / height² with categories: Underweight (< 18.5), Normal (18.5-24.9), Overweight (25-29.9), Obese (>= 30)
- Result shown to 2 decimal places
- Rejects empty, non-numeric, negative and zero values with helpful messages
- Rejects implausible values (weight 2-500 kg, height 0.5-2.8 m) to catch typos such as `175` typed in the metres field

## Advanced Features

- Graphical interface (tkinter); there is no command-line interface for the main application
- Labeled weight and height fields and a **Calculate BMI** button
- Colour-coded result (blue / green / orange / red) and a colour legend
- Multi-user support with named users (names are unique, ignoring upper/lower case)
- Separate saved history for every user, shown in a table (newest first)
- Records stored in SQLite and kept between runs
- Trend graph per user with matplotlib, with shaded category bands
- Database read/write failures are caught and shown in a clear error dialog instead of crashing the app

## Tech Stack

| Purpose | Technology |
|---|---|
| Language | Python 3.12 |
| GUI | tkinter |
| Storage | SQLite (`sqlite3`) |
| Graph | matplotlib |
| Tests | pytest |

## Architecture

Four layers, each depending only on the layers below it:

```
UI (tkinter)  ->  Service  ->  Core logic (pure functions)
                     |
                     +------>  Database (SQLite, parameterized queries)
```

- **Core** (`core/bmi.py`): validation, BMI calculation, classification. No GUI, no database.
- **Database** (`db/database.py`): the only code that runs SQL. Converts `sqlite3` errors into `DatabaseError`.
- **Service** (`services/tracker_service.py`): validates input, calculates, saves and prepares graph data.
- **UI** (`ui/`): windows that collect input and display results. The graph figure is built in `trend_chart.py` (testable without a window) and shown by `trend_view.py`.

The category is decided from the **rounded** BMI, so the number you see always matches the category beside it (for example 24.996 is shown as 25.00 and is Overweight).

## Project Structure

```
Python-Task2-Advanced-BMICalculator/
├── bmi_tracker/
│   ├── config.py              # paths, limits, colours
│   ├── exceptions.py          # ValidationError, DuplicateUserError, DatabaseError
│   ├── core/bmi.py            # calculation, classification, validation
│   ├── db/database.py         # SQLite layer
│   ├── services/tracker_service.py
│   └── ui/
│       ├── main_window.py     # main window
│       ├── trend_chart.py     # matplotlib figure builder
│       └── trend_view.py      # graph window
├── tests/                     # pytest test suite
├── data/                      # SQLite file is created here (git-ignored)
├── screenshots/               # README images
├── docs/MANUAL_TEST_CHECKLIST.md
├── requirements.txt
├── pytest.ini
├── .gitignore
└── run.py                     # starts the application
```

## Installation

Requires Python 3.12 on Windows with tkinter (included in the standard python.org installer).

```powershell
git clone <your-repository-url>
cd Python-Task2-Advanced-BMICalculator
```

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first.

## Configuration

No configuration, API keys or environment variables are needed. Limits, colours and the database location are constants in `bmi_tracker/config.py`. The database is created automatically at `data/bmi_records.db`.

## Running the Application

```powershell
python run.py
```

1. Type a name under **New user name** and click **Add User**.
2. Enter weight and height, then click **Calculate BMI** (or press Enter).
3. Add more users and switch between them with **Select user**.
4. Click **View Trend Graph** to see the BMI trend of the selected user.

## Testing

```powershell
python -m pytest -q
```

The automated tests cover normal values, category boundaries, invalid and empty input, user and record storage, per-user separation, persistence, database failures and the graph data. They use temporary databases, so your real data is never touched. The GUI is checked with the manual list in [docs/MANUAL_TEST_CHECKLIST.md](docs/MANUAL_TEST_CHECKLIST.md).

## Screenshots

| Main window | Trend graph |
|---|---|
| ![Main window](screenshots/main-window.png) | ![Trend graph](screenshots/trend-graph.png) |

## Error Handling

- Invalid input shows a red message under the input fields and nothing is saved.
- Database problems (missing/locked/corrupt file, unwritable folder) raise `DatabaseError`; the UI shows an error dialog and keeps running.
- Writes are committed only when they succeed, so a failed save leaves no partial data.

## Security / Privacy

- No secrets, credentials or API keys exist in this project.
- All SQL uses parameterized queries.
- Data stays on your computer; `data/*.db` is git-ignored so personal records are never committed.

## Future Improvements

- Delete a record or a user
- Export history to CSV
- Imperial units (lb, ft/in)
- Date-range filter on the trend graph

## Author

**Harika** - MCA, Hyderabad
GitHub: `<your-github-profile-link>` | LinkedIn: `<your-linkedin-profile-link>`
