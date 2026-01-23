import functools
import warnings


class TokenInvalidError(Exception):
    pass


class TokenExchangeError(Exception):
    pass


class TokenMissingError(Exception):
    pass


class CircuitOpenError(Exception):
    pass


class RequestFailedError(Exception):
    pass


def deprecated(reason="此函数已弃用"):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(f"{func.__name__} 已弃用: {reason}", category=DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        return wrapper

    return decorator
