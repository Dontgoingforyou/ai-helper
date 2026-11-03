class AppError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class InvalidInputError(AppError):
    pass


class LLMError(AppError):
    pass


class OutputCheckError(AppError):
    pass
