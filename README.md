# Murajaa (مراجعة): a flash-card trainer

Advanced Programming 462, individual project. Ubaidullah Shuaib.

Murajaa means *review*. It keeps question-and-answer cards for revising before an exam. In the
Tkinter window you add, view, edit and delete cards, and filter them by deck. The window sends
every action to a Flask server, which checks the values and saves the cards in SQLite.

**Extra feature: study mode.** Each card sits in one of five boxes. The *Study N due cards* button
(N is the number due) shows the cards that are due today, one at a time. A card you knew moves up
one box and comes back later; a card you missed goes back to box 1 and comes back tomorrow.

| Box | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| Comes back after | 1 day | 2 days | 4 days | 7 days | 14 days |

`seed.py` adds 26 sample cards for this course's final exam and common Python mistakes.

## How the parts connect

```
desktop.py (Tkinter)  ──HTTP request──▶  server.py (Flask, port 5050)  ──SQL──▶  murajaa.db (SQLite)
                      ◀──JSON reply────                                ◀──rows──
```

The user only works in the window. The window never touches the database: it sends a request to
Flask with `urlopen`, Flask uses SQLite through the `CardStore` class, and the JSON reply tells the
window what to show.

## Install and run

Python 3.10 or newer. In this folder:

```
pip install -r requirements.txt
python seed.py        # creates the cards table and adds the 26 sample cards (once)
python server.py      # starts Flask on http://127.0.0.1:5050; keep it running
python desktop.py     # in a second terminal: the window
```

`seed.py` is optional: the server also creates the table when it starts, and keeps any cards
already saved. Without `seed.py` the window starts with an empty list.

Report helper (with the server running):

```
python report.py              # writes report.txt
python report.py cards.txt    # writes cards.txt
```

Automatic checks (they start their own test server on port 5051 with an empty database):

```
python checks.py
```

## Using the window

- The table lists the cards. *Show* picks one deck or all decks. Cards due today say *due now*
  and are written in teal.
- Click a card to show it in the form, which is then headed *Card 2* (its ID). Change the fields
  and press *Save changes*, or press *Delete* (the window asks first).
- To add a card, press *Clear* (the form is headed *New card*, and *Save changes* and *Delete* are
  greyed out), fill in the four fields and press *Add card*. Pick the deck from the list or type a
  new one.
- The *Study … due cards* button shows how many cards are due (for example *Study 21 due cards*
  for AP final) and opens the study window for the deck that is shown. It shows one card at a time,
  *Card 3 of 21*.
- The line at the bottom shows what happened, in teal, or what went wrong, in red.

## Routes

| Method | Address | What it does | Errors (JSON) |
|---|---|---|---|
| GET | `/cards` | every card (the report helper uses this) | |
| GET | `/cards?deck=AP+final` | the cards of one deck | |
| GET | `/cards/<id>` | one card | 404 unknown ID |
| GET | `/decks` | the deck names | |
| GET | `/due?deck=AP+final` | the cards due today | |
| POST | `/cards/add` | adds a card from the form fields | 400 missing or too long field |
| POST | `/cards/<id>/edit` | changes the text of a card | 404 unknown ID, 400 bad field |
| POST | `/cards/<id>/delete` | deletes a card | 404 unknown ID |
| POST | `/cards/<id>/answer` | records a study answer, `knew_it=yes` or `no` | 400, 404, 409 already answered today |

Each card has an ID, a name, a deck, a question, an answer, a box (1 to 5) and a due date. The
name is required and has at most 40 characters; the deck 30, the question 300, the answer 500
(`LIMITS` in `cards.py`). An address the server does not have gives a JSON 404, and a GET to a
POST address a JSON 405. If SQLite fails while the server is running, for example because the
database file cannot be opened, the reply is a JSON 500, "The server could not use the database.
Try again." An ID too large for SQLite gives a JSON 404.

## One request from Tkinter and its reply

Adding a card: the user fills in the form and presses *Add card*.

1. `CardWindow.add_card` (`desktop.py`) calls `ask_server('/cards/add', values)` (`client.py`).
2. `ask_server` turns the dictionary into a form body, `name=urlopen&deck=AP+final&...`, with
   `urlencode(values).encode('utf-8')`, and passes it to `urlopen` as `data`. Because `data` is
   given, `urlopen` sends a POST to `http://127.0.0.1:5050/cards/add`.
3. Flask calls `CardServer.add_card` (`server.py`). `read_form` reads `request.form` and checks
   each field with `check_text` (`cards.py`). `CardStore.add` (`store.py`) runs the `INSERT`
   with `?` placeholders.
4. Flask replies with status 201 and the new card as JSON, for example
   `{"id": 27, "name": "urlopen", "deck": "AP final", "box": 1, "due": "2026-11-11", ...}`.
5. `ask_server` reads it with `json.loads`. The window reloads the table, selects the new card and
   shows *Added "urlopen" to AP final with ID 27.*

If the name is empty, step 3 stops: Flask replies with status 400 and
`{"error": "The name must not be empty."}`. `urlopen` raises `HTTPError`, `ask_server` reads the
message with `error.read()` and raises `ServerError`, and the window shows the message in red.

## Where each course topic is used

| Topic | File: function or class |
|---|---|
| Python and collections | `cards.py`: `INTERVALS` and `LIMITS` dictionaries; `server.py`: `read_form` builds a dictionary in a loop over the `FIELDS` list; `store.py`: `all_cards` returns a list of `Card` objects; `report.py`: `build_report` groups the cards in a dictionary of lists and counts the boxes |
| Exceptions | `cards.py`: `CardError(Exception)` and its subclass `NotDueError`.<br>`server.py`: every route catches them and replies with JSON 400, 404 or 409; `database_failed` turns any `sqlite3.Error` into a JSON 500, and `id_too_big` turns the `OverflowError` of a too-large ID into a JSON 404.<br>`client.py`: `HTTPError` caught before `URLError`, then `socket.timeout` and `OSError`, all turned into `ServerError`.<br>`report.py`: `OSError` when the file cannot be written.<br>`store.py`: `try/finally` closes every connection. |
| Classes | `cards.py`: `Card`; `store.py`: `CardStore` holds every SQL query; `server.py`: `CardServer`, the Flask app with one method per route; `desktop.py`: `CardWindow` and `StudyWindow` |
| SQLite | `store.py`: `CardStore` (`CREATE TABLE IF NOT EXISTS`, `INSERT`, `SELECT`, `UPDATE`, `DELETE`, all with `?` placeholders); `_query` connects, executes, commits and closes, so every request has its own connection |
| Threads and files | `report.py`: `main` starts one `threading.Thread` running `write_report`, then `join()`; `write_report` writes the UTF-8 report inside `with open(...)`. `server.py`: `answer_lock`, because Flask answers requests in several threads at once |
| Tkinter | `desktop.py`: `CardWindow` (`ttk.Entry`, `Text`, `ttk.Button`, `ttk.Combobox`, `ttk.Treeview` with a `tag_configure` for due rows, `messagebox.askyesno`, `grid` and `pack`, the `clam` theme) and `StudyWindow` (`Toplevel`, a `Frame` drawn as an index card) |
| Client and server | `client.py`: `ask_server` (`urlopen`, `urlencode`, `json.loads`, `timeout=5`); see *One request from Tkinter and its reply* above |
| Flask | `server.py`: `CardServer` registers the routes with `add_url_rule`, reads `request.form` and `request.args`, returns `jsonify(...)` with a status code, and handles 404, 405, `sqlite3.Error` and `OverflowError` with `register_error_handler` |

## Files

