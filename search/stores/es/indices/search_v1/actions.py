import time

from . import INDEX
from ..import SEARCH_ALIAS


def create_index(*args, **kwargs):
    INDEX.aliases(**{SEARCH_ALIAS: {}})
    INDEX.delete(ignore=404)
    INDEX.create()
    waiting = True
    while waiting:
        health = INDEX.connection.cluster.health()
        waiting = health['status'] != 'red'
        print 'waiting for cluster to get out of "red" status: %s' % (health,)
        time.sleep(1)
