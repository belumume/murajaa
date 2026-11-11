from datetime import date, timedelta

# days to wait before a card in each box comes back
INTERVALS = {1: 1, 2: 2, 3: 4, 4: 7, 5: 14}
LAST_BOX = 5
# the longest text each field may hold
LIMITS = {'name': 40, 'deck': 30, 'question': 300, 'answer': 500}


class CardError(Exception):
    """Raised when a card is given a missing or wrong value, or does not exist."""


class NotDueError(CardError):
    """Raised when a card is answered before its due date."""


def check_text(field: str, value: str) -> str:
    # used by the server on every value that comes from the window
    value = value.strip()
    if value == '':
        raise CardError('The ' + field + ' must not be empty.')
    if len(value) > LIMITS[field]:
        raise CardError('The ' + field + ' can have at most ' + str(LIMITS[field]) + ' characters.')
    return value


class Card:
    def __init__(self, name: str, deck: str, question: str, answer: str, box: int = 1,
                 due: date | None = None, card_id: int | None = None):
        # the server checks the text with check_text before it makes a card
        self.name = name
        self.deck = deck
        self.question = question
        self.answer = answer
        if box not in INTERVALS:
            raise CardError('The box must be a number from 1 to ' + str(LAST_BOX) + '.')
        self.box = box
        # a new card is due at once
        self.due = due if due is not None else date.today()
        self.card_id = card_id

    def is_due(self, today: date) -> bool:
        return self.due <= today

    def record_answer(self, knew_it: bool, today: date) -> None:
        # a second click on the same card must not move it again
        if not self.is_due(today):
            raise NotDueError('That card was already answered. It is due again on ' + self.due.isoformat() + '.')
        # right: one box up, so it waits longer; wrong: back to box 1
        if knew_it:
            self.box = min(self.box + 1, LAST_BOX)
        else:
            self.box = 1
        self.due = today + timedelta(days=INTERVALS[self.box])

    def to_dict(self) -> dict:
        return {'id': self.card_id, 'name': self.name, 'deck': self.deck, 'question': self.question,
                'answer': self.answer, 'box': self.box, 'due': self.due.isoformat()}
