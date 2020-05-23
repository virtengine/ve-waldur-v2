from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions as rf_permissions
from rest_framework import viewsets

from . import filters, models, serializers


class ResourceSlaStateTransitionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Service SLAs are connected with occurrences of events.
    To get a list of such events issue a **GET** request to */api/resource-sla-state-transition/*.

    The output contains a list of states and timestamps when the state was reached.
    The list is sorted in descending order by the timestamp.
    """

    queryset = models.ResourceSlaStateTransition.objects.all().order_by('-timestamp')
    serializer_class = serializers.ResourceSlaStateTransitionSerializer
    permission_classes = (rf_permissions.IsAuthenticated,)
    filter_backends = (filters.ResourceScopeFilterBackend, DjangoFilterBackend)
    filterset_class = filters.ResourceStateFilter
