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
        for recent in self.get_paginated_objects(recents):
            docs.append({'_type': recent.document_type, '_id': str(recent.document_id)})

        read_alias = get_read_alias(self.parsed_token.organization_id)
        es = connections.connections.get_connection()
        response = es.mget(index=read_alias, body={'docs': docs})
        for doc in response['docs']:
            doc_type = doc['_type']
            object_type = types.type_with_name(doc_type)
            
            if not object_type:
                logger.warn('unsupported search result doc_type: %s', doc_type)
                continue

            container = self.response.recents.add()
            try:
                result_object = getattr(container, object_type._doc_type.name)
            except AttributeError:
                logger.warn('object_type: "%s" does not exist', object_type)
                continue

            data = doc['_source']
            object_type.prepare_protobuf_dict(data)
            dict_to_protobuf(data, result_object)
