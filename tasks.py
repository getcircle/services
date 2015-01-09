from invoke import task, run


@task
def test(app):
    run('./manage.py test -k --failfast %s' % (app,))
