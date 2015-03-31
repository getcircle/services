import datetime
from protobufs.profile_service_pb2 import ProfileService

from services.test import factory

from . import models


class ProfileFactory(factory.Factory):
    class Meta:
        model = models.Profile
        protobuf = ProfileService.Containers.Profile

    organization_id = factory.FuzzyUUID()
    user_id = factory.FuzzyUUID()
    address_id = factory.FuzzyUUID()
    location_id = factory.FuzzyUUID()
    team_id = factory.FuzzyUUID()
    title = factory.FuzzyText()
    first_name = factory.FuzzyText()
    last_name = factory.FuzzyText()
    # TODO add a custom factory FuzzyPhoneNumber
    cell_phone = '+19492933322'
    work_phone = '+19492933322'
    image_url = factory.FuzzyText(prefix='http://www.media.com/')
    email = factory.FuzzyText(suffix='@example.com')
    hire_date = factory.FuzzyDate(datetime.date(2000, 1, 1))
    birth_date = factory.FuzzyDate(datetime.date(1950, 1, 1))
    about = factory.FuzzyText()
    nickname = factory.FuzzyText()

    @classmethod
    def get_protobuf_data(cls, **data):
        model = cls.build(**data)
        return model.as_dict(exclude=('created', 'changed', 'items'))

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            # profiles and tags need to have the same organization_id
            self.organization_id = extracted[0].organization_id
            for tag in extracted:
                self.tags.through.objects.create(tag=tag, profile=self)


class TagFactory(factory.Factory):
    class Meta:
        model = models.Tag
        protobuf = ProfileService.Containers.Tag

    organization_id = factory.FuzzyUUID()
    name = factory.FuzzyText()
    type = factory.FuzzyChoice(ProfileService.TagType.values())
