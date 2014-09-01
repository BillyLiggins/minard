from redis import StrictRedis
from itertools import chain

redis = StrictRedis()

HMINCRBY = """
local k
for i, v in ipairs(ARGV) do
    if i % 2 == 1 then
        k = v
    else
        redis.call('HINCRBY', KEYS[1], k, tonumber(v))
    end
end
return true
"""

HMDIV = """
for i, v in ipairs(ARGV) do
    local n = tonumber(redis.call('HGET', KEYS[2], v))
    local d = tonumber(redis.call('HGET', KEYS[3], v))
    redis.call('HSET', KEYS[1], v, n/d)
end
return true
"""

AVGRANGE = """
local start = tonumber(ARGV[1])
local stop = tonumber(ARGV[2])
local n = 0
local sum = 0
for i=start,stop do
    local v = redis.call('HGET', KEYS[1], i)
    if v then
        sum = sum + tonumber(v)
        n = n + 1
    end
end

if n > 0 then
    return string.format('%g',sum/n)
else
    return nil
end
"""

MAXRANGE = """
local start = tonumber(ARGV[1])
local stop = tonumber(ARGV[2])
local max = nil
for i=start, stop do
    local v = redis.call('HGET', KEYS[1], i)
    if v then
        v = tonumber(v)

        if max == nil or v > max then
            max = v
        end
    end
end

if max == nil then
    return max
else
    return string.format('%g', max)
end
"""

_hmincrby = redis.register_script(HMINCRBY)
_hmdiv = redis.register_script(HMDIV)
_avgrange = redis.register_script(AVGRANGE)
_maxrange = redis.register_script(MAXRANGE)

def maxcard(key, crate, card, client=None):
    """
    Returns the maximum field value for channels in card `card`
    and crate `crate`.
    """
    start = crate << 9 + card << 5
    stop = start + 32
    return _maxrange(keys=[key], args=[start,stop], client=client)

def maxcrate(key, crate, client=None):
    """Returns the maximum field value for channels in `crate`."""
    start = crate << 9
    stop = start + 16*32
    return _maxrange(keys=[key], args=[start,stop], client=client)

def avgcard(key, crate, card, client=None):
    """
    Returns the average field value for channels in card `card`
    and crate `crate`, not counting missing or 0 values.
    """
    start = crate << 9 + card << 5
    stop = start + 32
    return _avgrange(keys=[key], args=[start,stop], client=client)

def avgcrate(key, crate, client=None):
    """
    Averages the hash fields for channels in a crate, not counting
    any missing or 0 values.
    """

    Example:
        >>> redis.hmset('spam', {3584: 1, 3589: 100, 9728: 1e6})
        True
        >>> avgcrate('spam', 7)
        '50.5'
        >>> avgcrate('spam',19)
        '1e+06'
        >>> avgcrate('spam',0)
        None
    """
    start = crate << 9
    stop = start + 16*32
    return _avgrange(keys=[key], args=[start,stop], client=client)

def hmincrby(key, mapping, client=None):
    """
    Increment multiple fields in the hash stored at `key`.

    Example:
        >>> redis.hmset('spam', {'a': 0, 'b': 1})
        True
        >>> hmincr('spam', {'a': 10, 'b': 1})
        1L
        >>> redis.hgetall('spam')
        {'a': '10', 'b': '2'}
    """
    args = chain.from_iterable(mapping.items())
    return _hmincrby(keys=[key], args=args, client=client)

def hmdiv(result, a, b, fields, client=None):
    """
    Divide multiple fields in the hash stored at `a` by
    fields in `b` and store the result in `result`.

    Example:
        >>> redis.hmset('a', {'a': 1, 'b': 2})
        True
        >>> redis.hmset('b', {'a': 2, 'b': 2})
        True
        >>> hmdiv('c','a','b', ['a','b'])
        1L
        >>> redis.hgetall('c')
        {'a': '0.5', 'b': '1'}
    """
    return _hmdiv(keys=[result,a,b], args=fields, client=client)