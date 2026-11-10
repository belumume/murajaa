from cards import Card
from server import DB_PATH
from store import CardStore

# (name, deck, question, answer): cards for this course's final exam and common Python mistakes
STARTER_CARDS = [
    ('list vs tuple', 'AP final', 'What is the difference between a list and a tuple?',
     'A list is mutable: items can be added, removed or changed. A tuple is immutable: once made it cannot change.'),
    ('sets', 'AP final', 'What is a set, and when do you use one?',
     'An unordered collection with no duplicates. Use it to remove repeats or to test membership quickly.'),
    ('dictionaries', 'AP final', 'What is a dictionary?',
     'A collection of key: value pairs. Each key is unique and is used to look up its value, e.g. marks["Sara"].'),
    ('try and except', 'AP final', 'What do try, except, else and finally do?',
     'try holds code that may fail; except runs if the try block raised that exception; else runs if nothing was raised; finally runs in every case.'),
    ('custom exception', 'AP final', 'How do you make your own exception?',
     'Write a class that inherits from Exception, e.g. class CardError(Exception), then raise CardError("message").'),
    ('class and object', 'AP final', 'What is a class, and what is an object?',
     'A class is the blueprint (attributes and methods). An object is one instance made from it, e.g. card = Card(...).'),
    ('constructor', 'AP final', 'What is the constructor in Python?',
     'The method __init__(self, ...). It runs once for every new object and sets the object\'s attributes on self.'),
    ('class vs instance attribute', 'AP final', 'Class attribute or instance attribute: where does Product.count += 1 store the value, and where does self.count += 1?',
     'Product.count += 1 changes the one value shared by the class. The first time, self.count += 1 reads the class value and stores a new value inside that one object; the class value stays the same.'),
    ('mainloop', 'AP final', 'In Tkinter, what does root.mainloop() do?',
     'It starts the event loop: the window waits for clicks and key presses and runs their commands until it is closed.'),
    ('grid', 'AP final', 'In Tkinter, what does grid(row=0, column=1) do?',
     'Places the widget in a table layout: row 0, column 1 of its parent.'),
    ('start and join', 'AP final', 'What do start() and join() do on a thread?',
     'start() makes the thread run its target next to the main program and returns at once. join() makes the caller wait until the thread finishes.'),
    ('race condition and Lock', 'AP final', 'What is a race condition, and how does a Lock prevent it?',
     'Two threads read and change the same data at the same time, so one change is lost. with lock: lets only one thread at a time run those lines.'),
    ('SQLite 5 steps', 'AP final', 'The 5 steps to use SQLite in Python',
     '1 import sqlite3, 2 connect, 3 execute, 4 commit (after INSERT, UPDATE, DELETE), 5 close.'),
    ('? placeholders', 'AP final', 'Why write ? placeholders in SQL instead of joining strings?',
     'The values go in safely as a tuple in the same order, so text cannot change the SQL (SQL injection). One value needs a trailing comma: (name,).'),
    ('bind, listen, accept', 'AP final', 'What does a socket server do with bind, listen and accept?',
     'bind attaches it to an address and port; listen makes it ready to take connections (it does not wait); accept waits for one client and returns a new socket for that client and its address.'),
    ('client-server model', 'AP final', 'What is the client-server model?',
     'A client sends a request; the server waits for requests, processes them and sends back a response.'),
    ('GET or POST', 'AP final', 'GET or POST: which one sends a form that saves data?',
     'POST: the data goes in the body of the request. GET asks for a page, with any values in the URL.'),
    ('status codes', 'AP final', 'What do status codes 200, 404 and 405 mean?',
     '200 OK; 404 Not Found (no such page or item); 405 Method Not Allowed (e.g. a GET sent to a route that only takes POST).'),
    ('Flask route variables', 'AP final', 'In Flask, what does @app.route("/cards/<int:card_id>") do?',
     'It connects that URL to the function under it. The part in < > is a variable passed to the function as card_id; int: accepts only a whole number.'),
    ('render_template', 'AP final', 'What does render_template do?',
     'Fills the gaps of an HTML file in the templates folder with the values passed to it and returns the finished HTML as a string; the view function returns that string and Flask sends it to the browser.'),
    ('JSON', 'AP final', 'What is JSON?',
     'A text format for data made of objects (like dictionaries) and arrays (like lists). json.loads turns the text into Python values.'),
    ('/ and //', 'Python mistakes', 'What does 10 / 2 give, and what does 10 // 2 give?',
     '10 / 2 gives 5.0 (always a float). 10 // 2 gives 5 (floor division).'),
    ('naming a variable sum', 'Python mistakes', 'Why not name a variable sum?',
     'It hides the built-in function sum(), so a later sum(list) fails.'),
    ('self.fee', 'Python mistakes', 'Inside a method, why write self.fee and not fee?',
     'Attributes live on the object, self. A bare fee is looked up as a local or global name, not on the object; if there is none, NameError.'),
    ('raise in __init__', 'Python mistakes', 'sara = BankAccount("Sara", -10) and a raise inside __init__ runs. Does sara get the object?',
     'No. The object is thrown away because __init__ did not finish, the assignment to sara never happens, and the next lines do not run (unless a try catches the exception).'),
    ('empty file check', 'Python mistakes', 'Where do you check that a file was empty: inside the for loop or after it?',
     'After it. With an empty file the loop body never runs, so a check inside it never runs either.'),
]


if __name__ == '__main__':
    # making the store creates the table if it is missing
    store = CardStore(DB_PATH)
    if len(store.all_cards()) > 0:
        print('The database already has cards, so nothing was added.')
    else:
        for name, deck, question, answer in STARTER_CARDS:
            store.add(Card(name, deck, question, answer))
        print('Added', len(STARTER_CARDS), 'cards to', DB_PATH)
