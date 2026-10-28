import uuid
from datetime import datetime

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Length, Lower, Trim
from django.db.models.lookups import GreaterThan, LessThanOrEqual
from django.utils import timezone


def nonempty(field):
    return GreaterThan(Length(Trim(field)), 0)


class Organizer(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        db_table = "organizers"


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organizer = models.ForeignKey(
        Organizer, on_delete=models.PROTECT, related_name="events"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=1000)
    date = models.DateField()
    time = models.TimeField()
    location = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "events"
        indexes = [models.Index(fields=["date", "time"], name="events_date_time_idx")]
        constraints = [
            models.CheckConstraint(
                condition=nonempty("name") & LessThanOrEqual(Length("name"), 100),
                name="event_name_required_max100",
            ),
            models.CheckConstraint(
                condition=nonempty("description")
                & LessThanOrEqual(Length("description"), 1000),
                name="event_description_required_max1000",
            ),
            models.CheckConstraint(
                condition=nonempty("location"), name="event_location_required"
            ),
        ]

    @property
    def starts_at(self):
        return timezone.make_aware(
            datetime.combine(self.date, self.time), timezone.get_current_timezone()
        )

    def clean(self):
        super().clean()
        if self.date and self.time and self.starts_at <= timezone.now():
            raise ValidationError({"date": "The event date and time must be in the future."})

    def save(self, *args, **kwargs):
        for field in ("name", "description", "location"):
            value = getattr(self, field)
            if isinstance(value, str):
                setattr(self, field, value.strip())
        self.full_clean()
        return super().save(*args, **kwargs)


class Registration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="registrations"
    )
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=254)
    normalized_email = models.GeneratedField(
        expression=Lower(Trim("email")),
        output_field=models.CharField(max_length=254),
        db_persist=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "registrations"
        constraints = [
            models.CheckConstraint(
                condition=nonempty("name") & LessThanOrEqual(Length("name"), 100),
                name="registration_name_required_max100",
            ),
            models.CheckConstraint(
                condition=nonempty("email")
                & LessThanOrEqual(Length("email"), 254),
                name="registration_email_required_max254",
            ),
            models.UniqueConstraint(
                fields=["event", "normalized_email"],
                name="unique_registration_event_email",
            ),
        ]

    def save(self, *args, **kwargs):
        if isinstance(self.name, str):
            self.name = self.name.strip()
        if isinstance(self.email, str):
            self.email = self.email.strip()
        self.full_clean()
        result = super().save(*args, **kwargs)
        self.refresh_from_db(fields=["normalized_email"])
        return result