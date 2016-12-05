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


class AttachmentFactory(factory.Factory):
    class Meta:
        model = models.Attachment

    organization_id = factory.FuzzyUUID()
    file_id = factory.FuzzyUUID()
    post = factory.SubFactory(PostFactory)

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        if 'post' in kwargs:
            kwargs['organization_id'] = kwargs['post'].organization_id
        return kwargs


class CollectionFactory(factory.Factory):
    class Meta:
        model = models.Collection
        protobuf = post_containers.CollectionV1

    organization_id = factory.FuzzyUUID()
    owner_id = factory.FuzzyUUID()
    owner_type = factory.FuzzyChoice(post_containers.CollectionV1.OwnerTypeV1.values())
    name = factory.FuzzyText()
    by_profile_id = factory.FuzzyUUID()
    position = factory.Sequence(lambda n: n)

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        if 'profile' in kwargs:
            profile = kwargs.pop('profile')
            kwargs['organization_id'] = profile.organization_id
            kwargs['owner_id'] = profile.id
            kwargs['owner_type'] = post_containers.CollectionV1.PROFILE
        elif 'team' in kwargs:
            team = kwargs.pop('team')
            kwargs['organization_id'] = team.organization_id
            kwargs['owner_id'] = team.id
            kwargs['owner_type'] = post_containers.CollectionV1.TEAM
        return kwargs


class CollectionItemFactory(factory.Factory):
    class Meta:
        model = models.CollectionItem
        protobuf = post_containers.CollectionItemV1

    collection = factory.SubFactory(CollectionFactory)
    position = factory.Sequence(lambda n: n)
    by_profile_id = factory.FuzzyUUID()
    organization_id = factory.FuzzyUUID()
    source = factory.FuzzyChoice(post_containers.CollectionItemV1.SourceV1.values())
    source_id = factory.FuzzyUUID()

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        if 'collection' in kwargs:
            kwargs['organization_id'] = kwargs['collection'].organization_id
        return kwargs
