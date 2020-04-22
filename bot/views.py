from django.shortcuts import render
from django.http import HttpResponse

def webhook(request):

    print('webhook received\n')
    print(request)

    return HttpResponse('<p>home view of the bot<p>')

    