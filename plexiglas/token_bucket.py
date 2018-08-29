"""
Copied from https://gist.github.com/drocco007/6155452, thanks @drocco007!
"""

from time import sleep, time


class TokenBucket(object):
    """An implementation of the token bucket algorithm.
    >>> bucket = TokenBucket(80, 0.5)
    >>> print bucket.consume(10)
    True
    adapted from http://code.activestate.com/recipes/511490-implementation-of-the-token-bucket-algorithm/?in=lang-python
    Not thread safe.
    """

    __slots__ = ['capacity', '_tokens', 'fill_rate', 'timestamp']

    def __init__(self, tokens, fill_rate):
        """tokens is the total tokens in the bucket. fill_rate is the
        rate in tokens/second that the bucket will be refilled."""
        self.capacity = float(tokens)
        self._tokens = float(tokens)
        self.fill_rate = float(fill_rate)
        self.timestamp = time()

    def consume(self, tokens, block=True):
        """Consume tokens from the bucket. Returns True if there were
        sufficient tokens.
        If there are not enough tokens and block is True, sleeps until the
        bucket is replenished enough to satisfy the deficiency.
        If there are not enough tokens and block is False, returns False.
        It is an error to consume more tokens than the bucket capacity.
        """

        assert tokens <= self.capacity, \
            'Attempted to consume {} tokens from a bucket with capacity {}' \
                .format(tokens, self.capacity)

        if block and tokens > self.tokens:
            deficit = tokens - self._tokens
            delay = deficit / self.fill_rate

            # print 'Have {} tokens, need {}; sleeping {} seconds'.format(self._tokens, tokens, delay)
            sleep(delay)

        if tokens <= self.tokens:
            self._tokens -= tokens
            return True
        else:
            return False

    @property
    def tokens(self):
        if self._tokens < self.capacity:
            now = time()
            delta = self.fill_rate * (now - self.timestamp)
            self._tokens = min(self.capacity, self._tokens + delta)
            self.timestamp = now
        return self._tokens


def rate_limit(data, bandwidth_or_burst, steady_state_bandwidth=None):
    """Limit the bandwidth of a generator.
    Given a data generator, return a generator that yields the data at no
    higher than the specified bandwidth.  For example, ``rate_limit(data, _256k)``
    will yield from data at no higher than 256KB/s.
    The three argument form distinguishes burst from steady-state bandwidth,
    so ``rate_limit(data, 1024 * 1024, 128 * 1024)`` would allow data to be consumed at
    128KB/s with an initial burst of 1MB.
    """

    bandwidth = steady_state_bandwidth or bandwidth_or_burst
    rate_limiter = TokenBucket(bandwidth_or_burst, bandwidth)

    for thing in data:
        rate_limiter.consume(len(str(thing)))
        yield thing
