from protobufs.services.search.containers import entity_pb2
from service import actions

from services.mixins import PreRunParseTokenMixin

from .. import tasks


def update_entities(entity_type, ids, organization_id):
    task = None
    if entity_type == entity_pb2.PROFILE:
        task = tasks.update_profile

    if task is None:
        raise ValueError(
            'entity_type: "%s" is not supported' % (
                entity_pb2.EntityTypeV1.Name(entity_type),
            )
        )

    [task.delay(pk, organization_id) for pk in ids]


class Action(PreRunParseTokenMixin, actions.Action):

    required_fields = ('ids',)

    def run(self, *args, **kwargs):
        update_entities(self.request.type, self.request.ids, self.parsed_token.organization_id)
