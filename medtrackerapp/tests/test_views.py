from django.test import TestCase
from medtrackerapp.models import Medication, DoseLog
from django.urls import reverse
from rest_framework import status
from django.utils import timezone
from datetime import datetime, date, timedelta
from unittest.mock import patch
import json


class MedicationViewTests(TestCase):
    def setUp(self):
        self.med = Medication.objects.create(name="Aspirin", dosage_mg=100, prescribed_per_day=2)
        self.valid_payload = {
            "name": "Ibuprofen",
            "dosage_mg": 200,
            "prescribed_per_day": 3
        }

    # POSITIVE PATHS - Medication CRUD operations

    def test_list_medications_valid_data(self):
        """Equivalence partition: normal list operation"""
        url = reverse("medication-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Aspirin")
        self.assertEqual(response.data[0]["dosage_mg"], 100)

    def test_create_medication_valid_data(self):
        """Equivalence partition: valid medication data"""
        url = reverse("medication-list")
        response = self.client.post(url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Medication.objects.count(), 2)
        self.assertEqual(response.data["name"], "Ibuprofen")

    def test_retrieve_medication_valid_id(self):
        """Equivalence partition: existing medication ID"""
        url = reverse("medication-detail", kwargs={'pk': self.med.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Aspirin")

    def test_update_medication_valid_data(self):
        """Equivalence partition: valid update data"""
        url = reverse("medication-detail", kwargs={'pk': self.med.pk})
        update_data = {"name": "Aspirin Extra", "dosage_mg": 150, "prescribed_per_day": 2}

        # Explicitly set content type for PUT request
        response = self.client.put(
            url,
            data=json.dumps(update_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.med.refresh_from_db()
        self.assertEqual(self.med.name, "Aspirin Extra")

    def test_delete_medication_valid_id(self):
        """Equivalence partition: existing medication ID"""
        url = reverse("medication-detail", kwargs={'pk': self.med.pk})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Medication.objects.count(), 0)

    # NEGATIVE PATHS - Medication CRUD operations

    def test_retrieve_medication_invalid_id(self):
        """Boundary testing: non-existent medication ID"""
        url = reverse("medication-detail", kwargs={'pk': 9999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_medication_invalid_id(self):
        """Boundary testing: non-existent medication ID"""
        url = reverse("medication-detail", kwargs={'pk': 9999})
        response = self.client.put(
            url,
            data=json.dumps(self.valid_payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_medication_invalid_id(self):
        """Boundary testing: non-existent medication ID"""
        url = reverse("medication-detail", kwargs={'pk': 9999})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_medication_missing_name(self):
        """Boundary testing: missing required field"""
        url = reverse("medication-list")
        invalid_payload = {
            "dosage_mg": 200,
            "prescribed_per_day": 3
        }
        response = self.client.post(url, invalid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

    def test_create_medication_missing_dosage(self):
        """Boundary testing: missing required field"""
        url = reverse("medication-list")
        invalid_payload = {
            "name": "Ibuprofen",
            "prescribed_per_day": 3
        }
        response = self.client.post(url, invalid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("dosage_mg", response.data)

    def test_create_medication_missing_frequency(self):
        """Boundary testing: missing required field"""
        url = reverse("medication-list")
        invalid_payload = {
            "name": "Ibuprofen",
            "dosage_mg": 200
        }
        response = self.client.post(url, invalid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("prescribed_per_day", response.data)

    def test_create_medication_invalid_dosage_type(self):
        """Boundary testing: wrong data type"""
        url = reverse("medication-list")
        invalid_payload = {
            "name": "Ibuprofen",
            "dosage_mg": "two hundred",  # String instead of integer
            "prescribed_per_day": 3
        }
        response = self.client.post(url, invalid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_medication_negative_dosage(self):
        """Boundary testing: negative value"""
        url = reverse("medication-list")
        invalid_payload = {
            "name": "Ibuprofen",
            "dosage_mg": -100,  # Negative value
            "prescribed_per_day": 3
        }
        response = self.client.post(url, invalid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # EXTERNAL INFO ENDPOINT TESTS

    @patch('medtrackerapp.models.DrugInfoService.get_drug_info')
    def test_get_external_info_success(self, mock_get_drug_info):
        """Positive path: external API returns valid data"""
        mock_get_drug_info.return_value = {
            "brand_name": "Aspirin",
            "generic_name": "acetylsalicylic acid",
            "manufacturer": "Bayer"
        }

        url = reverse("medication-get-external-info", kwargs={'pk': self.med.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["brand_name"], "Aspirin")
        mock_get_drug_info.assert_called_once_with("Aspirin")

    @patch('medtrackerapp.models.DrugInfoService.get_drug_info')
    def test_get_external_info_api_error(self, mock_get_drug_info):
        """Negative path: external API returns error"""
        mock_get_drug_info.return_value = {"error": "API unavailable"}

        url = reverse("medication-get-external-info", kwargs={'pk': self.med.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(response.data["error"], "API unavailable")

    def test_get_external_info_invalid_medication(self):
        """Boundary testing: non-existent medication"""
        url = reverse("medication-get-external-info", kwargs={'pk': 9999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class DoseLogViewTests(TestCase):
    def setUp(self):
        self.med = Medication.objects.create(name="Aspirin", dosage_mg=100, prescribed_per_day=2)
        self.dose_log = DoseLog.objects.create(
            medication=self.med,
            taken_at=timezone.now(),
            was_taken=True
        )
        self.valid_payload = {
            "medication": self.med.pk,
            "taken_at": timezone.now().isoformat(),
            "was_taken": True
        }

    # POSITIVE PATHS - DoseLog CRUD operations

    def test_list_dose_logs_valid_data(self):
        """Equivalence partition: normal list operation"""
        url = reverse("doselog-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["was_taken"], True)

    def test_create_dose_log_valid_data(self):
        """Equivalence partition: valid dose log data"""
        url = reverse("doselog-list")
        response = self.client.post(url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DoseLog.objects.count(), 2)

    def test_retrieve_dose_log_valid_id(self):
        """Equivalence partition: existing dose log ID"""
        url = reverse("doselog-detail", kwargs={'pk': self.dose_log.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["was_taken"], True)

    def test_update_dose_log_valid_data(self):
        """Equivalence partition: valid update data"""
        url = reverse("doselog-detail", kwargs={'pk': self.dose_log.pk})
        update_data = {
            "medication": self.med.pk,
            "taken_at": timezone.now().isoformat(),
            "was_taken": False  # Changing from taken to missed
        }

        # Explicitly set content type for PUT request
        response = self.client.put(
            url,
            data=json.dumps(update_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.dose_log.refresh_from_db()
        self.assertEqual(self.dose_log.was_taken, False)

    def test_delete_dose_log_valid_id(self):
        """Equivalence partition: existing dose log ID"""
        url = reverse("doselog-detail", kwargs={'pk': self.dose_log.pk})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(DoseLog.objects.count(), 0)

    # NEGATIVE PATHS - DoseLog CRUD operations

    def test_create_dose_log_missing_medication(self):
        """Boundary testing: missing required field"""
        url = reverse("doselog-list")
        invalid_payload = {
            "taken_at": timezone.now().isoformat(),
            "was_taken": True
        }
        response = self.client.post(url, invalid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("medication", response.data)

    def test_create_dose_log_missing_timestamp(self):
        """Boundary testing: missing required field"""
        url = reverse("doselog-list")
        invalid_payload = {
            "medication": self.med.pk,
            "was_taken": True
        }
        response = self.client.post(url, invalid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("taken_at", response.data)

    def test_create_dose_log_invalid_medication(self):
        """Boundary testing: non-existent medication"""
        url = reverse("doselog-list")
        invalid_payload = {
            "medication": 9999,  # Non-existent medication
            "taken_at": timezone.now().isoformat(),
            "was_taken": True
        }
        response = self.client.post(url, invalid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_dose_log_invalid_timestamp(self):
        """Boundary testing: invalid date format"""
        url = reverse("doselog-list")
        invalid_payload = {
            "medication": self.med.pk,
            "taken_at": "invalid-date-format",
            "was_taken": True
        }
        response = self.client.post(url, invalid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # FILTER BY DATE ENDPOINT TESTS - Only test working scenarios for now

    def test_filter_by_date_valid_range(self):
        """Positive path: valid date range"""
        # Create logs with different dates
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)

        DoseLog.objects.create(
            medication=self.med,
            taken_at=timezone.make_aware(datetime.combine(yesterday, datetime.min.time())),
            was_taken=True
        )
        DoseLog.objects.create(
            medication=self.med,
            taken_at=timezone.make_aware(datetime.combine(tomorrow, datetime.min.time())),
            was_taken=True
        )

        url = reverse("doselog-filter-by-date")
        response = self.client.get(url, {
            'start': yesterday.isoformat(),
            'end': tomorrow.isoformat()
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_by_date_single_day(self):
        """Boundary testing: single day range"""
        today = timezone.now().date()

        url = reverse("doselog-filter-by-date")
        response = self.client.get(url, {
            'start': today.isoformat(),
            'end': today.isoformat()
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_by_date_no_results(self):
        """Boundary testing: date range with no logs"""
        url = reverse("doselog-filter-by-date")
        response = self.client.get(url, {
            'start': '2024-01-01',
            'end': '2024-01-31'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


# EQUIVALENCE PARTITIONING TESTS

class MedicationEquivalencePartitioningTests(TestCase):
    """Tests based on equivalence partitioning principles"""

    def setUp(self):
        # Each test will start fresh due to TestCase's transaction rollback
        pass

    def test_dosage_equivalence_partitions(self):
        """Equivalence partitioning for dosage_mg in API"""
        test_cases = [
            {"name": "Low Dose", "dosage_mg": 1, "prescribed_per_day": 1},  # Very low
            {"name": "Normal Dose", "dosage_mg": 250, "prescribed_per_day": 2},  # Normal
            {"name": "High Dose", "dosage_mg": 1000, "prescribed_per_day": 1},  # High
        ]

        url = reverse("medication-list")

        for test_case in test_cases:
            with self.subTest(test_case=test_case):
                response = self.client.post(url, test_case, format='json')
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class ExternalAPIMockTests(TestCase):
    """
    Tests specifically for mocking the external DrugInfoService API.
    These tests cover the requirements from the problem set.
    """

    def setUp(self):
        self.medication = Medication.objects.create(
            name="Aspirin",
            dosage_mg=100,
            prescribed_per_day=2
        )

    @patch('medtrackerapp.models.DrugInfoService.get_drug_info')
    def test_external_api_mock_success(self, mock_get_drug_info):
        """
        Test mocking external API with successful response.
        Uses patch decorator to mock the GET request response.
        """
        # Mock the external API response
        mock_api_response = {
            "results": [
                {
                    "openfda": {
                        "brand_name": ["Aspirin"],
                        "generic_name": ["acetylsalicylic acid"]
                    },
                    "dosage_form": ["TABLET"],
                    "product_type": ["HUMAN OTC DRUG"]
                }
            ]
        }
        mock_get_drug_info.return_value = mock_api_response

        url = reverse("medication-get-external-info", kwargs={'pk': self.medication.pk})
        response = self.client.get(url)

        # Verify the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, mock_api_response)

        # Verify the mock was called with correct parameters
        mock_get_drug_info.assert_called_once_with("Aspirin")

    @patch('medtrackerapp.models.DrugInfoService.get_drug_info')
    def test_external_api_mock_error(self, mock_get_drug_info):
        """
        Test mocking external API with error response.
        """
        # Mock API error
        mock_api_error = {"error": "Service unavailable"}
        mock_get_drug_info.return_value = mock_api_error

        url = reverse("medication-get-external-info", kwargs={'pk': self.medication.pk})
        response = self.client.get(url)

        # Verify error handling
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(response.data, mock_api_error)

    @patch('medtrackerapp.models.DrugInfoService.get_drug_info')
    def test_external_api_mock_exception(self, mock_get_drug_info):
        """
        Test mocking external API when it raises an exception.
        """
        # Mock API exception
        mock_get_drug_info.side_effect = Exception("Network error")

        url = reverse("medication-get-external-info", kwargs={'pk': self.medication.pk})
        response = self.client.get(url)

        # Verify exception handling
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn("error", response.data)


class ViewEdgeCaseTests(APITestCase):
    """
    Tests to cover edge cases in views
    """


    def setUp(self):
        self.med = Medication.objects.create(name="Aspirin", dosage_mg=100, prescribed_per_day=2)
        self.dose_log = DoseLog.objects.create(
            medication=self.med,
            taken_at=timezone.now(),
            was_taken=True
        )

    def test_medication_list_pagination(self):
        """Test medication list view with multiple items"""
        # Create multiple medications
        for i in range(5):
            Medication.objects.create(
                name=f"Medication {i}",
                dosage_mg=100 + i * 50,
                prescribed_per_day=1 + i
            )

        url = reverse("medication-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 6)  # 5 new + 1 from setUp

    def test_dose_log_filter_invalid_date_combinations(self):
        """Test dose log filter with various invalid date combinations"""
        url = reverse("doselog-filter-by-date")

        # Test with completely invalid dates
        response = self.client.get(url, {
            'start': 'not-a-date',
            'end': 'also-not-a-date'
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_medication_update_partial_data(self):
        """Test medication update with partial data"""
        url = reverse("medication-detail", kwargs={'pk': self.med.pk})

        # Partial update - only change name
        update_data = {"name": "Updated Aspirin"}
        response = self.client.patch(url, update_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.med.refresh_from_db()
        self.assertEqual(self.med.name, "Updated Aspirin")
        # Other fields should remain unchanged
        self.assertEqual(self.med.dosage_mg, 100)


# Replace the problematic test with this corrected version

class ViewFinalCoverageTests(APITestCase):
    """
    Final tests to reach 100% coverage in views.py
    """

    def setUp(self):
        self.med = Medication.objects.create(name="Aspirin", dosage_mg=100, prescribed_per_day=2)

    def test_filter_by_date_specific_error_path(self):
        """
        Test the specific error path in filter_by_date that covers line 97.
        This tests when parse_date returns None for invalid dates.
        """
        url = reverse("doselog-filter-by-date")

        # Test with dates that parse_date cannot parse (will return None, not raise exception)
        response = self.client.get(url, {
            'start': 'invalid-date-format',  # This will make parse_date return None
            'end': 'also-invalid-format'  # This will make parse_date return None
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertIn("valid dates", response.data["error"])

    def test_filter_by_date_mixed_valid_invalid_dates(self):
        """
        Test filter_by_date with one valid and one invalid date.
        """
        url = reverse("doselog-filter-by-date")

        # Test with one valid and one invalid date
        response = self.client.get(url, {
            'start': '2025-01-01',  # Valid date
            'end': 'invalid-date-format'  # Invalid date
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_medication_external_info_specific_error_types(self):
        """
        Test various specific error types in get_external_info.
        """
        url = reverse("medication-get-external-info", kwargs={'pk': self.med.pk})

        # Test with different error formats from fetch_external_info
        with patch('medtrackerapp.models.Medication.fetch_external_info') as mock_fetch:
            # Test error dict with 'error' key - should return 502
            mock_fetch.return_value = {"error": "API unavailable"}
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)

            # Test successful response without 'error' key - should return 200
            mock_fetch.return_value = {"data": "some valid data"}
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_by_date_empty_string_dates(self):
        """
        Test filter_by_date with empty string dates.
        """
        url = reverse("doselog-filter-by-date")

        response = self.client.get(url, {
            'start': '',  # Empty string
            'end': ''  # Empty string
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
