from .collection.document import CollectionV1  # NOQA
from .location.document import LocationV1  # NOQA
from .post.document import PostV1  # NOQA
from .profile.document import ProfileV1  # NOQA
from .team.document import TeamV1  # NOQA


def get_doc_type_with_name(name):
    doc_type = None

    if name == ProfileV1._doc_type.name:
        doc_type = ProfileV1
    elif name == TeamV1._doc_type.name:
        doc_type = TeamV1
    elif name == LocationV1._doc_type.name:
        doc_type = LocationV1
    elif name == PostV1._doc_type.name:
        doc_type = PostV1
    elif name == CollectionV1._doc_type.name:
        doc_type = CollectionV1

    return doc_type
