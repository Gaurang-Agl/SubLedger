class DomainException(Exception):
    """Base domain exception."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundException(DomainException):
    """Resource not found."""
    pass


class BusinessRuleException(DomainException):
    """Business rule violation."""
    pass


class ConflictException(DomainException):
    """Resource conflict (e.g. duplicate unique field)."""
    pass
