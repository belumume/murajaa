import tkinter as tk
from datetime import date
from tkinter import font, messagebox, ttk
from urllib.parse import urlencode

from client import ServerError, ask_server

ALL_DECKS = 'All decks'


class CardWindow:
    """The main window: the list of cards, the form, and the buttons."""

    def __init__(self, root):
        self.root = root
        self.selected_id = None  # ID of the card shown in the form, or None
        root.title('Murajaa')
        root.minsize(860, 460)

        # ----- top row: deck filter and actions -----
        top = tk.Frame(root)
        top.grid(row=0, column=0, columnspan=2, sticky='we', padx=10, pady=(10, 4))
        tk.Label(top, text='Show').pack(side='left')
        self.deck_filter = ttk.Combobox(top, state='readonly', width=24, values=[ALL_DECKS])
        self.deck_filter.set(ALL_DECKS)
        self.deck_filter.pack(side='left', padx=6)
        self.deck_filter.bind('<<ComboboxSelected>>', lambda event: self.refresh())
        tk.Button(top, text='Refresh', command=self.refresh).pack(side='left')
        tk.Button(top, text='Study due cards', command=self.study).pack(side='right')

        # ----- left: the table of cards -----
        # rows tall enough for the font, also on screens with large text
        line = font.nametofont('TkDefaultFont').metrics('linespace')
        ttk.Style().configure('Treeview', rowheight=line + 6)
        columns = ('id', 'name', 'deck', 'box', 'due')
        self.table = ttk.Treeview(root, columns=columns, show='headings', height=16, selectmode='browse')
        headings = {'id': 'ID', 'name': 'Name', 'deck': 'Deck', 'box': 'Box', 'due': 'Due'}
        widths = {'id': 40, 'name': 220, 'deck': 120, 'box': 40, 'due': 90}
        for column in columns:
            self.table.heading(column, text=headings[column])
            self.table.column(column, width=widths[column], anchor='w')
        self.table.grid(row=1, column=0, sticky='nsew', padx=(10, 0))
        self.table.bind('<<TreeviewSelect>>', lambda event: self.show_selected())
        scroll = ttk.Scrollbar(root, orient='vertical', command=self.table.yview)
        self.table.configure(yscrollcommand=scroll.set)
        scroll.grid(row=1, column=1, sticky='nsw')

        # ----- right: the form -----
        form = tk.LabelFrame(root, text='Card', padx=8, pady=8)
        form.grid(row=1, column=2, sticky='nsew', padx=10)
        self.entries = {}
        # (field, label) for each one-line text box
        for row, (field, label) in enumerate([('name', 'Name'), ('deck', 'Deck'), ('question', 'Question')]):
            tk.Label(form, text=label).grid(row=row, column=0, sticky='w', pady=3)
            entry = tk.Entry(form, width=40)
            entry.grid(row=row, column=1, sticky='we', pady=3)
            self.entries[field] = entry
        tk.Label(form, text='Answer').grid(row=3, column=0, sticky='nw', pady=3)
        self.answer_box = tk.Text(form, width=40, height=6, wrap='word', font='TkDefaultFont')
        self.answer_box.grid(row=3, column=1, sticky='we', pady=3)

        buttons = tk.Frame(form)
        buttons.grid(row=4, column=0, columnspan=2, pady=(10, 0))
        tk.Button(buttons, text='Add card', command=self.add_card).pack(side='left', padx=3)
        tk.Button(buttons, text='Save changes', command=self.save_changes).pack(side='left', padx=3)
        tk.Button(buttons, text='Delete', command=self.delete_card).pack(side='left', padx=3)
        tk.Button(buttons, text='Clear', command=self.clear_form).pack(side='left', padx=3)

        # ----- bottom: one line for success and error messages -----
        self.message = tk.Label(root, text='', anchor='w')
        self.message.grid(row=2, column=0, columnspan=3, sticky='we', padx=10, pady=8)

        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)
        self.refresh()

    # ---------- small helpers ----------

    def say(self, text, ok=True):
        self.message.config(text=text, fg='#0f766e' if ok else '#b42318')

    def form_values(self) -> dict:
        values = {field: entry.get() for field, entry in self.entries.items()}
        values['answer'] = self.answer_box.get('1.0', 'end').strip()
        return values

    def fill_form(self, card):
        self.empty_fields()
        self.selected_id = card['id']
        for field, entry in self.entries.items():
            entry.insert(0, card[field])
        self.answer_box.insert('1.0', card['answer'])

    def clear_form(self):
        self.selected_id = None
        self.table.selection_remove(self.table.selection())
        self.empty_fields()

    def empty_fields(self):
        for entry in self.entries.values():
            entry.delete(0, 'end')
        self.answer_box.delete('1.0', 'end')

    # ---------- view ----------

    def refresh(self, keep_message=False):
        try:
            decks = ask_server('/decks')
            deck = self.deck_filter.get()
            if deck == ALL_DECKS or deck not in decks:
                deck = ALL_DECKS
                cards = ask_server('/cards')
            else:
                cards = ask_server('/cards?' + urlencode({'deck': deck}))
        except ServerError as error:
            self.say(str(error), ok=False)
            return
        self.deck_filter.config(values=[ALL_DECKS] + decks)
        self.deck_filter.set(deck)
        self.table.delete(*self.table.get_children())
        for card in cards:
            self.table.insert('', 'end', iid=str(card['id']),
                              values=(card['id'], card['name'], card['deck'], card['box'], card['due']))
        if keep_message:
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
            if error.status == 404:
                # deleted in another window: show the list as it is now
                self.clear_form()
                self.refresh(keep_message=True)
            self.say(str(error), ok=False)
            return
        self.fill_form(card)
        self.say('Showing "' + card['name'] + '". Change it and press Save changes, or press Delete.')

    # ---------- add, edit, delete ----------

    def add_card(self):
        try:
            card = ask_server('/cards/add', self.form_values())
        except ServerError as error:
            self.say(str(error), ok=False)
            return
        self.refresh(keep_message=True)
        self.fill_form(card)
        self.select(card['id'])
        self.say('Added "' + card['name'] + '" to ' + card['deck'] + ' with ID ' + str(card['id']) + '.')

    def save_changes(self):
        if self.selected_id is None:
            self.say('Choose a card in the list first.', ok=False)
            return
        try:
            card = ask_server('/cards/' + str(self.selected_id) + '/edit', self.form_values())
        except ServerError as error:
            if error.status == 404:
                # deleted somewhere else: show the list as it is now
                self.clear_form()
                self.refresh(keep_message=True)
            self.say(str(error), ok=False)
            return
        self.refresh(keep_message=True)
        self.fill_form(card)
        self.select(card['id'])
        self.say('Saved the changes to "' + card['name'] + '".')

    def delete_card(self):
        if self.selected_id is None:
            self.say('Choose a card in the list first.', ok=False)
            return
        name = self.entries['name'].get()
        if not messagebox.askyesno('Delete card', 'Delete "' + name + '"? This cannot be undone.'):
            return
        try:
            ask_server('/cards/' + str(self.selected_id) + '/delete', {})
        except ServerError as error:
            if error.status == 404:
                # already deleted somewhere else: show the list as it is now
                self.clear_form()
                self.refresh(keep_message=True)
            self.say(str(error), ok=False)
            return
        self.clear_form()
        self.refresh(keep_message=True)
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
        self.window = tk.Toplevel(main.root)
        self.window.title('Study ' + (deck if deck != '' else 'all decks'))
        self.window.minsize(560, 300)
        self.question = tk.Label(self.window, text='', font=('Arial', 14, 'bold'), wraplength=520, justify='left')
        self.question.pack(anchor='w', padx=16, pady=(16, 8))
        self.answer = tk.Label(self.window, text='', font=('Arial', 12), wraplength=520, justify='left')
        self.answer.pack(anchor='w', padx=16)
        buttons = tk.Frame(self.window)
        buttons.pack(pady=16)
        self.show_button = tk.Button(buttons, text='Show the answer', command=self.show_answer)
        self.yes_button = tk.Button(buttons, text='I knew it', command=lambda: self.send_answer('yes'))
        self.no_button = tk.Button(buttons, text='I did not', command=lambda: self.send_answer('no'))
        for button in (self.show_button, self.yes_button, self.no_button):
            button.pack(side='left', padx=6)
        self.message = tk.Label(self.window, text='', anchor='w')
        self.message.pack(fill='x', padx=16)
        # when the study window closes, the main list shows the new boxes
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.load()

    def load(self):
        try:
            self.cards = ask_server('/due?' + urlencode({'deck': self.deck}))
        except ServerError as error:
            self.question.config(text='Could not load the cards.')
            self.message.config(text=str(error), fg='#b42318')
            self.set_buttons(show=False, answer=False)
            return
        self.next_card()

    def next_card(self):
        self.answer.config(text='')
        if len(self.cards) == 0:
            self.question.config(text='Nothing is due today.')
            self.set_buttons(show=False, answer=False)
            return
        card = self.cards[0]
        self.question.config(text=card['question'])
        self.set_buttons(show=True, answer=False)

    def show_answer(self):
        self.answer.config(text=self.cards[0]['answer'])
        self.set_buttons(show=False, answer=True)

    def send_answer(self, knew_it):
        card = self.cards[0]
        try:
            saved = ask_server('/cards/' + str(card['id']) + '/answer', {'knew_it': knew_it})
        except ServerError as error:
            self.message.config(text=str(error), fg='#b42318')
            if error.status in (404, 409):
                # deleted or already answered somewhere else: go on to the next card
                self.cards.pop(0)
                self.next_card()
            return
        self.cards.pop(0)
        due = date.fromisoformat(saved['due'])
        self.message.config(text='Now in box ' + str(saved['box']) + ', back on ' + str(due.day) + ' '
                            + due.strftime('%b') + '. ' + str(len(self.cards)) + ' left.', fg='#0f766e')
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
