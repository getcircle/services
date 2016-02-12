from bulk_update.helper import bulk_update
from common import utils
from common.db import models
import django.db
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

        if 'contact_methods' not in overrides:
            if utils.should_inflate_field('contact_methods', inflations):
                overrides['contact_methods'] = self.contact_methods.filter(
                    organization_id=self.organization_id,
                ).order_by('created')

        for method in overrides.pop('contact_methods', []):
            container = protobuf.contact_methods.add()
            method.to_protobuf(container)

    def to_protobuf(self, protobuf=None, inflations=None, token=None, **overrides):
        protobuf = self.new_protobuf_container(protobuf)
        self._inflate(protobuf, inflations, overrides, token)
        return super(Team, self).to_protobuf(protobuf, inflations=inflations, **overrides)

    def update_from_protobuf(self, protobuf, **kwargs):
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

    class Meta:
        index_together = (('team', 'organization_id', 'role'), ('profile_id', 'organization_id'))
        unique_together = ('team', 'profile_id')
        protobuf = team_containers.TeamMemberV1


class ContactMethod(models.UUIDModel, models.TimestampableModel):

    as_dict_value_transforms = {
        'type': int,
    }

    team = models.ForeignKey(Team, related_name='contact_methods')
    label = models.CharField(max_length=64)
    value = models.CharField(max_length=64)
    type = models.SmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(team_containers.ContactMethodV1.TypeV1),
        default=team_containers.ContactMethodV1.EMAIL,
    )
    organization_id = models.UUIDField()

    class Meta:
        index_together = ('team', 'organization_id')
        protobuf = team_containers.ContactMethodV1


def update_contact_methods(contact_methods, team):
    """Update the contact methods for a team.

    Args:
        contact_methods (repeated
            protobufs.services.team.containers.ContactMethodV1): contact methods
        team (team.models.Team): team model we're updating

    Returns:
        repeated protobufs.services.team.containers.ContactMethodV1

    """
    with django.db.transaction.atomic():
        existing_methods = team.contact_methods.filter(organization_id=team.organization_id)
        existing_methods_dict = dict((str(method.id), method) for method in existing_methods)
        existing_ids = set(existing_methods_dict.keys())
        new_ids = set(method.id for method in contact_methods if method.id)
        to_delete = existing_ids - new_ids

        to_create = []
        to_update = []
        for container in contact_methods:
            if container.id:
                contact_method = existing_methods_dict[container.id]
                contact_method.update_from_protobuf(container)
                to_update.append(contact_method)
            else:
                contact_method = ContactMethod.objects.from_protobuf(
                    container,
                    team_id=team.id,
                    organization_id=team.organization_id,
                    commit=False,
                )
                to_create.append(contact_method)

        if to_create:
            ContactMethod.objects.bulk_create(to_create)

        if to_update:
            bulk_update(to_update)

        if to_delete:
            team.contact_methods.filter(
                id__in=to_delete,
                organization_id=team.organization_id,
            ).delete()
