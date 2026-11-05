# Four answers to the same card arrive at the same moment, as four threads.
# A card may be answered once a day, so exactly one of them should count.
# It runs the test 50 times with the lock of server.py, then 50 times without it.
import contextlib
import os
import tempfile
import threading

from cards import Card, NotDueError
from store import CardStore
import server


def four_answers_at_once():
    server.store = CardStore(os.path.join(tempfile.mkdtemp(), 'demo.db'))
    server.store.add(Card('Demo', 'question', 'answer'))
    counted = []

    def click():
        try:
            server.record_answer(1, True)
            counted.append(1)
        except NotDueError:
            pass

    threads = [threading.Thread(target=click) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return len(counted)


real_lock = server.answer_lock
for name, lock in (('with the lock', real_lock), ('without the lock', contextlib.nullcontext())):
    server.answer_lock = lock
    results = [four_answers_at_once() for _ in range(50)]
    exactly_one = results.count(1)
    print(name + ': exactly one answer counted in', exactly_one, 'of 50 runs; at most', max(results), 'counted in one run')
