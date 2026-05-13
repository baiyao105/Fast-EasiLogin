import functools
import warnings


class TokenInvalidError(Exception):
    pass


class TokenExchangeError(Exception):
    pass


class TokenMissingError(Exception):
    pass


class CircuitOpenError(Exception):
    def __init__(self, message: str = "熔断器已打开, 请求被拦截"):
        super().__init__(message)


class RequestFailedError(Exception):
    def __init__(self, message: str = "请求失败, 已达最大重试次数"):
        super().__init__(message)


def deprecated(reason="此函数已弃用"):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(f"{func.__name__} 已弃用: {reason}", category=DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        return wrapper

    return decorator
