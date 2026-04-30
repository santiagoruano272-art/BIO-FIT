# ============================================================
#  BIO-FIT — apps/routines/forms.py
# ============================================================

from django import forms
from biofit.apps.rutinas.prompts import (
    EXPERIENCE_LEVELS,
    TRAINING_GOALS,
    EQUIPMENT_OPTIONS,
    TRAINING_LOCATIONS,
)


class RoutineRequestForm(forms.Form):

    # ── Objetivo principal ──────────a────────────────────────
    main_goal = forms.ChoiceField(
        label='¿Cuál es tu objetivo principal?',
        choices=[(k, v) for k, v in TRAINING_GOALS.items()],
        widget=forms.RadioSelect(attrs={'class': 'goal-radio'}),
        help_text='Selecciona el que más se ajuste a lo que quieres lograr.',
    )

    secondary_goals = forms.MultipleChoiceField(
        label='Objetivos secundarios (opcional)',
        choices=[(k, v) for k, v in TRAINING_GOALS.items()],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'goal-checkbox'}),
        required=False,
        help_text='Puedes seleccionar hasta 2 adicionales (distintos al principal).',
    )

    # ── Nivel de experiencia ────────────────────────────────
    experience_level = forms.ChoiceField(
        label='Nivel de experiencia',
        choices=[(k, v) for k, v in EXPERIENCE_LEVELS.items()],
        widget=forms.RadioSelect(attrs={'class': 'level-radio'}),
    )

    # ── Disponibilidad ──────────────────────────────────────
    days_per_week = forms.IntegerField(
        label='Días disponibles por semana',
        min_value=1,
        max_value=7,
        initial=3,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'type': 'range',
            'min': '1',
            'max': '7',
            'step': '1',
        }),
        help_text='¿Cuántos días a la semana puedes entrenar?',
    )

    session_duration_min = forms.ChoiceField(
        label='Duración por sesión',
        choices=[
            (20,  '20 minutos (express)'),
            (30,  '30 minutos'),
            (45,  '45 minutos (recomendado)'),
            (60,  '1 hora'),
            (90,  '1.5 horas'),
        ],
        initial=45,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    # ── Lugar y equipamiento ────────────────────────────────
    training_location = forms.ChoiceField(
        label='¿Dónde vas a entrenar?',
        choices=[(k, v) for k, v in TRAINING_LOCATIONS.items()],
        widget=forms.RadioSelect(attrs={'class': 'location-radio'}),
    )

    equipment = forms.MultipleChoiceField(
        label='Equipamiento disponible',
        choices=[(e, e) for e in EQUIPMENT_OPTIONS],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'equipment-checkbox'}),
        required=False,
        help_text='Selecciona todo el equipamiento al que tienes acceso.',
    )

    # ── Condiciones de salud ────────────────────────────────
    medical_conditions = forms.CharField(
        label='Condiciones médicas relevantes',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Ej: hipertensión, diabetes, asma... (déjalo en blanco si no aplica)',
        }),
    )

    injuries = forms.CharField(
        label='Lesiones actuales o pasadas',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Ej: dolor de rodilla derecha, lesión en manguito rotador...',
        }),
    )

    # ── Preferencias ───────────────────────────────────────
    preferred_exercises = forms.CharField(
        label='Ejercicios que te gustan (opcional)',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: sentadillas, natación, running...',
        }),
    )

    disliked_exercises = forms.CharField(
        label='Ejercicios que prefieres evitar (opcional)',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: burpees, jumping jacks...',
        }),
    )

    # ── Validaciones ───────────────────────────────────────
    def clean_secondary_goals(self):
        goals = self.cleaned_data.get('secondary_goals', [])
        if len(goals) > 2:
            raise forms.ValidationError('Selecciona máximo 2 objetivos secundarios.')
        return goals

    def clean(self):
        cleaned = super().clean()

        main_goal = cleaned.get('main_goal')
        secondary_goals = cleaned.get('secondary_goals', [])

        if main_goal and main_goal in secondary_goals:
            self.add_error(
                'secondary_goals',
                'El objetivo secundario no puede ser igual al principal.'
            )

        # Convertir preferencias de texto a listas
        for field in ('preferred_exercises', 'disliked_exercises'):
            value = cleaned.get(field, '')
            cleaned[field] = (
                [item.strip() for item in value.split(',') if item.strip()]
                if value else []
            )

        # Convertir duración a int
        if cleaned.get('session_duration_min'):
            cleaned['session_duration_min'] = int(cleaned['session_duration_min'])

        return cleaned

    def to_prompt_data(self, user_profile: dict) -> dict:
        """
        ✅ NUEVO: Combina los datos del form con el perfil del usuario
        para construir el dict completo que recibe build_routine_user_prompt().

        Args:
            user_profile: dict del perfil guardado en Firestore (edad, peso, etc.)

        Returns:
            dict listo para pasar a build_routine_user_prompt()
        """
        form_data = self.cleaned_data.copy()

        return {
            **form_data,
            # Datos físicos que vienen del perfil, no del form
            'age':        user_profile.get('age'),
            'gender':     user_profile.get('gender'),
            'weight_kg':  user_profile.get('weight_kg'),
            'height_cm':  user_profile.get('height_cm'),
        }   