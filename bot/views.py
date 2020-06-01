from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

import logging
import time
import datetime
import socket
import os
import sys
import configparser
import json
import re
from webexteamssdk import WebexTeamsAPI, Webhook
import xlsxwriter
import pymysql.cursors

@csrf_exempt
def webhook(request):

    def SetupLogging():
        # Configure the logger to write to the matilde.log file and to the console

        global logger

        logging.Formatter.converter = time.gmtime
        hostName = socket.gethostname()
        logger = logging.getLogger(hostName)
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)-8s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(formatter)
        logger.addHandler(console)

        # the log file is located in the same folder as this script
        # -> adds the absolute path of the current module to the log file
        file = os.path.join(os.path.dirname(__file__), 'matilde-bot.log')
        logfile = logging.FileHandler(file)
        logfile.setLevel(logging.DEBUG)
        logfile.setFormatter(formatter)
        logger.addHandler(logfile)

    def ReadSettings(file):
        # reads the settings INI file and assign the values to global variables
        # returns TRUE if OK

        def ResetConfigFile(filename, newfile):
            # Writes or resets the configuration file. Returns nothing

            # note: allow_no_value is required to add comments
            config = configparser.ConfigParser(allow_no_value=True)
            config.optionxform = str
            try:
                config.add_section('WXT')
                config.set('WXT', 'botToken', '<input here>')
                config.set('WXT', 'logSpace', '<input here>')
                config.set('WXT', 'notification', 'No')
                config.set('WXT', 'TeamScope', '<input here>')
                config.add_section('DB')
                config.set('DB', 'host',     '<input here>')
                config.set('DB', 'port',     '<input here>')
                config.set('DB', 'user',     '<input here>')
                config.set('DB', 'password', '<input here>')
                config.set('DB', 'dbname',   '<input here>')

                with open(filename, 'w') as configfile:
                    config.write(configfile)
                if newfile:
                    logger.warning('Config file created in the current folder.')
                else:
                    logger.warning(
                        'Configuration file reset in the current folder.')
                logger.warning(
                    'Please set the required configuration parameters and re-run.')
            except Exception as e:
                logger.error('Error creating the configuration file: ' + e)

        global botToken, logSpace, NOTIF_ON, TeamScope
        global DBhost, DBport, DBuser, DBpass, DBname


        config = configparser.ConfigParser(allow_no_value=True)

        # the .ini file is located in the same folder as this script
        # -> adds the absolute path of the current module to the .ini filename
        file = os.path.join(os.path.dirname(__file__), file)

        if os.path.isfile(file):
            try:
                config.read(file)
                botToken  = str(config['WXT']['botToken']).strip()
                logSpace  = str(config['WXT']['logSpace']).strip()
                NOTIF_ON  = config.getboolean('WXT', 'notification')
                TeamScope = str(config['WXT']['TeamScope']).strip()
                DBhost = str(config['DB']['host']).strip()
                DBport = str(config['DB']['port']).strip()
                DBuser = str(config['DB']['user']).strip()
                DBpass = str(config['DB']['password']).strip()
                DBname = str(config['DB']['dbname']).strip()

                # Validation of settings
                if len(botToken) < 90:
                    raise ValueError('Setting not valid ' + botToken)
                if NOTIF_ON and len(logSpace) < 30:
                    raise ValueError('Setting not valid ' + logSpace)

            except Exception as e:
                logger.critical('Error reading the .ini file ' + str(e))
                ResetConfigFile(file, newfile=False)
                return False
        else:
            # Creates config file because it does not exist
            logger.critical('The .ini file does not exist')
            ResetConfigFile(file, newfile=True)
            return False
        return True

    SetupLogging()
    logger.info("Matilde's webhook received...")
    if not ReadSettings(file='config.ini'):
        logger.critical('Terminating')
        sys.exit()

    api = WebexTeamsAPI(botToken)

    # Create a Webhook object from the JSON data
    whookData = json.loads(request.body)
    webhook_obj = Webhook(whookData)

    # Get the space details
    room = api.rooms.get(webhook_obj.data.roomId)
    # Get the message details
    message = api.messages.get(webhook_obj.data.id)
    # Get the sender details
    person = api.people.get(message.personId)

    # print("NEW MESSAGE IN ROOM '{}'".format(room.title))
    # print("FROM '{}'".format(person.displayName))
    # print("MESSAGE '{}'\n".format(message.text))

    # filters out messages sent by Matilde herself
    if person.displayName != 'Matilde':

        # checks if the sender and/or the space are authorized
        if authorizedRequest(person.emails[0], room.id):
            logger.info('Request from authz user/space {}/{}'.format(person.emails[0], room.id))

            # checks if the BOT service is enabled in the Matilde's DB
            argument = ''
            if not BOT_enabled():
                response = 'maintenance'
            else:
                reqText = message.text.strip().lower()
                if reqText.lower() == 'matilde' or 'help' in reqText:
                    response = 'help'
                elif 'status' in reqText:
                    response = 'status'
                elif 'report' in reqText:
                    trialId = re.search(r'\s[0-9]+', reqText)
                    if trialId:
                        trialId = int(trialId.group().strip())
                        if trialId > 0:
                            response = 'trial_report'
                            argument = trialId
                        else:
                            response = 'report_incomplete'
                    else:
                        response = 'report_incomplete'
                elif 'echo' in reqText:
                    response = 'echo'
                    argument = reqText
                else:
                    response = 'unknown'
        else:
            response = 'unauthorized'
            argument = ''
        # executes
        action(person.emails[0], room.id, response, argument)

    return HttpResponse('<p>greetings from Matilde<p>')



