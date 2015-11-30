import logging

from protobuf_to_dict import dict_to_protobuf
from elasticsearch_dsl import connections
from service import actions
from services.mixins import PreRunParseTokenMixin
from ..stores.es.indices.organization.actions import get_read_alias
from ..stores.es import types
from .. import models


logger = logging.getLogger(__file__)


class Action(PreRunParseTokenMixin, actions.Action):

    def run(self, *args, **kwargs):
        recents = models.Recent.objects.filter(
            organization_id=self.parsed_token.organization_id,
            by_profile_id=self.parsed_token.profile_id,
        ).order_by('-changed')

        docs = []
        for recent in recents:
            docs.append({'_type': recent.document_type, '_id': str(recent.document_id)})

        read_alias = get_read_alias(self.parsed_token.organization_id)
        es = connections.connections.get_connection()
        response = es.mget(index=read_alias, body={'docs': docs})

        def serialize_to_recent(doc, container):
            object_type = None
            doc_type = doc['_type']
            if doc_type == types.ProfileV1._doc_type.name:
                object_type = types.ProfileV1
            elif doc_type == types.TeamV1._doc_type.name:
                object_type = types.TeamV1
            elif doc_type == types.LocationV1._doc_type.name:
                object_type = types.LocationV1
            elif doc_type == types.PostV1._doc_type.name:
                object_type = types.PostV1

            if not object_type:
                logger.warn('unsupported search result doc_type: %s', doc_type)
                return

            recent_container = container.add()
            try:
                result_object = getattr(recent_container, object_type._doc_type.name)
            except AttributeError:
                logger.warn('object_type: "%s" does not exist', object_type)
                return

            data = doc['_source']
            object_type.prepare_protobuf_dict(data)
            dict_to_protobuf(data, result_object)

        self.paginated_response(
            self.response.recents,
            response['docs'],
            serialize_to_recent,
        )
