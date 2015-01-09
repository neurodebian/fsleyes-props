#!/usr/bin/env python
#
# callqueue.py - A queue for calling functions sequentially.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""The :mod:`callqueue` module provides the :class:`CallQueue` class, which
is used by :class:`~props.properties_value.PropertyValue` objects to enqueue
property listener callback functions.
"""

import logging
log = logging.getLogger(__name__)

import Queue
import inspect
import traceback

def _getCallbackDetails(cb):
    """Returns the function name and module name of the given
    function reference. Used purely for debug log statements.
    """
    
    members = inspect.getmembers(cb)

    funcName  = ''
    modName   = ''

    for name, val in members:
        if name == '__func__':
            funcName  = val.__name__
            modName   = val.__module__
            break

    return funcName, modName



class CallQueue(object):
    """A queue of functions to be called. Functions can be enqueued via
    the :meth:`call` or :meth:`callAll` methods.
    """

    def __init__(self, skipDuplicates=False):
        """Create a :class:`CallQueue` instance.

        If ``skipDuplicates`` is ``True``, a function which is already on
        the queue will be silently dropped if an attempt is made to add it
        again.
        """

        self._queue          = Queue.Queue()
        self._skipDuplicates = skipDuplicates
        self._queued         = set()
        self._calling        = False

        
    def _call(self):
        """Call all of the functions which are currently enqueued.

        This method is not re-entrant - if a call to one of the
        functions in the queue triggers another call to this method,
        this second call will return immediately without doing anything.
        """

        if self._calling: return
        self._calling = True

        while True:

            try:
                desc, func, args = self._pop()

                funcName, modName = _getCallbackDetails(func)

                log.debug('Calling listener {} [{}.{}] ({} in queue)'.format(
                    desc, modName, funcName, self._queue.qsize()))

                try: func(*args)
                except Exception as e:
                    log.warn('Listener {} raised exception: {}'.format(
                        desc, e), exc_info=True)
                    traceback.print_stack()
            except Queue.Empty:
                break

        self._calling = False


    def _push(self, desc, func, args):
        """Enqueues the given function, along with a description, and
        the arguments to pass it.

        If ``True`` was passed in for the ``skipDuplicates`` parameter
        during initialisation, and the function is already enqueued,
        it is not added to the queue, and this method returns ``False``.

        Otherwise, this method returnes ``True``.
        """
        if self._skipDuplicates:

            # We can't assume that the args will be hashable
            # (e.g. numpy arrays), so i'm taking a hash of
            # the string representation. This is not ideal,
            # and could break, as there's no guarantee that
            # two things with the same string representation
            # actually have the same value.
            #
            # Something to come back to if things are
            # breaking because of it.
            if (func, str(args)) in self._queued:
                return False
            else:
                self._queued.add((func, str(args)))
                
        self._queue.put_nowait((desc, func, args))
        return True

    
    def _pop(self):
        """Pops the next function from the queue and returns a 3-tuple
        containing the function description, the function, and the arguments
        to be passed to it.
        """

        desc, func, args = self._queue.get_nowait()

        if self._skipDuplicates:
            self._queued.remove((func, str(args)))
            
        return desc, func, args
        

    def call(self, desc, func, args):
        """Enqueues the given function, and calls all functions in the queue
        
        (unless the call to this method was as a result another function
        being called from the queue).
        """

        funcName, modName = _getCallbackDetails(func)
        log.debug('Adding listener {} [{}.{}] to queue ({} in queue)'.format(
            desc, modName, funcName, self._queue.qsize()))
        
        if self._push(desc, func, args):
            self._call()


    def callAll(self, funcs):
        """Enqueues all of the given functions, and calls all functions in
        the queue.
        
        (unless the call to this method was as a result another function
        being called from the queue).
        """
        
        anyEnqueued = False
        for func in funcs:
            desc, func, args = func
            funcName, modName = _getCallbackDetails(func)
            log.debug('Adding listener {} [{}.{}] '
                      'to queue ({} in queue)'.format(
                          desc, modName, funcName, self._queue.qsize())) 

            if self._push(desc, func, args):
                anyEnqueued = True

        if anyEnqueued:
            self._call()
