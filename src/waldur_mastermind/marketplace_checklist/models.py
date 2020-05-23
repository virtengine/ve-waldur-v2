from django.db import models
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel

from waldur_core.core import models as core_models
from waldur_core.structure.models import Project, StructureModel
from waldur_mastermind.marketplace import models as marketplace_models


class Category(
    core_models.UuidMixin, core_models.NameMixin, core_models.DescribableMixin,
):
    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)


class Checklist(
    core_models.UuidMixin,
    core_models.NameMixin,
    core_models.DescribableMixin,
    TimeStampedModel,
):
    category = models.ForeignKey(
        to=Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='checklists',
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)


class Question(core_models.UuidMixin, core_models.DescribableMixin):
    checklist = models.ForeignKey(
        to=Checklist, on_delete=models.CASCADE, related_name='questions',
    )
    order = models.PositiveIntegerField(default=0)
    category = models.ForeignKey(
        to=marketplace_models.Category, on_delete=models.CASCADE, null=True, blank=True,
    )
    correct_answer = models.BooleanField(default=True)
    solution = models.TextField(
        blank=True,
        null=True,
        help_text=_('It is shown when incorrect or N/A answer is chosen'),
    )

    class Meta:
        ordering = (
            'checklist',
            'order',
        )

    def __str__(self):
        return self.description


class Answer(StructureModel, TimeStampedModel):
    user = models.ForeignKey(
        to=core_models.User, on_delete=models.SET_NULL, null=True, blank=True
    )
    question = models.ForeignKey(to=Question, on_delete=models.CASCADE)
    project = models.ForeignKey(to=Project, on_delete=models.CASCADE)
    value = models.NullBooleanField()

    class Permissions:
        project_path = 'project'
        customer_path = 'project__customer'