| File | What it holds |
|---|---|
| `server.py` | Flask back end, the `CardServer` class |
| `store.py` | `CardStore`: the SQLite table and every query |
| `cards.py` | `Card`, the study rule, the field checks and the exceptions |
| `desktop.py` | Tkinter front end: `CardWindow` and `StudyWindow` |
| `client.py` | `ask_server`: one HTTP request with `urlopen` |
| `report.py` | report helper: a thread writes a text report |
| `seed.py` | creates the table and adds the sample cards |
| `checks.py` | automatic checks of every route |
| `requirements.txt` | the package to install (Flask) |
| `Murajaa-presentation.pptx` | the slides (PowerPoint) |
| `Murajaa-presentation.pdf` | the same slides as a PDF |
| `Murajaa-report.pdf` | a short written report: what the app does, how the parts connect, a screenshot of each action, one request traced through the code, the course topics and the test results |
| `screenshots/` | screenshots of the running app, one for each action and error (used in the report and the slides) |

## Test results

Run on 24 Nov 2026, Python 3.13.15, Flask 3.1.3.

**`python checks.py`: 34 passed, 0 failed.** It covers: an empty list; add (new ID, box 1, spaces
trimmed); view all, one deck, one card, the deck names; missing name, an answer of only spaces and
a 41-character name each give 400 with a message, and a failed add saves nothing; edit changes only
the chosen card, and an empty question gives 400; delete removes only the chosen card; an unknown
ID gives 404 for view, edit and delete, and an ID too large for SQLite gives 404 for view and
delete; study answers move the box, a second answer the same day
gives 409, and a wrong `knew_it` gives 400; an unknown address gives JSON 404 and a GET to a POST
address JSON 405; with the server stopped the message is "Cannot reach the server. Start
server.py and try again."; after a restart on the same file the cards are still there; a server
that cannot open its database gives a JSON 500 with a message; a server that takes the connection
but never answers gives "The server took too long to answer. Try again." after the 5-second
timeout; the report file is saved, a folder that does not exist is reported without a crash, and
`report.main()` starts the thread, waits with `join()` and saves the file.

**Window checks** (run on 11 Nov 2026; the actions in `screenshots/` were repeated on 24 Nov 2026):

| Check | Result |
|---|---|
| Followed this README in a new, empty folder and environment | works |
| Start after `python seed.py` | table shows 26 cards |
| Start, before choosing a card | form headed *New card*; *Save changes* and *Delete* greyed out |
| Click a card | form headed *Card 1* shows its name, deck, question and answer; *Save changes* and *Delete* are no longer greyed out |
| Add with an empty name | red: "The name must not be empty." Nothing saved |
| Add a valid card | teal: *Added "urlopen" to AP final with ID 27.* The new card is selected in the table |
| Edit that card's name | the table shows the new name; card 1 is unchanged |
| Show *Python mistakes* only | 5 cards |
| Delete card 27 (Yes in the confirmation box) | 26 cards again |
| Same card open in two windows: delete in one, then *Save changes* in the other | red: "There is no card with ID 27. It may have been deleted." The table reloads |
| Show *AP final*, then *Study 21 due cards* | the study window shows "Card 1 of 21" |
| Study: *I knew it*, then *I did not* | "Now in box 2, back on 13 Nov." then "Now in box 1, back on 12 Nov."; after closing the study window the table shows card 1 in box 2, due 13 Nov |
| Stop the server, then *Refresh* and *Add card* | red: "Cannot reach the server. Start server.py and try again." |
| Start the server again, press *Add card* again (same window) | the card is added |
| Stop and start both programs | the saved cards are still there |
| `python report.py` | "Saved 26 cards to report.txt"; the file lists every card by deck with its box and due date |
| `python report.py /nonexistent/report.txt` | "The report was not saved: [Errno 2] No such file or directory: ..." |

## Credits

- [Flask](https://flask.palletsprojects.com/) (BSD-3-Clause licence). Everything else is the
  Python standard library.
- The study boxes follow the Leitner system for flash cards.
- The sample cards were written for this project from the course material.
- Most of the code was written with an AI coding assistant. I directed the work and tested it, and I
  can explain every file.
