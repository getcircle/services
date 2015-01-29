import time
from dogapi import dog_stats_api
from invoke import (
    run,
    task,
)

dog_stats_api.start(api_key='6253fdebf2c8e3648d5eba97a9ba92bf', flush_in_thread=False)


def execute_with_settings(command, settings='local', **kwargs):
    run('DJANGO_SETTINGS_MODULE=services.settings.%s %s' % (settings, command), **kwargs)


@task(help={
    'fail-fast': 'Flag for whether or not you want to fail on the first test failure',
    'keep-db': 'Flag for whether or not you want to reuse the test db',
})
def test(app='', fail_fast=False, keep_db=False):
    """Trigger a test run"""
    test_args = []
    if fail_fast:
        test_args.append('--failfast')
    if keep_db:
        test_args.append('-k')
    execute_with_settings('./manage.py test %s %s' % (' '.join(test_args), app,), pty=True)


@task
def serve():
    """Serve the development server"""
    execute_with_settings('./manage.py runserver', pty=True)


@task(help={'deis-remote': 'The deis remote you want to push to'})
def release(deis_remote='deis'):
    """Trigger a release to a deis environment"""
    start = time.time()
    try:
        run('time git push %s master' % (deis_remote,), pty=True)
    finally:
        dog_stats_api.histogram(
            'deis.release.time',
            time.time() - start,
            tags=['deis', 'release', 'release.%s' % (deis_remote,)],
        )
        dog_stats_api.flush()
