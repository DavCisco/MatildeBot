from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
import re
from webexteamssdk import WebexTeamsAPI, Webhook
import time

@csrf_exempt
def webhook(request):

    global bot_token
    
    bot_token = 'MDdiYTJmMjQtYTI1My00NzdkLWFiYWEtOTFlMDhiYWViMTBlY2I2OTY4MWEtNTBi_PF84_1eb65fdf-9643-417f-9974-ad72cae0e10f'

    wxapi = WebexTeamsAPI(bot_token)

    # Create a Webhook object from the JSON data
    whookData = json.loads(request.body)
    webhook_obj = Webhook(whookData)

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

            argument = ''
            reqText = message.text.strip().lower()
            if 'help' in reqText:
                response = 'help'
            elif 'list' in reqText:
                response = 'list_trials'
            elif 'status' in reqText:
                response = 'status'
            elif 'report' in reqText:
                trialId = re.search(r'\s[0-9]+', reqText)
                if trialId:
                    trialId = int(trialId.group().strip())
                    if trialId > 0:
                        response = 'report for trial '
                        argument = trialId
                    else:
                        response = 'report_incomplete'
                else:
                    response = 'report_incomplete'
            else:
                response = 'unknown'
        else:
            response = 'unauthorized'

        # executes
        action(person.emails[0], room.id, response, argument)

    return HttpResponse('<p>greetings from Matilde<p>')




    
def authorizedRequest(email, space):

    # if email == 'dgrandis@cisco.com':
    #     return True
    # else:
    #     return False
    
    return True


def action(person_email, space_id, action, argument):

    wxapi = WebexTeamsAPI(bot_token)

    action += str(argument)
    message = 'the request is ' + action

    if person_email == 'dgrandis@cisco.com':
        message = '<@personEmail:dgrandis@cisco.com|Master>, ' + message
    else:
        message = '<@personEmail:' + person_email + '>, ' + message

    wxapi.messages.create(space_id, markdown=message)




