from protobufs.services.common import containers_pb2 as common_containers
import service.control

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
        else:
            # only fetch this if the above fails so we're not calling this each
            # time a post is updated, only when admins are trying to update
            profile = service.control.get_object(
                service='profile',
                action='get_profile',
                return_object='profile',
                client_kwargs={'token': self.token},
            )
            if profile.is_admin:
                permissions.can_edit = True
                permissions.can_delete = True

        return permissions
