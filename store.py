import sqlite3
from datetime import date

from cards import Card, CardError


class CardStore:
    """Every SQL query of the project. Only the Flask server uses this class."""

    def __init__(self, path: str):
        self.path = path
        # makes the table on the first run and keeps the cards already saved
        self._query('CREATE TABLE IF NOT EXISTS cards ('
                    'id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, deck TEXT NOT NULL, '
                    'question TEXT NOT NULL, answer TEXT NOT NULL, '
                    'box INTEGER NOT NULL, due TEXT NOT NULL)')

    def _query(self, sql: str, values: tuple = ()) -> tuple[list, int]:
        # a new connection for each query: Flask answers every request in its
        # own thread, and a SQLite connection belongs to the thread that made it
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
        card_id, name, deck, question, answer, box, due = row
        return Card(name, deck, question, answer, box, date.fromisoformat(due), card_id)

    def add(self, card: Card) -> Card:
        _, new_id = self._query(
            'INSERT INTO cards (name, deck, question, answer, box, due) VALUES (?, ?, ?, ?, ?, ?)',
            (card.name, card.deck, card.question, card.answer, card.box, card.due.isoformat()))
        card.card_id = new_id
        return card

    def get(self, card_id: int) -> Card:
        rows, _ = self._query('SELECT * FROM cards WHERE id = ?', (card_id,))
        if len(rows) == 0:
            raise CardError('There is no card with ID ' + str(card_id) + '. It may have been deleted.')
        return self._to_card(rows[0])

    def update(self, card: Card) -> None:
        self._query('UPDATE cards SET name = ?, deck = ?, question = ?, answer = ?, box = ?, due = ? '
                    'WHERE id = ?',
                    (card.name, card.deck, card.question, card.answer, card.box,
                     card.due.isoformat(), card.card_id))

    def delete(self, card_id: int) -> None:
        self.get(card_id)  # raises CardError if the card is not there
        self._query('DELETE FROM cards WHERE id = ?', (card_id,))

    def all_cards(self, deck: str = '') -> list[Card]:
        # an empty deck name means every deck
        if deck == '':
            rows, _ = self._query('SELECT * FROM cards ORDER BY deck, id')
        else:
            rows, _ = self._query('SELECT * FROM cards WHERE deck = ? ORDER BY id', (deck,))
        return [self._to_card(row) for row in rows]

    def due_cards(self, deck: str, today: date) -> list[Card]:
        # dates are saved as text like 2026-11-10, which sorts in date order
        if deck == '':
            rows, _ = self._query('SELECT * FROM cards WHERE due <= ? ORDER BY box, id',
                                  (today.isoformat(),))
        else:
            rows, _ = self._query('SELECT * FROM cards WHERE deck = ? AND due <= ? ORDER BY box, id',
                                  (deck, today.isoformat()))
        return [self._to_card(row) for row in rows]

    def deck_names(self) -> list[str]:
        rows, _ = self._query('SELECT DISTINCT deck FROM cards ORDER BY deck')
        return [row[0] for row in rows]
