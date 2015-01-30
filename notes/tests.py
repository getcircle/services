import service.control
from services.test import (
    fuzzy,
    mocks,
    TestCase,
)

from . import (
    factories,
    models,
)


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
        factories.NoteFactory.create(
            for_profile_id=for_profile_id,
            owner_profile_id=owner_profile_id,
            status=models.Note.DELETED_STATUS,
        )

        response = self.client.call_action(
            'get_notes',
            for_profile_id=for_profile_id,
            owner_profile_id=owner_profile_id,
        )
        self.assertTrue(response.success)

        # verify we didn't return the deleted note
        self.assertEqual(len(response.result.notes), 2)
        # ensure that the notes are sorted by most recently added
        self._verify_containers(response.result.notes[0], second)
        self._verify_containers(response.result.notes[1], first)

    def test_get_notes_all_notes_for_owner(self):
        owner_profile_id = fuzzy.FuzzyUUID().fuzz()
        factories.NoteFactory.create_batch(size=5, owner_profile_id=owner_profile_id)
        response = self.client.call_action(
            'get_notes',
            owner_profile_id=owner_profile_id,
        )
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.notes), 5)

    def test_delete_note_not_owner(self):
        note = factories.NoteFactory.create_protobuf()
        client = service.control.Client('note', token=mocks.mock_token())
        response = client.call_action('delete_note', note=note)
        self.assertFalse(response.success)
        self.assertIn('FORBIDDEN', response.errors)

    def test_delete_note_does_not_exist(self):
        note = mocks.mock_note()
        response = self.client.call_action('delete_note', note=note)
        self._verify_field_error(response, 'note.id', 'DOES_NOT_EXIST')

    def test_delete_note(self):
        note = factories.NoteFactory.create_protobuf()
        client = service.control.Client(
            'note',
            token=mocks.mock_token(profile_id=note.owner_profile_id),
        )
        response = client.call_action('delete_note', note=note)
        self.assertTrue(response.success)

        note = models.Note.objects.get(pk=note.id)
        self.assertEqual(note.status, models.Note.DELETED_STATUS)

    def test_update_note_not_owner(self):
        note = factories.NoteFactory.create_protobuf()
        client = service.control.Client('note', token=mocks.mock_token())
        response = client.call_action('update_note', note=note)
        self.assertFalse(response.success)
        self.assertIn('FORBIDDEN', response.errors)

    def test_update_note_does_not_exist(self):
        note = mocks.mock_note()
        response = self.client.call_action('update_note', note=note)
        self._verify_field_error(response, 'note.id', 'DOES_NOT_EXIST')

    def test_update_note(self):
        note = factories.NoteFactory.create_protobuf()
        note.content = 'updated'
        client = service.control.Client(
            'note',
            token=mocks.mock_token(profile_id=note.owner_profile_id),
        )
        response = client.call_action('update_note', note=note)
        self.assertTrue(response.success)

        self.assertEqual(response.result.note.content, 'updated')

        note = models.Note.objects.get(pk=note.id)
        self.assertEqual(note.content, 'updated')
