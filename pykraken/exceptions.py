"""
Defines exceptions that are thrown by the kraken client.
"""


class ApiError(Exception):
    """Represents an exception returned by the remote API."""

    def __init__(self, status, message=None):
        self.status = status
        self.message = message

    def __str__(self):
        if self.message is None:
            return self.status
        else:
            return "%s (%s)" % (self.status, self.message)


class TransportError(Exception):
    """Something went wrong while trying to execute the request."""

    def __init__(self, base_exception=None):
        self.base_exception = base_exception

    def __str__(self):
        if self.base_exception:
            return str(self.base_exception)

        return "An unknown error occurred."


class HTTPError(TransportError):
    """An unexpected HTTP error occurred."""

    def __init__(self, status_code):
        self.status_code = status_code

    def __str__(self):
        return "HTTP Error: %d" % self.status_code


class Timeout(Exception):
    """The request timed out."""
    pass


class _RetriableRequest(Exception):
    """Signifies that the request can be retried."""
    pass


class _InvalidRequest(Exception):
    """Signifies that the request is invalid."""
    pass


class BadParamterError(Exception):
    """Signifies that the parameter passed is incorrect."""

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return "Bad parameter error: {}".format(self.message)


class RequiredParameterError(Exception):
    """Signifies that the parameter is required"""

    def __init__(self, required):
        self.required = required

    def __str__(self):
        return "Parameter {} is required".format(self.required)
