from __future__ import unicode_literals

from nodeconductor.core import NodeConductorExtension


class PackagesExtension(NodeConductorExtension):

    @staticmethod
    def django_app():
        return 'nodeconductor_assembly_waldur.packages'

    @staticmethod
    def rest_urls():
        from .urls import register_in
        return register_in
