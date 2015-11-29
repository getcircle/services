from services.test import factory
from . import models
from stores.es import types


class RecentFactory(factory.Factory):
    class Meta:
        model = models.Recent

    organization_id = factory.FuzzyUUID()
    by_profile_id = factory.FuzzyUUID()
    document_type = types.ProfileV1._doc_type.name
    document_id = factory.FuzzyUUID()

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        if 'profile' in kwargs:
            profile = kwargs.pop('profile')
            kwargs['by_profile_id'] = profile.id
            kwargs['organization_id'] = profile.organization_id
        if 'document_type' in kwargs:
            kwargs['document_type'] = kwargs.pop('document_type')
        if 'document_id' in kwargs:
            kwargs['document_id'] = kwargs.pop('document_id')
        return kwargs
