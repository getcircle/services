from csv import DictReader

from protobuf_to_dict import protobuf_to_dict
from protobufs.profile_service_pb2 import ProfileService
import service.control

from .base import OrganizationParser
from .exceptions import ParseError


class Parser(OrganizationParser):

    def parse(self, *args, **kwargs):
        tag_type = kwargs.get('tag_type', ProfileService.SKILL)
        tags = set()
        with open(self.filename, 'r') as csvfile:
            reader = DictReader(csvfile)
            for row in reader:
                tag = ProfileService.Containers.Tag()
                tag.tag_type = tag_type
                tag.name = row['name']
                self.debug_log('adding tag: %s' % (protobuf_to_dict(tag),))
                tags.add(tag.SerializeToString())

        deduped_tags = [ProfileService.Containers.Tag.FromString(t) for t in tags]
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
