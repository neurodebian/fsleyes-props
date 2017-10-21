#!/usr/bin/env python
#
# callqueue.py - A queue for calling functions sequentially.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""This module provides the :class:`CallQueue` class, which is used by
:class:`.PropertyValue` instances to enqueue and execute property listener
callback functions.
"""


import logging

import six.moves.queue as queue

import fsl.utils.async as async


log = logging.getLogger(__name__)


class Call(object):
    """A little class which is used to represent function calls that are
    on the queue.
    """

    def __init__(self, func, name, args, kwargs):
        self.func    = func
        self.name    = name
        self.args    = args
        self.kwargs  = kwargs
        self.execute = True

        # The CallQueue.dequeue method sets the
        # above execute attribute to False for
        # calls which are to be dequeued - this
        # causees the CallQueue.__call method
        # to skip over the call.


class CallQueue(object):
    """A queue of functions to be called. Functions can be enqueued via
    the :meth:`call` or :meth:`callAll` methods.
    """

    def __init__(self, skipDuplicates=False):
        """Create a ``CallQueue`` instance.

        If ``skipDuplicates`` is ``True``, a function which is already on
        the queue will be silently dropped if an attempt is made to add it
        again.

          .. note::

             The ``skipDuplicates`` test is based solely on the name of the
             function. This means that the ``CallQueue`` does not support
             enqueueing the same function with different arguments.

             Testing for function *and* argument equality is a difficult task:

               - I can't take the hash of the arguments, as I can't assume
                 that they are hashable (e.g.  ``numpy`` arrays).

               - I can't test for identity, as things which have the same
                 value may not have the same id (e.g. strings).

               - I can't test argument equality, because in some cases the
                 argument may be a mutable type (e.g. a ``list``), and its
                 value may have changed between the time the function was
                 queued, and the time it is called. *And* the arguments might
                 be big (again, ``numpy`` arrays), so an equality test could
                 be expensive.

             So this is quite a pickle. Something to come back to if things
             are breaking because of it.


        **Holding the queue**


        The :meth:`hold` method temporarily stops the ``CallQueue`` from
        queueing and executing functions. Any functions which are enqueued
        while the queue is held are kept in a separate queue. The queue is
        released via the :meth:`release` method, after which any held
        functions may be accessed via the :meth:`clearHeld` method (which
        also clears the internal queue of held functions). Once the queue
        has been released, these held functions can be re-queued as normal
        via the :meth:`call` or :meth:`callAll` methods.
        """

        # The queue is a queue of Call instances
        #
        # The queued dict contains mappings of
        # {name : [List of Call instances]}
        #
        self.__queue          = queue.Queue()
        self.__queued         = {}
        self.__skipDuplicates = skipDuplicates
        self.__calling        = False


        # Every call to hold will increment
        # this count, and every call to
        # release will decrement it.
        self.__holding        = 0


        # If the queue is being held, enqueued
        # functions are added to this list
        self.__held           = []


    @async.mutex
    def dequeue(self, name):
        """If the specified function is on the queue, it is (effectively)
        dequeued, and not executed.

        If ``skipDuplicates`` is ``False``, and more than one function of
        the same name is enqueued, they are all dequeued.
        """

        # Get all calls with the specified name
        calls = self.__queued.get(name, [])

        # Set each of their execute flags to
        # False - the __call method will skip
        # over Call instances with execute=False
        for call in calls:

            self.__debug(call, 'Dequeueing function', 'from queue')
            call.execute = False

        # Check the held queue as well
        for call in self.__held:
            if call.name == name:
                self.__debug(call, 'Dequeueing held function', 'from queue')
                call.execute = False


    def call(self, func, name, *args, **kwargs):
        """Enqueues the given function, and calls all functions in the queue

        (unless the call to this method was as a result another function
        being called from the queue).
        """

        if self.__push(Call(func, name, args, kwargs)):
            self.__call()


    def callAll(self, funcs):
        """Enqueues all of the given functions, and calls all functions in
        the queue.

        (unless the call to this method was as a result another function
        being called from the queue).

        Assumes that the given ``funcs`` parameter is a list of
        ``(function, name, args, kwargs)`` tuples.
        """

        anyEnqueued = False

        for func in funcs:
            if self.__push(Call(*func)):
                anyEnqueued = True

        if anyEnqueued:
            self.__call()


    @async.mutex
    def hold(self):
        """Holds the queue. For every call to ``hold``, the :meth:`release`
        method must be called once before the queue will be truly released.
        """
        self.__holding += 1


    @async.mutex
    def release(self):
        """Releases the queue. """
        self.__holding -= 1


    @async.mutex
    def clearHeld(self):
        """Clears and returns the list of held functions. """

        if self.__holding > 0:
            return []

        held = self.__held
        self.__held = []
        return [(c.func, c.name, c.args, c.kwargs) for c in held if c.execute]


    def __call(self):
        """Call all of the functions which are currently enqueued.

        This method is not re-entrant - if a call to one of the
        functions in the queue triggers another call to this method,
        this second call will return immediately without doing anything.
        """

        if self.__calling: return
        self.__calling = True

        while True:

            try:
                call = self.__pop()

                if not call.execute:
                    self.__debug(call, 'Skipping dequeued function')
                    continue

                self.__debug(call, 'Calling function')

                try:
                    call.func(*call.args, **call.kwargs)

                except Exception as e:
                    import traceback
                    log.warning('Function {} raised exception: {}'.format(
                        call.name, e), exc_info=True)
                    traceback.print_stack()

            except queue.Empty:
                break

        self.__calling = False


    @async.mutex
    def __push(self, call):
        """Enqueues the given ``Call`` instance.

        If the queue has been held (see :meth:`hold`), the call is
        stored, and ``False`` is returned.

        If ``True`` was passed in for the ``skipDuplicates`` parameter
        during initialisation, and the function is already enqueued,
        it is not added to the queue, and this method returns ``False``.

        Otherwise, this method returnes ``True``.
        """

        enqueued = self.__queued.get(call.name, [])

        if self.__holding > 0:
            self.__debug(call, 'Holding function')
            self.__held.append(call)
            return False

        # Skip this function if there are already
        # functions in the queue with the same name
        if self.__skipDuplicates and (len(enqueued) > 0):
            self.__debug(call, 'Skipping function')
            return False

        self.__debug(call, 'Queueing function', 'to queue')

        self.__queue.put_nowait(call)
        self.__queued[call.name] = enqueued + [call]

        return True


    @async.mutex
    def __pop(self):
        """Pops the next function from the queue and returns the ``Call``
        instance which encapsulates it.
        """

        call     = self.__queue.get_nowait()
        enqueued = self.__queued[call.name]

        # TODO shouldn't the call always
        # be at the end of the list?
        #
        # This will be a little bit faster
        # if you remove the call by index.
        enqueued.remove(call)

        if len(enqueued) == 0:
            self.__queued.pop(call.name)

        return call


    def __debug(self, call, prefix, postfix=None):
        """Prints a standardised log message."""

        if log.getEffectiveLevel() != logging.DEBUG:
            return

        funcName, modName = self.__getCallbackDetails(call.func)

        if postfix is None: postfix = ' '
        else:               postfix = ' {} '.format(postfix)

        log.debug('{} {} [{}.{}]{}({} in queue)'.format(
            prefix,
            call.name,
            modName,
            funcName,
            postfix,
            self.__queue.qsize()))


    def __getCallbackDetails(self, cb):
        """Returns the function name and module name of the given
        function reference. Used purely for debug log statements.
        """

        import inspect

        if log.getEffectiveLevel() != logging.DEBUG:
            return '', ''

        members = inspect.getmembers(cb)

        funcName  = ''
        modName   = ''

        for name, val in members:
            if name == '__func__':
                funcName  = val.__name__
                modName   = val.__module__
                break

        return funcName, modName
