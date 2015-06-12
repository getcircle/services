from services.test import factory
from protobufs.services.group import containers_pb2 as group_containers

from .. import models


class GroupMembershipRequestFactory(factory.Factory):
    class Meta:
        model = models.GroupMembershipRequest

    status = factory.FuzzyChoice(group_containers.MembershipRequestStatusV1.values())
    requester_profile_id = factory.FuzzyUUID()
    group_id = factory.FuzzyUUID()
    provider = group_containers.GOOGLE


class GoogleGroupFactory(factory.Factory):
    class Meta:
        model = models.GoogleGroup

    email = factory.FuzzyText(suffix='@example.com')
    display_name = factory.FuzzyText()
    name = factory.FuzzyText()
    description = factory.FuzzyText()
    last_sync_id = factory.FuzzyUUID()
    organization_id = factory.FuzzyUUID()
    provider_uid = factory.FuzzyUUID()


class GoogleGroupMemberFactory(factory.Factory):
    class Meta:
        model = models.GoogleGroupMember

    profile_id = factory.FuzzyUUID()
    group = factory.SubFactory(GoogleGroupFactory)
    role = factory.FuzzyChoice([
        'MEMBER',
        'OWNER',
        'MANAGER',
    ])
    organization_id = factory.FuzzyUUID()
    last_sync_id = factory.FuzzyUUID()
    provider_uid = factory.FuzzyUUID()
