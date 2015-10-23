from protobufs.services.post import containers_pb2 as post_containers

from services.test import factory

from . import models


class PostFactory(factory.Factory):
    class Meta:
        model = models.Post
        protobuf = post_containers.PostV1

    organization_id = factory.FuzzyUUID()
    by_profile_id = factory.FuzzyUUID()
    title = factory.FuzzyText()
    content = factory.Faker('text')
    state = factory.FuzzyChoice(post_containers.PostStateV1.values())

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        if 'profile' in kwargs:
            profile = kwargs.pop('profile')
            kwargs['by_profile_id'] = profile.id
            kwargs['organization_id'] = profile.organization_id
        return kwargs
