#!/usr/bin/env python
#
# test_callqueue.py -
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#

import time
import threading
import logging
import numpy as np

import fsleyes_props.callqueue as callqueue


def test_call():

    ncalls = 10
    called = [0] * ncalls
    calls  = []

    for i in range(ncalls):
        def func(ii=i):
            called[ii] = ii

        calls.append(func)

    q = callqueue.CallQueue()

    for i, c in enumerate(calls):
        q.call(c, 'Call {}'.format(i))

    assert called == list(range(ncalls))


# callqueu has some internal functions that are
# only called if logging level >= DEBUG
def test_debug():

    def func():
        pass

    logging.basicConfig()
    log = logging.getLogger('fsleyes_props.callqueue')
    log.setLevel(logging.DEBUG)

    q = callqueue.CallQueue()
    q.call(func, 'func', ())

    log.setLevel(logging.WARNING)


def test_callAll():

    ncalls = 10
    called = [0] * ncalls
    calls  = []

    for i in range(ncalls):
        def func(ii=i):
            called[ii] = ii

        calls.append(func)

    q     = callqueue.CallQueue()
    calls = [(c, 'Call {}'.format(i), (), {}) for i, c in enumerate(calls)]

    q.callAll(calls)

    assert called == list(range(ncalls))


def test_call_raise():

    def badfunc():
        raise Exception('Call that was supposed to crash crashed!')

    # Not crashing means the test passes
    q = callqueue.CallQueue()
    q.call(badfunc, 'Bad function', ())


def test_dequeue():

    q      = callqueue.CallQueue()
    called = [False, False]

    def func0():
        q.dequeue('func1')
        called[0] = True

    def func1():
        called[1] = True

    calls = [(func0, 'func0', (), {}), (func1, 'func1', (), {})]

    q.callAll(calls)

    assert     called[0]
    assert not called[1]


def test_call_recursive():

    q         = callqueue.CallQueue()
    callOrder = []

    def func0():
        callOrder.append(0)
        q.call(func1, 'func1')

    def func1():
        callOrder.append(1)

    def func2():
        callOrder.append(2)

    calls = [(func0, 'func0', (), {}), (func2, 'func2', (), {})]

    q.callAll(calls)

    assert callOrder == [0, 2, 1]


def test_call_threaded():

    q = callqueue.CallQueue()

    calltime = {}

    def func(delay):
        calltime[delay] = time.time()
        time.sleep(delay / 50.0)

    def threadfunc(delay):
        time.sleep(delay / 100.0)
        q.call(func, 'func_{}'.format(delay), delay)

    delays  = np.arange(1, 20)
    threads = [threading.Thread(target=threadfunc, args=(d,)) for d in delays]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    calltimes = [calltime[d] for d in delays]
    assert calltimes == sorted(calltimes)


def test_dequeue_threaded():

    q = callqueue.CallQueue()

    called = {}

    def func(delay):
        called[delay] = True
        time.sleep(delay / 5.0)

    def threadfunc():
        calls = [(func, 'slowfunc', (5,), {}),
                 (func, 'fastfunc', (1,), {})]
        q.callAll(calls)

    t = threading.Thread(target=threadfunc)

    t.start()
    time.sleep(0.1)

    q.dequeue('fastfunc')
    t.join()

    assert     called[5]
    assert not called.get(1, False)


def test_skipDuplicates():   _test_skipDuplicates(True)
def test_noSkipDuplicates(): _test_skipDuplicates(False)
def _test_skipDuplicates(skip):


    nthreads = 5
    q        = callqueue.CallQueue(skipDuplicates=skip)
    ncalls   = [0]

    def func():
        ncalls[0] += 1
        time.sleep(0.5)

    def threadfunc(name):
        q.call(func, name)

    threads = [threading.Thread(target=threadfunc, args=('func', ))
               for i in range(nthreads)]
    blockt  = threading.Thread(target=threadfunc, args=('block',))

    blockt.start()
    for t in threads:
        t.start()

    blockt.join()
    for t in threads:
        t.join()

    if skip: assert ncalls[0] == 2
    else:    assert ncalls[0] == nthreads + 1


def test_dequeue_noSkipDuplicates():

    nthreads = 5

    q = callqueue.CallQueue(skipDuplicates=True)

    ncalls = [0]

    def func():
        ncalls[0] += 1
        time.sleep(0.5)

    def threadfunc(name):
        q.call(func, name)

    threads = [threading.Thread(target=threadfunc, args=('func', ))
               for i in range(nthreads)]
    blockt  = threading.Thread(target=threadfunc, args=('block',))

    blockt.start()
    time.sleep(0.1)
    for t in threads:
        t.start()
    q.dequeue('func')

    blockt.join()
    for t in threads:
        t.join()

    assert ncalls[0] == 1


def test_hold():

    q      = callqueue.CallQueue()
    called = {}

    def func(name):
        called[name] = called.get(name, 0) + 1

    q.call(func, 'one', 'one')
    q.hold()
    q.call(func, 'two',   'two')
    q.call(func, 'three', 'three')
    q.call(func, 'four',  'four')

    # clearheld should only
    # return functions when
    # the queue is not being
    # held
    assert q.clearHeld() == []

    assert called['one'] == 1
    assert 'two'   not in called
    assert 'three' not in called
    assert 'four'  not in called

    # Try and dequeue a held function
    q.dequeue('two')
    q.release()
    q.call(func, 'five', 'five')

    assert called['five'] == 1
    assert 'two'   not in called
    assert 'three' not in called
    assert 'four'  not in called

    q.callAll(q.clearHeld())

    assert called['one']   == 1
    assert 'two'  not in called
    assert called['three'] == 1
    assert called['four']  == 1
    assert called['five']  == 1

def test_hold_threaded():

    # TODO
    assert True
