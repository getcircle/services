

class Unauthorized(Exception):
    """Exception raised when the user doesn't have the permissions to perform an action"""


class AlreadyRequested(Exception):
    """Exception raised when the user has already requested to join the group"""
