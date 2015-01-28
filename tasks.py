from invoke import task, run


def execute_with_settings(command, settings='local', **kwargs):
    run('DJANGO_SETTINGS_MODULE=services.settings.%s %s' % (settings, command), **kwargs)


@task
def test(app):
    execute_with_settings('./manage.py test -k --failfast %s' % (app,), pty=True)
