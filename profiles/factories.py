import datetime
from django.db.models.signals import post_save
import factory.django

from protobufs.services.profile import containers_pb2 as profile_containers

from services.test import factory

from . import models


@factory.django.mute_signals(post_save)
class ProfileFactory(factory.Factory):
    class Meta:
        model = models.Profile
        protobuf = profile_containers.ProfileV1

    organization_id = factory.FuzzyUUID()
    user_id = factory.FuzzyUUID()
    title = factory.FuzzyText()
    first_name = factory.FuzzyText()
    last_name = factory.FuzzyText()
    image_url = factory.FuzzyText(prefix='http://www.media.com/')
    hire_date = factory.FuzzyDate(datetime.date(2000, 1, 1))
    birth_date = factory.FuzzyDate(datetime.date(1950, 1, 1))
    nickname = factory.FuzzyText()
    email = factory.FuzzyText(suffix='@example.com')
    small_image_url = factory.FuzzyText(prefix='http://www.media.com/small/')
    authentication_identifier = factory.FuzzyUUID()

    @classmethod
    def get_protobuf_data(cls, **data):
        model = cls.build(**data)
        return model.as_dict(fields={'exclude': ('created', 'changed', 'items')})

    @factory.post_generation
    def contact_methods(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for method in extracted:
                models.ContactMethod.objects.from_protobuf(
                    method,
                    profile_id=self.id,
                    organization_id=self.organization_id,
                )

    @factory.post_generation
    def status(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            if isinstance(extracted, dict):
                value = extracted['value']
            else:
                value = extracted.value

            models.ProfileStatus.objects.create(
                profile=self,
                value=value,
                organization_id=self.organization_id,
            )
