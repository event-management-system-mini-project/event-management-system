"""Validated organizer credentials and event-creation input."""

from datetime import datetime

from django import forms
from django.utils import timezone


class LoginForm(forms.Form):
    username = forms.CharField(max_length=150, strip=True)
    password = forms.CharField(max_length=4096, strip=False)


class EventForm(forms.Form):
    """The create/edit payload shared by the organizer mutations.

    Length and required-field rules mirror the canonical Event model. The date
    and time are interpreted in the configured timezone (Asia/Kolkata).
    """

    name = forms.CharField(max_length=100, strip=True)
    description = forms.CharField(max_length=1000, strip=True)
    date = forms.DateField(
        input_formats=["%Y-%m-%d"],
        error_messages={"invalid": "Use the YYYY-MM-DD format."},
    )
    time = forms.TimeField(
        input_formats=["%H:%M:%S", "%H:%M", "%H:%M:%S.%f"],
        error_messages={"invalid": "Use the HH:MM or HH:MM:SS format."},
    )
    location = forms.CharField(strip=True)

    def clean(self):
        cleaned = super().clean()
        date = cleaned.get("date")
        time = cleaned.get("time")
        if date and time:
            starts_at = timezone.make_aware(
                datetime.combine(date, time), timezone.get_current_timezone()
            )
            if starts_at <= timezone.now():
                self.add_error(
                    "date", "The event date and time must be in the future."
                )
        return cleaned
