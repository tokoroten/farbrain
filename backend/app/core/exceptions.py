"""Custom exception classes for FarBrain application."""


class FarBrainException(Exception):
    """Base exception for all FarBrain-specific errors."""

    def __init__(self, message: str, details: str | None = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class SessionNotFoundError(FarBrainException):
    """Raised when a session is not found."""

    def __init__(self, session_id: str):
        super().__init__(
            message=f"Session not found: {session_id}",
            details="The requested session does not exist"
        )
        self.session_id = session_id


class SessionNotAcceptingIdeasError(FarBrainException):
    """Raised when attempting to add ideas to a session that is not accepting them."""

    def __init__(self, session_id: str):
        super().__init__(
            message=f"Session {session_id} is not accepting new ideas",
            details="The session has been paused or is no longer accepting submissions"
        )
        self.session_id = session_id


class SessionEndedError(FarBrainException):
    """Raised when attempting to interact with an ended session."""

    def __init__(self, session_id: str):
        super().__init__(
            message=f"Session {session_id} has ended",
            details="This session is no longer active"
        )
        self.session_id = session_id


class UserNotFoundError(FarBrainException):
    """Raised when a user is not found."""

    def __init__(self, user_id: str, session_id: str | None = None):
        message = f"User not found: {user_id}"
        if session_id:
            message += f" in session {session_id}"
        super().__init__(
            message=message,
            details="The requested user does not exist or is not part of the session"
        )
        self.user_id = user_id
        self.session_id = session_id


class IdeaNotFoundError(FarBrainException):
    """Raised when an idea is not found."""

    def __init__(self, idea_id: str):
        super().__init__(
            message=f"Idea not found: {idea_id}",
            details="The requested idea does not exist"
        )
        self.idea_id = idea_id


class ClusterNotFoundError(FarBrainException):
    """Raised when a cluster is not found."""

    def __init__(self, cluster_id: int, session_id: str):
        super().__init__(
            message=f"Cluster {cluster_id} not found in session {session_id}",
            details="The requested cluster does not exist"
        )
        self.cluster_id = cluster_id
        self.session_id = session_id


class LLMServiceError(FarBrainException):
    """Raised when LLM service encounters an error."""

    def __init__(self, operation: str, original_error: Exception | None = None):
        message = f"LLM service error during {operation}"
        if original_error:
            message += f": {str(original_error)}"
        super().__init__(
            message=message,
            details="The language model service is temporarily unavailable"
        )
        self.operation = operation
        self.original_error = original_error


class EmbeddingServiceError(FarBrainException):
    """Raised when embedding service encounters an error."""

    def __init__(self, operation: str, original_error: Exception | None = None):
        message = f"Embedding service error during {operation}"
        if original_error:
            message += f": {str(original_error)}"
        super().__init__(
            message=message,
            details="The embedding service is temporarily unavailable"
        )
        self.operation = operation
        self.original_error = original_error


class ClusteringServiceError(FarBrainException):
    """Raised when clustering service encounters an error."""

    def __init__(self, operation: str, original_error: Exception | None = None):
        message = f"Clustering service error during {operation}"
        if original_error:
            message += f": {str(original_error)}"
        super().__init__(
            message=message,
            details="The clustering service encountered an error"
        )
        self.operation = operation
        self.original_error = original_error
