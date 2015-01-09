from __future__ import absolute_import
from factory import DjangoModelFactory
from factory.base import (
    OptionDefault,
)
from factory.django import DjangoOptions
from .fuzzy import *


class ProtobufDjangoOptions(DjangoOptions):

    def _build_default_options(self):
        options = super(ProtobufDjangoOptions, self)._build_default_options()
        options.append(OptionDefault('protobuf', None, inherit=True))
        return options


class Factory(DjangoModelFactory):
    _options_class = ProtobufDjangoOptions

    @classmethod
    def create_protobuf(cls, *args, **kwargs):
        if cls._meta.protobuf is None:
            raise NotImplementedError('Must define `protobuf` in meta')

        container = cls._meta.protobuf()
        model = cls.create(*args, **kwargs)
        model.to_protobuf(container)
        return container
