from ...indices.actions import closed_index
from .document import ProfileV1


def create_mapping_v1(*args, **kwargs):
    with closed_index(ProfileV1._doc_type.index):
        ProfileV1.init()
