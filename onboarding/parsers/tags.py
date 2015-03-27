from csv import DictReader
from protobuf_to_dict import protobuf_to_dict
import service.control

from protobufs.profile_service_pb2 import ProfileService

from .base import OrganizationParser
from .exceptions import ParseError


class Parser(OrganizationParser):

    def parse(self, *args, **kwargs):
        skills = set()
        with open(self.filename, 'r') as csvfile:
            reader = DictReader(csvfile)
            for row in reader:
                skill = ProfileService.Containers.Skill()
                skill.name = row['name']
                self.debug_log('adding skill: %s' % (protobuf_to_dict(skill),))
                skills.add(skill.SerializeToString())

        deduped_skills = [ProfileService.Containers.Skill.FromString(t) for t in skills]
        if kwargs.get('commit'):
            self.debug_log('saving %s skills' % (len(skills),))
            client = service.control.Client('profile', token=self.token)
            response = client.call_action(
                'create_skills',
                organization_id=self.organization.id,
                skills=deduped_skills,
            )
            if not response.success:
                raise ParseError('failed to create skills: %s' % (response.errors,))

            created_count = len(response.result.skills)
            expected_count = len(skills)
            if created_count != expected_count:
                raise ParseError(
                    'created skills do not equal input skills! expected: %s, got: %s' % (
                        expected_count,
                        created_count,
                    )
                )
