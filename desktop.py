import json
from datetime import date
import queue
import socket
import threading
import tkinter as tk
from urllib.parse import quote, urlencode

HOST = '127.0.0.1'
PORT = 5077


class ServerError(Exception):
    """Raised when the server answers with a status code of 400 or more."""

    def __init__(self, status):
        super().__init__('the server answered ' + str(status))
        self.status = status


def ask_server(path, form=None):
    # one HTTP request over a socket: GET without a form, POST with one
    if form is None:
        request = ('GET ' + path + ' HTTP/1.1\r\nHost: ' + HOST + ':' + str(PORT) + '\r\n'
                   'Connection: close\r\n\r\n').encode()
    else:
        body = urlencode(form).encode()
        request = ('POST ' + path + ' HTTP/1.1\r\nHost: ' + HOST + ':' + str(PORT) + '\r\n'
                   'Connection: close\r\nContent-Type: application/x-www-form-urlencoded\r\n'
                   'Content-Length: ' + str(len(body)) + '\r\n\r\n').encode() + body
    client = socket.socket()
    client.settimeout(5)
    try:
        client.connect((HOST, PORT))
        client.sendall(request)
        # read until the server closes the connection
        response = b''
        while True:
            data = client.recv(1024)
            if data == b'':
                break
            response = response + data
    finally:
        client.close()
    head, body = response.decode().split('\r\n\r\n', 1)
    # the status line looks like: HTTP/1.1 200 OK
    words = head.split('\r\n')[0].split(' ')
    if len(words) < 2 or not words[1].isdigit():
        raise ValueError('not an HTTP response')
    status = int(words[1])
    if status >= 400:
        raise ServerError(status)
    return json.loads(body)


