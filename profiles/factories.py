import factory
from protobufs.profile_service_pb2 import ProfileService

from services.test import fuzzy

from . import models

class ProfileFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Profile

    organization_id = fuzzy.FuzzyUUID()
    user_id = fuzzy.FuzzyUUID()
    address_id = fuzzy.FuzzyUUID()
    team_id = fuzzy.FuzzyUUID()
    title = fuzzy.FuzzyText()
    first_name = fuzzy.FuzzyText()
    last_name = fuzzy.FuzzyText()
    # TODO add a custom fuzzy FuzzyPhoneNumber
    cell_phone = '+19492933322'
    image_url = fuzzy.FuzzyText(prefix='http://www.media.com/')
    email = fuzzy.FuzzyText(suffix='@example.com')

    @classmethod
    def create_protobuf(cls, *args, **kwargs):
        container = ProfileService.Containers.Profile()
        model = cls.create(*args, **kwargs)
        model.to_protobuf(container)
        return container
