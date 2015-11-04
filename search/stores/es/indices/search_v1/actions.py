import time

from . import INDEX
from ..import SEARCH_ALIAS
from ...analysis import default_search


def create_index(*args, **kwargs):
    INDEX.aliases(**{SEARCH_ALIAS: {}})
    INDEX.delete(ignore=404)
    INDEX.settings(index={'analysis': default_search.get_analysis_definition()})
    INDEX.create()
    waiting = True
    while waiting:
        health = INDEX.connection.cluster.health()
        waiting = health['status'] == 'red'
        print 'waiting for cluster to get out of "red" status: %s' % (health,)
        time.sleep(1)
