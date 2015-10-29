from . import INDEX


def create_index(*args, **kwargs):
    INDEX.aliases(search={})
    INDEX.delete(ignore=404)
    INDEX.create()
