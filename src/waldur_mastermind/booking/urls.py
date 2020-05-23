from django.conf.urls import url

from waldur_mastermind.booking import views


def register_in(router):
    router.register(
        r'booking-resources', views.ResourceViewSet, basename='booking-resource'
    )


urlpatterns = [
    url(
        r'^api/marketplace-bookings/(?P<uuid>[a-f0-9]+)/$',
        views.OfferingBookingsViewSet.as_view(),
    ),
]
