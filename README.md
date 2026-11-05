# Murajaa (مراجعة): a Leitner flash-card trainer

Advanced Programming (CCS 3474), individual project. Ubaidullah Shuaib.

Murajaa means *review*. It keeps question-and-answer cards in five Leitner boxes. A card
you answer right moves up one box and waits longer before it comes back; a card you miss
goes back to box 1 and comes back the next day. So the cards you know come back less and
less often, and the ones you keep missing come back every day. A card counts once on each day
it is due, so a double click does not move it twice.

| Box | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| Comes back after | 1 day | 2 days | 4 days | 7 days | 14 days |

It starts with 26 cards for this course's final exam (collections, exceptions, OOP, GUI,
threads, SQLite, sockets, Flask) and common Python mistakes. You can add your own decks.

## Two ways to study, one server

```
 browser ──── HTML pages ────┐
                             ├── server.py (Flask) ── store.py ── murajaa.db (SQLite)
 desktop.py ── JSON API ─────┘
 (Tkinter)
```

- **In the browser**: `http://127.0.0.1:5077`. The home page shows every deck and how many
  cards sit in each box; *Study* shows the next due card; a form adds a card.
- **On the desktop**: `desktop.py` is a Tkinter window that asks the same server for the
  due cards as JSON and sends each answer back. It writes each HTTP request itself, over a socket.

## Run it

Python 3.10 or newer. In the `murajaa` folder:

```
pip install flask
python seed.py        # once: adds the 26 starter cards
python server.py      # keep this running
python desktop.py     # in a second terminal (keys: space, 1, 2)
python lock_demo.py   # shows why the server needs its lock
```

## The files

| File | What it holds |
|---|---|
| `cards.py` | `Card` class: the Leitner rule (`answer`), `is_due`, `to_dict`; `CardError` and `NotDueError` exceptions; `INTERVALS` dictionary |
| `store.py` | `CardStore` class: every SQLite query (create, insert, select, update) |
| `server.py` | Flask application: web pages, JSON API, the lock around answers |
| `desktop.py` | Tkinter client: HTTP over a socket (`ask_server`), a worker thread for each request, a queue back to the window |
| `seed.py` | the starter cards, as a list of tuples |
| `lock_demo.py` | four answers to one card at the same moment, with and without the lock |
| `templates/` | `home.html` and `study.html` |
| `static/style.css` | the look of both pages |

## Where each chapter is used

| Chapter | Where |
|---|---|
| Collections and generic types | `INTERVALS` dict (box → days); `STARTER_CARDS` list of tuples; `summary()` builds a dict of dicts; type hints such as `date | None` in `cards.py` and `list[Card]` in `store.py` |
| Exceptions | `CardError(Exception)` and its subclass `NotDueError`, raised by `Card` and `CardStore.get` and caught in the server (message, 404 or 409); `ServerError`, `OSError` and `ValueError` caught in the desktop app; `try/finally` closes every database connection and socket |
| OOP | classes `Card`, `CardStore`, `StudyWindow`; constructors with validation; `__str__` |
| GUI | `desktop.py`: `Tk`, `Label`, `Button`, `OptionMenu`, `Frame`, `grid` and `pack`, key bindings with `bind`, `mainloop`, `after` |
| Multithreading | `threading.Lock` in `server.py` so that only one of several answers arriving together counts (`lock_demo.py`); worker threads and a `queue.Queue` in `desktop.py` so the window does not freeze while it waits for the server |
| Databases | SQLite with `?` placeholders: connect, execute, commit, close |
| Client-server | `desktop.py` opens a socket, connects, sends a GET or POST request with `sendall`, reads the response with `recv` until the server closes, and reads the status line |
| Web (Flask) | routes with variables (`/study/<deck>`), GET and POST, `render_template`, `redirect` with a message, a `static` stylesheet, `abort` with 400, 404 and 409, `jsonify` |

## Errors it handles

| Situation | What happens |
|---|---|
| Empty deck, question or answer in the form | the home page shows "Deck, question and answer must not be empty." in red |
| A deck name with `/`, or only dots | the home page shows "A deck name cannot contain / or be only dots." in red |
| Unknown deck or card in the URL | 404 Not Found |
| A card answered twice on one day | the web page says "That card was already answered." and shows the next card; the JSON API answers 409 Conflict |
| `knew_it` other than `yes` or `no` | 400 Bad Request |
| A GET to a route that only takes POST | 405 Method Not Allowed (Flask) |
| Desktop app started before the server | the window says "Cannot reach the server. Start server.py first." |
