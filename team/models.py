from common import utils
from common.db import models
from protobufs.services.team import containers_pb2 as team_containers
import service.control

from services.fields import DescriptionField


class Team(models.UUIDModel, models.TimestampableModel):

    organization_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=255)
    description = DescriptionField(null=True)

    def _inflate(self, protobuf, inflations, overrides, token):
        if self.description and self.description.by_profile_id:
            if token and utils.should_inflate_field('description.by_profile_id', inflations):
                by_profile = service.control.get_object(
                    service='profile',
                    action='get_profile',
                    client_kwargs={'token': token},
                    return_object='profile',
                    profile_id=str(self.description.by_profile_id),
                    inflations={'disabled': True},
                )
                self.description.by_profile.CopyFrom(by_profile)

    def to_protobuf(self, protobuf=None, inflations=None, token=None, **overrides):
        protobuf = self.new_protobuf_container(protobuf)
        self._inflate(protobuf, inflations, overrides, token)
        return super(Team, self).to_protobuf(protobuf, inflations=inflations, **overrides)

    class Meta:
        protobuf = team_containers.TeamV1


class TeamMember(models.UUIDModel, models.TimestampableModel):

    as_dict_value_transforms = {
        'role': int,
    }

    team = models.ForeignKey(Team, related_name='members')
    profile_id = models.UUIDField()
    organization_id = models.UUIDField()
    role = models.SmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(team_containers.TeamMemberV1.RoleV1),
        default=team_containers.TeamMemberV1.MEMBER,
    )

    class Meta:
        index_together = (('team', 'organization_id', 'role'), ('profile_id', 'organization_id'))
        unique_together = ('team', 'profile_id')
        protobuf = team_containers.TeamMemberV1
