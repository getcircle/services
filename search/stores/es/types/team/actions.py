from ...indices.actions import closed_index
from .document import TeamV1


def create_mapping_v1(*args, **kwargs):
    with closed_index(TeamV1._doc_type.index):
        TeamV1.init()