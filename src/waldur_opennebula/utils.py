# Place for OpenNebula utility functions 
import uuid

def generate_unique_tenant_name(base_name):
    return f"{base_name}-{uuid.uuid4().hex[:8]}" 