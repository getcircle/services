import re

from common.db import models
from django.conf import settings
from protobufs.services.file import containers_pb2 as file_containers
import service.control


def _safe_int(value):
    if value is not None:
        return int(value)


class File(models.UUIDModel, models.TimestampableModel):

    as_dict_value_transforms = {'size': _safe_int}

    by_profile_id = models.UUIDField()
    organization_id = models.UUIDField()
    source_url = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=255)
    size = models.BigIntegerField(null=True)
    bucket = models.CharField(max_length=64, default=settings.AWS_S3_FILE_BUCKET)
    key = models.CharField(max_length=255)
    region_name = models.CharField(max_length=255, default=settings.AWS_REGION_NAME)

    class Meta:
        protobuf = file_containers.FileV1
        index_together = ('id', 'organization_id')

    def _get_source_url(self, organization):
        scheme = 'https'
        frontend_url = settings.FRONTEND_URL
        # If the scheme is already in the front-end URL, take it out.
        scheme_match = re.match(r'^(\w+):\/\/\S+$', frontend_url)
        if scheme_match:
            scheme = scheme_match.group(1)
            frontend_url = frontend_url[len(scheme + '://'):]
        domain = organization.domain
        details = {
            'scheme': scheme,
            'domain': domain,
            'dot': '.' if domain else '',
            'frontend_url': frontend_url,
            'id': self.id,
            'name': self.name.encode('utf-8'),
        }
        return '{scheme}://{domain}{dot}{frontend_url}/file/{id}/{name}'.format(**details)

    def to_protobuf(self, protobuf=None, inflations=None, token=None, fields=None, **overrides):
        organization = None
        if 'organization' in overrides:
            organization = overrides['organization']
        elif token:
            organization = service.control.get_object(
                service='organization',
                action='get_organization',
                client_kwargs={'token': token},
                return_object='organization',
            )
        if organization:
            overrides['source_url'] = self._get_source_url(organization)
        protobuf = self.new_protobuf_container(protobuf)
        return super(File, self).to_protobuf(
            protobuf,
            inflations=inflations,
            fields=fields,
            **overrides
        )
