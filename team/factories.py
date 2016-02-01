from protobufs.services.team import containers_pb2 as team_containers

from services.test import factory

from . import models


class TeamFactory(factory.Factory):
    class Meta:
        model = models.Team
        protobuf = team_containers.TeamV1

    organization_id = factory.FuzzyUUID()
    name = factory.FuzzyText()


class TeamMemberFactory(factory.Factory):
    class Meta:
        model = models.TeamMember
        protobuf = team_containers.TeamMemberV1

    organization_id = factory.FuzzyUUID()
    profile_id = factory.FuzzyUUID()
    team = factory.SubFactory(TeamFactory)
