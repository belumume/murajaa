import tkinter as tk
from datetime import date
from tkinter import font, messagebox, ttk
from urllib.parse import urlencode

from client import ServerError, ask_server

ALL_DECKS = 'All decks'
TEAL = '#0f766e'  # the one colour: due cards, the chosen row and good news
RED = '#b42318'   # error messages, and the line on the study card
CARD_WHITE = '#fffdf7'


def short_date(iso_text: str) -> str:
    # '2026-11-12' -> '12 Nov'
    day = date.fromisoformat(iso_text)
    return str(day.day) + ' ' + day.strftime('%b')


class CardWindow:
    """The main window: the list of cards, the form, and the buttons."""

    def __init__(self, root):
        self.root = root
        self.selected_id = None  # ID of the card shown in the form, or None
        root.title('Murajaa')
        root.minsize(900, 500)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview', rowheight=26)
        style.map('Treeview', background=[('selected', TEAL)])
        self.title_font = font.Font(size=16, weight='bold')
        self.big_font = font.Font(size=14, weight='bold')

        # ----- top row: title, deck filter and actions -----
        top = ttk.Frame(root, padding=(10, 10, 10, 4))
        top.grid(row=0, column=0, columnspan=3, sticky='we')
        ttk.Label(top, text='Murajaa', font=self.title_font).pack(side='left')
        ttk.Label(top, text='flash cards for exam revision').pack(side='left', padx=(8, 24))
        ttk.Label(top, text='Show').pack(side='left')
        self.deck_filter = ttk.Combobox(top, state='readonly', width=22, values=[ALL_DECKS])
        self.deck_filter.set(ALL_DECKS)
        self.deck_filter.pack(side='left', padx=6)
        self.deck_filter.bind('<<ComboboxSelected>>', lambda event: self.refresh())
        ttk.Button(top, text='Refresh', command=self.refresh).pack(side='left')
        self.study_button = ttk.Button(top, text='Study due cards', command=self.study)
        self.study_button.pack(side='right')

        # ----- left: the table of cards -----
        columns = ('id', 'name', 'deck', 'box', 'due')
        self.table = ttk.Treeview(root, columns=columns, show='headings', height=16, selectmode='browse')
        headings = {'id': 'ID', 'name': 'Name', 'deck': 'Deck', 'box': 'Box', 'due': 'Due'}
        widths = {'id': 45, 'name': 230, 'deck': 120, 'box': 50, 'due': 95}
        for column in columns:
            self.table.heading(column, text=headings[column])
            # only the Name column grows when the window gets wider
            self.table.column(column, width=widths[column], anchor='w', stretch=(column == 'name'))
        # rows of cards that are due today are written in teal
        self.table.tag_configure('due', foreground=TEAL)
        self.table.grid(row=1, column=0, sticky='nsew', padx=(10, 0))
        self.table.bind('<<TreeviewSelect>>', lambda event: self.show_selected())
        scroll = ttk.Scrollbar(root, orient='vertical', command=self.table.yview)
        self.table.configure(yscrollcommand=scroll.set)
        scroll.grid(row=1, column=1, sticky='nsw')

        # ----- right: the form -----
        self.form = ttk.LabelFrame(root, text='New card', padding=8)
        self.form.grid(row=1, column=2, sticky='nsew', padx=10)
        ttk.Label(self.form, text='Name').grid(row=0, column=0, sticky='w', pady=3)
        self.name_entry = ttk.Entry(self.form, width=40)
        self.name_entry.grid(row=0, column=1, sticky='we', pady=3)
        ttk.Label(self.form, text='Deck').grid(row=1, column=0, sticky='w', pady=3)
        # pick a deck from the list, or type a new deck name
        self.deck_entry = ttk.Combobox(self.form, width=38)
        self.deck_entry.grid(row=1, column=1, sticky='we', pady=3)
        ttk.Label(self.form, text='Question').grid(row=2, column=0, sticky='w', pady=3)
        self.question_entry = ttk.Entry(self.form, width=40)
        self.question_entry.grid(row=2, column=1, sticky='we', pady=3)
        ttk.Label(self.form, text='Answer').grid(row=3, column=0, sticky='nw', pady=3)
        self.answer_box = tk.Text(self.form, width=40, height=6, wrap='word', font='TkDefaultFont')
        self.answer_box.grid(row=3, column=1, sticky='we', pady=3)

        buttons = ttk.Frame(self.form)
        buttons.grid(row=4, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(buttons, text='Add card', command=self.add_card).pack(side='left', padx=3)
        self.save_button = ttk.Button(buttons, text='Save changes', command=self.save_changes)
        self.save_button.pack(side='left', padx=3)
        self.delete_button = ttk.Button(buttons, text='Delete', command=self.delete_card)
        self.delete_button.pack(side='left', padx=3)
        ttk.Button(buttons, text='Clear', command=self.clear_form).pack(side='left', padx=3)

        # ----- bottom: one line for success and error messages -----
        self.message = ttk.Label(root, text='')
        self.message.grid(row=2, column=0, columnspan=3, sticky='we', padx=10, pady=8)

        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)
        self.clear_form()
        self.refresh()

    # ---------- small helpers ----------

    def say(self, text, ok=True):
        self.message.config(text=text, foreground=TEAL if ok else RED)

    def form_values(self) -> dict:
        return {'name': self.name_entry.get(),
                'deck': self.deck_entry.get(),
                'question': self.question_entry.get(),
                'answer': self.answer_box.get('1.0', 'end').strip()}

    def fill_form(self, card):
        self.empty_fields()
        self.selected_id = card['id']
        self.name_entry.insert(0, card['name'])
        self.deck_entry.insert(0, card['deck'])
        self.question_entry.insert(0, card['question'])
        self.answer_box.insert('1.0', card['answer'])
        # the form now edits this card, so Save and Delete can be used
        self.form.config(text='Card ' + str(card['id']))
        self.save_button.config(state='normal')
        self.delete_button.config(state='normal')

    def clear_form(self):
        self.selected_id = None
        self.table.selection_remove(self.table.selection())
        self.empty_fields()
        # no card chosen: only Add card makes sense
        self.form.config(text='New card')
        self.save_button.config(state='disabled')
        self.delete_button.config(state='disabled')

    def empty_fields(self):
        self.name_entry.delete(0, 'end')
        self.deck_entry.delete(0, 'end')
        self.question_entry.delete(0, 'end')
        self.answer_box.delete('1.0', 'end')

    # ---------- view ----------

    def load_table(self):
        """Asks the server for the decks and cards and shows them. Returns the cards, or None on an error."""
        deck = self.deck_filter.get()
        try:
            decks = ask_server('/decks')
            if deck not in decks:
                deck = ALL_DECKS
            if deck == ALL_DECKS:
                cards = ask_server('/cards')
                due = ask_server('/due')
            else:
                cards = ask_server('/cards?' + urlencode({'deck': deck}))
                due = ask_server('/due?' + urlencode({'deck': deck}))
        except ServerError as error:
            self.say(str(error), ok=False)
            return None
        self.deck_filter.config(values=[ALL_DECKS] + decks)
        self.deck_filter.set(deck)
        self.deck_entry.config(values=decks)
        self.study_button.config(text='Study ' + str(len(due)) + (' due card' if len(due) == 1 else ' due cards'))
        due_ids = [card['id'] for card in due]
        self.table.delete(*self.table.get_children())
        for card in cards:
            if card['id'] in due_ids:
                shown_date, tags = 'due now', ('due',)
            else:
                shown_date, tags = short_date(card['due']), ()
            self.table.insert('', 'end', iid=str(card['id']), tags=tags,
                              values=(card['id'], card['name'], card['deck'], card['box'], shown_date))
        return cards

    def refresh(self):
        cards = self.load_table()
        if cards is None:
            return
        if len(cards) == 0:
            self.say('No cards yet. Fill in the form and press Add card.')
        else:
            self.say(str(len(cards)) + ' card(s) shown.')

    def show_selected(self):
        chosen = self.table.selection()
        # nothing chosen, or the card is already in the form
        if len(chosen) == 0 or chosen[0] == str(self.selected_id):
            return
        try:
            card = ask_server('/cards/' + chosen[0])
        except ServerError as error:
            self.show_error(error)
            return
        self.fill_form(card)
        self.say('Showing "' + card['name'] + '". Change it and press Save changes, or press Delete.')

    def show_error(self, error):
        if error.status == 404:
            # the card was deleted in another window: show the list as it is now
            self.clear_form()
            self.load_table()
        self.say(str(error), ok=False)

    # ---------- add, edit, delete ----------

    def add_card(self):
        try:
            card = ask_server('/cards/add', self.form_values())
        except ServerError as error:
            self.say(str(error), ok=False)
            return
        self.load_table()
        self.fill_form(card)
        self.select(card['id'])
        self.say('Added "' + card['name'] + '" to ' + card['deck'] + ' with ID ' + str(card['id']) + '.')

    def save_changes(self):
        try:
            card = ask_server('/cards/' + str(self.selected_id) + '/edit', self.form_values())
        except ServerError as error:
            self.show_error(error)
            return
        self.load_table()
        self.fill_form(card)
        self.select(card['id'])
        self.say('Saved the changes to "' + card['name'] + '".')

    def delete_card(self):
        name = self.name_entry.get()
        if not messagebox.askyesno('Delete card', 'Delete "' + name + '"? This cannot be undone.'):
            return
        try:
            ask_server('/cards/' + str(self.selected_id) + '/delete', {})
        except ServerError as error:
            self.show_error(error)
            return
        self.clear_form()
        self.load_table()
        self.say('Deleted "' + name + '".')

    def select(self, card_id):
        # highlight a card in the table without asking the server again
        if self.table.exists(str(card_id)):
            self.table.selection_set(str(card_id))
            self.table.see(str(card_id))

    # ---------- the extra feature: study the cards that are due ----------

    def study(self):
        deck = self.deck_filter.get()
        StudyWindow(self, '' if deck == ALL_DECKS else deck)


