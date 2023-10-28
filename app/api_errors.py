""" API error class. """


class APIError(Exception):
    """ API error class. """
    def __init__(self, message: str, code: int):
        self._message = message
        self._code = code
        super().__init__(self._message)

    @property
    def message(self) -> str:
        """
        Get the message property.

        Returns:
            str: The value of the message property.
        """
        return self._message

    @property
    def code(self) -> int:
        """
        Returns the value of the `code` property.

        :return: An integer representing the value of the `code` property.
        :rtype: int
        """
        return self._code

    def __str__(self) -> str:
        """
        Returns a string representation of the object.

        :return: A string representation of the object.
        :rtype: str
        """
        return str(self._code) + ': ' + self._message
