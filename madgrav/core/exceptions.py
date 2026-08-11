class MadgravError(Exception):
    """
    This root Madgrav exception is provided in case we ever want to provide common functionality
    across all Madgrav exceptions.
    """


class BadFileError(MadgravError):
    """Abort loading a malformed file"""
