import factory
from django.urls import reverse

from .. import models


class ChecklistFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Checklist

    name = factory.Sequence(lambda n: 'checklist-%s' % n)

    @classmethod
    def get_url(cls, checklist=None):
        if checklist is None:
            checklist = ChecklistFactory()
        return 'http://testserver' + reverse(
            'marketplace-checklist-detail', kwargs={'uuid': checklist.uuid.hex}
        )


class QuestionFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Question

    checklist = factory.SubFactory(ChecklistFactory)
