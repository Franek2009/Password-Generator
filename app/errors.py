"""Stable error identifiers for translation; ValueError compatibility is retained."""


class GenerationError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
