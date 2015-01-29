from dogapi import dog_stats_api
from invoke import (
    run,
    task,
)

dog_stats_api.start(api_key='6253fdebf2c8e3648d5eba97a9ba92bf')


def execute_with_settings(command, settings='local', **kwargs):
    run('DJANGO_SETTINGS_MODULE=services.settings.%s %s' % (settings, command), **kwargs)


@task
def test(app='', failfast=False, keepdb=False):
    test_args = []
    if failfast:
        test_args.append('--failfast')
    if keepdb:
        test_args.append('-k')
    execute_with_settings('./manage.py test %s %s' % (' '.join(test_args), app,), pty=True)


@task
def serve():
    execute_with_settings('./manage.py runserver', pty=True)


@dog_stats_api.timed('deis.deploy.time', tags=['deis', 'deploy'])
@task
def release(deis_remote='deis'):
    run('time git push %s master' % (deis_remote,), pty=True)