def authorizedRequest(email, space):

    # for the spaces, the bot must be a member of the Team Space
    api = WebexTeamsAPI(botToken)

    authz_users = ['dgrandis@cisco.com']
    if email in authz_users:
        return True
    else:
        spaces = api.rooms.list(teamId=TeamScope)
        authz_spaces = []
        for record in spaces:
            authz_spaces.append(record.id)
        if space in authz_spaces:
            return True
        else:
            return False

def BOT_enabled():

    global connection

    try:
        connection = pymysql.connect(host=DBhost, port=int(DBport), user=DBuser, password=DBpass, db=DBname)
    except Exception as e:
        logger.critical('BOT_enabled: error opening the DB. ' + str(e) + '. Check settings in the .ini file')
        logger.critical('Terminating')
        sys.exit()
    logger.debug('BOT_enabled: connected to the DB')

    # retrieves the channel from the space
    cursor = connection.cursor()
    sql = "SELECT active FROM control WHERE process = 'bot'"
    cursor.execute(sql)
    field = cursor.fetchone()
    if field[0] == 'yes':
        logger.info('BOT process active in the DB, continues')
        return True
    else:
        logger.warning('BOT process inactive in the DB, stopping')
        return False

def action(person_email, space_id, action, argument):
    '''
    # List of actions:

    # - 'help'               -> done
    # - 'status'             -> done
    # - 'trial_report' with argument = trial_id

    # Others:
    # - 'echo' with argument = request
    # - 'report_incomplete'
    # - 'unknown'
    # - 'unauthorized'
    # - 'maintenance'
    '''

    # if person_email == 'dgrandis@cisco.com':
    #     message = '<@personEmail:dgrandis@cisco.com|Master>, {}'.format(message)
    # else:
    #     message = '<@personEmail:' + person_email + '>, {}'.format(message)

    api = WebexTeamsAPI(botToken)

    if argument == '':
        log_msg = 'Request: {} from user {} and space {}'.format(action, person_email, space_id)
    else:
        log_msg = 'Request: {}/{} from user {} and space {}'.format(action, argument, person_email, space_id)
    logger.info(log_msg)

    if action == 'help':
        response = 'these are the commands:\n'
        response += '```\n'
        response += 'status:      summary of all trials\n'
        response += 'report <id>: report of trial #id\n'
        response += 'help:        this output\n'
        response += '```'
        mention = '<@personEmail:{}>'.format(person_email)
        message = '{}, {}'.format(mention, response)
        api.messages.create(space_id, markdown=message)

    elif action == 'echo':
        response  = 'request:\n'
        response += argument
        mention = '<@personEmail:{}>'.format(person_email)
        message = '{}, {}'.format(mention, response)
        api.messages.create(space_id, markdown=message)

    elif action == 'status':
        message = 'checking...'
        api.messages.create(space_id, markdown=message)
        ChannelReport(space_id, person_email)

    elif action == 'trial_report':
        message = 'checking...'
        api.messages.create(space_id, markdown=message)
        OrgReport(space_id, person_email, argument)

    elif action == 'report_incomplete':
        message = 'please specify the trial id for the report'
        api.messages.create(space_id, markdown=message)

    elif action == 'unauthorized':
        message = '*unauthorized access*'
        api.messages.create(space_id, markdown=message)

    elif action == 'maintenance':
        message = "Sorry, I'm temporarily unavailable. Please try again later"
        api.messages.create(space_id, markdown=message)

    elif action == 'unknown':
        message = "Don't understand your request. Please check ```help```"
        api.messages.create(space_id, markdown=message)

    else:
        return

