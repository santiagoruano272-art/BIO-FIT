from rest_framework import serializers

class EquipmentSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=100, error_messages={
        'required': 'El nombre del equipamiento es obligatorio.',
        'blank': 'El nombre no puede estar vacío.'
    })
    descripcion = serializers.CharField(max_length=500, required=False, allow_blank=True)
    estado = serializers.ChoiceField(
        choices=['excelente', 'bueno', 'mantenimiento', 'fuera_de_servicio'],
        error_messages={'invalid_choice': 'El estado seleccionado no es válido.'}
    )
    fecha_adquisicion = serializers.DateField(error_messages={
        'invalid': 'Formato de fecha inválido. Use AAAA-MM-DD.'
    })
    ubicacion = serializers.CharField(max_length=100, error_messages={
        'required': 'La ubicación en el gimnasio es obligatoria.'
    })
    cantidad = serializers.IntegerField(min_value=1, default=1, error_messages={
        'min_value': 'La cantidad debe ser al menos 1.'
    })