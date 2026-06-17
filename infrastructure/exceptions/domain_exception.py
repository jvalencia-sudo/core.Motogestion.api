import starlette.status


class DomainException(Exception):
    def __init__(
        self,
        message: str,
        code: int = starlette.status.HTTP_400_BAD_REQUEST,
        *args,
    ):
        self.message: str = message
        self.code = code
        self.arguments = args
        super().__init__(self.message)
