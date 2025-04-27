# Place for OpenNebula Django signals 
from django.dispatch import Signal

tenant_created = Signal(providing_args=["tenant"]) 