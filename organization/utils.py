from django.http import Http404
from organization.models import Organization


def get_org_from_request(request):
    host = request.get_host()          
    hostname = host.split(':')[0]       

    try:
        return Organization.objects.get(domain_name=hostname)
    except Organization.DoesNotExist:
        raise Http404("No organization found for this domain.")

