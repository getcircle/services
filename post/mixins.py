from protobufs.services.common import containers_pb2 as common_containers

from services import (
    mixins,
    utils,
)


class PostPermissionsMixin(mixins.PreRunParseTokenMixin):

    def get_permissions(self, post):
        permissions = common_containers.PermissionsV1()
        if utils.matching_uuids(self.parsed_token.profile_id, post.by_profile_id):
            permissions.can_edit = True
            permissions.can_delete = True

        return permissions