class StudyWindow:
    """A second window that shows one due card at a time."""

    def __init__(self, main, deck):
        self.main = main
        self.deck = deck
        self.cards = []
        self.total = 0
        self.window = tk.Toplevel(main.root)
        self.window.title('Study ' + (deck if deck != '' else 'all decks'))
        self.window.minsize(580, 360)
        # stays in front of the main window, a little to the right of it
        self.window.transient(main.root)
        self.window.geometry('+' + str(main.root.winfo_x() + 120) + '+' + str(main.root.winfo_y() + 80))
        frame = ttk.Frame(self.window, padding=16)
        frame.pack(fill='both', expand=True)
        # the card looks like a paper index card: white, a thin border, a red line under the top
        card = tk.Frame(frame, bg=CARD_WHITE, highlightthickness=1, highlightbackground='#c9c6bd',
                        padx=16, pady=12)
        card.pack(fill='both', expand=True)
        self.position = tk.Label(card, text='', bg=CARD_WHITE)
        self.position.pack(anchor='w')
        tk.Frame(card, bg=RED, height=2).pack(fill='x', pady=(4, 10))
        self.question = tk.Label(card, text='', font=main.big_font, bg=CARD_WHITE, wraplength=500,
                                 justify='left')
        self.question.pack(anchor='w', pady=(0, 8))
        self.answer = tk.Label(card, text='', bg=CARD_WHITE, wraplength=500, justify='left')
        self.answer.pack(anchor='w')
        buttons = ttk.Frame(frame)
        buttons.pack(pady=16)
        self.show_button = ttk.Button(buttons, text='Show the answer', command=self.show_answer)
        self.yes_button = ttk.Button(buttons, text='I knew it', command=lambda: self.send_answer('yes'))
        self.no_button = ttk.Button(buttons, text='I did not', command=lambda: self.send_answer('no'))
        for button in (self.show_button, self.yes_button, self.no_button):
            button.pack(side='left', padx=6)
        self.message = ttk.Label(frame, text='')
        self.message.pack(anchor='w')
        # when the study window closes, the main list shows the new boxes
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.load()

    def load(self):
        try:
            self.cards = ask_server('/due?' + urlencode({'deck': self.deck}))
        except ServerError as error:
            self.question.config(text='Could not load the cards.')
            self.message.config(text=str(error), foreground=RED)
            self.set_buttons(show=False, answer=False)
            return
        self.total = len(self.cards)
        self.next_card()

    def next_card(self):
        self.answer.config(text='')
        if len(self.cards) == 0:
            self.position.config(text='')
            self.question.config(text='Nothing is due today.')
            self.set_buttons(show=False, answer=False)
            return
        number = self.total - len(self.cards) + 1
        self.position.config(text='Card ' + str(number) + ' of ' + str(self.total))
        self.question.config(text=self.cards[0]['question'])
        self.set_buttons(show=True, answer=False)

    def show_answer(self):
        self.answer.config(text=self.cards[0]['answer'])
        self.set_buttons(show=False, answer=True)

    def send_answer(self, knew_it):
        card = self.cards[0]
        try:
            saved = ask_server('/cards/' + str(card['id']) + '/answer', {'knew_it': knew_it})
        except ServerError as error:
            self.message.config(text=str(error), foreground=RED)
            if error.status in (404, 409):
                # deleted or already answered somewhere else: go on to the next card
                self.cards.pop(0)
                self.next_card()
            return
        self.cards.pop(0)
        self.message.config(text='Now in box ' + str(saved['box']) + ', back on ' + short_date(saved['due'])
                            + '.', foreground=TEAL)
        self.next_card()

    def set_buttons(self, show, answer):
        self.show_button.config(state='normal' if show else 'disabled')
        self.yes_button.config(state='normal' if answer else 'disabled')
        self.no_button.config(state='normal' if answer else 'disabled')

    def close(self):
        self.window.destroy()
        self.main.refresh()


if __name__ == '__main__':
    root = tk.Tk()
    CardWindow(root)
    root.mainloop()
