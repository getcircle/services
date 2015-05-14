from common.db import models
from common import utils
from django.contrib.postgres.fields import (
    ArrayField,
    HStoreField,
)
from protobufs.services.group import containers_pb2 as group_containers


class GroupMembershipRequest(models.UUIDModel, models.TimestampableModel):

    as_dict_value_transforms = {
        'status': int,
        'provider': int,
    }

    status = models.SmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(group_containers.MembershipRequestStatusV1),
    )
    requester_profile_id = models.UUIDField()
    approver_profile_ids = ArrayField(models.UUIDField(), null=True)
    group_key = models.CharField(max_length=255)
    provider = models.SmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(group_containers.GroupProviderV1),
    )
    meta = HStoreField(null=True)

    def get_meta(self):
        meta = []
        if self.meta:
            meta = [{'key': key, 'value': value} for key, value in self.meta.iteritems()]
        return meta
