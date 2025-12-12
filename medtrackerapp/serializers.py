from rest_framework import serializers
from .models import Medication, DoseLog, Note

class MedicationSerializer(serializers.ModelSerializer):
    adherence = serializers.SerializerMethodField()

    class Meta:
        model = Medication
        fields = ["id", "name", "dosage_mg", "prescribed_per_day", "adherence"]

    def get_adherence(self, obj):
        return obj.adherence_rate()


class DoseLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoseLog
        fields = ["id", "medication", "taken_at", "was_taken"]



class NoteSerializer(serializers.ModelSerializer):
    """
    Serializer for Note model.

    Handles conversion between Note instances and JSON,
    including validation of incoming data.
    """

    class Meta:
        model = Note
        fields = ['id', 'medication', 'text', 'date']
        read_only_fields = ['id']

    def validate_medication(self, value):
        """Validate that medication exists."""
        if not Medication.objects.filter(id=value.id).exists():
            raise serializers.ValidationError("Medication does not exist.")
        return value

    def validate_date(self, value):
        """Validate date is not in the future."""
        from django.utils import timezone
        if value > timezone.now().date():
            raise serializers.ValidationError("Date cannot be in the future.")
        return value