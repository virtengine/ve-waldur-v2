from django.db.models import F, Q
from django.utils.translation import ugettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from waldur_core.core.models import User
from waldur_core.structure.filters import filter_visible_users
from waldur_core.structure.models import Customer, Project
from waldur_core.structure.permissions import is_administrator, is_owner

from . import models, serializers


def get_score(num, den):
    return round(100 * num / max(1, den), 2)


class CategoriesView(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    queryset = models.Category.objects.all()
    serializer_class = serializers.CategorySerializer
    lookup_field = 'uuid'


class CategoryChecklistsView(ListModelMixin, GenericViewSet):
    serializer_class = serializers.ChecklistSerializer

    def get_queryset(self):
        return models.Checklist.objects.filter(
            category__uuid=self.kwargs['category_uuid']
        )


class ChecklistListView(ListModelMixin, GenericViewSet):
    queryset = models.Checklist.objects.all()
    serializer_class = serializers.ChecklistSerializer


class ChecklistDetailView(RetrieveModelMixin, GenericViewSet):
    queryset = models.Checklist.objects.all()
    serializer_class = serializers.ChecklistSerializer


class QuestionsView(ListModelMixin, GenericViewSet):
    serializer_class = serializers.QuestionSerializer

    def get_queryset(self):
        return models.Question.objects.filter(
            checklist__uuid=self.kwargs['checklist_uuid']
        )


class StatsView(APIView):
    def get(self, request, checklist_uuid, format=None):
        if not request.user.is_staff and not request.user.is_support:
            raise PermissionDenied()

        checklist = get_object_or_404(models.Checklist, uuid=checklist_uuid)
        total_questions = checklist.questions.count()
        points = []
        for customer in Customer.objects.all():
            customer_users = customer.get_users()
            correct_count = models.Answer.objects.filter(
                user__in=customer_users,
                question__checklist=checklist,
                value=F('question__correct_answer'),
            ).count()
            points.append(
                dict(
                    name=customer.name,
                    uuid=customer.uuid,
                    latitude=customer.latitude,
                    longitude=customer.longitude,
                    score=get_score(
                        correct_count, customer_users.count() * total_questions
                    ),
                )
            )
        return Response(points)


class ProjectStatsView(APIView):
    def get(self, request, project_uuid, format=None):
        try:
            project = Project.objects.get(uuid=project_uuid)
        except Project.DoesNotExist:
            raise ValidationError(_('Project does not exist.'))

        is_administrator(request, self, project)

        checklists = []
        for checklist in models.Checklist.objects.all():
            users = project.get_users()
            qs = models.Answer.objects.filter(
                user__in=users, question__checklist=checklist
            )
            total = checklist.questions.count() * users.count()
            positive_count = qs.filter(value=F('question__correct_answer')).count()
            negative_count = (
                qs.exclude(value__isnull=True)
                .exclude(value=F('question__correct_answer'))
                .count()
            )
            unknown_count = total - positive_count - negative_count
            checklists.append(
                dict(
                    name=checklist.name,
                    uuid=checklist.uuid,
                    positive_count=positive_count,
                    negative_count=negative_count,
                    unknown_count=unknown_count,
                    score=get_score(positive_count, total)
                    if total > 0
                    else 100,  # consider empty lists as fully compliant
                )
            )
        return Response(checklists)


class CustomerStatsView(APIView):
    def get(self, request, customer_uuid, checklist_uuid, format=None):
        customer = get_object_or_404(Customer, uuid=customer_uuid)
        is_owner(request, self, customer)

        checklist = get_object_or_404(models.Checklist, uuid=checklist_uuid)
        total_questions = checklist.questions.count()
        points = []
        for project in Project.objects.filter(customer=customer).order_by('name'):
            project_users = project.get_users()
            customer_users = customer.get_owners()
            users_count = project_users.count() + customer_users.count()
            correct_count = (
                models.Answer.objects.filter(
                    Q(user__in=project_users) | Q(user__in=customer_users)
                )
                .filter(
                    question__checklist=checklist, value=F('question__correct_answer'),
                )
                .count()
            )
            points.append(
                dict(
                    name=project.name,
                    uuid=project.uuid.hex,
                    score=get_score(correct_count, total_questions * users_count),
                )
            )
        return Response(points)


class CustomerChecklistUpdateView(APIView):
    def get(self, request, customer_uuid, format=None):
        customer = get_object_or_404(Customer, uuid=customer_uuid)
        is_owner(request, self, customer)

        ChecklistCustomers = models.Checklist.customers.through
        current_checklists = ChecklistCustomers.objects.filter(customer=customer)
        serializer = serializers.CustomerChecklistUpdateSerializer(
            [cc.checklist for cc in current_checklists], context={'request': request}
        )
        return Response(serializer.data)

    def post(self, request, customer_uuid, format=None):
        customer = get_object_or_404(Customer, uuid=customer_uuid)
        is_owner(request, self, customer)

        serializer = serializers.CustomerChecklistUpdateSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        target_ids = set([checklist.id for checklist in serializer.validated_data])

        ChecklistCustomers = models.Checklist.customers.through
        current_checklists = ChecklistCustomers.objects.filter(customer=customer)
        current_ids = set([checklist.id for checklist in current_checklists])

        stale_ids = current_ids - target_ids
        new_ids = target_ids - current_ids

        current_checklists.filter(id__in=stale_ids).delete()
        for checklist_id in new_ids:
            ChecklistCustomers.objects.create(
                customer=customer, checklist_id=checklist_id
            )

        return Response({'detail': _('Customer checklist have been updated.')})


class AnswersListView(ListModelMixin, GenericViewSet):
    serializer_class = serializers.AnswerListSerializer

    def get_queryset(self):
        return models.Answer.objects.filter(
            question__checklist__uuid=self.kwargs['checklist_uuid'],
            user=self.request.user,
        )


class UserAnswersListView(ListModelMixin, GenericViewSet):
    serializer_class = serializers.AnswerListSerializer

    def get_queryset(self):
        visible_users = filter_visible_users(User.objects.all(), self.request.user)
        user = get_object_or_404(visible_users, uuid=self.kwargs['user_uuid'])
        return models.Answer.objects.filter(
            question__checklist__uuid=self.kwargs['checklist_uuid'], user=user,
        )


class AnswersSubmitView(CreateModelMixin, GenericViewSet):
    serializer_class = serializers.AnswerSubmitSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        checklist = get_object_or_404(
            models.Checklist, uuid=self.kwargs['checklist_uuid']
        )

        for answer in serializer.validated_data:
            question = get_object_or_404(
                models.Question, uuid=answer['question_uuid'], checklist=checklist
            )
            models.Answer.objects.update_or_create(
                question=question,
                user=request.user,
                defaults={'value': answer['value']},
            )

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )
