import logging
import time
import sys

from dogapi import dog_stats_api
from invoke import (
    run,
    task,
)


def execute_with_settings(command, settings='local', **kwargs):
    run(
        'DJANGO_SETTINGS_MODULE=services.settings.%s ./manage.py %s' % (settings, command),
        **kwargs
    )


@task(help={
    'failfast': 'Flag for whether or not you want to fail on the first test failure',
    'keepdb': 'Flag for whether or not you want to reuse the test db',
})
def test(app='', failfast=False, keepdb=False):
    """Trigger a test run"""
    test_args = []
    if failfast:
        test_args.append('--failfast')
    if keepdb:
        test_args.append('-k')
    execute_with_settings('test %s %s' % (' '.join(test_args), app,), pty=True)


@task
def qt(app):
    """Trigger a test run, defaulting to keep database and fail fast"""
    test(app, failfast=True, keepdb=True)


@task
def serve():
    """Serve the development server"""
    execute_with_settings('runserver', pty=True)


@task(help={'remote': 'The deis remote you want to push to'})
def release(remote='deis'):
    """Trigger a release to a deis environment"""
    # XXX look into why invoke causes an issue with this
    #logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    #dog_stats_api.start(api_key='6253fdebf2c8e3648d5eba97a9ba92bf')
    #with dog_stats_api.timer(
        #'deis.release.time',
        #tags=['deis', 'release', 'release.%s' % (remote,)]
    #):
    run('time git push %s master' % (remote,))


@task
def release_all():
    """Release to staging and production"""
    run('time git push deis master && time git push production master')


@task
def manage(command, settings='local'):
    """Execute a manage command with the given settings"""
    execute_with_settings(command, settings=settings, pty=True)
