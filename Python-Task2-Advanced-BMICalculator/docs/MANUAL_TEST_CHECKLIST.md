# Manual Test Checklist

Run `python run.py` and tick each item. (The automated tests do not open the GUI.)

| # | Action | Expected result |
|---|--------|-----------------|
| 1 | Start the app | Window opens, no console errors, "Select user" list is empty on first run |
| 2 | Click **Calculate BMI** with no user selected | Red message asks you to select or add a user |
| 3 | Type `Alice` in "New user name", click **Add User** | Alice appears and is selected |
| 4 | Add `alice` again | Red message: a user with that name already exists |
| 5 | Weight `70`, Height `1.75`, **Calculate BMI** | `BMI: 22.86`, `Category: Normal`, shown in **green**; one row in History |
| 6 | Try `55/1.80` (Underweight), `80/1.75` (Overweight), `100/1.70` (Obese) | Blue, orange and red results; four rows in History, newest first |
| 7 | Invalid input: `abc`, empty, `-70`, `0`, height `175` | Helpful red message each time; nothing added to History |
| 8 | Add user `Bob`, calculate `95` / `1.70` | Bob's History shows only his own record |
| 9 | Switch back to Alice in the user list | Alice's History is shown again, Bob's records are not mixed in |
| 10 | Click **View Trend Graph** for Alice | Graph window with a BMI line, coloured category bands, date axis |
| 11 | Close the app and run `python run.py` again | Users and History are still there (SQLite persistence) |
| 12 | Close the app, rename `data\bmi_records.db` to `bmi_records.bak`, then start again | A fresh empty database is created; restore the file afterwards |
| 13 | Error handling: close the app, replace `data\bmi_records.db` with a text file, start the app | An error dialog explains the database problem instead of crashing |
