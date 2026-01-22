# test_services.py
from django.test import TestCase
from unittest.mock import patch, Mock
import requests
from medtrackerapp.services import DrugInfoService


class DrugInfoServiceTests(TestCase):
    """
    Tests for DrugInfoService to cover the missing lines in services.py
    """

    def test_get_drug_info_success(self):
        """Test successful API call with valid response"""
        mock_response = {
            "results": [
                {
                    "openfda": {
                        "generic_name": ["ibuprofen"],
                        "manufacturer_name": ["Test Manufacturer"],
                    },
                    "warnings": ["Keep out of reach of children"],
                    "purpose": ["Pain relief"],
                }
            ]
        }

        with patch("medtrackerapp.services.requests.get") as mock_get:
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_response
            mock_get.return_value = mock_resp

            result = DrugInfoService.get_drug_info("ibuprofen")

            self.assertEqual(result["name"], "ibuprofen")
            self.assertEqual(result["manufacturer"], "Test Manufacturer")
            mock_get.assert_called_once()

    def test_get_drug_info_empty_drug_name(self):
        """Test with empty drug name - should raise ValueError"""
        with self.assertRaises(ValueError) as context:
            DrugInfoService.get_drug_info("")

        self.assertIn("drug_name is required", str(context.exception))

    def test_get_drug_info_none_drug_name(self):
        """Test with None drug name - should raise ValueError"""
        with self.assertRaises(ValueError) as context:
            DrugInfoService.get_drug_info(None)

        self.assertIn("drug_name is required", str(context.exception))

    def test_get_drug_info_http_error(self):
        """Test API returns non-200 status code"""
        with patch("medtrackerapp.services.requests.get") as mock_get:
            mock_resp = Mock()
            mock_resp.status_code = 404
            mock_get.return_value = mock_resp

            with self.assertRaises(ValueError) as context:
                DrugInfoService.get_drug_info("test")

            self.assertIn("OpenFDA API error: 404", str(context.exception))

    def test_get_drug_info_no_results(self):
        """Test API returns empty results"""
        mock_response = {"results": []}

        with patch("medtrackerapp.services.requests.get") as mock_get:
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_response
            mock_get.return_value = mock_resp

            with self.assertRaises(ValueError) as context:
                DrugInfoService.get_drug_info("unknown_drug")

            self.assertIn("No results found", str(context.exception))

    def test_get_drug_info_connection_error(self):
        """Test network connection error"""
        with patch("medtrackerapp.services.requests.get") as mock_get:
            mock_get.side_effect = requests.ConnectionError("Connection failed")

            with self.assertRaises(requests.ConnectionError):
                DrugInfoService.get_drug_info("test")

    def test_get_drug_info_timeout(self):
        """Test request timeout"""
        with patch("medtrackerapp.services.requests.get") as mock_get:
            mock_get.side_effect = requests.Timeout("Request timed out")

            with self.assertRaises(requests.Timeout):
                DrugInfoService.get_drug_info("test")

    def test_get_drug_info_missing_openfda_fields(self):
        """Test response with missing openfda fields"""
        mock_response = {
            "results": [
                {
                    "openfda": {},  # Empty openfda
                    "warnings": ["Test warning"],
                    "purpose": ["Test purpose"],
                }
            ]
        }

        with patch("medtrackerapp.services.requests.get") as mock_get:
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_response
            mock_get.return_value = mock_resp

            result = DrugInfoService.get_drug_info("test_drug")

            self.assertEqual(
                result["name"], "test_drug"
            )  # Should fall back to input name
            self.assertEqual(result["manufacturer"], "Unknown")

    def test_get_drug_info_with_list_fields(self):
        """Test response with list fields in openfda"""
        mock_response = {
            "results": [
                {
                    "openfda": {
                        "generic_name": ["ibuprofen", "advil"],
                        "manufacturer_name": ["Manufacturer A", "Manufacturer B"],
                    }
                }
            ]
        }

        with patch("medtrackerapp.services.requests.get") as mock_get:
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_response
            mock_get.return_value = mock_resp

            result = DrugInfoService.get_drug_info("test")

            self.assertEqual(result["name"], "ibuprofen")  # Should take first element
            self.assertEqual(result["manufacturer"], "Manufacturer A")
