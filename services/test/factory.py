from __future__ import absolute_import

# import factory helpers so tests can just import this file
from .fuzzy import *  # NOQA
from factory import *  # NOQA

from factory.base import (
    OptionDefault,
)
from factory.django import DjangoOptions


class ProtobufDjangoOptions(DjangoOptions):

    def _build_default_options(self):
        options = super(ProtobufDjangoOptions, self)._build_default_options()
        options.append(OptionDefault('protobuf', None, inherit=True))
        return options


class Factory(DjangoModelFactory):
    _options_class = ProtobufDjangoOptions

    @classmethod
    def verify_has_protobuf(cls):
        if cls._meta.protobuf is None:
            raise NotImplementedError('Must define `protobuf` in meta')

    @classmethod
    def create_protobuf(cls, to_protobuf_kwargs=None, *args, **kwargs):
        if not to_protobuf_kwargs:
            to_protobuf_kwargs = {}

        cls.verify_has_protobuf()
        container = cls._meta.protobuf()
        model = cls.create(*args, **kwargs)
        model.to_protobuf(container, **to_protobuf_kwargs)
        return container

    @classmethod
    def build_protobuf(cls, *args, **kwargs):
        cls.verify_has_protobuf()
        container = cls._meta.protobuf()
        model = cls.build(*args, **kwargs)
        model.to_protobuf(container)
        return container

    # TODO we should move this to the model
    @classmethod
    def to_protobuf(cls, model):
        cls.verify_has_protobuf()
        container = cls._meta.protobuf()
        model.to_protobuf(container)
        return container

    @classmethod
    def create_protobufs(cls, to_protobuf_kwargs=None, *args, **kwargs):
        if not to_protobuf_kwargs:
            to_protobuf_kwargs = {}

        cls.verify_has_protobuf()
        models = cls.create_batch(*args, **kwargs)
        containers = []
        for model in models:
            container = cls._meta.protobuf()
            model.to_protobuf(container, **to_protobuf_kwargs)
            containers.append(container)
        return containers

    @classmethod
    def build_protobufs(cls, *args, **kwargs):
        cls.verify_has_protobuf()
        models = cls.build_batch(*args, **kwargs)
        containers = []
        for model in models:
            container = cls._meta.protobuf()
            model.to_protobuf(container)
            containers.append(container)
        return containers
