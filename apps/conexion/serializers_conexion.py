from rest_framework import serializers

class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(error_messages={
        'invalid': 'Por favor, introduce una dirección de correo válida.',
        'required': 'El correo electrónico es obligatorio.'
    })
    password = serializers.CharField(min_length=6, error_messages={
        'min_length': 'La contraseña debe tener al menos 6 caracteres.',
        'required': 'La contraseña es obligatoria.'
    })
    rol = serializers.ChoiceField(
        choices=['atleta', 'entrenador', 'admin'],
        default='atleta',
        error_messages={
            'invalid_choice': 'El rol seleccionado no es válido en el sistema.'
        }
    )