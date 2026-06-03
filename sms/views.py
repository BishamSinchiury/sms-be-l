from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def demo_no_csrf(request):
    if request.method == "GET":
        return JsonResponse({
        "message": "hello get request made sucessfully"
    })

    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except:
            data = {}

        return JsonResponse({
            "message": "POST received without CSRF",
            "data": data
        })

    return JsonResponse({
        "message": "Send a POST request to test no CSRF"
    })