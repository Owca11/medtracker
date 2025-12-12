from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.dateparse import parse_date
from .models import Medication, DoseLog
from .serializers import MedicationSerializer, DoseLogSerializer

class MedicationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and managing medications.

    Provides standard CRUD operations via the Django REST Framework

    Endpoints:
        - GET /medications/ — list all medications
        - POST /medications/ — create a new medication
        - GET /medications/{id}/ — retrieve a specific medication
        - PUT/PATCH /medications/{id}/ — update a medication
        - DELETE /medications/{id}/ — delete a medication
        - GET /medications/{id}/info/ — fetch external drug info from OpenFDA
        - GET /medications/{id}/expected-doses/ — calculate expected doses over days
    """
    queryset = Medication.objects.all()
    serializer_class = MedicationSerializer

    @action(detail=True, methods=["get"], url_path="info")
    def get_external_info(self, request, pk=None):
        """
        Retrieve external drug information from the OpenFDA API.

        Calls the `Medication.fetch_external_info()` method, which
        delegates to the `DrugInfoService` for API access.

        Args:
            request (Request): The current HTTP request.
            pk (int): Primary key of the medication record.

        Returns:
            Response:
                - 200 OK: External API data returned successfully.
                - 502 BAD GATEWAY: If the external API request failed.

        Example:
            GET /medications/1/info/
        """
        medication = self.get_object()
        data = medication.fetch_external_info()

        if isinstance(data, dict) and data.get("error"):
            return Response(data, status=status.HTTP_502_BAD_GATEWAY)
        return Response(data)

    @action(detail=True, methods=["get"], url_path="expected-doses")
    def expected_doses(self, request, pk=None):
        """
        Calculate expected number of doses for a medication over a given number of days.

        Query Parameters:
            - days (int): Number of days for calculation (must be positive integer > 0).

        Returns:
            Response:
                - 200 OK: Returns medication_id, days, and expected_doses.
                - 400 BAD REQUEST: If days parameter is missing, invalid, or calculation fails.
                - 404 NOT FOUND: If medication with given ID does not exist.

        Example:
            GET /medications/1/expected-doses/?days=7
        """
        medication = self.get_object()

        # Validate days parameter
        days = self._validate_days_parameter(request)
        if isinstance(days, Response):
            return days

        # Calculate expected doses
        try:
            expected_doses = medication.expected_doses(days)
        except ValueError as e:
            return Response(
                {"error": f"Calculation failed: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Return success response
        return Response({
            "medication_id": medication.id,
            "days": days,
            "expected_doses": expected_doses
        })

    def _validate_days_parameter(self, request):
        """
        Validate the 'days' query parameter.

        Args:
            request: HTTP request object

        Returns:
            int: Validated days value if successful
            Response: Error response if validation fails
        """
        days_param = request.query_params.get("days")

        # Check if parameter exists
        if days_param is None:
            return Response(
                {"error": "Query parameter 'days' is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if parameter can be converted to integer
        try:
            days = int(days_param)
        except (ValueError, TypeError):
            return Response(
                {"error": "Days must be a valid integer."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if parameter is positive
        if days <= 0:
            return Response(
                {"error": "Days must be a positive integer greater than zero."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return days


class DoseLogViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and managing dose logs.

    A DoseLog represents an event where a medication dose was either
    taken or missed. This viewset provides standard CRUD operations
    and a custom filtering action by date range.

    Endpoints:
        - GET /logs/ — list all dose logs
        - POST /logs/ — create a new dose log
        - GET /logs/{id}/ — retrieve a specific log
        - PUT/PATCH /logs/{id}/ — update a dose log
        - DELETE /logs/{id}/ — delete a dose log
        - GET /logs/filter/?start=YYYY-MM-DD&end=YYYY-MM-DD —
          filter logs within a date range
    """
    queryset = DoseLog.objects.all()
    serializer_class = DoseLogSerializer

    @action(detail=False, methods=["get"], url_path="filter")
    def filter_by_date(self, request):
        """
        Retrieve all dose logs within a given date range.

        Query Parameters:
            - start (YYYY-MM-DD): Start date of the range (inclusive).
            - end (YYYY-MM-DD): End date of the range (inclusive).

        Returns:
            Response:
                - 200 OK: A list of dose logs between the two dates.
                - 400 BAD REQUEST: If start or end parameters are missing or invalid.

        Example:
            GET /logs/filter/?start=2025-11-01&end=2025-11-07
        """
        start = parse_date(request.query_params.get("start"))
        end = parse_date(request.query_params.get("end"))

        if not start or not end:
            return Response(
                {"error": "Both 'start' and 'end' query parameters are required and must be valid dates."},
                status=status.HTTP_400_BAD_REQUEST
            )

        logs = self.get_queryset().filter(
            taken_at__date__gte=start,
            taken_at__date__lte=end
        ).order_by("taken_at")

        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)