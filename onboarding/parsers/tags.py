from csv import DictReader

from protobuf_to_dict import protobuf_to_dict
from protobufs.services.profile import containers_pb2 as profile_containers
import service.control

from .base import OrganizationParser
from .exceptions import ParseError


class Parser(OrganizationParser):

    def parse(self, *args, **kwargs):
        tag_type = kwargs.get('tag_type', profile_containers.TagV1.SKILL)
        tags = set()
        with open(self.filename, 'r') as csvfile:
            reader = DictReader(csvfile)
            for row in reader:
                tag = profile_containers.TagV1()
                tag.tag_type = tag_type
                tag.name = row['name']
                self.debug_log('adding tag: %s' % (protobuf_to_dict(tag),))
                tags.add(tag.SerializeToString())

        deduped_tags = [profile_containers.TagV1.FromString(t) for t in tags]
        if kwargs.get('commit'):
            self.debug_log('saving %s tags' % (len(tags),))
            client = service.control.Client('profile', token=self.token)
            response = client.call_action(
                'create_tags',
                organization_id=self.organization.id,
                tags=deduped_tags,
            )
            if not response.success:
                raise ParseError('failed to create tags: %s' % (response.errors,))

            created_count = len(response.result.tags)
            expected_count = len(tags)
            if created_count != expected_count:
                raise ParseError(
                    'created tags do not equal input tags! expected: %s, got: %s' % (
                        expected_count,
                        created_count,
                    )
                )
