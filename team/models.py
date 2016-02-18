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

        if (
            'contact_methods' not in overrides and
            utils.should_inflate_field('contact_methods', inflations)
        ):
            overrides['contact_methods'] = self.contact_methods.filter(
                organization_id=self.organization_id,
            ).order_by('created')

        if (
            'total_members' not in overrides and
            utils.should_inflate_field('total_members', inflations)
        ):
            overrides['total_members'] = self.members.count()

        for method in overrides.pop('contact_methods', []):
            container = protobuf.contact_methods.add()
            method.to_protobuf(container)

    def to_protobuf(self, protobuf=None, inflations=None, token=None, **overrides):
        protobuf = self.new_protobuf_container(protobuf)
        self._inflate(protobuf, inflations, overrides, token)
        return super(Team, self).to_protobuf(protobuf, inflations=inflations, **overrides)

    def update_from_protobuf(self, protobuf, **kwargs):
        # avoid circular import
        from .actions import update_contact_methods

        contact_methods = update_contact_methods(protobuf.contact_methods, self)
        return super(Team, self).update_from_protobuf(
            protobuf,
            contact_methods=contact_methods,
            **kwargs
        )

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

    def _inflate(self, protobuf, inflations, fields, overrides):
        team_inflations = inflations and utils.inflations_for_item('team', inflations)
        team_fields = fields and utils.fields_for_item('team', fields)
        if 'team' not in overrides and utils.should_inflate_field('team', inflations):
            self.team.to_protobuf(protobuf.team, inflations=team_inflations, fields=team_fields)

    def to_protobuf(self, protobuf=None, inflations=None, fields=None, **overrides):
        protobuf = self.new_protobuf_container(protobuf)
        self._inflate(protobuf, inflations, fields, overrides)
        return super(TeamMember, self).to_protobuf(
            protobuf,
            inflations=inflations,
            fields=fields,
            **overrides
        )

    class Meta:
        index_together = (('team', 'organization_id', 'role'), ('profile_id', 'organization_id'))
        unique_together = ('team', 'profile_id')
        protobuf = team_containers.TeamMemberV1


class ContactMethod(models.UUIDModel, models.TimestampableModel):

    as_dict_value_transforms = {
        'type': int,
        'label': lambda x: x if x else None,
    }

    team = models.ForeignKey(Team, related_name='contact_methods')
    label = models.CharField(max_length=64, null=True)
    value = models.CharField(max_length=64)
    type = models.SmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(team_containers.ContactMethodV1.TypeV1),
        default=team_containers.ContactMethodV1.EMAIL,
    )
    organization_id = models.UUIDField()

    class Meta:
        index_together = ('team', 'organization_id')
        protobuf = team_containers.ContactMethodV1
