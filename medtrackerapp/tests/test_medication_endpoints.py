
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from medtrackerapp.models import Medication


class MedicationExpectedDosesEndpointTest(APITestCase):
    """Test cases for the /api/medications/<id>/expected-doses/ endpoint."""

    def setUp(self):
        """Set up test data."""
        self.medication = Medication.objects.create(
            name="Test Medication",
            dosage_mg=500,
            prescribed_per_day=2
        )
        self.valid_url = reverse('medication-expected-doses', kwargs={'pk': self.medication.id})

    def test_valid_request_returns_expected_doses(self):
        """Test that a valid request returns correct expected doses."""
        response = self.client.get(self.valid_url, {'days': 7})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check response structure
        self.assertIn('medication_id', response.data)
        self.assertIn('days', response.data)
        self.assertIn('expected_doses', response.data)

        # Check response values
        self.assertEqual(response.data['medication_id'], self.medication.id)
        self.assertEqual(response.data['days'], 7)
        self.assertEqual(response.data['expected_doses'], 14)  # 7 days * 2 per day

    def test_missing_days_parameter_returns_400(self):
        """Test that missing days parameter returns 400."""
        response = self.client.get(self.valid_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_negative_days_returns_400(self):
        """Test that negative days value returns 400."""
        response = self.client.get(self.valid_url, {'days': -5})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_zero_days_returns_400(self):
        """Test that zero days value returns 400 (days must be positive)."""
        response = self.client.get(self.valid_url, {'days': 0})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_integer_days_returns_400(self):
        """Test that non-integer days value returns 400."""
        response = self.client.get(self.valid_url, {'days': 'abc'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_decimal_days_returns_400(self):
        """Test that decimal days value returns 400."""
        response = self.client.get(self.valid_url, {'days': 7.5})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_string_days_returns_400(self):
        """Test that empty string for days returns 400."""
        response = self.client.get(self.valid_url, {'days': ''})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_medication_returns_404(self):
        """Test that requesting non-existent medication returns 404."""
        invalid_url = reverse('medication-expected-doses', kwargs={'pk': 9999})
        response = self.client.get(invalid_url, {'days': 7})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_medication_with_zero_prescribed_per_day_returns_400(self):
        """Test that medication with prescribed_per_day=0 returns 400."""
        # Create medication with zero prescribed per day
        medication_zero = Medication.objects.create(
            name="Zero Prescribed Medication",
            dosage_mg=100,
            prescribed_per_day=0
        )
        url = reverse('medication-expected-doses', kwargs={'pk': medication_zero.id})
        response = self.client.get(url, {'days': 5})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)