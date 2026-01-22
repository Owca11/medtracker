# test_external_api.py
from rest_framework.test import APITestCase
from django.urls import reverse
from rest_framework import status
from unittest.mock import patch
from medtrackerapp.models import Medication


class DrugInfoServiceMockTests(APITestCase):
    """
    Tests for mocking the external DrugInfoService API.

    These tests use unittest.mock.patch to simulate different responses
    from the external API without making actual network calls.
    """

    def setUp(self):
        """Set up test data"""
        self.medication = Medication.objects.create(
            name="Aspirin", dosage_mg=100, prescribed_per_day=2
        )
        self.url = reverse(
            "medication-get-external-info", kwargs={"pk": self.medication.pk}
        )

    @patch("medtrackerapp.models.DrugInfoService.get_drug_info")
    def test_external_api_success_response(self, mock_get_drug_info):
        """
        Test successful response from external API.

        Equivalence partition: Valid medication name, API returns successful response.
        """
        # Mock the successful API response
        mock_response = {
            "results": [
                {
                    "openfda": {
                        "brand_name": ["Aspirin"],
                        "generic_name": ["acetylsalicylic acid"],
                        "manufacturer_name": ["Bayer"],
                    },
                    "dosage_form": ["TABLET"],
                    "product_type": ["HUMAN OTC DRUG"],
                }
            ]
        }
        mock_get_drug_info.return_value = mock_response

        response = self.client.get(self.url)

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, mock_response)
        mock_get_drug_info.assert_called_once_with("Aspirin")

    @patch("medtrackerapp.models.DrugInfoService.get_drug_info")
    def test_external_api_empty_response(self, mock_get_drug_info):
        """
        Test empty response from external API.

        Boundary testing: API returns empty results for unknown medication.
        """
        # Mock empty API response
        mock_response = {"results": []}
        mock_get_drug_info.return_value = mock_response

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, mock_response)
        mock_get_drug_info.assert_called_once_with("Aspirin")

    @patch("medtrackerapp.models.DrugInfoService.get_drug_info")
    def test_external_api_error_response(self, mock_get_drug_info):
        """
        Test error response from external API.

        Negative path: API returns error dictionary.
        """
        # Mock error response
        mock_response = {"error": "API rate limit exceeded"}
        mock_get_drug_info.return_value = mock_response

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(response.data, mock_response)
        mock_get_drug_info.assert_called_once_with("Aspirin")

    @patch("medtrackerapp.models.DrugInfoService.get_drug_info")
    def test_external_api_exception(self, mock_get_drug_info):
        """
        Test exception during API call.

        Negative path: External API raises an exception.
        """
        # Mock API raising an exception
        mock_get_drug_info.side_effect = Exception("Network connection failed")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn("error", response.data)
        self.assertIn("Network connection failed", response.data["error"])
        mock_get_drug_info.assert_called_once_with("Aspirin")

    @patch("medtrackerapp.models.DrugInfoService.get_drug_info")
    def test_external_api_timeout(self, mock_get_drug_info):
        """
        Test API timeout scenario.

        Boundary testing: API call times out.
        """
        # Mock timeout exception
        mock_get_drug_info.side_effect = TimeoutError("Request timed out")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn("error", response.data)
        self.assertIn("Request timed out", response.data["error"])

    @patch("medtrackerapp.models.DrugInfoService.get_drug_info")
    def test_external_api_partial_data(self, mock_get_drug_info):
        """
        Test API response with partial/missing data.

        Equivalence partition: API returns data but some fields are missing.
        """
        # Mock response with missing fields
        mock_response = {
            "results": [
                {
                    "openfda": {
                        "brand_name": ["Aspirin"]
                        # Missing generic_name and manufacturer_name
                    }
                    # Missing dosage_form and product_type
                }
            ]
        }
        mock_get_drug_info.return_value = mock_response

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, mock_response)

    @patch("medtrackerapp.models.DrugInfoService.get_drug_info")
    def test_external_api_different_medication_names(self, mock_get_drug_info):
        """
        Test API with different medication name formats.

        Equivalence partitioning: Different name formats should all work.
        """
        test_cases = [
            ("Aspirin", {"results": [{"openfda": {"brand_name": ["Aspirin"]}}]}),
            (
                "ibuprofen",
                {"results": [{"openfda": {"brand_name": ["Advil", "Motrin"]}}]},
            ),
            ("LISINOPRIL", {"results": [{"openfda": {"brand_name": ["Zestril"]}}]}),
            (
                "Vitamin C",
                {"results": [{"openfda": {"brand_name": ["Ascorbic Acid"]}}]},
            ),
        ]

        for med_name, mock_response in test_cases:
            with self.subTest(medication_name=med_name):
                # Create medication with different name
                medication = Medication.objects.create(
                    name=med_name, dosage_mg=100, prescribed_per_day=1
                )
                url = reverse(
                    "medication-get-external-info", kwargs={"pk": medication.pk}
                )

                mock_get_drug_info.return_value = mock_response

                response = self.client.get(url)

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                mock_get_drug_info.assert_called_with(med_name)

    @patch("medtrackerapp.models.DrugInfoService.get_drug_info")
    def test_external_api_multiple_calls(self, mock_get_drug_info):
        """
        Test multiple API calls to verify mock reset behavior.

        Boundary testing: Ensure mock works correctly across multiple calls.
        """
        # First call
        mock_response_1 = {"results": [{"openfda": {"brand_name": ["Aspirin"]}}]}
        mock_get_drug_info.return_value = mock_response_1

        response_1 = self.client.get(self.url)
        self.assertEqual(response_1.status_code, status.HTTP_200_OK)

        # Second call with different response
        mock_response_2 = {"results": []}
        mock_get_drug_info.return_value = mock_response_2

        response_2 = self.client.get(self.url)
        self.assertEqual(response_2.status_code, status.HTTP_200_OK)
        self.assertEqual(response_2.data, mock_response_2)

        # Verify mock was called twice
        self.assertEqual(mock_get_drug_info.call_count, 2)

    @patch("medtrackerapp.models.DrugInfoService.get_drug_info")
    def test_external_api_with_query_parameters(self, mock_get_drug_info):
        """
        Test that the service is called with correct parameters.

        Positive path: Verify the correct medication name is passed to the service.
        """
        mock_response = {"results": [{"openfda": {"brand_name": ["Test Med"]}}]}
        mock_get_drug_info.return_value = mock_response

        # Test with different medication
        test_med = Medication.objects.create(
            name="Test Medication 123", dosage_mg=50, prescribed_per_day=3
        )
        url = reverse("medication-get-external-info", kwargs={"pk": test_med.pk})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_get_drug_info.assert_called_once_with("Test Medication 123")


