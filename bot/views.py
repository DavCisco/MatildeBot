from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
from webexteamssdk import WebexTeamsAPI

@csrf_exempt
def webhook(request):

    botToken = 'MDdiYTJmMjQtYTI1My00NzdkLWFiYWEtOTFlMDhiYWViMTBlY2I2OTY4MWEtNTBi_PF84_1eb65fdf-9643-417f-9974-ad72cae0e10f'

    print('webhook received, details:')
    whookData = json.loads(request.body)
    print(whookData)
    fromUserId  = whookData['data']['personId']
    fromSpaceId = whookData['data']['roomId']
    messageId = whookData['data']['id']

    wxapi = WebexTeamsAPI(botToken)

    try:
        fromUser  = str(wxapi.people.get(fromUserId))
        fromSpace = wxapi.rooms.get(fromSpaceId)
        message   = wxapi.messages.get(messageId)        
    except:
        print('API read error')

    userDName   = json.loads(fromUser)['displayName']
    spaceName   = json.loads(fromSpace)['title']
    messageText = json.loads(message)['text']

    print('** user:\n' + userDName)
    print('** space:\n' + spaceName)
    print('** message:\n' + messageText)
    print('\n')




    return HttpResponse('<p>greetings from Matilde<p>')

    
