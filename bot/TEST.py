import json
import re


a = '''
    { "id": "Y2lzY29zcGFyazovL3VzL1BFT1BMRS9hZjA3NzZiZS1jOGRiLTRjZWYtOWJhOS0xOGNiOTc1NDQ0YzQ",
    "emails": [
        "dgrandis@cisco.com"
    ],
    "phoneNumbers": [
        {
            "type": "mobile",
            "value": "+39 335 74 54 069"
        },
        {
            "type": "work",
            "value": "+39 039 629 5432"
        }
    ],
    "displayName": "Davide Grandis",
    "nickName": "Davide",
    "firstName": "Davide",
    "lastName": "Grandis",
    "avatar": "https://1efa7a94ed216783e352-c62266528714497a17239ececf39e9e2.ssl.cf1.rackcdn.com/V1~f40715dea579a4497621cf346eac9008~R_Kgg-gsTyO3t8O34ItdUw==~1600",
    "orgId": "Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi8xZWI2NWZkZi05NjQzLTQxN2YtOTk3NC1hZDcyY2FlMGUxMGY",
    "created": "2012-06-15T20:24:09.641Z",
    "lastActivity": "2020-04-22T13:42:03.417Z",
    "status": "DoNotDisturb",
    "type": "person"
    }
    '''
    
b = json.loads(a)

dn = b['emails'][0]
print(dn)

a = 'matilde helpp c  asuse'

trialId = re.search(r'\s[0-9]+', a)

if trialId:
    print('yes')

