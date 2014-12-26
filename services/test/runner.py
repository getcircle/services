from django.test.runner import DiscoverRunner
from ..bootstrap import Bootstrap


class ServicesTestSuiteRunner(DiscoverRunner):

    def run_tests(self, *args, **kwargs):
        Bootstrap.bootstrap()
        return super(ServicesTestSuiteRunner, self).run_tests(*args, **kwargs)
