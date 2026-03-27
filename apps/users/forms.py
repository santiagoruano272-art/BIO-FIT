# ============================================================
#  BIO-FIT — apps/routines/forms.py
#
#  Formulario principal de generación de rutinas.
#  Este es el "bandeja" que el usuario llena para que la IA
#  genere su rutina personalizada.
# ============================================================

from django import forms
from .prompts import (
    EXPERIENCE_LEVELS,
    TRAINING_GOALS,
    EQUIPMENT_OPTIONS,
    TRAINING_LOCATIONS,
)


class RoutineRequestForm(forms.Form):
    """
    Formulario de solicitud de rutina personalizada.
    Los campos de este formulario alimentan directamente
    el prompt que se envía a la IA.
    """

    # ── Objetivo principal ──────────────────────────────────
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
        help_text='Puedes seleccionar hasta 2 adicionales.',
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
            (20, '20 minutos (express)'),
            (30, '30 minutos'),
            (45, '45 minutos (recomendado)'),
            (60, '1 hora'),
            (90, '1.5 horas'),
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

        # Convertir strings de preferencias a listas
        preferred = cleaned.get('preferred_exercises', '')
        if preferred:
            cleaned['preferred_exercises'] = [p.strip() for p in preferred.split(',') if p.strip()]
        else:
            cleaned['preferred_exercises'] = []

        disliked = cleaned.get('disliked_exercises', '')
        if disliked:
            cleaned['disliked_exercises'] = [d.strip() for d in disliked.split(',') if d.strip()]
        else:
            cleaned['disliked_exercises'] = []

        # Convertir session_duration_min a int
        if cleaned.get('session_duration_min'):
            cleaned['session_duration_min'] = int(cleaned['session_duration_min'])

        return cleaned
