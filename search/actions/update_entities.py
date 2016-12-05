from protobufs.services.search.containers import entity_pb2
from service import actions
from service.settings import MAX_PAGE_SIZE

from services.mixins import PreRunParseTokenMixin

from .. import tasks


def get_batches(items, batch_size=MAX_PAGE_SIZE):
    batch_size = int(batch_size)
    num_full_batches = len(items) / batch_size
    batches = []
    for i in range(num_full_batches):
        batch = items[(i * batch_size):(i + 1) * batch_size]
        batches.append(batch)

    if len(items) % batch_size:
        batches.append(items[num_full_batches * batch_size:])
    return batches


def update_entities(entity_type, ids, organization_id):
    task = None
    if entity_type == entity_pb2.PROFILE:
        task = tasks.update_profiles
    elif entity_type == entity_pb2.TEAM:
        task = tasks.update_teams
    elif entity_type == entity_pb2.LOCATION:
        task = tasks.update_locations
    elif entity_type == entity_pb2.POST:
        task = tasks.update_posts
    elif entity_type == entity_pb2.COLLECTION:
        task = tasks.update_collections

    if task is None:
        raise ValueError(
            'entity_type: "%s" is not supported' % (
                entity_pb2.EntityTypeV1.Name(entity_type),
            )
        )

    batches = get_batches(ids)
    [task.delay(batch, organization_id) for batch in batches]


class Action(PreRunParseTokenMixin, actions.Action):

    required_fields = ('ids',)

    def run(self, *args, **kwargs):
        update_entities(self.request.type, self.request.ids, self.parsed_token.organization_id)
