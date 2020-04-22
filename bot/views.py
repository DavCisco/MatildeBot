from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
from webexteamssdk import WebexTeamsAPI, Webhook

@csrf_exempt
def webhook(request):

    botToken = 'MDdiYTJmMjQtYTI1My00NzdkLWFiYWEtOTFlMDhiYWViMTBlY2I2OTY4MWEtNTBi_PF84_1eb65fdf-9643-417f-9974-ad72cae0e10f'

    print('Webhook received')

    # Create a Webhook object from the JSON data
    whookData = json.loads(request.body)
    webhook_obj = Webhook(whookData)

    # # print(whookData)
    # fromUserId  = whookData['data']['personId']
    # fromSpaceId = whookData['data']['roomId']
    # messageId = whookData['data']['id']
    wxapi = WebexTeamsAPI(botToken)

    try:
        # Get the room details
        room = wxapi.rooms.get(webhook_obj.data.roomId)
        # Get the message details
        message = wxapi.messages.get(webhook_obj.data.id)
        # Get the sender's details
        person = wxapi.people.get(message.personId)
    except:
        print('API read error')

    print("NEW MESSAGE IN ROOM '{}'".format(room.title))
    print("FROM '{}'".format(person.displayName))
    print("MESSAGE '{}'\n".format(message.text))






    return HttpResponse('<p>greetings from Matilde<p>')

    
