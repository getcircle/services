from ...indices.actions import closed_index
from .document import PostV1


def create_mapping_v1(*args, **kwargs):
    with closed_index(PostV1._doc_type.index):
        PostV1.init()
