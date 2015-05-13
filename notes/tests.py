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
        with self.assertFieldError('note.for_profile_id'):
            self.client.call_action(
                'create_note',
                note={
                    'for_profile_id': 'invalid',
                    'owner_profile_id': fuzzy.FuzzyUUID().fuzz(),
                    'content': fuzzy.FuzzyText().fuzz(),
                },
            )

    def test_create_note_invalid_owner_profile_id(self):
        with self.assertFieldError('note.owner_profile_id'):
            self.client.call_action(
                'create_note',
                note={
                    'for_profile_id': fuzzy.FuzzyUUID().fuzz(),
                    'owner_profile_id': 'invalid',
                    'content': fuzzy.FuzzyText().fuzz(),
                },
            )

    def test_create_note_content_required(self):
        with self.assertFieldError('note.content', 'MISSING'):
            self.client.call_action(
                'create_note',
                note={
                    'for_profile_id': fuzzy.FuzzyUUID().fuzz(),
                    'owner_profile_id': fuzzy.FuzzyUUID().fuzz(),
                    'content': '',
                },
            )

    def test_create_note(self):
        note = {
            'for_profile_id': fuzzy.FuzzyUUID().fuzz(),
            'owner_profile_id': fuzzy.FuzzyUUID().fuzz(),
            'content': fuzzy.FuzzyText().fuzz(),
        }
        response = self.client.call_action('create_note', note=note)
        self.assertTrue(response.success)
        self.verify_container_matches_data(response.result.note, note)

    def test_get_notes_invalid_for_profile_id(self):
        with self.assertFieldError('for_profile_id'):
            self.client.call_action(
                'get_notes',
                for_profile_id='invalid',
                owner_profile_id=fuzzy.FuzzyUUID().fuzz(),
            )

    def test_get_notes_invalid_owner_profile_id(self):
        with self.assertFieldError('owner_profile_id'):
            self.client.call_action(
                'get_notes',
                for_profile_id=fuzzy.FuzzyUUID().fuzz(),
                owner_profile_id='invalid',
            )

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
        self.verify_containers(response.result.notes[0], second)
        self.verify_containers(response.result.notes[1], first)

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
        with self.assertRaisesCallActionError() as expected:
            client.call_action('delete_note', note=note)

        self.assertIn('FORBIDDEN', expected.exception.response.errors)

    def test_delete_note_does_not_exist(self):
        note = mocks.mock_note()
        with self.assertFieldError('note.id', 'DOES_NOT_EXIST'):
            self.client.call_action('delete_note', note=note)

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
        with self.assertRaisesCallActionError() as expected:
            client.call_action('update_note', note=note)
        self.assertIn('FORBIDDEN', expected.exception.response.errors)

    def test_update_note_does_not_exist(self):
        note = mocks.mock_note()
        with self.assertFieldError('note.id', 'DOES_NOT_EXIST'):
            self.client.call_action('update_note', note=note)

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

    def test_get_notes_paginated(self):
        owner_profile_id = fuzzy.FuzzyUUID().fuzz()
        factories.NoteFactory.create_batch(size=10, owner_profile_id=owner_profile_id)
        client = service.control.Client(
            'note',
            token=mocks.mock_token(profile_id=owner_profile_id),
        )
        response = client.call_action(
            'get_notes',
            owner_profile_id=owner_profile_id,
            control={'paginator': {'page_size': 5}},
        )
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.notes), 5)
        self.assertEqual(response.control.paginator.next_page, 2)
        self.assertEqual(response.control.paginator.total_pages, 2)
