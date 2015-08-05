

class UnsupportedProvider(Exception):

    def __init__(self, provider, *args, **kwargs):
        self.provider = provider
        message = "Unsupported provider: %s" % (provider,)
        super(UnsupportedProvider, self).__init__(message, *args, **kwargs)


class UnsupportedPlatform(Exception):

    def __init__(self, platform, *args, **kwargs):
        self.platform = platform
        message = "Unsupported platform: %s" % (platform,)
        super(UnsupportedPlatform, self).__init__(message, *args, **kwargs)


class ProviderError(Exception):
    pass


class TokenAlreadyRegistered(Exception):
    pass
