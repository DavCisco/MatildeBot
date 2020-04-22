from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def webhook(request):

    print('webhook received\n')
    print(request)

    return HttpResponse('<p>home view of the bot<p>')

    
