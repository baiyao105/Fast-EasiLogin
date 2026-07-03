class LoginFailedError(Exception):
    """登录失败"""

    def __init__(self, message: str = "登录失败", status_code: int = 401):
        self.status_code = status_code
        super().__init__(message)


class NetworkError(Exception):
    """网络错误"""

    def __init__(self, message: str = "网络错误", status_code: int = 504):
        self.status_code = status_code
        super().__init__(message)


class RequestFailedError(Exception):
    """请求失败"""

    def __init__(self, message: str = "Request failed", url: str = "", max_attempts: int = 0):
        self.url = url
        self.max_attempts = max_attempts
        if url and max_attempts:
            super().__init__(f"{message} after {max_attempts} attempts: url={url}")
        else:
            super().__init__(message)


class HttpClientNotInitializedError(Exception):
    """HTTP 客户端未初始化"""

    def __init__(self):
        super().__init__("HttpClientManager not initialized, call init() first")
