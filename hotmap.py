from hotqueue import HotQueue
from uuid import uuid4

"""HotMap is a proof-of-concept distributed computing framework
for Python built on top of Redis and HotQueue"""

class HotMap(object):

    def __init__(self, name, *args, **kwargs):
        """All constructor arguments are passed straight through
        to HotQueue. See the HotQueue docs for details"""
        self._name = name
        self._hotqueue_args = args
        self._hotqueue_kwargs = kwargs
        self._outbound_queue = self._get_queue()

    def _get_queue(self, postfix=None):
        name = self._name
        if postfix:
            name += ':%s' % postfix
        return HotQueue(name, *self._hotqueue_args, **self._hotqueue_kwargs)

    def map(self, items):
        """Return a generator that yields each item in the
        provided iterable after passing it through a remote
        worker function. Example:

        >>> for processed_item in mapper.map([1, 2, 3]):
        ...     print processed_item
        """
        item_ids = []
        for item in items:
            item_id = uuid4()
            item_ids.append(item_id)
            self._outbound_queue.put((item_id, item))

        for item_id in item_ids:
            return_queue = self._get_queue(item_id)
            yield return_queue.get(block=True)

    def worker(self, function):
        """Decorator to convert a function into a worker. The
        decorated function should accept a single argument,
        and return a single value. After it has been decorated,
        the function will have an extra property called `wait`
        which is a function that, when called, blocks until an
        item is received for processing. It then calls the
        original function, passing in the value to be processed,
        and returns the result to the remote code. Example:

        >>> @mapper.worker
        ... def square(number):
        ...     return number * number
        >>> square.wait()
        """
        def wait(task):
            item_id, item = task
            return_value = function(item)
            return_queue = self._get_queue(item_id)
            return_queue.put(return_value)
        function.wait = self._outbound_queue.worker(wait)
        return function
