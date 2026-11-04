import sqlite3
from datetime import date

from cards import Card, CardError, INTERVALS


class CardStore:
    def __init__(self, path):
        self.path = path
        self._query('CREATE TABLE IF NOT EXISTS cards ('
                    'id INTEGER PRIMARY KEY AUTOINCREMENT, deck TEXT NOT NULL, '
                    'front TEXT NOT NULL, back TEXT NOT NULL, '
                    'box INTEGER NOT NULL, due TEXT NOT NULL)')

    def _query(self, sql, values=()):
        # a new connection each time: the web server answers every
        # request in its own thread, and a connection belongs to one thread
        connection = sqlite3.connect(self.path)
        try:
            cursor = connection.cursor()
            cursor.execute(sql, values)
            rows = cursor.fetchall()
            connection.commit()
            return rows, cursor.lastrowid
        finally:
            connection.close()

    def _to_card(self, row: tuple) -> Card:
        card_id, deck, front, back, box, due = row
        return Card(deck, front, back, box, date.fromisoformat(due), card_id)

    def add(self, card: Card) -> Card:
        _, new_id = self._query(
            'INSERT INTO cards (deck, front, back, box, due) VALUES (?, ?, ?, ?, ?)',
            (card.deck, card.front, card.back, card.box, card.due.isoformat()))
        card.card_id = new_id
        return card

    def get(self, card_id: int) -> Card:
        rows, _ = self._query('SELECT * FROM cards WHERE id = ?', (card_id,))
        if len(rows) == 0:
            raise CardError('there is no card ' + str(card_id))
        return self._to_card(rows[0])

    def save(self, card: Card) -> None:
        self._query('UPDATE cards SET box = ?, due = ? WHERE id = ?',
                    (card.box, card.due.isoformat(), card.card_id))

    def due_cards(self, deck: str, today: date) -> list[Card]:
        rows, _ = self._query(
            'SELECT * FROM cards WHERE deck = ? AND due <= ? ORDER BY box, id',
            (deck, today.isoformat()))
        return [self._to_card(row) for row in rows]

    def deck_names(self) -> list[str]:
        rows, _ = self._query('SELECT DISTINCT deck FROM cards ORDER BY deck')
        return [row[0] for row in rows]

    def summary(self, today: date) -> dict[str, dict]:
        # deck name -> {'total': .., 'due': .., 'boxes': {1: .., ..., 5: ..}}
        rows, _ = self._query('SELECT deck, box, due FROM cards ORDER BY deck')
        decks = {}
        for deck, box, due in rows:
            if deck not in decks:
                decks[deck] = {'total': 0, 'due': 0,
                               'boxes': {number: 0 for number in INTERVALS}}
            decks[deck]['total'] += 1
            decks[deck]['boxes'][box] += 1
            if date.fromisoformat(due) <= today:
                decks[deck]['due'] += 1
        return decks
