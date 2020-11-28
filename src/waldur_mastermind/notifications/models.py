from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import JSONField
from django.db import models
from model_utils.fields import AutoCreatedField

from waldur_core.core.validators import validate_name
from waldur_core.logging.models import UuidMixin

User = get_user_model()


class Notification(UuidMixin):
    author = models.ForeignKey(to=User, on_delete=models.SET_NULL, null=True)
    created = AutoCreatedField()
    subject = models.CharField(max_length=1000, validators=[validate_name])
    body = models.TextField(validators=[validate_name])
    query = JSONField()
    emails = JSONField()
