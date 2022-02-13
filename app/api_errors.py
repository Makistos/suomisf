class APIError(Exception):
    def __init__(self, message: str, code: int):
        self._message = message
        self._code = code
        super().__init__(self._message)

    @property
    def message(self) -> str:
        return self._message

    @property
    def code(self) -> int:
        return self._code

    def __str__(self) -> str:
        return str(self._code) + ': ' + self._message
