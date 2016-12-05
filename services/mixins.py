from .token import parse_token


class PreRunParseTokenMixin(object):

    def pre_run(self, *args, **kwargs):
        super(PreRunParseTokenMixin, self).pre_run(*args, **kwargs)
        self.parsed_token = parse_token(self.token)