class StudyWindow:
    def __init__(self, root):
        self.root = root
        self.cards = []
        # finished network jobs wait here until the window thread picks them up
        self.results = queue.Queue()

        root.title('Murajaa')
        root.geometry('600x380')
        root.minsize(600, 380)

        tk.Label(root, text='Deck').grid(row=0, column=0, padx=8, pady=8, sticky='w')
        self.deck_name = tk.StringVar(value='')
        self.deck_menu = tk.OptionMenu(root, self.deck_name, '')
        self.deck_menu.grid(row=0, column=1, sticky='we')
        self.load_button = tk.Button(root, text='Load due cards', command=self.load_cards)
        self.load_button.grid(row=0, column=2, padx=8)

        self.status = tk.Label(root, text='', fg='#555')
        self.status.grid(row=1, column=0, columnspan=3, padx=8, sticky='w')

        self.front = tk.Label(root, text='', font=('Arial', 16, 'bold'), wraplength=560, justify='left')
        self.front.grid(row=2, column=0, columnspan=3, padx=8, pady=12, sticky='w')
        self.back = tk.Label(root, text='', font=('Arial', 12), wraplength=560, justify='left')
        self.back.grid(row=3, column=0, columnspan=3, padx=8, sticky='w')

        buttons = tk.Frame(root)
        buttons.grid(row=4, column=0, columnspan=3, pady=16)
        self.show_button = tk.Button(buttons, text='Show the answer (space)', command=self.show_answer)
        self.yes_button = tk.Button(buttons, text='I knew it (1)', command=lambda: self.send_answer('yes'))
        self.no_button = tk.Button(buttons, text='I did not (2)', command=lambda: self.send_answer('no'))
        for button in (self.show_button, self.yes_button, self.no_button):
            button.pack(side='left', padx=6)
            button.config(state='disabled')

        # where the last answered card went
        self.last = tk.Label(root, text='', fg='#0f766e')
        self.last.grid(row=5, column=0, columnspan=3, padx=8, sticky='w')

        # keys: space shows the answer, 1 = I knew it, 2 = I did not.
        # invoke() does nothing while a button is disabled.
        root.bind('<space>', lambda event: self.show_button.invoke())
        root.bind('1', lambda event: self.yes_button.invoke())
        root.bind('2', lambda event: self.no_button.invoke())

        root.columnconfigure(1, weight=1)
        self.check_results()
        self.in_background(lambda: ask_server('/api/decks'), self.fill_decks)

    # ---------- threads ----------

    def in_background(self, job, when_done):
        # the network can be slow; a worker thread waits for it so the window
        # keeps answering clicks. Tk widgets may only be touched by the window
        # thread, so the worker hands its result over through the queue.
        def work():
            try:
                self.results.put((when_done, job(), None))
            except (ServerError, OSError, ValueError) as error:
                self.results.put((when_done, None, error))
        self.status.config(text='Waiting for the server...')
        # one request at a time: every button waits until this one is back
        for button in (self.load_button, self.show_button, self.yes_button, self.no_button):
            button.config(state='disabled')
        # daemon: the thread does not keep the program alive after the window closes
        threading.Thread(target=work, daemon=True).start()

    def check_results(self):
        while not self.results.empty():
            when_done, result, error = self.results.get()
            self.load_button.config(state='normal')
            if error is not None:
                self.show_error(error)
            else:
                when_done(result)
        self.root.after(100, self.check_results)

    def show_error(self, error):
        if isinstance(error, ServerError) and error.status == 404:
            self.status.config(text='The server does not know this deck or card.')
        elif isinstance(error, ServerError) and error.status == 409:
            # answered already (for example in the browser): go to the next card
            self.cards.pop(0)
            self.next_card()
            self.last.config(text='That card was already answered.')
            return
        elif isinstance(error, ServerError):
            self.status.config(text='The server answered with error ' + str(error.status) + '.')
        elif isinstance(error, ValueError):
            self.status.config(text='The server sent an answer the app cannot read.')
        else:
            self.status.config(text='Cannot reach the server. Start server.py first.')
        # give back the buttons of the step the user was on
        if len(self.cards) > 0 and self.back.cget('text') != '':
            self.yes_button.config(state='normal')
            self.no_button.config(state='normal')
        elif len(self.cards) > 0:
            self.show_button.config(state='normal')

    # ---------- what the window does with each answer ----------

    def fill_decks(self, decks):
        names = list(decks)
        if len(names) > 0:
            # a new menu with one entry per deck; choosing one sets deck_name
            self.deck_menu.destroy()
            self.deck_menu = tk.OptionMenu(self.root, self.deck_name, *names)
            self.deck_menu.grid(row=0, column=1, sticky='we')
            self.deck_name.set(names[0])
            self.status.config(text=str(len(decks)) + ' deck(s) on the server.')
        else:
            self.status.config(text='The server has no cards yet.')

    def load_cards(self):
        deck = self.deck_name.get()
        if deck == '':
            # no decks yet (perhaps the server was not running at start): ask again
            self.in_background(lambda: ask_server('/api/decks'), self.fill_decks)
            return
        self.in_background(lambda: ask_server('/api/due/' + quote(deck)), self.got_cards)

    def got_cards(self, cards):
        self.cards = cards
        self.next_card()

    def next_card(self):
        self.back.config(text='')
        if len(self.cards) == 0:
            self.front.config(text='Nothing is due in this deck today.')
            self.status.config(text='Done for today.')
            for button in (self.show_button, self.yes_button, self.no_button):
                button.config(state='disabled')
            return
        card = self.cards[0]
        self.front.config(text=card['front'])
        self.status.config(text=str(len(self.cards)) + ' due. This one is in box ' + str(card['box']) + '.')
        self.show_button.config(state='normal')
        self.yes_button.config(state='disabled')
        self.no_button.config(state='disabled')

    def show_answer(self):
        self.back.config(text=self.cards[0]['back'])
        self.show_button.config(state='disabled')
        self.yes_button.config(state='normal')
        self.no_button.config(state='normal')

    def send_answer(self, knew_it):
        card_id = self.cards[0]['id']
        self.yes_button.config(state='disabled')
        self.no_button.config(state='disabled')
        self.in_background(lambda: ask_server('/api/answer/' + str(card_id), {'knew_it': knew_it}),
                           self.answer_saved)

    def answer_saved(self, card):
        self.cards.pop(0)
        self.next_card()
        due = date.fromisoformat(card['due'])
        self.last.config(text='Last card: now in box ' + str(card['box']) + ', back on '
                         + str(due.day) + ' ' + due.strftime('%b') + '.')


if __name__ == '__main__':
    root = tk.Tk()
    StudyWindow(root)
    root.mainloop()