def ChannelReport(space_id, person_email):

    def BuildChannelReport(id):

        reportDate = datetime.datetime.now().strftime("%b %d, %Y %H:%M")

        # First check if there is any companies for the report otherwise returns
        cursor = connection.cursor()
        sql = "SELECT id FROM companies WHERE channelId = '%s'" % id
        cursor.execute(sql)
        test = cursor.fetchone()
        if not test:
            return ''

        # Reads the channel details for the header of the report
        sql = "SELECT project, partner, countryId, segment, salesLead FROM channels WHERE id = '%s'" % id
        cursor.execute(sql)
        channelRecord = cursor.fetchone()
        ch_name = channelRecord[0]
        ch_partner = channelRecord[1]
        if str(ch_partner) == 'None' or str(ch_partner) == '':
            ch_partner = channelRecord[4] + '@cisco.com'
        ch_countryId = channelRecord[2]
        ch_segment = channelRecord[3]

        if ch_partner == None or ch_partner == '':
            ch_partner = 'None'
        cursor = connection.cursor()
        sql = "SELECT country_name FROM countries WHERE id = '%s'" % ch_countryId
        cursor.execute(sql)
        countryRecord = cursor.fetchone()
        ch_country = countryRecord[0]

        # creates the Excel report
        if not os.path.exists('reports'):
            os.makedirs('reports')
        filename = 'reports/' + datetime.datetime.now().strftime("%Y-%m-%d") + \
            '_Report_Channel_' + str(id) + '.xlsx'
        workbook = xlsxwriter.Workbook(filename)
        worksheet = workbook.add_worksheet('Report')

        # Format of the excel file
        worksheet.hide_gridlines(2)
        worksheet.set_zoom(120)
        bigrow = workbook.add_format(
            {'font_size': 13, 'font_name': 'Arial'})

        worksheet.set_column('A:A', 12)
        worksheet.set_column('B:B', 10)
        worksheet.set_column('C:C', 50)
        worksheet.set_column('D:D', 35)
        worksheet.set_column('E:E', 35)
        worksheet.set_column('F:F', 20)
        worksheet.set_column('G:G', 60)

        worksheet.set_row(0, 20, bigrow)
        worksheet.set_row(2, 20, bigrow)
        worksheet.set_row(3, 20, bigrow)
        worksheet.set_row(4, 20, bigrow)
        worksheet.set_row(5, 20, bigrow)
        worksheet.autofilter('A8:G999999')
        worksheet.freeze_panes('A9')
        h1 = workbook.add_format({'align': 'vcenter', 'font_size': 18,
                                    'bold': True, 'font_color': 'purple', 'font_name': 'Arial'})
        ar = workbook.add_format(
            {'align': 'right', 'font_name': 'Arial', 'font_size': 13})
        ar_bold = workbook.add_format(
            {'align': 'right', 'bold': True, 'font_name': 'Arial', 'font_size': 13})
        hl_bd2 = workbook.add_format(
            {'bg_color': 'yellow', 'bold': True, 'border': 2, 'font_name': 'Arial'})
        hl_bd2_c = workbook.add_format(
            {'bg_color': 'yellow', 'bold': True, 'border': 2, 'font_name': 'Arial', 'align': 'center'})
        black_bd = workbook.add_format(
            {'font_color': 'black', 'border': 1, 'font_name': 'Arial', 'align': 'left'})
        black_bd_c = workbook.add_format(
            {'font_color': 'black', 'border': 1, 'font_name': 'Arial', 'align': 'center'})
        orange_bd = workbook.add_format(
            {'font_color': 'orange', 'border': 1, 'font_name': 'Arial', 'align': 'left'})
        orange_bd_c = workbook.add_format(
            {'font_color': 'orange', 'border': 1, 'font_name': 'Arial', 'align': 'center'})
        red_bd = workbook.add_format(
            {'font_color': 'red', 'border': 1, 'font_name': 'Arial', 'align': 'left'})
        red_bd_c = workbook.add_format(
            {'font_color': 'red', 'border': 1, 'font_name': 'Arial', 'align': 'center'})

        # title
        # worksheet.insert_image('A1', 'logo.jpg', {'x_scale': 0.1, 'y_scale': 0.1})
        worksheet.write('A1', 'Matilde Project Report', h1)
        worksheet.write('G1', reportDate, ar)

        # summary
        worksheet.write('B3', 'Project:', ar_bold)
        worksheet.write('B4', 'Owner:', ar_bold)
        worksheet.write('B5', 'Summary:', ar_bold)
        worksheet.write('D3', 'Segment:', ar_bold)
        worksheet.write('D4', 'Country:', ar_bold)
        worksheet.write('C3', ch_name, )
        worksheet.write('C4', ch_partner)
        worksheet.write('E3', ch_segment)
        worksheet.write('E4', ch_country)

        # details - header
        worksheet.write('A8', 'Date',        hl_bd2_c)
        worksheet.write('B8', 'Id',          hl_bd2_c)
        worksheet.write('C8', 'Name',        hl_bd2)
        worksheet.write('D8', 'Site',        hl_bd2)
        worksheet.write('E8', 'Admin email', hl_bd2)
        worksheet.write('F8', 'Status',      hl_bd2)
        worksheet.write('G8', 'Notes',       hl_bd2)

        # body: initial row value and counters
        row = 8
        totCompanies = 0
        totCompProvisioned = 0
        totAccounts = 0
        totAccProvisioned = 0

        # reads all the companies for the channel

        sql = "SELECT id, name, wxSiteUrl, provisioningStatus, provisioningError, creationDate, provisioningDate"
        sql += " FROM companies WHERE channelId = '%s'" % id
        sql += " ORDER BY provisioningDate, id"
        cursor.execute(sql)
        companiesRecords = cursor.fetchall()

        for company in companiesRecords:

            # read values and update counters
            cp_id = company[0]
            cp_name = company[1]
            cp_site = company[2]
            cp_ProvStatus = company[3]
            if cp_ProvStatus == 'provisioned':
                cp_date = company[6]
                totCompProvisioned += 1
            else:
                cp_date = company[5]
            cp_date = str(cp_date)[0:10]
            totCompanies += 1

            # retrieves the email of the provAdmin of the trial (if it's provisioned)
            if cp_ProvStatus == 'provisioned':
                sql = "SELECT accounts.email"
                sql += " FROM accounts INNER JOIN companiesAndAccounts ON accounts.id = companiesAndAccounts.accountId"
                sql += " WHERE companiesAndAccounts.companyId = '%s'" % cp_id
                sql += " AND accounts.role='provAdmin'"
                cursor.execute(sql)
                admins = cursor.fetchone()
                if len(admins) == 0:
                    cp_admin = 'Error: no admin found'
                else:
                    cp_admin = admins[0]
            else:
                cp_admin = 'n.a.'

            # reads all the accounts for the company
            cp_totAccounts = 0
            cp_totAccProvisioned = 0

            sql = "SELECT provisioningStatus"
            sql += " FROM accounts INNER JOIN companiesAndAccounts ON accounts.id = companiesAndAccounts.accountId"
            sql += " WHERE companiesAndAccounts.companyId = '%s'" % cp_id
            sql += " AND accounts.role <> 'billing'"
            cursor.execute(sql)
            accountsRecords = cursor.fetchall()

            for account in accountsRecords:

                cp_totAccounts += 1
                totAccounts += 1
                if account[0] == 'provisioned':
                    cp_totAccProvisioned += 1
                    totAccProvisioned += 1

            # calculates the company's provisioning status and sets the row format
            if cp_ProvStatus == 'provisioned':

                if cp_totAccProvisioned == cp_totAccounts:
                    cp_status = 'Fully provisioned'
                    rowFormat = black_bd
                    rowFormat_c = black_bd_c

                else:
                    cp_status = 'Partially provisioned'
                    rowFormat = orange_bd
                    rowFormat_c = orange_bd_c
            else:
                cp_status = 'Not provisioned'
                rowFormat = red_bd
                rowFormat_c = red_bd_c

            # retrieves the error message for not provisioned org -> from the admin account
            # the error message for the company (companies.provisioningError) is misleading
            if cp_ProvStatus != 'provisioned':
                sql = "SELECT email, lastError"
                sql += " FROM accounts INNER JOIN companiesAndAccounts ON companiesAndAccounts.accountId = accounts.id "
                sql += " WHERE companiesAndAccounts.companyId = '%s' " % cp_id
                sql += "  AND accounts.role = 'admin'"
                cursor.execute(sql)
                accountError = cursor.fetchone()
                if not accountError:
                    cp_ProvError = 'No admin account found'
                else:
                    cp_ProvError = 'Admin email address ' + \
                        accountError[0] + ' is not valid'
            else:
                cp_ProvError = ''

            # writes the body
            worksheet.write(row, 0, cp_date,      rowFormat_c)
            worksheet.write(row, 1, cp_id,        rowFormat_c)
            worksheet.write(row, 2, cp_name,      rowFormat)
            worksheet.write(row, 3, cp_site,      rowFormat)
            worksheet.write(row, 4, cp_admin,     rowFormat)
            worksheet.write(row, 5, cp_status,    rowFormat)
            worksheet.write(row, 6, cp_ProvError, rowFormat)
            row += 1

        # creates summary strings
        if totCompProvisioned == totCompanies:
            summary1 = str(totCompProvisioned) + ' trials provisioned'
        else:
            summary1 = str(totCompanies) + ' trials: ' + str(totCompProvisioned) + \
                ' provisioned, ' + \
                str(totCompanies-totCompProvisioned) + ' not provisioned'
        summary2 = str(totAccounts) + ' accounts, ' + \
            str(int(totAccProvisioned/totAccounts*100)) + '% provisioned'

        worksheet.write('C5', summary1)
        worksheet.write('C6', summary2)

        workbook.close()
        return filename

    global connection

    api = WebexTeamsAPI(botToken)

    try:
        connection = pymysql.connect(host=DBhost, port=int(DBport), user=DBuser, password=DBpass, db=DBname)
    except Exception as e:
        logger.critical('ChannelReport: error opening the DB. ' + str(e) + '. Check settings in the .ini file')
        logger.critical('Terminating')
        sys.exit()
    logger.debug('ChannelReport: connected to the DB')

    # retrieves the channel from the space
    cursor = connection.cursor()
    sql = "SELECT id FROM channels WHERE notificationSpace = '%s'" % space_id
    cursor.execute(sql)
    channels = cursor.fetchall()  # for channels that share the same space

    if not channels:
        msg = 'no channel found'
        logger.warning(msg)
        mention  = '<@personEmail:{}>'.format(person_email)
        message  = '{}, {}'.format(mention, msg)
        api.messages.create(space_id, markdown=message)

    else:
        for record in channels:
            channel = str(record[0])
            logger.info('Requested report for channel {}'.format(channel))
            # Creates the report in the "/reports" folder
            filename = BuildChannelReport(channel)
            if not filename:
                msg = 'No trials have been requested yet'
                logger.warning(msg)
                mention = '<@personEmail:{}>'.format(person_email)
                message = '{}, {}'.format(mention, msg)
                api.messages.create(space_id, markdown=message)
            else:
                msg = 'Report for channel {} ready at {}'.format(channel, filename)
                logger.info(msg)
                # posts the report
                response = 'here is the report with the list of all trials'
                mention  = '<@personEmail:{}>'.format(person_email)
                message  = '{}, {}'.format(mention, response)
                api.messages.create(space_id, markdown=message, files=[filename])
                logger.info('Report posted')

    connection.close()
    logger.debug('ChannelReport: closed connection to the DB')

