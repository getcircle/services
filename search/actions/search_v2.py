import logging

from elasticsearch_dsl import (
    Search,
    Q,
)
from protobuf_to_dict import dict_to_protobuf
from protobufs.services.search.containers import search_pb2
from service import actions

from services.mixins import PreRunParseTokenMixin
from ..stores.es import types
from ..stores.es.indices.organization.actions import get_read_alias
from ..stores.es.types.location import actions as location_actions
from ..stores.es.types.post import actions as post_actions
from ..stores.es.types.profile import actions as profile_actions
from ..stores.es.types.team import actions as team_actions

logger = logging.getLogger(__file__)

CATEGORY_TO_ACTIONS = {
    search_pb2.POSTS: [post_actions],
    search_pb2.PROFILES: [profile_actions],
    search_pb2.LOCATIONS: [location_actions],
    search_pb2.TEAMS: [team_actions],
}


def _combine_statements(statement_funcs, query):
    statements = []
    for func in statement_funcs:
        for statement in func(query):
            if statement not in statements:
                statements.append(statement)
    return statements


class Action(PreRunParseTokenMixin, actions.Action):

    required_fields = ('query',)

    def _get_doc_type(self):
        if not self.request.HasField('category'):
            return None

        doc_types = []
        if self.request.category == search_pb2.PROFILES:
            doc_types.append(types.ProfileV1._doc_type.name)
        elif self.request.category == search_pb2.TEAMS:
            doc_types.append(types.TeamV1._doc_type.name)
        elif self.request.category == search_pb2.LOCATIONS:
            doc_types.append(types.LocationV1._doc_type.name)
        elif self.request.category == search_pb2.POSTS:
            doc_types.append(types.PostV1._doc_type.name)
        return ','.join(doc_types) or None

    def _get_statements(self, statement_type):
        actions = []
        if not self.request.HasField('category'):
            actions = sum(CATEGORY_TO_ACTIONS.values(), [])
        else:
            actions = CATEGORY_TO_ACTIONS[self.request.category]

        statements = []
        for action in actions:
            if hasattr(action, statement_type):
                statements.append(getattr(action, statement_type))

        if statements:
            return _combine_statements(statements, self.request.query)

    def _get_should_statements(self):
        return self._get_statements('get_should_statements_v1')

    def _get_rescore_statements(self):
        return self._get_statements('get_rescore_statements_v1')


    def run(self, *args, **kwargs):
        read_alias = get_read_alias(self.parsed_token.organization_id)
        search = Search(index=read_alias, doc_type=self._get_doc_type())

        should_statements = self._get_should_statements()
        rescore_statements = self._get_rescore_statements()
        extra = {}
        if rescore_statements:
            rescore_query = Q('bool', should=rescore_statements)
            extra['rescore'] = {
                'window_size': 20,
                'query': {
                    'rescore_query': rescore_query.to_dict(),
                },
            }

        q = Q('bool', should=should_statements)
        response = search.query(q).extra(**extra).execute()
        for result in response.hits:
            result_object_type = None
            if result.meta.doc_type == types.ProfileV1._doc_type.name:
                result_object_type = types.ProfileV1
            elif result.meta.doc_type == types.TeamV1._doc_type.name:
                result_object_type = types.TeamV1
            elif result.meta.doc_type == types.LocationV1._doc_type.name:
                result_object_type = types.LocationV1
            elif result.meta.doc_type == types.PostV1._doc_type.name:
                result_object_type = types.PostV1

            if not result_object_type:
                logger.warn('unsupported search result doc_type: %s', result.meta.doc_type)
                continue

            container = self.response.results.add()
            try:
                result_object = getattr(container, result_object_type._doc_type.name)
            except AttributeError:
                logger.warn('result_object_type: "%s" does not exist', result_object_type)
                continue

            data = result.to_dict()
            result_object_type.prepare_protobuf_dict(data)
            dict_to_protobuf(data, result_object)
            container.score = result.meta.score
