import os
import sqlite3
import threading
from datetime import date

from flask import Flask, jsonify, request

from cards import Card, CardError, NotDueError, check_text
from store import CardStore

PORT = 5050
# the database file sits next to this program, wherever it is started from
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'murajaa.db')
FIELDS = ['name', 'deck', 'question', 'answer']


def error_reply(message: str, status: int):
    # the window reads the "error" value and shows it to the user
    return jsonify({'error': message}), status


class CardServer:
    """The Flask back end. Each route is a method, so every route can use self.store."""

    def __init__(self, db_path: str):
        self.store = CardStore(db_path)
        # two answers to the same card at the same moment would both find it due
        self.answer_lock = threading.Lock()
        self.app = Flask(__name__)
        # add_url_rule does the same job as @app.route, for a method
        self.app.add_url_rule('/cards', view_func=self.list_cards)
        self.app.add_url_rule('/cards/<int:card_id>', view_func=self.show_card)
        self.app.add_url_rule('/cards/add', view_func=self.add_card, methods=['POST'])
        self.app.add_url_rule('/cards/<int:card_id>/edit', view_func=self.edit_card, methods=['POST'])
        self.app.add_url_rule('/cards/<int:card_id>/delete', view_func=self.delete_card, methods=['POST'])
        self.app.add_url_rule('/decks', view_func=self.list_decks)
        self.app.add_url_rule('/due', view_func=self.list_due)
        self.app.add_url_rule('/cards/<int:card_id>/answer', view_func=self.answer_card, methods=['POST'])
        self.app.register_error_handler(404, self.unknown_address)
        self.app.register_error_handler(405, self.wrong_method)
        # errors the routes do not catch themselves: the reply is still JSON, not an HTML page
        self.app.register_error_handler(sqlite3.Error, self.database_failed)
        self.app.register_error_handler(OverflowError, self.id_too_big)

    def read_form(self) -> dict:
        # the four text fields sent by the window; raises CardError on a bad value
        values = {}
        for field in FIELDS:
            values[field] = check_text(field, request.form.get(field, ''))
        return values

    # ---------- GET: read records ----------

    def list_cards(self):
        # GET /cards gives every card; GET /cards?deck=AP+final gives one deck
        deck = request.args.get('deck', '')
        return jsonify([card.to_dict() for card in self.store.all_cards(deck)])

    def show_card(self, card_id):
        try:
            card = self.store.get(card_id)
        except CardError as error:
            return error_reply(str(error), 404)
        return jsonify(card.to_dict())

    def list_decks(self):
        return jsonify(self.store.deck_names())

    def list_due(self):
        deck = request.args.get('deck', '')
        return jsonify([card.to_dict() for card in self.store.due_cards(deck, date.today())])

    # ---------- POST: add, edit, delete ----------

    def add_card(self):
        try:
            values = self.read_form()
        except CardError as error:
            return error_reply(str(error), 400)
        card = Card(values['name'], values['deck'], values['question'], values['answer'])
        self.store.add(card)
        return jsonify(card.to_dict()), 201

    def edit_card(self, card_id):
        try:
            old = self.store.get(card_id)
        except CardError as error:
            return error_reply(str(error), 404)
        try:
            values = self.read_form()
        except CardError as error:
            return error_reply(str(error), 400)
        # editing changes the text only; the box and due date stay
        card = Card(values['name'], values['deck'], values['question'], values['answer'],
                    old.box, old.due, card_id)
        self.store.update(card)
        return jsonify(card.to_dict())

    def delete_card(self, card_id):
        try:
            self.store.delete(card_id)
        except CardError as error:
            return error_reply(str(error), 404)
        return jsonify({'deleted': card_id})

    # ---------- POST: the study answer (the extra feature) ----------

    def answer_card(self, card_id):
        knew_it = request.form.get('knew_it', '')
        if knew_it not in ('yes', 'no'):
            return error_reply('knew_it must be yes or no.', 400)
        with self.answer_lock:
            try:
                card = self.store.get(card_id)
                card.record_answer(knew_it == 'yes', date.today())
            # NotDueError is a kind of CardError, so it must come first
            except NotDueError as error:
                return error_reply(str(error), 409)
            except CardError as error:
                return error_reply(str(error), 404)
            self.store.update(card)
        return jsonify(card.to_dict())

    # ---------- errors: unknown addresses, and failures the routes do not catch ----------

    def unknown_address(self, error):
        return error_reply('The server has no such address.', 404)

    def wrong_method(self, error):
        return error_reply('This address does not take that kind of request.', 405)

    def database_failed(self, error):
        # for example the database file cannot be opened, or another program has locked it
        return error_reply('The server could not use the database. Try again.', 500)

    def id_too_big(self, error):
        # SQLite cannot hold a number this long, so no card can have this ID
        return error_reply('There is no card with that ID.', 404)

    def run(self):
        self.app.run(port=PORT)


if __name__ == '__main__':
    CardServer(DB_PATH).run()