def OrgReport(space_id, person_email, trial_id):

    def BuildOrgProvReport(id):

        # Used by OrgProvReport and OrgReport

        reportDate = datetime.datetime.now().strftime("%b %d, %Y %H:%M")
        cursor = connection.cursor()
        sql = "SELECT name, wxSiteUrl, provisioningStatus, provisioningError FROM companies WHERE id = '%s'" % id
        cursor.execute(sql)
        companyrecord = cursor.fetchone()

        companyName = companyrecord[0]
        companySite = companyrecord[1]

        # retrieves the accounts (excluding the Billing accounts)
        sql = "SELECT accounts.firstName, accounts.lastName, accounts.email, accounts.role, accounts.provisioningStatus,"
        sql += " accounts.isAlreadyInUse, accounts.isDomainClaim, accounts.lastError"
        sql += " FROM accounts INNER JOIN companiesAndAccounts ON accounts.id = companiesAndAccounts.accountId"
        sql += " WHERE companiesAndAccounts.companyId = '%s' AND accounts.role <> 'billing'" % id
        sql += " ORDER BY accounts.firstname, accounts.lastname"
        cursor.execute(sql)
        records = cursor.fetchall()

        # creates the Excel report
        if not os.path.exists('reports'):
            os.makedirs('reports')
        filename = 'reports/' + datetime.datetime.now().strftime("%Y-%m-%d") + \
            '_Report_' + str(id) + '.xlsx'
        workbook = xlsxwriter.Workbook(filename)
        worksheet = workbook.add_worksheet('Report')

        # Format
        worksheet.hide_gridlines(2)
        worksheet.set_zoom(120)
        # bigrow = workbook.add_format({'font_size': 13, 'font_name': 'Arial'})
        worksheet.set_column('A:B', 20)
        worksheet.set_column('C:C', 45)
        worksheet.set_column('D:E', 15)
        worksheet.set_column('F:F', 34)
        worksheet.set_row(0, 25)
        worksheet.set_row(2, 22)
        worksheet.set_row(3, 22)
        worksheet.set_row(4, 22)
        worksheet.set_row(5, 22)

        worksheet.autofilter('A8:F999999')
        worksheet.freeze_panes('A9')
        h1 = workbook.add_format({'align': 'vcenter', 'font_size': 18,
                                'bold': True, 'font_color': 'purple', 'font_name': 'Arial'})
        ar = workbook.add_format(
            {'align': 'right', 'font_name': 'Arial', 'font_size': 13})
        ar_bold = workbook.add_format(
            {'align': 'right', 'bold': True, 'font_name': 'Arial', 'font_size': 13})
        hl_bd2 = workbook.add_format(
            {'bg_color': 'yellow', 'bold': True, 'border': 2, 'font_name': 'Arial'})
        black = workbook.add_format(
            {'font_color': 'black', 'font_name': 'Arial', 'align': 'left'})
        black_bd = workbook.add_format(
            {'font_color': 'black', 'border': 1, 'font_name': 'Arial', 'align': 'left'})
        # black big (for the provisioning error content, header)
        black_big = workbook.add_format(
            {'font_color': 'black', 'font_name': 'Arial', 'align': 'left', 'font_size': 13})
        # black big, align right (for the trial id, header)
        black_big_r = workbook.add_format(
            {'font_color': 'black', 'font_name': 'Arial', 'align': 'left', 'font_size': 13, 'align': 'right'})
        # black, big, bold (for the summary content, header)
        black_bb = workbook.add_format(
            {'font_color': 'black', 'font_name': 'Arial', 'align': 'left', 'font_size': 13, 'bold': True})
        blue_bd = workbook.add_format(
            {'font_color': 'blue', 'border': 1, 'font_name': 'Arial', 'align': 'left'})
        red = workbook.add_format(
            {'font_color': 'red', 'font_name': 'Arial', 'align': 'left'})
        red_bd = workbook.add_format(
            {'font_color': 'red', 'border': 1, 'font_name': 'Arial', 'align': 'left'})
        red_big = workbook.add_format(
            {'font_color': 'red', 'font_name': 'Arial', 'align': 'left', 'font_size': 13, 'bold': True})
        url = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 13, 'underline': True})

        # title
        worksheet.write('A1', 'Matilde Provisioning Report', h1)
        worksheet.write('F1', reportDate, ar)

        # summary
        worksheet.write('A3', 'Trial id:', ar_bold)
        worksheet.write('B3', 'Name:', ar_bold)
        worksheet.write('B4,', 'Site:', ar_bold)
        worksheet.write('B5', 'Summary:', ar_bold)
        worksheet.write('B6', 'Provisioning errors:', ar_bold)
        worksheet.write('A4', id, black_big_r)
        worksheet.write_url('C3', url='https://admin.webex.com',
                            string=companyName, tip='Click here', cell_format=url)
        worksheet.write_url('C4', url='https://' + companySite,
                            string=companySite, tip='Click here', cell_format=url)

        # details - header
        worksheet.write('A8', 'First name', hl_bd2)
        worksheet.write('B8', 'Last name', hl_bd2)
        worksheet.write('C8', 'Email', hl_bd2)
        worksheet.write('D8', 'Role', hl_bd2)
        worksheet.write_comment('D8', 'includes external admins')
        worksheet.write('E8', 'Status', hl_bd2)
        worksheet.write('F8', 'Notes', hl_bd2)

        # details - account records and stats
        row = 8
        totAdmins = 0
        provAdmins = 0
        totUsers = 0
        provUsers = 0

        for record in records:
            fname = record[0]
            lname = record[1]
            email = record[2]
            role = record[3].title()
            prov = record[4]
            lastError = record[7]
            # removes the email address from the error message (redundant)
            lastError = str(lastError).split(':')[0]

            rowFormat = black_bd
            # counts admins and users and sets the error and the format of the row
            error = ''
            if 'admin' in role.lower():
                role = "Admin"
                rowFormat = blue_bd
                totAdmins += 1
                if prov == 'provisioned':
                    provAdmins += 1
                else:
                    error = lastError
                    rowFormat = red_bd
            else:
                totUsers += 1
                if prov == 'provisioned':
                    provUsers += 1
                else:
                    error = lastError
                    rowFormat = red_bd

            worksheet.write(row, 0, fname,        rowFormat)
            worksheet.write(row, 1, lname,        rowFormat)
            worksheet.write(row, 2, email,        rowFormat)
            worksheet.write(row, 3, role,         rowFormat)
            worksheet.write(row, 4, prov.title(), rowFormat)
            worksheet.write(row, 5, error,        rowFormat)
            row += 1

        # creates summary strings
        stringAdmins = 'admin'
        if totAdmins != 1:
            stringAdmins += 's'
        stringUsers = 'user'
        if totUsers != 1:
            stringUsers += 's'
        admins = str(provAdmins) + '/' + str(totAdmins)
        users = str(provUsers) + '/' + str(totUsers)
        perc = int((provAdmins+provUsers)/(totAdmins+totUsers)*100)
        summary = str('{}% provisioned ({} ' + stringAdmins +
                    ', {} ' + stringUsers + ')').format(perc, admins, users)
        numErrors = str(totAdmins-provAdmins+totUsers-provUsers)
        fmtErrors = red_big
        if numErrors == '0':
            numErrors = 'no'
            fmtErrors = black_big
        provErrors = numErrors + ' errors'
        worksheet.write('C5', summary, black_bb)
        worksheet.write('C6', provErrors, fmtErrors)

        workbook.close()
        return filename

    global connection

    api = WebexTeamsAPI(botToken)

    try:
        connection = pymysql.connect(host=DBhost, port=int(DBport), user=DBuser, password=DBpass, db=DBname)
    except Exception as e:
        logger.critical('OrgReport: error opening the DB. ' + str(e) + '. Check settings in the .ini file')
        logger.critical('Terminating')
        sys.exit()
    logger.debug('OrgReport: connected to the DB')

    if person_email == 'dgrandis@cisco.com':
        sql  = "SELECT * FROM companies WHERE id= '%s'" % trial_id
    else:
        # privacy: only trials associated to the space via the channel(s) 
        sql  = "SELECT * FROM companies INNER JOIN channels ON companies.channelId = channels.id"
        sql += " WHERE channels.notificationSpace = '%s'" % space_id
        sql += " AND companies.id = '%s'" % trial_id

    cursor = connection.cursor()
    cursor.execute(sql)
    company = cursor.fetchone()
    if not company:
        response = 'invalid trial id {}'.format(trial_id)
        mention = '<@personEmail:{}>'.format(person_email)
        message = '{}, {}'.format(mention, response)
        api.messages.create(space_id, markdown=message)
        message = '*Hint: **list** all trials first*'
        api.messages.create(space_id, markdown=message)
        logger.info('OrgReport: invalid trial id requested')

    else:
        # Creates the report in the "/reports" folder
        filename = BuildOrgProvReport(trial_id)
        # posts the report
        response = 'here is the report for the requested trial'
        mention = '<@personEmail:{}>'.format(person_email)
        message = '{}, {}'.format(mention, response)
        api.messages.create(space_id, markdown=message, files=[filename])
        logger.info('Report for trial_id #{} posted'.format(trial_id))

    connection.close()
    logger.debug('OrgReport: closed connection to the DB')
