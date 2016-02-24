from base64 import b64encode
import logging

import service.control
import watson

from .token import make_admin_token

logger = logging.getLogger(__name__)


class SearchAdapter(watson.SearchAdapter):

    def get_protobuf(self, obj):
        return obj.to_protobuf()

    def get_meta(self, obj):
        container = self.get_protobuf(obj)
        return {
            'protobuf': '.'.join([container.__module__, container.__class__.__name__]),
            'data': b64encode(container.SerializeToString()),
        }


def update_entity(primary_key, organization_id, entity_type):
    token = make_admin_token(organization_id=organization_id)
    try:
        service.control.call_action(
            service='search',
            action='update_entities',
            client_kwargs={'token': token},
            ids=[str(primary_key)],
            type=entity_type,
        )
    except service.control.CallActionError as e:
        logger.error(e.summary)
