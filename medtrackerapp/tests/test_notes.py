# medtrackerapp/tests/test_notes.py
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from medtrackerapp.models import Medication, Note


class NoteModelTest(TestCase):
    """Test cases for Note model."""

    def setUp(self):
        """Set up test data."""
        self.medication = Medication.objects.create(
            name="Test Medication", dosage_mg=100, prescribed_per_day=2
        )

    def test_create_note(self):
        """Test creating a note."""
        note = Note.objects.create(
            medication=self.medication, text="Take with food", date="2024-01-15"
        )

        self.assertEqual(note.medication, self.medication)
        self.assertEqual(note.text, "Take with food")
        self.assertEqual(str(note.date), "2024-01-15")
        self.assertIn("Test Medication", str(note))

    def test_note_medication_relationship(self):
        """Test note belongs to medication."""
        note = Note.objects.create(
            medication=self.medication, text="Test note", date="2024-01-15"
        )

        self.assertEqual(note.medication.id, self.medication.id)
        self.assertIn(note, self.medication.note_set.all())


class NoteEndpointTest(APITestCase):
    """Test cases for /api/notes/ endpoint."""

    def setUp(self):
        """Set up test data."""
        self.medication = Medication.objects.create(
            name="Test Medication", dosage_mg=100, prescribed_per_day=2
        )

        self.note_data = {
            "medication": self.medication.id,
            "text": "Take medication after breakfast",
            "date": "2024-01-15",
        }

        # Create an existing note for retrieval tests
        self.existing_note = Note.objects.create(
            medication=self.medication, text="Existing note", date="2024-01-10"
        )

    def test_get_all_notes(self):
        """Test retrieving all notes."""
        url = reverse("note-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["text"], "Existing note")

    def test_get_specific_note(self):
        """Test retrieving a specific note by ID."""
        url = reverse("note-detail", kwargs={"pk": self.existing_note.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["text"], "Existing note")
        self.assertEqual(response.data["medication"], self.medication.id)

    def test_create_note(self):
        """Test creating a new note."""
        url = reverse("note-list")
        response = self.client.post(url, self.note_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["text"], self.note_data["text"])
        self.assertEqual(response.data["medication"], self.medication.id)

        # Verify note was created in database
        self.assertEqual(Note.objects.count(), 2)

    def test_create_note_invalid_medication(self):
        """Test creating note with non-existent medication."""
        invalid_data = {
            "medication": 9999,  # Non-existent ID
            "text": "Test note",
            "date": "2024-01-15",
        }

        url = reverse("note-list")
        response = self.client.post(url, invalid_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_note_missing_fields(self):
        """Test creating note with missing required fields."""
        incomplete_data = {"text": "Missing medication field"}

        url = reverse("note-list")
        response = self.client.post(url, incomplete_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_note(self):
        """Test deleting a note."""
        url = reverse("note-detail", kwargs={"pk": self.existing_note.id})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Note.objects.count(), 0)

    def test_delete_nonexistent_note(self):
        """Test deleting a note that doesn't exist."""
        url = reverse("note-detail", kwargs={"pk": 9999})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_note_not_allowed(self):
        """Test that updating a note is not allowed."""
        update_data = {"text": "Updated text", "date": "2024-01-20"}

        url = reverse("note-detail", kwargs={"pk": self.existing_note.id})
        response = self.client.put(url, update_data, format="json")

        # PUT should not be allowed
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_patch_note_not_allowed(self):
        """Test that patching a note is not allowed."""
        patch_data = {"text": "Patched text"}

        url = reverse("note-detail", kwargs={"pk": self.existing_note.id})
        response = self.client.patch(url, patch_data, format="json")

        # PATCH should not be allowed
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_filter_notes_by_medication(self):
        """Test filtering notes by medication ID."""
        # Create another medication and note
        medication2 = Medication.objects.create(
            name="Another Medication", dosage_mg=50, prescribed_per_day=1
        )
        Note.objects.create(
            medication=medication2, text="Note for medication 2", date="2024-01-16"
        )

        # Filter by first medication
        url = reverse("note-list")
        response = self.client.get(url, {"medication": self.medication.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["text"], "Existing note")
