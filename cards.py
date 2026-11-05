from datetime import date, timedelta

# days to wait before a card in each box comes back
INTERVALS = {1: 1, 2: 2, 3: 4, 4: 7, 5: 14}
LAST_BOX = 5


class CardError(Exception):
    """Raised when a card is given a missing or wrong value."""


class NotDueError(CardError):
    """Raised when a card is answered before its due date."""


class Card:
    def __init__(self, deck: str, front: str, back: str, box: int = 1,
                 due: date | None = None, card_id: int | None = None):
        deck = deck.strip()
        front = front.strip()
        back = back.strip()
        if deck == '' or front == '' or back == '':
            raise CardError('Deck, question and answer must not be empty.')
        # the deck name becomes part of a URL such as /study/<deck>
        if '/' in deck or deck.strip('.') == '':
            raise CardError('A deck name cannot contain / or be only dots.')
        if box not in INTERVALS:
            raise CardError('box must be a number from 1 to ' + str(LAST_BOX))
        self.card_id = card_id
        self.deck = deck
        self.front = front
        self.back = back
        self.box = box
        # a new card is due at once
        self.due = due if due is not None else date.today()

    def is_due(self, today: date) -> bool:
        return self.due <= today

    def answer(self, knew_it: bool, today: date) -> None:
        # a second click on the same card must not move it again
        if not self.is_due(today):
            raise NotDueError('card ' + str(self.card_id) + ' is not due until ' + self.due.isoformat())
        # right: one box up, so it waits longer; wrong: back to box 1
        if knew_it:
            self.box = min(self.box + 1, LAST_BOX)
        else:
            self.box = 1
        self.due = today + timedelta(days=INTERVALS[self.box])

    def to_dict(self) -> dict:
        return {'id': self.card_id, 'deck': self.deck, 'front': self.front,
                'back': self.back, 'box': self.box, 'due': self.due.isoformat()}

    def __str__(self) -> str:
        return self.deck + ' | box ' + str(self.box) + ' | ' + self.front
