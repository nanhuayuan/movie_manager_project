# app/core/exceptions.py
class MediaServiceError(Exception):
    """Base exception for media service"""
    pass

class ResourceNotFoundError(MediaServiceError):
    """Resource not found"""
    pass

class DuplicateError(MediaServiceError):
    """Duplicate resource"""
    pass

class ProcessingError(MediaServiceError):
    """Processing error"""
    pass