class LoginFailedError(Exception):
    def __init__(self, message: str = "登录失败", status_code: int = 401):
        self.status_code = status_code
        super().__init__(message)


class NetworkError(Exception):
    def __init__(self, message: str = "网络错误", status_code: int = 504):
        self.status_code = status_code
        super().__init__(message)


class RequestFailedError(Exception):
    def __init__(self, message: str = "请求失败, 已达最大重试次数"):
        super().__init__(message)
