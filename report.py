# Writes every saved card to a text report. Start server.py first, then run:
#   python report.py              (writes report.txt)
#   python report.py my_cards.txt (writes my_cards.txt)
import sys
import threading
from datetime import date

from client import ServerError, ask_server
from cards import INTERVALS


def build_report(cards: list[dict]) -> str:
    today = date.today().isoformat()
    # deck name -> the cards in that deck
    decks = {}
    for card in cards:
        if card['deck'] not in decks:
            decks[card['deck']] = []
        decks[card['deck']].append(card)
    due = [card for card in cards if card['due'] <= today]
    lines = ['Murajaa report, ' + today,
             str(len(cards)) + ' cards in ' + str(len(decks)) + ' decks, ' + str(len(due)) + ' due today',
             '']
    for deck, deck_cards in decks.items():
        # box number -> how many cards of this deck are in it
        counts = {box: 0 for box in INTERVALS}
        for card in deck_cards:
            counts[card['box']] += 1
        boxes = ', '.join('box ' + str(box) + ': ' + str(counts[box]) for box in INTERVALS)
        lines.append(deck + ' (' + str(len(deck_cards)) + ' cards; ' + boxes + ')')
        for card in deck_cards:
            lines.append('  ' + str(card['id']).rjust(3) + '  box ' + str(card['box']) + '  due '
                         + card['due'] + '  ' + card['name'])
        lines.append('')
    return '\n'.join(lines)


def write_report(cards: list[dict], path: str, result: dict) -> None:
    # runs in the worker thread; result tells the main thread how it went
    try:
        with open(path, 'w', encoding='utf-8') as file:
            file.write(build_report(cards))
        result['saved'] = True
    except OSError as error:
        # for example a folder that does not exist, or a file open in another program
        result['error'] = str(error)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'report.txt'
    try:
        cards = ask_server('/cards')
    except ServerError as error:
        print('Could not get the cards:', error)
        return
    result = {'saved': False, 'error': ''}
    writer = threading.Thread(target=write_report, args=(cards, path, result))
    writer.start()
    writer.join()  # wait for the thread before reading result
    if result['saved']:
        print('Saved', len(cards), 'cards to', path)
    else:
        print('The report was not saved:', result['error'])


if __name__ == '__main__':
    main()
