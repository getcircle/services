import time

from . import INDEX


def create_index(*args, **kwargs):
    INDEX.aliases(search={})
    INDEX.delete(ignore=404)
    INDEX.create()
    waiting = True
    while waiting:
        health = INDEX.connection.cluster.health()
        waiting = health['status'] != 'red'
        print 'waiting for cluster to get out of "red" status: %s' % (health,)
        time.sleep(1)
