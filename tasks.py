from invoke import (
    run,
    task,
)


def execute_with_settings(command, settings='docker', extra='', **kwargs):
    command = 'DJANGO_SETTINGS_MODULE=services.settings.%s ./manage.py %s %s' % (
        settings,
        command,
        extra,
    )
    run(command, **kwargs)


@task(help={
    'failfast': 'Flag for whether or not you want to fail on the first test failure',
    'keepdb': 'Flag for whether or not you want to reuse the test db',
})
def test(app='', failfast=False, keepdb=False, extra=''):
    """Trigger a test run"""
    test_args = []
    if failfast:
        test_args.append('--failfast')
    if keepdb:
        test_args.append('-k')
    execute_with_settings(
        'test %s %s' % (' '.join(test_args), app,),
        settings='test',
        extra=extra,
        pty=True,
    )


@task
def qt(app, extra='', infer=False):
    """Trigger a test run, defaulting to keep database and fail fast"""
    if infer and app.endswith('.py'):
        app = app.rsplit('.', 1)[0].replace('/', '.')

    test(app, failfast=True, keepdb=True, extra=extra)


@task
def serve():
    """Serve the development server"""
    execute_with_settings('runserver', pty=True)


@task
def manage(command, settings='local', extra=''):
    """Execute a manage command with the given settings"""
    execute_with_settings(command, settings=settings, extra=extra, pty=True)
