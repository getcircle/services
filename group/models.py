from bulk_update.manager import BulkUpdateManager
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
    group_id = models.UUIDField()
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
        index_together = ('provider', 'group_id')


class GoogleGroup(models.UUIDModel, models.TimestampableModel):

    model_to_protobuf_mapping = {'description': 'group_description'}

    bulk_update_manager = BulkUpdateManager()

    provider_uid = models.CharField(max_length=255)
    email = models.CharField(max_length=255, db_index=True)
    display_name = models.CharField(max_length=255, null=True)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True)
    direct_members_count = models.IntegerField(default=0)
    # XXX should potentially support searching by alias
    aliases = ArrayField(models.CharField(max_length=255), null=True)
    settings = HStoreField(null=True)
    last_sync_id = models.UUIDField(null=True)
    organization_id = models.UUIDField()

    class Meta:
        protobuf = group_containers.GroupV1
        index_together = ('last_sync_id', 'organization_id')
        unique_together = ('provider_uid', 'organization_id')


class GoogleGroupMember(models.TimestampableModel):

    bulk_update_manager = BulkUpdateManager()

    profile_id = models.UUIDField(db_index=True)
    provider_uid = models.CharField(max_length=255)
    group = models.ForeignKey(GoogleGroup, db_index=True)
    # XXX not sure what max_length should be here, google admin can configure custom roles
    role = models.CharField(max_length=255, db_index=True)
    organization_id = models.UUIDField()
    last_sync_id = models.UUIDField(null=True)

    class Meta:
        index_together = (
            ('last_sync_id', 'organization_id'),
            ('profile_id', 'organization_id'),
            ('group', 'organization_id'),
        )
        unique_together = ('profile_id', 'group', 'organization_id')