class DrugInfoServiceIntegrationMockTests(APITestCase):
    """
    Integration-style tests mocking the external API at different levels.
    """

    def setUp(self):
        self.medication = Medication.objects.create(
            name="Paracetamol", dosage_mg=500, prescribed_per_day=4
        )

    @patch("medtrackerapp.views.Medication.fetch_external_info")
    def test_mock_at_view_level(self, mock_fetch_external_info):
        """
        Test mocking at the view level (Medication model method).

        This tests the integration between view and model.
        """
        mock_response = {
            "results": [
                {
                    "openfda": {
                        "brand_name": ["Tylenol"],
                        "generic_name": ["acetaminophen"],
                    }
                }
            ]
        }
        mock_fetch_external_info.return_value = mock_response

        url = reverse("medication-get-external-info", kwargs={"pk": self.medication.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, mock_response)
        mock_fetch_external_info.assert_called_once()

    @patch("medtrackerapp.models.DrugInfoService.get_drug_info")
    def test_mock_at_service_level(self, mock_get_drug_info):
        """
        Test mocking at the service level (DrugInfoService class).

        This tests the actual service integration.
        """
        mock_response = {
            "results": [
                {
                    "openfda": {
                        "brand_name": ["Paracetamol"],
                        "generic_name": ["paracetamol"],
                    }
                }
            ]
        }
        mock_get_drug_info.return_value = mock_response

        # Call the model method directly
        result = self.medication.fetch_external_info()

        self.assertEqual(result, mock_response)
        mock_get_drug_info.assert_called_once_with("Paracetamol")

    @patch("medtrackerapp.models.DrugInfoService.get_drug_info")
    def test_mock_chain_calls(self, mock_get_drug_info):
        """
        Test the complete chain: View -> Model -> Service.

        Integration test verifying the full flow with mocked external API.
        """
        mock_response = {
            "results": [
                {
                    "openfda": {
                        "brand_name": ["Complete Chain Test"],
                        "generic_name": ["test substance"],
                    }
                }
            ]
        }
        mock_get_drug_info.return_value = mock_response

        url = reverse("medication-get-external-info", kwargs={"pk": self.medication.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, mock_response)

        # Verify the service was called with correct parameters
        mock_get_drug_info.assert_called_once_with("Paracetamol")


class DrugInfoServiceEdgeCaseTests(APITestCase):
    """
    Tests for edge cases and boundary conditions in external API mocking.
    """

    def setUp(self):
        self.medication = Medication.objects.create(
            name="Edge Case Med", dosage_mg=100, prescribed_per_day=1
        )
        self.url = reverse(
            "medication-get-external-info", kwargs={"pk": self.medication.pk}
        )

    @patch("medtrackerapp.models.DrugInfoService.get_drug_info")
    def test_external_api_large_response(self, mock_get_drug_info):
        """
        Test handling of large API responses.

        Boundary testing: API returns large amount of data.
        """
        # Mock a large response with multiple results
        large_response = {
            "results": [
                {
                    "openfda": {
                        "brand_name": [f"Brand {i}" for i in range(100)],
                        "generic_name": [f"Generic {i}" for i in range(100)],
                    },
                    "description": "A" * 1000,  # Long string
                }
                for _ in range(10)  # Multiple items
            ]
        }
        mock_get_drug_info.return_value = large_response

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, large_response)

    @patch("medtrackerapp.models.DrugInfoService.get_drug_info")
    def test_external_api_special_characters(self, mock_get_drug_info):
        """
        Test API with medication names containing special characters.

        Boundary testing: Unusual medication names.
        """
        special_meds = [
            "Medication-V2",
            "Drug+Plus",
            "Pill (Extended Release)",
            "Capsule, 24HR",
        ]

        for med_name in special_meds:
            with self.subTest(medication_name=med_name):
                medication = Medication.objects.create(
                    name=med_name, dosage_mg=100, prescribed_per_day=1
                )
                url = reverse(
                    "medication-get-external-info", kwargs={"pk": medication.pk}
                )

                mock_response = {"results": [{"openfda": {"brand_name": [med_name]}}]}
                mock_get_drug_info.return_value = mock_response

                response = self.client.get(url)

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                mock_get_drug_info.assert_called_with(med_name)

    @patch("medtrackerapp.models.DrugInfoService.get_drug_info")
    def test_external_api_concurrent_calls(self, mock_get_drug_info):
        """
        Test behavior with concurrent API calls.

        Boundary testing: Multiple rapid API calls.
        """
        import threading

        results = []

        def make_api_call(med_id, mock_response):
            medication = Medication.objects.create(
                name=f"Concurrent Med {med_id}", dosage_mg=100, prescribed_per_day=1
            )
            url = reverse("medication-get-external-info", kwargs={"pk": medication.pk})

            mock_get_drug_info.return_value = mock_response
            response = self.client.get(url)
            results.append((med_id, response.status_code))

        # Create multiple threads for concurrent calls
        threads = []
        for i in range(5):
            mock_response = {"results": [{"openfda": {"brand_name": [f"Med {i}"]}}]}
            thread = threading.Thread(target=make_api_call, args=(i, mock_response))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all calls were successful
        for med_id, status_code in results:
            self.assertEqual(status_code, status.HTTP_200_OK)
