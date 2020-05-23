from django.conf.urls import url

from . import views


def register_in(router):
    router.register(r'rancher', views.ServiceViewSet, basename='rancher')
    router.register(
        r'rancher-spl', views.ServiceProjectLinkViewSet, basename='rancher-spl'
    )
    router.register(
        r'rancher-clusters', views.ClusterViewSet, basename='rancher-cluster'
    )
    router.register(r'rancher-nodes', views.NodeViewSet, basename='rancher-node')
    router.register(
        r'rancher-catalogs', views.CatalogViewSet, basename='rancher-catalog'
    )
    router.register(
        r'rancher-projects', views.ProjectViewSet, basename='rancher-project'
    )
    router.register(
        r'rancher-namespaces', views.NamespaceViewSet, basename='rancher-namespace'
    )
    router.register(
        r'rancher-templates', views.TemplateViewSet, basename='rancher-template'
    )


urlpatterns = [
    url(
        r'^api/rancher-template-versions/(?P<template_uuid>[a-f0-9]+)/(?P<version>[0-9.]+)/$',
        views.TemplateVersionView.as_view(),
    ),
    url(r'^api/rancher-apps/$', views.ApplicationViewSet.as_view()),
]
