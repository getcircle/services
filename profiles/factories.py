import datetime
from protobufs.services.profile import containers_pb2 as profile_containers

from services.test import factory

from . import models


class ProfileFactory(factory.Factory):
    class Meta:
        model = models.Profile
        protobuf = profile_containers.ProfileV1

    organization_id = factory.FuzzyUUID()
    user_id = factory.FuzzyUUID()
    address_id = factory.FuzzyUUID()
    location_id = factory.FuzzyUUID()
    team_id = factory.FuzzyUUID()
    title = factory.FuzzyText()
    first_name = factory.FuzzyText()
    last_name = factory.FuzzyText()
    image_url = factory.FuzzyText(prefix='http://www.media.com/')
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

    @factory.post_generation
    def contact_methods(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for method in extracted:
                models.ContactMethod.objects.from_protobuf(method, profile_id=self.id)


class TagFactory(factory.Factory):
    class Meta:
        model = models.Tag
        protobuf = profile_containers.TagV1

    organization_id = factory.FuzzyUUID()
    name = factory.FuzzyText()
    type = factory.FuzzyChoice(profile_containers.TagV1.TagTypeV1.values())
