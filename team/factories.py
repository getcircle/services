from protobufs.services.team import containers_pb2 as team_containers

from services.test import factory

from . import models


class TeamFactory(factory.Factory):
    class Meta:
        model = models.Team
        protobuf = team_containers.TeamV1

    organization_id = factory.FuzzyUUID()
    name = factory.FuzzyText()

    @factory.post_generation
    def contact_methods(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for method in extracted:
                models.ContactMethod.objects.from_protobuf(
                    method,
                    organization_id=self.organization_id,
                    team_id=self.id,
                )


class TeamMemberFactory(factory.Factory):
    class Meta:
        model = models.TeamMember
        protobuf = team_containers.TeamMemberV1

    organization_id = factory.FuzzyUUID()
    profile_id = factory.FuzzyUUID()
    team = factory.SubFactory(TeamFactory)

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        if 'profile' in kwargs:
            profile = kwargs.pop('profile')
            kwargs['profile_id'] = profile.id
            kwargs['organization_id'] = profile.organization_id
        elif 'team' in kwargs:
            team = kwargs['team']
            kwargs['organization_id'] = team.organization_id
        return kwargs


class ContactMethodFactory(factory.Factory):
    class Meta:
        model = models.ContactMethod
        protobuf = team_containers.ContactMethodV1

    organization_id = factory.FuzzyUUID()
    team = factory.SubFactory(TeamFactory)
    label = factory.FuzzyText()
    value = factory.FuzzyText()

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        if 'team' in kwargs:
            kwargs['organization_id'] = kwargs['team'].organization_id
        return kwargs

    @factory.post_generation
    def created(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.created = extracted
            self.save()
