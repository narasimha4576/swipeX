import threading
import time

_store = {}
_lock = threading.Lock()


def cached(key, seconds, build):
    """Returns the remembered value for `key`, or runs `build()` and remembers it for `seconds`."""
    now = time.monotonic()
    with _lock:
        hit = _store.get(key)
        if hit and hit[0] > now:
            return hit[1]
    value = build()
    with _lock:
        _store[key] = (time.monotonic() + seconds, value)
    return value


def clear_cache():
    with _lock:
        _store.clear()