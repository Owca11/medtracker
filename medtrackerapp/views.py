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
    `ModelViewSet`, as well as a custom action for retrieving
    additional information from an external API (OpenFDA).

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
            - days (int): Number of days for calculation (must be positive integer).

        Returns:
            Response:
                - 200 OK: Returns medication_id, days, and expected_doses.
                - 400 BAD REQUEST: If days parameter is missing, invalid, or calculation fails.
                - 404 NOT FOUND: If medication with given ID does not exist.

        Example:
            GET /medications/1/expected-doses/?days=7
        """
        # Validate days parameter
        validation_result = self._validate_days_parameter(request)
        if isinstance(validation_result, Response):
            return validation_result

        days = validation_result
        medication = self.get_object()

        # Calculate expected doses using the model method
        try:
            expected_doses_value = medication.expected_doses(days)
        except ValueError as error:
            return Response(
                {"error": str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Return success response
        return Response({
            "medication_id": medication.id,
            "days": days,
            "expected_doses": expected_doses_value
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
            days_value = int(days_param)
        except (ValueError, TypeError):
            return Response(
                {"error": "Days must be a valid integer."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if parameter is positive
        if days_value <= 0:
            return Response(
                {"error": "Days must be a positive integer greater than zero."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return days_value


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
        start_str = request.query_params.get("start")
        end_str = request.query_params.get("end")

        # Check if parameters are provided
        if start_str is None or end_str is None:
            return Response(
                {"error": "Both 'start' and 'end' query parameters are required and must be valid dates."},
                status=status.HTTP_400_BAD_REQUEST
            )

        start = parse_date(start_str)
        end = parse_date(end_str)

        # Check if parameters are valid dates
        if start is None or end is None:
            return Response(
                {"error": "Both 'start' and 'end' must be valid dates in YYYY-MM-DD format."},
                status=status.HTTP_400_BAD_REQUEST
            )

        logs = self.get_queryset().filter(
            taken_at__date__gte=start,
            taken_at__date__lte=end
        ).order_by("taken_at")

        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)


from .models import Note
from .serializers import NoteSerializer


class NoteViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and managing doctor's notes.

    A Note represents additional information or instructions
    from a doctor regarding a specific medication.

    Endpoints:
        - GET /notes/ — list all notes
        - POST /notes/ — create a new note
        - GET /notes/{id}/ — retrieve a specific note
        - DELETE /notes/{id}/ — delete a note
        - PUT/PATCH are NOT ALLOWED (notes cannot be updated)
    """
    queryset = Note.objects.all()
    serializer_class = NoteSerializer

    # Disable PUT and PATCH methods since notes cannot be updated
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        """
        Optionally filter notes by medication ID.

        Query Parameters:
            medication (int): Filter notes by medication ID

        Example:
            GET /notes/?medication=1
        """
        queryset = Note.objects.all()
        medication_id = self.request.query_params.get('medication')

        if medication_id is not None:
            try:
                queryset = queryset.filter(medication_id=int(medication_id))
            except ValueError:
                # If medication_id is not a valid integer, return empty queryset
                queryset = Note.objects.none()

        return queryset