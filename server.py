import os
import threading
from datetime import date

from flask import Flask, render_template, request, redirect, url_for, abort, jsonify

from cards import Card, CardError, NotDueError, INTERVALS
from store import CardStore

app = Flask(__name__)
# the database file sits next to this program, wherever it is started from
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'murajaa.db')
store = CardStore(DB_PATH)

# two answers to the same card at once would both read it as due;
# the lock lets one answer finish before the next one reads
answer_lock = threading.Lock()


def record_answer(card_id, knew_it):
    with answer_lock:
        card = store.get(card_id)
        card.answer(knew_it, date.today())
        store.save(card)
    return card


def read_knew_it():
    # the form field knew_it must be yes or no
    value = request.form.get('knew_it', '')
    if value not in ('yes', 'no'):
        abort(400)
    return value == 'yes'


# ---------- web pages for the browser ----------

@app.route('/')
def home():
    message = request.args.get('message', '')
    failed = request.args.get('failed', '') == 'yes'
    decks = store.summary(date.today())
    return render_template('home.html', decks=decks, boxes=INTERVALS, message=message, failed=failed)


@app.route('/add', methods=['POST'])
def add():
    try:
        card = Card(request.form['deck'], request.form['front'], request.form['back'])
        store.add(card)
    except CardError as error:
        return redirect(url_for('home', message=str(error), failed='yes'))
    return redirect(url_for('home', message='Added a card to ' + card.deck + '.'))


@app.route('/study/<deck>')
def study(deck):
    if deck not in store.deck_names():
        abort(404)
    due = store.due_cards(deck, date.today())
    card = due[0] if len(due) > 0 else None
    message = request.args.get('message', '')
    return render_template('study.html', deck=deck, card=card, left=len(due), message=message)


@app.route('/answer/<int:card_id>', methods=['POST'])
def answer(card_id):
    knew_it = read_knew_it()
    try:
        card = record_answer(card_id, knew_it)
    # NotDueError is a kind of CardError, so it must come first
    except NotDueError:
        # a double click: the first answer already counted
        card = store.get(card_id)
        return redirect(url_for('study', deck=card.deck, message='That card was already answered.'))
    except CardError:
        abort(404)
    message = 'Now in box ' + str(card.box) + ', back on ' + str(card.due.day) + ' ' + card.due.strftime('%b') + '.'
    return redirect(url_for('study', deck=card.deck, message=message))


# ---------- JSON API for the desktop app ----------

@app.route('/api/decks')
def api_decks():
    return jsonify(store.summary(date.today()))


@app.route('/api/due/<deck>')
def api_due(deck):
    if deck not in store.deck_names():
        abort(404)
    due = store.due_cards(deck, date.today())
    return jsonify([card.to_dict() for card in due])


@app.route('/api/answer/<int:card_id>', methods=['POST'])
def api_answer(card_id):
    knew_it = read_knew_it()
    try:
        card = record_answer(card_id, knew_it)
    except NotDueError:
        # 409 Conflict: this card was already answered
        abort(409)
    except CardError:
        abort(404)
    return jsonify(card.to_dict())


if __name__ == '__main__':
    print('Murajaa on http://127.0.0.1:5077')
    app.run(port=5077)
