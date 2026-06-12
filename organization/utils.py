from django.http import Http404
from organization.models import Organization


def get_org_from_request(request):
    origin = request.headers.get('Origin', '')
    print("the", origin)
    
    if origin:
        # Strip scheme → "org1.yourapp.com"
        hostname = origin.replace('https://', '').replace('http://', '').split(':')[0]
    else:
        # Fallback for Postman/tests/same-origin requests
        hostname = request.get_host().split(':')[0]
    if hostname == "127.0.0.1":
        hostname = "localhost"
    try:
        return Organization.objects.get(domain_name=hostname)
    except Organization.DoesNotExist:
        raise Http404("No organization found for this domain.")   

