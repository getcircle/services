import service.control
from services.test import (
    fuzzy,
    TestCase,
)

from . import factories


class NotesTests(TestCase):

    def setUp(self):
        self.client = service.control.Client('note', token='test-token')

    def test_create_note_invalid_for_profile_id(self):
        response = self.client.call_action(
            'create_note',
            note={
                'for_profile_id': 'invalid',
                'owner_profile_id': fuzzy.FuzzyUUID().fuzz(),
                'content': fuzzy.FuzzyText().fuzz(),
            },
        )
        self._verify_field_error(response, 'note.for_profile_id')

    def test_create_note_invalid_owner_profile_id(self):
        response = self.client.call_action(
            'create_note',
            note={
                'for_profile_id': fuzzy.FuzzyUUID().fuzz(),
                'owner_profile_id': 'invalid',
                'content': fuzzy.FuzzyText().fuzz(),
            },
        )
        self._verify_field_error(response, 'note.owner_profile_id')

    def test_create_note_content_required(self):
        response = self.client.call_action(
            'create_note',
            note={
                'for_profile_id': fuzzy.FuzzyUUID().fuzz(),
                'owner_profile_id': fuzzy.FuzzyUUID().fuzz(),
                'content': '',
            },
        )
        self._verify_field_error(response, 'note.content', 'MISSING')

    def test_create_note(self):
        note = {
            'for_profile_id': fuzzy.FuzzyUUID().fuzz(),
            'owner_profile_id': fuzzy.FuzzyUUID().fuzz(),
            'content': fuzzy.FuzzyText().fuzz(),
        }
        response = self.client.call_action('create_note', note=note)
        self.assertTrue(response.success)
        self._verify_container_matches_data(response.result.note, note)

    def test_get_notes_invalid_for_profile_id(self):
        response = self.client.call_action(
            'get_notes',
            for_profile_id='invalid',
            owner_profile_id=fuzzy.FuzzyUUID().fuzz(),
        )
        self._verify_field_error(response, 'for_profile_id')

    def test_get_notes_invalid_owner_profile_id(self):
        response = self.client.call_action(
            'get_notes',
            for_profile_id=fuzzy.FuzzyUUID().fuzz(),
            owner_profile_id='invalid',
        )
        self._verify_field_error(response, 'owner_profile_id')

    def test_get_notes(self):
        for_profile_id = fuzzy.FuzzyUUID().fuzz()
        owner_profile_id = fuzzy.FuzzyUUID().fuzz()
        first = factories.NoteFactory.create_protobuf(
            for_profile_id=for_profile_id,
            owner_profile_id=owner_profile_id,
        )
        second = factories.NoteFactory.create_protobuf(
            for_profile_id=for_profile_id,
            owner_profile_id=owner_profile_id,
        )

        response = self.client.call_action(
            'get_notes',
            for_profile_id=for_profile_id,
            owner_profile_id=owner_profile_id,
        )
        self.assertTrue(response.success)

        # ensure that the notes are sorted by most recently added
        self._verify_containers(response.result.notes[0], second)
        self._verify_containers(response.result.notes[1], first)
