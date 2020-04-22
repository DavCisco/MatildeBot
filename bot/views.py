from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def webhook(request):

    print('webhook received, details:')
    requestdata = json.loads(request.body)
    print(requestdata)
    print(requestdata['name'])
    print('\n')

    return HttpResponse('<p>home view of the bot<p>')

    
