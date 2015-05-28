from common.db import models
from common import utils
from django.contrib.postgres.fields import (
    ArrayField,
    HStoreField,
)
from protobufs.services.group import containers_pb2 as group_containers


# XXX look into adding organization_id
class GroupMembershipRequest(models.UUIDModel, models.TimestampableModel):

    as_dict_value_transforms = {
        'status': int,
        'provider': int,
        'approver_profile_ids': lambda x: [] if not x else map(str, x),
    }

    status = models.SmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(group_containers.MembershipRequestStatusV1),
    )
    requester_profile_id = models.UUIDField(db_index=True)
    approver_profile_ids = ArrayField(models.UUIDField(), null=True, db_index=True)
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

    class Meta:
        index_together = ('provider', 'group_key')
