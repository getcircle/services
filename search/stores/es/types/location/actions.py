from ...indices.actions import closed_index
from .document import LocationV1


def create_mapping_v1(*args, **kwargs):
    with closed_index(LocationV1._doc_type.index):
        LocationV1.init()
