# Checks the server through real HTTP requests, the same way the window sends them.
# It starts its own server on port 5051 with an empty test database, so it does not
# touch murajaa.db or a server already running on 5050. Run: python checks.py
import logging
import os
import tempfile
import threading

from werkzeug.serving import make_server

import client
import report
from client import ServerError, ask_server
from server import CardServer

# hide the line Flask prints for every request
logging.getLogger('werkzeug').setLevel(logging.ERROR)
passed = 0
failed = 0


def check(what, condition):
    global passed, failed
    if condition:
        passed += 1
        print('PASS ', what)
    else:
        failed += 1
        print('FAIL ', what)


def error_of(path, values=None):
    # the (status, message) of a request that should fail
    try:
        ask_server(path, values)
    except ServerError as error:
        return error.status, str(error)
    return 200, ''


def start_server(db_path, port):
    http = make_server('127.0.0.1', port, CardServer(db_path).app, threaded=True)
    threading.Thread(target=http.serve_forever, daemon=True).start()
    return http


folder = tempfile.mkdtemp()
db_path = os.path.join(folder, 'test.db')
client.SERVER = 'http://127.0.0.1:5051'
http = start_server(db_path, 5051)

check('empty database: /cards gives an empty list', ask_server('/cards') == [])

one = ask_server('/cards/add', {'name': 'list vs tuple', 'deck': 'AP', 'question': 'Q1', 'answer': 'A1'})
two = ask_server('/cards/add', {'name': 'sets', 'deck': 'AP', 'question': 'Q2', 'answer': 'A2'})
three = ask_server('/cards/add', {'name': '/ and //', 'deck': 'Mistakes', 'question': 'Q3', 'answer': 'A3'})
check('add: the reply has the new ID, box 1', one['id'] == 1 and one['box'] == 1)
check('add: spaces around values are removed',
      ask_server('/cards/add', {'name': '  tmp ', 'deck': 'X', 'question': 'q', 'answer': 'a'})['name'] == 'tmp')
ask_server('/cards/4/delete', {})
check('view: /cards lists the 3 cards', len(ask_server('/cards')) == 3)
check('view: /cards?deck=Mistakes gives only that deck',
      [card['id'] for card in ask_server('/cards?deck=Mistakes')] == [three['id']])
check('view: /cards/2 gives card 2', ask_server('/cards/2')['name'] == 'sets')
check('view: /decks gives the deck names', ask_server('/decks') == ['AP', 'Mistakes'])

check('missing name: 400 with a message',
      error_of('/cards/add', {'deck': 'AP', 'question': 'q', 'answer': 'a'})
      == (400, 'The name must not be empty.'))
check('only spaces in the answer: 400',
      error_of('/cards/add', {'name': 'n', 'deck': 'AP', 'question': 'q', 'answer': '   '})[0] == 400)
check('name over 40 characters: 400 with the limit in the message',
      error_of('/cards/add', {'name': 'x' * 41, 'deck': 'AP', 'question': 'q', 'answer': 'a'})
      == (400, 'The name can have at most 40 characters.'))
check('failed add saves nothing', len(ask_server('/cards')) == 3)

edited = ask_server('/cards/2/edit', {'name': 'sets (edited)', 'deck': 'AP', 'question': 'Q2', 'answer': 'A2 new'})
check('edit: the reply shows the new values', edited['name'] == 'sets (edited)' and edited['answer'] == 'A2 new')
check('edit: only the chosen card changed',
      ask_server('/cards/1') == one and ask_server('/cards/3') == three)
check('edit with an empty question: 400',
      error_of('/cards/2/edit', {'name': 'n', 'deck': 'AP', 'question': '', 'answer': 'a'})[0] == 400)

ask_server('/cards/1/delete', {})
check('delete: card 1 is gone, the others stay',
      [card['id'] for card in ask_server('/cards')] == [2, 3])
check('unknown ID: view gives 404', error_of('/cards/1')[0] == 404)
check('unknown ID: edit gives 404 (deleted in another window)',
      error_of('/cards/1/edit', {'name': 'n', 'deck': 'd', 'question': 'q', 'answer': 'a'})
      == (404, 'There is no card with ID 1. It may have been deleted.'))
check('unknown ID: delete again gives 404', error_of('/cards/1/delete', {})[0] == 404)

check('study: /due lists the due cards', len(ask_server('/due?deck=AP')) == 1)
answered = ask_server('/cards/2/answer', {'knew_it': 'yes'})
check('study: I knew it moves the card to box 2', answered['box'] == 2)
check('study: a second answer the same day gives 409', error_of('/cards/2/answer', {'knew_it': 'no'})[0] == 409)
check('study: knew_it other than yes or no gives 400', error_of('/cards/3/answer', {'knew_it': 'maybe'})[0] == 400)
check('study: the answered card is no longer due', ask_server('/due?deck=AP') == [])

check('an address the server does not have: JSON 404', error_of('/nothing')[0] == 404)
check('GET to a POST-only address: JSON 405', error_of('/cards/add')[0] == 405)

http.shutdown()
check('server stopped: a clear message', error_of('/cards') == (0, 'Cannot reach the server. Start server.py and try again.'))
http = start_server(db_path, 5051)
check('server started again on the same file: the cards are still there',
      [card['name'] for card in ask_server('/cards')] == ['sets (edited)', '/ and //'])

result = {'saved': False, 'error': ''}
report_path = os.path.join(folder, 'report.txt')
report.write_report(ask_server('/cards'), report_path, result)
with open(report_path, encoding='utf-8') as file:
    text = file.read()
check('report: the file is saved and lists both cards', result['saved'] and 'sets (edited)' in text and '/ and //' in text)
result = {'saved': False, 'error': ''}
report.write_report([], os.path.join(folder, 'no such folder', 'report.txt'), result)
check('report: a folder that does not exist is reported, not a crash', not result['saved'] and result['error'] != '')

http.shutdown()
print()
print(passed, 'passed,', failed, 'failed')
