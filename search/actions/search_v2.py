import logging

from elasticsearch_dsl import (
    Search,
    Q,
)
from protobuf_to_dict import dict_to_protobuf
from service import actions

from services.mixins import PreRunParseTokenMixin
from ..stores.es import types
from ..stores.es.indices import SEARCH_ALIAS
from ..stores.es.types.location import actions as location_actions
from ..stores.es.types.post import actions as post_actions
from ..stores.es.types.profile import actions as profile_actions
from ..stores.es.types.team import actions as team_actions

logger = logging.getLogger(__file__)


def _combine_statements(statement_funcs, query):
    statements = []
    for func in statement_funcs:
        for statement in func(query):
            if statement not in statements:
                statements.append(statement)
    return statements


class Action(PreRunParseTokenMixin, actions.Action):

    required_fields = ('query',)

    def run(self, *args, **kwargs):
        search = Search(index=SEARCH_ALIAS).filter(
            organization_id=self.parsed_token.organization_id,
        )
        query = self.request.query
        should_statements = _combine_statements([
            post_actions.get_should_statements_v1,
            profile_actions.get_should_statements_v1,
            team_actions.get_should_statements_v1,
            location_actions.get_should_statements_v1,
        ], query)

        q = Q('bool', should=should_statements)
        response = search.query(q).execute()
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
