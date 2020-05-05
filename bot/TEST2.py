import json
import re
from webexteamssdk import WebexTeamsAPI, Webhook

botToken  = 'MDdiYTJmMjQtYTI1My00NzdkLWFiYWEtOTFlMDhiYWViMTBlY2I2OTY4MWEtNTBi_PF84_1eb65fdf-9643-417f-9974-ad72cae0e10f'
TeamScope = 'Y2lzY29zcGFyazovL3VzL1RFQU0vZDkxNGIwYjAtNmRlZC0xMWVhLThhN2QtNWY5NzY0NDM5Y2U0'

source_space = "Y2lzY29zcGFyazovL3VzL1JPT00vMzdlZjBiMjAtNjlhMy0xMWVhLTkwNjEtOWJlMzc1YjViNjFj"

api = WebexTeamsAPI(botToken)
spaces = api.rooms.list(teamId=TeamScope)
list = []
for space in spaces:
    list.append(space.id)

if source_space in list:
    print('yes')

