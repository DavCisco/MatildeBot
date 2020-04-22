from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
import re
from webexteamssdk import WebexTeamsAPI, Webhook

@csrf_exempt
def webhook(request):

    botToken = 'MDdiYTJmMjQtYTI1My00NzdkLWFiYWEtOTFlMDhiYWViMTBlY2I2OTY4MWEtNTBi_PF84_1eb65fdf-9643-417f-9974-ad72cae0e10f'

    # Create a Webhook object from the JSON data
    whookData = json.loads(request.body)
    webhook_obj = Webhook(whookData)

    wxapi = WebexTeamsAPI(botToken)
    # Get the room details
    room = wxapi.rooms.get(webhook_obj.data.roomId)
    # Get the message details
    message = wxapi.messages.get(webhook_obj.data.id)
    # Get the sender's details
    person = wxapi.people.get(message.personId)

    # print("NEW MESSAGE IN ROOM '{}'".format(room.title))
    # print("FROM '{}'".format(person.displayName))
    # print("MESSAGE '{}'\n".format(message.text))

    # filters out messages sent directly by Matilde
    if person.displayName != 'Matilde':

        # checks if the sender and/or the space are authorized
        if authorizedRequest (person.emails[0], room.id):

            reqText = message.text.strip().lower()
            if 'help' in reqText:
                response = 'help'
            if 'list' in reqText:
                response = 'list_trials'
            if 'status' in reqText:
                response = 'status'
            if 'report' in reqText:
                trialId = re.search(r'\s[0-9]+', reqText)
                response = 'report for trial ' + str(trialId.group())
        else:
            response = 'unauthorized'

        print('The request is ' + response)

    return HttpResponse('<p>greetings from Matilde<p>')




    
def authorizedRequest(email, space):

    if email == 'dgrandis@cisco.com':
        return True
    else:
        return False
