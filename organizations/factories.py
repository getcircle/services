from protobufs.services.organization import containers_pb2 as organization_containers
from protobufs.services.organization.containers import integration_pb2

from services.test import factory

from . import models


class OrganizationFactory(factory.Factory):
    class Meta:
        model = models.Organization
        protobuf = organization_containers.OrganizationV1

    name = factory.FuzzyText()
    domain = factory.FuzzyText(suffix='.com')
    image_url = factory.FuzzyText(prefix='http://www.', suffix='.com')


class TeamFactory(factory.Factory):
    class Meta:
        model = models.Team
        protobuf = organization_containers.TeamV1

    name = factory.FuzzyText()
    organization = factory.SubFactory(OrganizationFactory)
    image_url = factory.FuzzyText(prefix='http://www.', suffix='.com')
    manager_profile_id = factory.FuzzyUUID()
    created_by_profile_id = factory.FuzzyUUID()

    @factory.post_generation
    def status(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            if isinstance(extracted, dict):
                value = extracted['value']
                by_profile_id = extracted['by_profile_id']
            else:
                value = extracted.value
                by_profile_id = extracted.by_profile_id

            models.TeamStatus.objects.create(
                team=self,
                value=value,
                organization_id=self.organization_id,
                by_profile_id=by_profile_id,
            )

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        # NB: If we're creating a team from scratch, ensure we create a manager
        # and a direct report since that is our requirement for a team. If one
        # already exists, we don't want to add anything.
        manager = models.ReportingStructure.objects.filter(
            organization=kwargs['organization'],
            profile_id=kwargs['manager_profile_id'],
        )
        if not manager:
            manager = ReportingStructureFactory.create(
                manager_id=None,
                organization=kwargs['organization'],
                profile_id=kwargs['manager_profile_id'],
            )
        else:
            manager = manager[0]

        if not manager.get_descendant_count():
            ReportingStructureFactory.create(
                manager_id=kwargs['manager_profile_id'],
                organization=kwargs['organization'],
            )
        return super(TeamFactory, cls)._create(model_class, *args, **kwargs)


class LocationFactory(factory.Factory):
    class Meta:
        model = models.Location
        protobuf = organization_containers.LocationV1

    name = factory.FuzzyText()
    organization = factory.SubFactory(OrganizationFactory)
    address_1 = factory.FuzzyText(suffix=' Street')
    address_2 = factory.FuzzyText(suffix=' Suite 700')
    city = factory.FuzzyText()
    region = factory.FuzzyText(length=2)
    postal_code = '94010'
    country_code = 'USA'
    latitude = '37.578286'
    longitude = '-122.348729'
    timezone = 'America/Los_Angeles'


class LocationMemberFactory(factory.Factory):
    class Meta:
        model = models.LocationMember

    location = factory.SubFactory(LocationFactory)
    profile_id = factory.FuzzyUUID()
    added_by_profile_id = factory.FuzzyUUID()
    organization = factory.SubFactory(OrganizationFactory)


class TokenFactory(factory.Factory):
    class Meta:
        model = models.Token
        protobuf = organization_containers.TokenV1

    organization = factory.SubFactory(OrganizationFactory)
    requested_by_user_id = factory.FuzzyUUID()


class IntegrationFactory(factory.Factory):
    class Meta:
        model = models.Integration
        protobuf = integration_pb2.IntegrationV1

    organization = factory.SubFactory(OrganizationFactory)
    type = integration_pb2.GOOGLE_GROUPS


class ReportingStructureFactory(factory.Factory):
    class Meta:
        model = models.ReportingStructure
        django_get_or_create = ('profile_id',)

    organization = factory.SubFactory(OrganizationFactory)
    profile_id = factory.FuzzyUUID()
    added_by_profile_id = factory.FuzzyUUID()
