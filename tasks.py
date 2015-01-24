from invoke import task, run


@task
def test(app):
    run('./manage.py test -k --failfast %s' % (app,), pty=True)

@task
def archive(version):
    run('git archive --format=zip HEAD > archives/services_%s.zip' % (version,))
