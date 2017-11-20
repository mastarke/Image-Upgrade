
# PLEASE READ DISCLAIMER
#
#    This framework demonstrates sample IxNetwork REST API usage for
#    demo and reference purpose only.
#    It is subject to change for content updates without warning.
#
# REQUIREMENTS
#    - Python 2.7+
#    - Python modules: requests, paramiko
#
# Created by: Hubert Gee

from __future__ import absolute_import, print_function, division
import os, re, sys, requests, json, time, subprocess, traceback

class IxNetRestApiException(Exception): pass

class IxNetRestMain(object):
    def __init__(self, apiServerIp=None, serverIpPort=None, serverOs='windows',
                 username=None, password='admin', licenseServerIp=None, licenseMode=None, licenseTier=None,
                 deleteSessionAfterTest=True, verifySslCert=False, includeDebugTraceback=True, sessionId=None,
                 apiKey=None, generateRestLogFile=False):
        """
        Description
            Class IxNetRestMain()
            Initial settings for this Class.

        Parameters
            serverIp: The REST API server IP address.
            serverPort: The server IP address socket port.
            apiServer: windows, windowsConnectionMgr or linux
            includeDebugTraceback: True or False.
                                   If True, traceback messsages are included in raised exceptions.
                                   If False, no traceback.  Less verbose.

            The rest of the parameters are for connecting to a Linux API server only.
               username: The login username.
               password: The login password.
               licenseServerIp: The license server IP address.
               licenseMode: subscription, perpetual or mixed.
               licenseTier: tier1, tier2, tier3.
               isLinuxApiServerNewlyInstalled: True or False.
                                               If True, then configure the global license server settings also.
               deleteSessionAfterTest: True or False.
                                       If True, delete the session.
                                       If False, session is not deleted for debugging or for viewing.
               verifySslCert: Include your SSL certificate for added access security.
               apiServerPlatform: windows or linux.  Defaults to windows.
               includeDebugTraceback: True or False. If True, include tracebacks in raised exceptions
               sessionId: To session ID on the Linux API server to connect to.
               apiKey: The Linux API server user API-KEY to use for the sessionId connection.

       Class Variables:
            apiServerPlatform: windows, windowsConnectionMgr, linux
            sessionUrl: The session's URL: http://{apiServerIp:11009}/api/v1/sessions/1/ixnetwork
            sessionId : http://{apiServerIp:11009}/api/v1/sessions/1
            jsonHeader: The default URL header: {"content-type": "application/json"}
            apiKey: For Linux API server only. Automatically provided by the server when connecting and authenticating.
                    You could also provide an API-Key to connect to an existing session. Get the API-Key from the Linux API server.
        """
        from requests.exceptions import ConnectionError
        from requests.packages.urllib3.connection import HTTPConnection

        self.jsonHeader = {"content-type": "application/json"}
        self.apiKey = None
        self.verifySslCert = verifySslCert
        self.configuredProtocols = []
        self.linuxApiServerIp = apiServerIp
        self.apiServerPort = serverIpPort
        self.generateRestLogFile = generateRestLogFile
        if generateRestLogFile:
            self.restLogFile = 'restApiLog.txt'
            with open(self.restLogFile, 'w') as restLogFile:
                restLogFile.write('')

        if serverOs in ['windows', 'windowsConnectionMgr']:
            self.apiServerPlatform = serverOs
            self.getSessionUrl(apiServerIp, serverIpPort)

        if serverOs == 'linux':
            # Disable SSL warning messages
            requests.packages.urllib3.disable_warnings()
            if self.apiServerPort == None:
                self.apiServerPort == 443
            self.apiServerPlatform = 'linux'
        
            # Connect to an existing session on the Linux API server
            if apiKey != None and sessionId == None:
                raise IxNetRestApiException('Providing an apiKey must also provide a sessionId.')
            if apiKey and sessionId:
                self.sessionId = 'https://{0}:{1}/api/v1/sessions/{2}'.format(self.linuxApiServerIp, self.apiServerPort, str(sessionId))
                self.sessionUrl = 'https://{0}:{1}/api/v1/sessions/{2}/ixnetwork'.format(self.linuxApiServerIp, self.apiServerPort, sessionId)
                self.httpHeader = self.sessionUrl.split('/api')[0]
                self.apiKey = apiKey
                self.jsonHeader = {'content-type': 'application/json', 'x-api-key': self.apiKey}

            self.connectToLinuxApiServer(apiServerIp, username=username, password=password, verifySslCert=verifySslCert)

            if licenseServerIp or licenseMode or licenseTier:
                self.configLicenseServerDetails(licenseServerIp, licenseMode, licenseTier)

        # For Linux API Server only: Delete the session when script is done.
        self.deleteSessionAfterTest = deleteSessionAfterTest

        if includeDebugTraceback == False:
            sys.tracebacklimit = 0

    def get(self, restApi, data={}, stream=False, silentMode=False, ignoreError=False):
        """
        Description
           A HTTP GET function to send REST APIs.

        Parameters
           restApi: The REST API URL.
           data: The data payload for the URL.
           silentMode: True or False.  To display URL, data and header info.
           ignoreError: True or False.  If False, the response will be returned.
        """
        if silentMode is False or self.generateRestLogFile is True:
            #print('\nGET:', restApi)
            #print('HEADERS:', self.jsonHeader)
            self.logInfo('\nGET: {0}'.format(restApi))
            self.logInfo('HEADERS: {0}'.format(self.jsonHeader))

        try:
            # For binary file
            if stream:
                response = requests.get(restApi, stream=True, headers=self.jsonHeader, verify=self.verifySslCert)
            if stream == False:
                response = requests.get(restApi, headers=self.jsonHeader, verify=self.verifySslCert)

            if silentMode is False:
                #print('STATUS CODE:', response.status_code)
                self.logInfo('STATUS CODE: {0}'.format(response.status_code))
            if not re.match('2[0-9][0-9]', str(response.status_code)):
                if ignoreError == False:
                    if 'message' in response.json() and response.json()['messsage'] != None:
                        #print('\nWARNING:', response.json()['message'])
                        self.logWarning('\n%s' % response.json()['message'])
                    raise IxNetRestApiException('GET error:{0}\n'.format(response.text))
            return response

        except requests.exceptions.RequestException as errMsg:
            raise IxNetRestApiException('GET error: {0}\n'.format(errMsg))

    def post(self, restApi, data={}, headers=None, silentMode=False, noDataJsonDumps=False, ignoreError=False):
        """
        Description
           A HTTP POST function to mainly used to create or start operations.

        Parameters
           restApi: The REST API URL.
           data: The data payload for the URL.
           headers: The special header to use for the URL.
           silentMode: True or False.  To display URL, data and header info.
           noDataJsonDumps: True or False. If True, use json dumps. Else, accept the data as-is.
           ignoreError: True or False.  If False, the response will be returned. No exception will be raised.
        """

        if headers != None:
            originalJsonHeader = self.jsonHeader
            self.jsonHeader = headers

        if noDataJsonDumps == True:
            data = data
        else:
            data = json.dumps(data)

        if silentMode == False or self.generateRestLogFile is True:
            #print('\nPOST:', restApi)
            #print('DATA:', data)
            #print('HEADERS:', self.jsonHeader)
            self.logInfo('\nPOST: %s' % restApi)
            self.logInfo('DATA: %s' % data)
            self.logInfo('HEADERS: %s' % self.jsonHeader)

        try:
            response = requests.post(restApi, data=data, headers=self.jsonHeader, verify=self.verifySslCert)
            # 200 or 201
            if silentMode == False:
                #print('STATUS CODE:', response.status_code)
                self.logInfo('STATUS CODE: %s' % response.status_code)
            if not re.match('2[0-9][0-9]', str(response.status_code)):
                if ignoreError == False:
                    if 'message' in response.json() and response.json()['messsage'] != None:
                        #print('\nWARNING:', response.json()['message'])
                        self.logWarning('\n%s' % response.json()['message'])
                    self.showErrorMessage()
                    raise IxNetRestApiException('POST error: {0}\n'.format(response.text))

            # Change it back to the original json header
            if headers != None:
                self.jsonHeader = originalJsonHeader
            return response
        except requests.exceptions.RequestException as errMsg:
            raise IxNetRestApiException('POST error: {0}\n'.format(errMsg))

    def patch(self, restApi, data={}, silentMode=False):
        """
        Description
           A HTTP PATCH function to modify configurations.

        Parameters
           restApi: The REST API URL.
           data: The data payload for the URL.
           silentMode: True or False.  To display URL, data and header info.
        """

        if silentMode == False:
            #print('\nPATCH:', restApi)
            #print('DATA:', data)
            #print('HEADERS:', self.jsonHeader)
            self.logInfo('\nPATCH: %s' % restApi)
            self.logInfo('DATA: %s' % data)
            self.logInfo('HEADERS: %s' % self.jsonHeader)

        try:
            response = requests.patch(restApi, data=json.dumps(data), headers=self.jsonHeader, verify=self.verifySslCert)
            if silentMode == False:
                print('STATUS CODE:', response.status_code)
            if not re.match('2[0-9][0-9]', str(response.status_code)):
                if 'message' in response.json() and response.json()['messsage'] != None:
                    #print('\nWARNING:', response.json()['message'])
                    self.logWarning('\n%s' % response.json()['message'])
                self.showErrorMessage()
                raise IxNetRestApiException('PATCH error: {0}\n'.format(response.text))
            return response
        except requests.exceptions.RequestException as errMsg:
            raise IxNetRestApiException('PATCH error: {0}\n'.format(errMsg))

    def delete(self, restApi, data={}, headers=None):
        """
        Description
           A HTTP DELETE function to delete the session.
           For Linux API server only.

        Parameters
           restApi: The REST API URL.
           data: The data payload for the URL.
           headers: The header to use for the URL.
        """

        if headers != None:
            self.jsonHeader = headers

        #print('\nDELETE:', restApi)
        #print('DATA:', data)
        #print('HEADERS:', self.jsonHeader)
        self.logInfo('\nDELETE: %s' % restApi)
        self.logInfo('DATA: %s' % data)
        self.logInfo('HEADERS: %s' % self.jsonHeader)
        try:
            response = requests.delete(restApi, data=json.dumps(data), headers=self.jsonHeader, verify=self.verifySslCert)
            print('STATUS CODE:', response.status_code)
            if not re.match('2[0-9][0-9]', str(response.status_code)):
                self.showErrorMessage()
                raise IxNetRestApiException('DELETE error: {0}\n'.format(response.text))
            return response
        except requests.exceptions.RequestException as errMsg:
            raise IxNetRestApiException('DELETE error: {0}\n'.format(errMsg))

    def getSessionUrl(self, ixNetRestServerIp, ixNetRestServerPort=11009):
        """
        Description
            Connect to a Windows IxNetwork API Server to create a session URL.
            http://{apiServerIp:port}/api/v1/sessions/1/ixnetwork

         ixNetRestServerIp: The IxNetwork API Server IP address.
         ixNetRestServerPort: Provide a port number to connect to your non Linux API Server.
                              On a Linux API Server, a socket port is not needed. State "None".
        """
        url = 'http://{0}:{1}/api/v1/sessions'.format(ixNetRestServerIp, ixNetRestServerPort)
        serverAndPort = ixNetRestServerIp+':'+str(ixNetRestServerPort)

        if self.apiServerPlatform == 'windowsConnectionMgr':
            # For Connection Manager, requires a POST to automatically get the next session.
            # {'links': [{'href': '/api/v1/sessions/8020', 'method': 'GET', 'rel': 'self'}]}
            self.logInfo('\nPlease wait while IxNetwork starts up...')
            response = self.post(url)
            # Just get the session ID number
            sessionId = response.json()['links'][0]['href'].split('/')[-1]

        if self.apiServerPlatform == 'windows':
            response = self.get(url)
            sessionId = response.json()[0]['id']

        self.sessionUrl = 'http://{apiServer}:{port}/api/v1/sessions/{id}/ixnetwork'.format(apiServer=ixNetRestServerIp,
                                                                                            port=ixNetRestServerPort,
                                                                                            id=sessionId)
        # http://192.168.70.127:11009
        self.httpHeader = self.sessionUrl.split('/api')[0]
        # http://192.168.70.127:11009/api/v1/sessions/1
        self.sessionId = self.sessionUrl.split('/ixnetwork')[0]
        return self.sessionUrl

    def deleteSession(self):
        # Mainly for Windows Connection Manager
        if self.deleteSessionAfterTest:
            self.delete(self.sessionId)

    def logInfo(self, msg, end='\n'):
        print('{0}'.format(msg), end=end)
        if self.generateRestLogFile:
            with open(self.restLogFile, 'a') as restLogFile:
                restLogFile.write(msg+end)

    def logWarning(self, msg, end='\n'):
        print('Warning: {0}'.format(msg), end=end)

    def logError(self, msg, end='\n'):
        print('Error: {0}'.format(msg), end=end)

    def getIxNetworkVersion(self):
        response = self.get(self.sessionUrl+'/globals', silentMode=True)
        return response.json()['buildNumber']

    def showErrorMessage(self, silentMode=False):
        """
        Description
            Show all the error messages from IxNetwork.

        Syntax
            GET: http://{apiServerIp:port}/api/v1/sessions/{id}/globals/appErrors/error
        """

        errorList = []
        response = self.get(self.sessionUrl+'/globals/appErrors/error', silentMode=silentMode)
        print()
        for errorId in response.json():
            if errorId['errorLevel'] == 'kError':
                print('CurrentErrorMessage: {0}'.format(errorId['name']))
                print('\tDescription: {0}'.format(errorId['lastModified']))
                errorList.append(errorId['name'])
        print()
        return errorList

    def waitForComplete(self, response='', url='', silentMode=True, timeout=90):
        """
        Description
            Wait for an operation progress to complete.

        Parameters
            response: The POST action response.  Generally, after an /operations action.
                      Such as /operations/startallprotocols, /operations/assignports
            silentMode: True or False. If True, display info messages.
            timeout: The time allowed to wait for success completion in seconds.
        """
        self.logInfo('\nwaitForComplete...')
        if response.json() == []:
            raise IxNetRestApiException('waitForComplete: response is empty.')
        if 'errors' in response.json():
            self.logInfo(response.json()["errors"][0])
            return 1
        self.logInfo("\tState: %s " %response.json()["state"])
        if response.json()['state'] == "SUCCESS":
            self.logInfo('\n')
            return 0
        if response.json()['state'] == "ERROR":
            self.showErrorMessage()
            return 1
        if response.json()['state'] == "EXCEPTION":
            self.logInfo(response.text)
            return 1

        while True:
            response = self.get(url, silentMode=silentMode)
            state = response.json()["state"]
            self.logInfo("\tState: {0}".format(state))
            if response.json()["state"] == "IN_PROGRESS" or response.json()["state"] == "down":
                if timeout == 0:
                    return 1
                time.sleep(1)
                continue
            if timeout > 0 and state == 'SUCCESS':
                break
            elif timeout > 0 and state == 'ERROR':
                self.showErrorMessage()
                return 1
            elif timeout > 0 and state == 'EXCEPTION':
                print('\n', response.text)
                return 1
            elif timeout == 0 and state != 'SUCCESS':
                return 1
            else:
                self.logInfo("\tState: {0} {1} seconds remaining".format(state, timeout))
                timeout = timeout-1
                continue
        self.logInfo('\n')

    def connectToLinuxApiServer(self, linuxServerIp, username='admin', password='admin', verifySslCert=False):
        """
        Description
            Connect to a secured access Linux API server.

        Parameters
            linuxServerIp: The Linux API server IP address.
            username: Login username. Default = admin.
            password: Login password. Default = admin.
            verifySslCert: The SSL Certificate to secure access verification.

        Syntax
            POST: 'https://{linuxApiServerIp}/api/v1/auth/session'
        """
        self.verifySslCert = verifySslCert

        if self.apiKey is None:
            # 1: Connect to the Linux API server
            url = 'https://{0}/api/v1/auth/session'.format(linuxServerIp)
            self.logInfo('\nconnectToLinuxApiServer: %s' % url)
            response = self.post(url, data={'username': username, 'password': password}, ignoreError=True)
            if not re.match('2[0-9][0-9]', str(response.status_code)):
                raise IxNetRestApiException('\nLogin username/password failed\n')
            self.apiKey = response.json()['apiKey']

            # 2: Create new session
            if self.apiServerPort != None:
                linuxServerIp = linuxServerIp + ':' + self.apiServerPort

            url = 'https://{0}/api/v1/sessions'.format(linuxServerIp)
            data = {'applicationType': 'ixnrest'}
            self.jsonHeader = {'content-type': 'application/json', 'x-api-key': self.apiKey}
            self.logInfo('\nlinuxServerCreateSession')
            response = self.post(url, data=data, headers=self.jsonHeader)
            sessionId = response.json()['id']
            self.sessionId = 'https://{0}/api/v1/sessions/{1}'.format(linuxServerIp, sessionId)
            self.sessionUrl = 'https://{0}/api/v1/sessions/{1}/ixnetwork'.format(linuxServerIp, sessionId)
            self.httpHeader = self.sessionUrl.split('/api')[0]

            # 3: Start the new session
            self.logInfo('\nlinuxServerStartSession: %s' % self.sessionId)
            response = self.post(self.sessionId+'/operations/start')
            if self.linuxServerWaitForSuccess(response.json()['url'], timeout=60) == 1:
                raise IxNetRestApiException

        # If an API-Key is provided, then verify the session ID connection.
        if self.apiKey:
            self.get(self.sessionId)

        self.logInfo('sessionId: %s' % self.sessionId)
        self.logInfo('\nsessionUrl: %s' % self.sessionUrl)
        self.logInfo('apiKey: %s' % self.apiKey)

    def linuxServerConfigGlobalLicenseServer(self, linuxServerIp, licenseServerIp, licenseMode, licenseTier):
        """
        Description
           On a new Linux API Linux installation, you need to set the global license server once.
           When a new session is created, it will check the global license settings and config the
           license settings on the new session.

        Parameters
            linuxServerIp: IP address of the Linux API server.
            licenseServerIp: Type = list. [IP address of the license server]
            licenseMode: subscription, perpetual or mixed
            licenseier: tier1, tier2, tier3

        Syntax
           PATCH: https://<apiServerIp>/api/v1/sessions/9999/ixnetworkglobals/license
           DATA:  {'servers': list(licenseServerIp),
                   'mode': str(licenseMode),
                   'tier': str(licenseTier)
                  }
        """

        staticUrl = 'https://{linuxServerIp}/api/v1/sessions/9999/ixnetworkglobals/license'.format(linuxServerIp=linuxServerIp)
        self.logInfo('\nlinuxServerConfigGlobalLicenseServer:\n\t{0}\n\t{1}\n\t{2}\n'. format(licenseServerIp,
                                                                                       licenseMode,
                                                                                       licenseTier))
        response = self.patch(staticUrl, data={'servers': [licenseServerIp], 'mode': licenseMode, 'tier': licenseTier})
        response = self.get(staticUrl)
        licenseServerIp = response.json()['servers'][0]
        licenseServerMode = response.json()['mode']
        licenseServerTier = response.json()['tier']
        self.logInfo('\nLinuxApiServer static license server:')
        self.logInfo('\t', licenseServerIp)
        self.logInfo('\t', licenseServerMode)
        self.logInfo('\t', licenseServerTier)

    def linuxServerGetGlobalLicense(self, linuxServerIp):
        """
        Description
            Get the global license server details from the Linux API server.

        Parameter
            linuxServerIp: The IP address of the Linux API server.

        Syntax
            GET: 'https://{linuxServerIp}/api/v1/sessions/9999/ixnetworkglobals/license'
        """
        staticUrl = 'https://{linuxServerIp}/api/v1/sessions/9999/ixnetworkglobals/license'.format(linuxServerIp=linuxServerIp)
        self.logInfo('\nlinuxServerGetGlobalLicense: %s ' % linuxServerIp)
        response = self.get(staticUrl, silentMode=False)
        licenseServerIp = response.json()['servers'][0]
        licenseServerMode = response.json()['mode']
        licenseServerTier = response.json()['tier']
        self.logInfo('\nlinuxServerGetGlobalLicenses:')
        self.logInfo('\t%s' % licenseServerIp)
        self.logInfo('\t%s' % licenseServerMode)
        self.logInfo('\t%s' % licenseServerTier)
        return licenseServerIp,licenseServerMode,licenseServerTier

    def configLicenseServerDetails(self, licenseServer=None, licenseMode=None, licenseTier=None):
        """
        Description
           Configure license server details: license server IP, license mode and license tier.

        Parameter
            licenseServer: License server IP address(s) in a list.
            licenseMode: subscription|perpetual}mixed
            licenseTier: tier1, tier2, tier3 ...

        Syntax
           PATCH: https://{apiServerIp}/api/v1/sessions/{id}/ixnetwork/globals/licensing
        """
        # Each new session requires configuring the new session's license details.
        data = {}
        if licenseServer:
            data.update({'licensingServers': licenseServer})
        if licenseMode:
            data.update({'mode': licenseMode})
        if licenseTier:
            data.update({'tier': licenseTier})

        response = self.patch(self.sessionUrl+'/globals/licensing', data=data)
        self.showLicenseDetails()

    def showLicenseDetails(self):
        """
        Description
            Verify the new session's license details.
        """

        response = self.get(self.sessionUrl+'/globals/licensing')
        self.logInfo('\nVerifying sessionId license server: %s' % self.sessionUrl)
        self.logInfo('\t%s' % response.json()['licensingServers'])
        self.logInfo('\t%s'%  response.json()['mode'])
        self.logInfo('\t%s' % response.json()['tier'])

    def linuxServerStopAndDeleteSession(self):
        """
        Description
           Wrapper to stop and delete the session ID on the Linux API server.

        Requirements
           * linuxServerStopOperations()
           * linuxServerDeleteSession()

        Syntax
           GET = https://{apiServerIp}/api/v1/sessions/{id}
        """
        if self.apiServerPlatform == 'linux' and self.deleteSessionAfterTest==True:
            self.linuxServerStopOperations()
            self.linuxServerDeleteSession()

    def linuxServerStopOperations(self, sessionId=None):
        """
        Description
            Stop the session ID on the Linux API server
        """
        if sessionId != None:
            sessionId = sessionId
        else:
            sessionId = self.sessionId

        self.logInfo('\nlinuxServerStopOperations: %s' % sessionId)
        response = self.post(sessionId+'/operations/stop')
        if self.linuxServerWaitForSuccess(response.json()['url'], timeout=10) == 1:
            raise IxNetRestApiException

    def linuxServerDeleteSession(self, sessionId=None):
        """
        Description
            Delete the session ID on the Linux API server.

        Syntax
            DELETE: https://{linuxApiServerIp}/api/v1/sessions/{id}/operations/stop
        """
        if sessionId != None:
            sessionId = sessionId
        else:
            sessionId = self.sessionId

        self.logInfo('\nlinuxServerDeleteSession: Deleting...%s' % sessionId)
        response = self.delete(sessionId)

    def linuxServerWaitForSuccess(self, url, timeout=120):
        """
        Description
            Wait for success completion on the Linux API server.

        Parameter
            url: The URL's ID of the operation to verify
        """
        data = {'applicationType': 'ixnrest'}
        jsonHeader = {'content-type': 'application/json', 'x-api-key': self.apiKey}
        for counter in range(1,timeout+1):
            response = self.get(url, data=data, silentMode=True)
            currentStatus = response.json()['message']
            self.logInfo('CurrentStatus: {0}  {1}/{2} seconds'.format(currentStatus, counter, timeout))
            if counter < timeout+1 and currentStatus != 'Operation successfully completed':
                time.sleep(1)
            if counter == timeout+1 and currentStatus != 'Operation successfully completed':
                return 1
            if counter < timeout+1 and currentStatus == 'Operation successfully completed':
                return 0


    def newBlankConfig(self):
        # Requires waitForComplete API also
        # sessionId = http://192.168.70.127:11009/api/v1/sessions/1/ixnetwork

        url = self.sessionUrl+'/operations/newconfig'
        self.logInfo('\nnewBlankConfig:', url)
        response = self.post(url)
        if response == 1: return 1
        url = self.sessionUrl+'/operations/newconfig/'+response.json()['id']
        if self.waitForComplete(response, url) == 1:
            raise IxNetRestApiException()

    def connectToVChassis(self, chassisIp):
        # Connects to the virtual chassis

        url = self.sessionUrl+'/operations/connecttochassis'
        data = {"arg1": chassisIp}

        response = self.post(url, data=data)
        if response == 1: return 1
        if response.json()['state'] == 'ERROR':
            self.logInfo('connectToVChassis error: %s' % response.json()['result'])
            return 1
        else:
            self.logInfo('connectToVChassis: Successfully connected to chassis: %s' % chassisIp)
            while response.json()["state"] == "IN_PROGRESS" or response.json()["state"] == "down":
                if timeout == 0:
                    break
                time.sleep(1)
                response = requests.get(self.sessionUrl)
                state = response.json()["state"]
                self.logInfo("\t\t%s" % state)
                timeout = timeout - 1
            return 0

    def connectIxChassis(self, chassisIp):
        """
        Description
           Connect to chassis.
           This needs to be done prior to assigning ports for testing.

        Syntax
           /api/v1/sessions/1/ixnetwork/availableHardware/chassis

        Parameter
           chassisIp: The chassis IP address.
        """
        url = self.sessionUrl+'/availableHardware/chassis'
        data = {'hostname': chassisIp}
        response = self.post(url, data=data)
        chassisIdObj = response.json()['links'][0]['href']
        # Chassis states: down, polling, ready
        for timer in range(1,61):
            response = self.get(self.httpHeader + chassisIdObj, silentMode=True)
            currentStatus = response.json()['state']
            self.logInfo('connectIxChassis {0}: Status: {1}'.format(chassisIp, currentStatus))
            if currentStatus != 'ready' and timer < 60:
                time.sleep(1)
            if currentStatus != 'ready' and timer == 60:
                raise IxNetRestApiException('connectIxChassis: Connecting to chassis {0} failed'.format(chassisIp))
            if currentStatus == 'ready' and timer < 60:
                break

        # http://192.168.70.127:11009/api/v1/sessions/1/ixnetwork/availableHardware/chassis/1
        return self.httpHeader + chassisIdObj

    def disconnectIxChassis(self, chassisIp):
        """
        Description
            Disconnect the chassis (both hardware or virtualChassis).

        Syntax
            http://{apiServerIp:11009}/api/v1/sessions/1/ixnetwork/availableHardware/chassis/<id>

        Parameter
            chassisIp: The chassis IP address.
        """
        url = self.sessionUrl+'/availableHardware/chassis'
        response = self.get(url)
        for eachChassisId in response.json():
            if eachChassisId['hostname'] == chassisIp:
                chassisIdUrl = eachChassisId['links'][0]['href']
                self.logInfo('\ndisconnectIxChassis: %s' % chassisIdUrl)
                response = self.delete(self.httpHeader+chassisIdUrl)

    def createVports(self, portList=None, rawTrafficVportStyle=False):
        """
        Description
           This API creates virtual ports based on a portList.

         portList:  Pass in a list of ports in the format of ixChassisIp, slotNumber, portNumber
           portList = [[ixChassisIp, '1', '1'],
                       [ixChassisIp, '2', '1']]

         rawTrafficVportStyle = For raw Traffic Item src/dest endpoints, vports must be in format:
                                /api/v1/sessions1/vport/{id}/protocols

         Next step is to call assignPort.

         Return: A list of vports
        """
        createdVportList = []
        for index in range(0, len(portList)):
            response = self.post(self.sessionUrl+'/vport')
            vportObj = response.json()['links'][0]['href']
            self.logInfo('\ncreateVports: %s' % vportObj)
            if rawTrafficVportStyle:
                createdVportList.append(vportObj+'/protocols')
            else:
                createdVportList.append(vportObj)
            if portList != None:
                response = self.get(self.httpHeader+vportObj)
                card = portList[index][1]
                port = portList[index][2]
                portNumber = card+'/'+port
                self.logInfo('\tName: %s' % portNumber)
                response = self.patch(self.httpHeader+vportObj, data={'name': portNumber})

        if createdVportList == []:
            raise IxNetRestApiException('No vports created')

        self.logInfo('\ncreateVports: %s' % createdVportList)
        return createdVportList

    def getVportObjectByName(self, portName):
        """
        Description:
           Get the vport object by the specified port name.
        """
        response = self.get(self.sessionUrl+'/vport')
        vportList = ["%s/vport/%s" % (self.sessionUrl, str(i["id"])) for i in response.json()]
        for vportObj in vportList:
            response = self.get(vportObj)
            if response.json()['name'] == portName:
                return vportObj
        return None

    def getVportName(self, vportObj):
        """
        Description
           Get the name of the vport by the specified vport object

        vportObj: "http://192.168.70.127:11009/api/v1/sessions/1/ixnetwork/vport/1"
        """
        response = self.get(vportObj)
        return response.json()['name']

    def linkUpDown(self, port, action='down'):
        """
        Description
            Flap a port up or down. 

        Parameters
            port: [ixChassisIp, str(card), str(port)] -> ['10.10.10.1', '1', '3']
        
        action
            up|down
        """
        vport = self.getVports([port])[0]
        self.post(self.sessionUrl+'/vport/operations/linkUpDn', data={'arg1': [vport], 'arg2': action})

    def getAllTopologyList(self):
        """
        Description
           If Topology exists: Returns a list of created Topologies.
           If no Topology exists: Returns []
        """
        response = self.get(self.sessionUrl+'/topology')
        topologyList = ['%s/%s/%s' % (self.sessionUrl, 'topology', str(i["id"])) for i in response.json()]
        return topologyList

    def getAllVportList(self):
        """
        Description
            Returns a list of all the created virtual ports
        
        Returns
            List of vports: ['/api/v1/sessions/1/ixnetwork/vport/1', '/api/v1/sessions/1/ixnetwork/vport/2']
        """
        response = self.get(self.sessionUrl+'/vport')
        vportList = ['%s' % vport['links'][0]['href'] for vport in response.json()]
        return vportList

    def getVports(self, portList):
        """
        Description
            Get the vports for the portList

            portList format = [[str(chassisIp), str(slotNumber), str(portNumber)]]
               Example 1: [[ixChassisIp, '1', '1']]
               Example 2: [[ixChassisIp, '1', '1'], [ixChassisIp, '2', '1']]
        """
        response = self.get(self.sessionUrl+'/vport')
        vportList = []

        for vportAttributes in response.json():
            #print(vportAttributes, end='\n')
            currentVportId = vportAttributes['links'][0]['href']
            # "assignedTo": "192.168.70.10:1:1
            assignedTo = vportAttributes['assignedTo']
            if assignedTo == '':
                return []

            chassisIp = assignedTo.split(':')[0]
            cardNum = assignedTo.split(':')[1]
            portNum = assignedTo.split(':')[2]
            port = [chassisIp, cardNum, portNum]

            if port in portList:
                # ['192.168.70.10', '1', '1']
                vport = vportAttributes['links'][0]['href']
                vportList.append(vport)

        # Returns:
        # ['http://192.168.70.127:11009/api/v1/sessions/1/ixnetwork/vport/1',
        #  'http://192.168.70.127:11009/api/v1/sessions/1/ixnetwork/vport/2']
        return vportList

    def getIpObjectsByTopologyObject(self, topologyObj, ipType='ipv4'):
        """
        Description
           Get all the Topology's IPv4 or IPv6 objects based on the specified topology object.

        Parameters
           ipType = ipv4 or ipv6
        """
        ipObjList = []
        deviceGroupResponse = self.get(topologyObj+'/deviceGroup')
        deviceGroupList = ['%s/%s/%s' % (topologyObj, 'deviceGroup', str(i["id"])) for i in deviceGroupResponse.json()]
        for deviceGroup in deviceGroupList:
            response = self.get(deviceGroup+'/ethernet')
            ethernetList = ['%s/%s/%s' % (deviceGroup, 'ethernet', str(i["id"])) for i in response.json()]
            for ethernet in ethernetList:
                response = self.get(ethernet+'/{0}'.format(ipType))
                ipObjList = ['%s/%s/%s' % (ethernet, 'ipv4', str(i["id"])) for i in response.json()]
        return ipObjList

    def clearAllTopologyVports(self):
        response = self.get(self.sessionUrl + "/topology")
        topologyList = ["%s%s" % (self.httpHeader, str(i["links"][0]["href"])) for i in response.json()]
        for topology in topologyList:
            self.patch(topology, data={"vports": []})

    def modifyTopologyPortsNgpf(self, topologyObj, portList, topologyName=None):
        """
        add/remove Topology ports.
        portList = A list of all the ports that you want for the Topology even if the port exists in
                   the Topology.

        Requirements:
            1> You must have already connected all the required ports for your configuration. Otherwise,
               adding additional port(s) that doesn't exists in your configuration's assigned port list
               will not work.

            2> This API requires getVports()

        topologyUrl = '/api/v1/sessions/1/ixnetwork/topology/1'

        portList format = [(str(chassisIp), str(slotNumber), str(portNumber))]
            Example 1: [ ['192.168.70.10', '1', '1'] ]
            Example 2: [ ['192.168.70.10', '1', '1'], ['192.168.70.10', '2', '1'] ]

        Return 1 if Failed.
        """

        vportList = self.getVports(portList)
        if len(vportList) != len(portList):
            raise IxNetRestApiException('modifyTopologyPortsNgpf: There is not enough vports created to match the number of ports.')
        self.logInfo('\nvportList: %s' % vportList)
        topologyData = {'vports': vportList}
        response = self.patch(self.httpHeader+topologyObj, data=topologyData)

    def getTopologyPorts(self, topologyObj):
        """
        Description
            Get all the configured ports in the Topology.

        Parameter
            topologyObj = '/api/v1/sessions/1/ixnetwork/topology/1'

        Returns
            A list of ports: [('192.168.70.10', '1', '1') ('192.168.70.10', '1', '2')]
        """

        topologyResponse = self.get(self.httpHeader+topologyObj)
        vportList = topologyResponse.json()['vports']
        if vportList == []:
            self.logError('No vport is created')
            return 1
        self.logInfo('vportList: %s' % vportList)
        portList = []
        for vport in vportList:
            response = self.get(self.httpHeader+vport)
            # 192.168.70.10:1:1
            currentPort = response.json()['assignedTo']
            chassisIp = currentPort.split(':')[0]
            card = currentPort.split(':')[1]
            port = currentPort.split(':')[2]
            portList.append((chassisIp, card, port))
        return portList

    def createTopologyNgpf(self, portList, topologyName=None):
        """
        Description
            Create a new Topology and assign ports to it.

        Parameters
            portList: format = [[(str(chassisIp), str(slotNumber), str(portNumber)] ]
                Example 1: [ ['192.168.70.10', '1', '1'] ]
                Example 2: [ ['192.168.70.10', '1', '1'], ['192.168.70.10', '2', '1'] ]

            topologyName: Give a name to the Topology Group.
        """
        url = self.sessionUrl+'/topology'
        self.logInfo('createTopology: Getting vport list: %s' % portList)
        vportList = self.getVports(portList)
        if len(vportList) != len(portList):
            raise IxNetRestApiException('createTopologyNgpf: There is not enough vports created to match the number of ports.')

        topologyData = {'vports': vportList}
        if topologyName != None:
            topologyData['name'] = topologyName

        response = self.post(url, data=topologyData)
        topologyObj = response.json()['links'][0]['href']
        return topologyObj

    def createDeviceGroupNgpf(self, topologyObj, multiplier=1, deviceGroupName=None):
        """
        Description
            Create a new Device Group.

        Parameters
            topologyObj: A Topology object: /api/v1/sessions/1/ixnetwork/topology/{id}
            multiplier: The amount of host to create (In integer).
            deviceGroupName: Optional: Device Group name.

        Returns:
            /api/v1/sessions/1/ixnetwork/topology/{id}/deviceGroup/{id}

        """
        url = self.httpHeader+topologyObj+'/deviceGroup'
        deviceGroupData = {'multiplier': int(multiplier)}
        if deviceGroupName != None:
            deviceGroupData['name'] = deviceGroupName
        response = self.post(url, data=deviceGroupData)
        deviceGroupObj = response.json()['links'][0]['href']
        self.logInfo('createDeviceGroup: %s' % deviceGroupObj)
        return deviceGroupObj

    def createEthernetNgpf(self, deviceGroupObj, ethernetName=None, macAddress=None,
                           macAddressPortStep='disabled', vlanId=None, vlanPriority=None, mtu=None):
        """
        Description
            Create an Ethernet header

        Parameters
            deviceGroupObj: '/api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/2'

            ethernetName: Ethernet header name.
            macAddress: By default, IxNetwork will generate unique Mac Addresses.
                        {'start': '00:01:02:00:00:01', 'direction': 'increment', 'step': '00:00:00:00:00:01'}
                        Note: step: '00:00:00:00:00:00' means don't increment.

            macAddressPortStep: Incrementing the Mac address on each port based on your input.
                                '00:00:00:00:00:01' means to increment the last byte on each port.
                                Options:
                                   - 'disable' or '00:00:00:01:00:00' format

            vlanId: None, single value or {'start': 103, 'direction': 'increment', 'step': 1}
            vlanPriority: None, single value or {'start': 2, 'direction': 'increment', 'step': 1}
            mtu: None, single value or {'start': 1300, 'direction': 'increment', 'step': 1})

         Example:
             ethernetObj1 = createEthernetNgpf(deviceGroupObj1,
                                          ethernetName='Eth1',
                                          macAddress={'start': '00:01:01:00:00:01',
                                                      'direction': 'increment',
                                                      'step': '00:00:00:00:00:01'},
                                          macAddressPortStep='00:00:00:00:01:00')
        """
        url = self.httpHeader+deviceGroupObj + '/ethernet'
        response = self.post(url)
        ethernetObj = response.json()['links'][0]['href']
        ethObjResponse = self.get(self.httpHeader+ethernetObj)
        if ethernetName != None:
            self.patch(self.httpHeader+ethernetObj, data={'name': ethernetName})

        if macAddress != None:
            multivalue = ethObjResponse.json()['mac']
            if type(macAddress) is dict:
                self.patch(self.httpHeader+multivalue+'/counter', data=macAddress)
            else:
                self.patch(self.httpHeader+multivalue+'/singleValue', data={'value': macAddress})

        # Config Mac Address Port Step
        portStepMultivalue = self.httpHeader + multivalue+'/nest/1'
        if macAddressPortStep is not 'disabled':
            self.patch(portStepMultivalue, data={'step': macAddressPortStep})

        if macAddressPortStep == 'disabled':
            self.patch(portStepMultivalue, data={'enabled': False})

        if vlanId != None:
            # Enable VLAN
            multivalue = ethObjResponse.json()['enableVlans']
            self.patch(self.httpHeader + multivalue+'/singleValue', data={'value': True})

            # CREATE vlan object (Creating vlanID always /vlan/1 and then do a get for 'vlanId')
            vlanIdObj = self.httpHeader+ethernetObj+'/vlan/1'
            vlanIdResponse = self.get(vlanIdObj)
            multivalue = vlanIdResponse.json()['vlanId']

            # CONFIG VLAN ID
            if type(vlanId) is dict:
                self.patch(self.httpHeader+multivalue+'/counter', data=vlanId)
            else:
                self.patch(self.httpHeader+multivalue+'/singleValue', data={'value': int(vlanId)})

            # CONFIG VLAN PRIORITY
            if vlanPriority != None:
                multivalue = vlanIdResponse.json()['priority']
                if type(vlanPriority) is dict:
                    self.patch(self.httpHeader+multivalue+'/counter', data=vlanPriority)
                else:
                    self.patch(self.httpHeader+multivalue+'/singleValue', data={'value': int(vlanPriority)})

        if mtu != None:
            multivalue = ethObjResponse.json()['mtu']
            if type(mtu) is dict:
                self.patch(self.httpHeader+multivalue+'/counter', data=json.dumps(mtu))
            else:
                self.patch(self.httpHeader+multivalue+'/singleValue', data={'value': int(mtu)})

        return ethernetObj

    def createIpv4Ngpf(self, ethernetObj, name=None, ipv4Address='', ipv4AddressPortStep='disabled', gateway=None,
                       gatewayPortStep='disabled', prefix=None, resolveGateway=True):
        """
        Description
            Create an IPv4 header.

        Parameters
            ethernetObj: The Ethernet Object
                         Example: '/api/v1/sessions/1/ixnetwork/topology/2/deviceGroup/1/ethernet/1'

            ipv4Address: Single value or {'start': '100.1.1.100', 'direction': 'increment', 'step': '0.0.0.1'},
            ipv4AddressPortStep: Incrementing the IP address on each port based on your input.
                                 0.0.0.1 means to increment the last octet on each port.
                                 Options:
                                    - 'disable' or 0.0.0.1 format

            gateway: Single value or {'start': '100.1.1.1', 'direction': 'increment', 'step': '0.0.0.1'},
            gatewayPortStep: Same as ipv4AddressPortStep
            prefix: Single value:  Example: 24
            rsolveGateway: True or False

         Example:
             ipv4Obj1 = createIpv4Ngpf(ethernetObj1,
                                  ipv4Address={'start': '100.1.1.1', 'direction': 'increment', 'step': '0.0.0.1'},
                                  ipv4AddressPortStep='disabled',
                                  gateway={'start': '100.1.1.100', 'direction': 'increment', 'step': '0.0.0.0'},
                                  gatewayPortStep='disabled',
                                  prefix=24,
                                  resolveGateway=True)
        """
        ipv4Url = self.httpHeader+ethernetObj+'/ipv4'
        response = self.post(ipv4Url)
        ipv4Obj = response.json()['links'][0]['href']
        ipv4Response = self.get(self.httpHeader+ipv4Obj)

        if name != None:
            self.patch(self.httpHeader+ipv4Obj, data={'name': name})

        # Config IPv4 address
        multivalue = ipv4Response.json()['address']
        if type(ipv4Address) is dict:
            self.patch(self.httpHeader+multivalue+"/counter", data=ipv4Address)
        else:
            self.patch(self.httpHeader+multivalue+"/singleValue", data={'value': ipv4Address})

        # Config IPv4 port step
        portStepMultivalue = self.httpHeader+multivalue+'/nest/1'
        if ipv4AddressPortStep is not 'disabled':
            self.patch(portStepMultivalue, data={'step': ipv4AddressPortStep})

        if ipv4AddressPortStep == 'disabled':
            self.patch(portStepMultivalue, data={'enabled': False})

        # Config Gateway
        multivalue = ipv4Response.json()['gatewayIp']
        if type(gateway) is dict:
            self.patch(self.httpHeader+multivalue+"/counter", data=gateway)
        else:
            self.patch(self.httpHeader+multivalue+"/singleValue", data={'value': gateway})

        # Config Gateway port step
        portStepMultivalue = self.httpHeader+multivalue+'/nest/1'
        if gatewayPortStep is not 'disabled':
            self.patch(portStepMultivalue, data={'step': gatewayPortStep})

        if gatewayPortStep == 'disabled':
            self.patch(portStepMultivalue, data={'enabled': False})

        # Config resolve gateway
        multivalue = ipv4Response.json()['resolveGateway']
        self.patch(self.httpHeader+multivalue+"/singleValue", data={'value': resolveGateway})

        multivalue = ipv4Response.json()['prefix']
        self.patch(self.httpHeader+multivalue+"/singleValue", data={'value': prefix})

        self.configuredProtocols.append(ipv4Obj)
        return ipv4Obj

    def configOspf(self, obj, **kwargs):
        """
        Description
            Create or modify OSPF.

        Parameters
            IPv4 object handle example:
            obj: /api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv4/1

            OSPF object handle example:
            obj: /api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv4/1/ospfv2/1

        Example:
            ospfObj1 = configOspf(ipv4Obj,
                          name = 'ospf_1',
                          areaId = '0',
                          neighborIp = '1.1.1.2',
                          helloInterval = '10',
                          areaIdIp = '0.0.0.0',
                          networkType = 'pointtomultipoint',
                          deadInterval = '40')
        """

        if 'ospf' not in obj:
            ospfUrl = self.httpHeader+obj+'/ospfv2'
            response = self.post(ospfUrl)
            # /api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv4/1/ospfv2/1
            ospfObj = response.json()['links'][0]['href']

        if 'ospf' in obj:
            ospfObj = obj

        ospfObjResponse = self.get(self.httpHeader+ospfObj)

        if 'name' in kwargs:
            self.patch(self.httpHeader+ospfObj, data={'name': kwargs['name']})

        if 'areaId' in kwargs:
            multiValue = ospfObjResponse.json()['areaId']
            self.patch(self.httpHeader+multiValue+"/singleValue", data={'value': kwargs['areaId']})

        if 'neighborIp' in kwargs:
            multiValue = ospfObjResponse.json()['neighborIp']
            self.patch(self.httpHeader+multiValue+"/singleValue", data={'value': kwargs['neighborIp']})

        if 'helloInterval' in kwargs:
            multiValue = ospfObjResponse.json()['helloInterval']
            self.patch(self.httpHeader+multiValue+"/singleValue", data={'value': kwargs['helloInterval']})

        if 'areaIdIp' in kwargs:
            multiValue = ospfObjResponse.json()['areaIdIp']
            self.patch(self.httpHeader+multiValue+"/singleValue", data={'value': kwargs['areaIdIp']})

        if 'networkType' in kwargs:
            multiValue = ospfObjResponse.json()['networkType']
            self.patch(self.httpHeader+multiValue+"/singleValue", data={'value': kwargs['networkType']})

        if 'deadInterval' in kwargs:
            multiValue = ospfObjResponse.json()['deadInterval']
            self.patch(self.httpHeader+multiValue+"/singleValue", data={'value': kwargs['deadInterval']})

        self.configuredProtocols.append(ospfObj)
        return ospfObj

    def configBgp(self, obj, **kwargs):
        """
        Description
            Create or modify BGP.  If creating a new BGP header, provide an IPv4 object handle.
            If modifying a BGP header, provide the BGP object handle.

        Parameters
            IPv4 object handle example:
               obj: /api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv4/1

            BGP object handle example:
               obj: /api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv4/1/bgpIpv4Peer/1

        Example:
            createBgp(obj,
                  name = 'bgp_1',
                  enableBgp = True,
                  holdTimer = 90,
                  dutIp={'start': '1.1.1.2', 'direction': 'increment', 'step': '0.0.0.0'},
                  localAs2Bytes=101,
                  enableGracefulRestart = False,
                  restartTime = 45,
                  type = 'internal',
                  enableBgpIdSameasRouterId = True,
                  staleTime = 0,
                  flap = ['false', 'false', 'false', 'false']

        # flap = true or false.  Provide a list of total true or false according to the total amount of host IP interfaces.
        """

        if 'bgp' not in obj:
            bgpUrl = self.httpHeader+obj+'/bgpIpv4Peer'
            response = self.post(bgpUrl)
            # /api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv4/1/bgpIpv4Peer/1
            bgpObj = response.json()['links'][0]['href']

        if 'bgp' in obj:
            bgpObj = obj

        bgpObjResponse = self.get(self.httpHeader+bgpObj)

        if 'enableBgp' in kwargs and kwargs['enableBgp'] == True:
            multiValue = bgpObjResponse.json()['enableBgpId']
            self.patch(self.httpHeader+multiValue+"/singleValue", data={'value': True})

        if 'name' in kwargs:
            self.patch(self.httpHeader+bgpObj, data={'name': kwargs['name']})

        if 'holdTimer' in kwargs:
            multiValue = bgpObjResponse.json()['holdTimer']
            self.patch(self.httpHeader+multiValue+"/singleValue", data={'value': kwargs['holdTimer']})

        if 'dutIp' in kwargs:
            multiValue = bgpObjResponse.json()['dutIp']
            self.patch(self.httpHeader+multiValue+"/counter",
                       data={'start': kwargs['dutIp']['start'],
                             'direction': kwargs['dutIp']['start'],
                             'step': kwargs['dutIp']['start']})

        if 'localAs2Bytes' in kwargs:
            multiValue = bgpObjResponse.json()['localAs2Bytes']
            self.patch(self.httpHeader+multiValue+"/singleValue", data={'value': kwargs['localAs2Bytes']})

        if 'enableGracefulRestart' in kwargs:
            multiValue = bgpObjResponse.json()['enableGracefulRestart']
            self.patch(self.httpHeader+multiValue+"/singleValue", data={'value': kwargs['enableGracefulRestart']})

        if 'restartTime' in kwargs:
            multiValue = bgpObjResponse.json()['restartTime']
            self.patch(self.httpHeader+multiValue+"/singleValue", data={'value': kwargs['restartTime']})

        if 'type' in kwargs:
            multiValue = bgpObjResponse.json()['type']
            self.patch(self.httpHeader+multiValue+"/singleValue", data={'value': kwargs['type']})

        if 'enableBgpIdSameasRouterId' in kwargs:
            multiValue = bgpObjResponse.json()['enableBgpIdSameasRouterId']
            self.patch(self.httpHeader+multiValue+"/singleValue", data={'value': kwargs['enableBgpIdSameasRouterId']})

        if 'staleTime' in kwargs:
            multiValue = bgpObjResponse.json()['staleTime']
            self.patch(self.httpHeader+multiValue+"/singleValue", data={'value': kwargs['staleTime']})

        if 'flap' in kwargs:
            multiValue = bgpObjResponse.json()['flap']
            self.patch(self.httpHeader+multiValue+"/singleValue", data={'value': kwargs['flap']})

        self.configuredProtocols.append(bgpObj)
        return bgpObj

    def configVxlanNgpf(self, obj, **kwargs):
        """
        Description
            Create or modify a VXLAN.  If creating a new VXLAN header, provide an IPv4 object handle.
            If modifying a VXLAN header, provide the VXLAN object handle.


        Parameters
            IPv4 object handle example:
               obj: /api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv4/1

            VXLAN object handle example:
               obj: /api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv4/vxlan/1

        Example:
            createVxlanNgpf(ipv4Object='/api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv4/1',
                        vtepName='vtep_1',
                        vtepVni={'start':2008, 'step':2, 'direction':'increment'},
                        vtepIpv4Multicast={'start':'225.8.0.1', 'step':'0.0.0.1', 'direction':'increment'})

         start = The starting value
         step  = 0 means don't increment or decrement.
                 For IP step = 0.0.0.1.  Increment on the last octet.
                               0.0.1.0.  Increment on the third octet.
         direction = increment or decrement the starting value.
        """
        if 'vxlan' not in obj:
            response = self.post(self.httpHeader+obj+'/vxlan')
            vxlanId = response.json()['links'][0]['href']
            self.logInfo('\ncreateVxlanNgpf: %s' % vxlanId)

        if 'vxlan' in obj:
            vxlanId = obj

        # Get VxLAN metadatas
        vxlanResponse = self.get(self.httpHeader+vxlanId)

        for key,value in kwargs.items():
            self.logInfo('key:%s = %s' % (key,value))

            if key == 'vtepName':
                self.patch(self.httpHeader+vxlanId, data={'name': value})

            if key == 'vtepVni':
                multivalue = vxlanResponse.json()['vni']
                self.patch(self.httpHeader+multivalue+'/counter',
                           data={'start':kwargs['vtepVni']['start'],
                                 'step':kwargs['vtepVni']['step'],
                                 'direction':kwargs['vtepVni']['direction']})

            if key == 'vtepIpv4Multicast':
                multivalue = vxlanResponse.json()['ipv4_multicast']
                self.patch(self.httpHeader+multivalue+'/counter',
                        data={'start':kwargs['vtepIpv4Multicast']['start'],
                              'step':kwargs['vtepIpv4Multicast']['step'],
                              'direction':kwargs['vtepIpv4Multicast']['direction']})

        self.configuredProtocols.append(vxlanId)
        return vxlanId

    def configNetworkGroup(self, deviceGroupObj, **kwargs):
        """
        Description
            Create a Network Group for network advertisement.

        Parameters
            deviceGroupObj: /api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1

        Example:
            configNetworkGroup(dgObj,
                       name='networkGroup1',
                       multiplier = 100,
                       networkAddress = {'start': '160.1.0.0', 'step': '0.0.0.1', 'direction': 'increment'},
                       prefixLength = 24)
        """
        if 'networkGroupObj' not in kwargs:
            response = self.post(self.httpHeader+deviceGroupObj+'/networkGroup')
            networkGroupObj = response.json()['links'][0]['href']

        if 'networkGroupObj' in kwargs:
            networkGroupObj = kwargs['networkGroupObj']

        self.logInfo('\nconfigNetworkGroup: %s' % networkGroupObj)
        if 'name' in kwargs:
            self.patch(self.httpHeader+networkGroupObj, data={'name': kwargs['name']})

        if 'multiplier' in kwargs:
            self.patch(self.httpHeader+networkGroupObj, data={'multiplier': kwargs['multiplier']})

        if 'networkAddress' in kwargs:
            response = self.post(self.httpHeader+networkGroupObj+'/ipv4PrefixPools')
            prefixPoolObj = self.httpHeader + response.json()['links'][0]['href']

            # prefixPoolId = /api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/networkGroup/3/ipv4PrefixPools/1
            ipv4PrefixResponse = self.get(prefixPoolObj)

            if 'networkAddress' in kwargs:
                multiValue = ipv4PrefixResponse.json()['networkAddress']
                self.patch(self.httpHeader+multiValue+"/counter",
                           data={'start': kwargs['networkAddress']['start'],
                                 'step': kwargs['networkAddress']['step'],
                                 'direction': kwargs['networkAddress']['direction']})

            if 'prefixLength' in kwargs:
                multiValue = ipv4PrefixResponse.json()['prefixLength']
                self.patch(self.httpHeader+multiValue+"/singleValue",
                           data={'value': kwargs['prefixLength']})

        return prefixPoolObj

    def configTrafficItem(self, mode=None, obj=None, trafficItem=None, endpoints=None, configElements=None):
        """
        Description
            Create or modify a Traffic Item.

            When creating a new Traffic Item, this API will return 3 object handles:
                 trafficItemObj, endpointSetObjList and configElementObjList

            NOTE:
                Each Traffic Item could create multiple endpoints and for each endpoint,
                you could provide a list of configElements for each endpoint.
                The endpoints and configElements must be in a list.

        If mode is create:
            The required parameters are: mode, trafficItem, endpoints and configElements

        If mode is modify:
            The required parameters are: mode, obj, and one of (trafficIem, endpoints or configElements).

        If mode is modify, you need to provide the right object handle.

            To modify trafficItem:
                  Ex: /api/v1/sessions/1/ixnetwork/traffic/trafficItem/1

            To modify endpointSet:
                  Ex: /api/v1/sessions/1/ixnetwork/traffic/trafficItem/1/endpointSet/1

            To modify configElements = configElement object handle
                  Ex: /api/v1/sessions/1/ixnetwork/traffic/trafficItem/1/configElement/1

            Look at sample script l2l3RestNgpy.py

        Traffic Item Parameters
            trafficType options:
               raw, ipv4, ipv4, ethernetVlan, frameRelay, atm, fcoe, fc, hdlc, ppp

            srcDestMesh:
               Defaults to one-to-one
               Options: manyToMany or fullMesh

            routeMesh:
               fullMesh or oneToOne

            allowSelfDestined: True or False

        ConfigElement Parameters
            transmissionType:
               - continuous, fixedFrameCount
               - custom (for burstPacketCount)
            frameCount: (For continuous and fixedFrameCount traffic)
            burstPacketCount: (For bursty traffic)

            frameRate: The rate to transmit packets
            frameRateType: percentLineRate or framesPerSecond
            trackBy: put in a list:

        Endpoints Parameters
            A list of topology, deviceGroup or protocol objects
                sources: Object in a list.
                destinations: Object in a lsit.

            Example:
               ['/api/v1/sessions/1/ixnetwork/topology/8']
               or a list ['.../topology/1', '.../topology/3']
               ['.../topology/1/deviceGroup/1', '.../topology/2/deviceGroup/1/ethernet/1/ipv4/1']

        USAGE EXAMPLE:
            To create new Traffic Item:
            configTrafficItem(sessionUrl,
                              mode='create',
                              trafficItem = {
                                  'name':'Topo1 to Topo2',
                                  'trafficType':'ipv4',
                                  'biDirectional':True,
                                  'srcDestMesh':'one-to-one',
                                  'routeMesh':'oneToOne',
                                  'allowSelfDestined':False,
                                  'trackBy': ['flowGroup0', 'vlanVlanId0']},
                               endpoints = [{'name':'Flow-Group-1',
                                             'sources': [topologyObj1],
                                             'destinations': [topologyObj2]}],
                               configElements = [{'transmissionType': 'fixedFrameCount',
                                                  'frameCount': 50000,
                                                  'frameRate': 88,
                                                  'frameRateType': 'percentLineRate',
                                                  'frameSize': 128}])

        For bursty packet count,
              transmissionType = 'custom',
              burstPacketCount = 50000,

        Return: trafficItemObj, endpointSetObjList, configElementObjList
        """
        if mode == 'create':
            trafficItemUrl = self.sessionUrl+'/traffic/trafficItem'
        if mode == 'modify' and obj is None:
            raise IxNetRestApiException('Modifying Traffic Item requires a Traffic Item object')
        if mode == 'create' and trafficItem is None:
            raise IxNetRestApiException('Creating Traffic Item requires trafficItem kwargs')
        if mode == None:
            raise IxNetRestApiException('configTrafficItem Error: Must include mode: config or modify')

        # Create a new Traffic Item
        if mode == 'create' and trafficItem != None:
            if 'trackBy' in trafficItem:
                trackBy = trafficItem['trackBy']
                del trafficItem['trackBy']

            self.logInfo('\nconfigTrafficItem: %s : %s' % (trafficItemUrl, trafficItem))
            response = self.post(trafficItemUrl, data=trafficItem)
            trafficItemObj = response.json()['links'][0]['href']

        if mode == 'modify' and trafficItem != None:
            trafficItemObj = obj
            if 'trackBy' in trafficItem:
                trafficItemObj = self.httpHeader+trafficItemObj+'/tracking'
            self.patch(self.httpHeader+trafficItemObj, data=trafficItem)

        # Create Endpoints
        if mode == 'create' and endpoints != None:
            if type(endpoints) != list:
                raise IxNetRestApiException('configTrafficItem error: Please provide endpoints in a list')

            endpointSetObjList = []
            if 'trafficItemObj' not in locals():
                # Expect the user to pass in the endpoint object handle correctly and parse
                # out the traffic item object handle.
                trafficItemObj = self.sessionUrl.split('/endpointSet')[0]

            for eachEndPoint in endpoints:
                response = self.post(self.httpHeader+trafficItemObj+'/endpointSet', data=eachEndPoint)

                # Get the RETURNED endpointSet/# object
                endpointSetObj = response.json()['links'][0]['href']
                response = self.get(self.httpHeader+endpointSetObj)

                # This endpontSet ID is used for getting the corresponding Config Element ID
                # in case there are multiple endpoint sets created.
                endpointSetId = response.json()['id']
                endpointSetObjList.append(endpointSetObj)

        if mode == 'modify' and endpoints != None:
            endpointSetObj = obj
            self.patch(self.httpHeader+endpointSetObj, data=endpoints)

        if configElements is not None:
            if mode == 'create' and type(configElements) != list:
                raise IxNetRestApiException('configTrafficItem error: Please provide configElements in a list')

            if mode == 'modify':
                configElementObj = obj
                self.configConfigElements(self.httpHeader+configElementObj, configElements)

            if mode == 'create':
                endpointResponse = self.get(self.httpHeader+trafficItemObj+'/endpointSet')

                index = 0
                configElementCounter = 1
                configElementObjList = []
                for eachEndpoint in endpointResponse.json():
                    configElementObj = trafficItemObj+'/configElement/'+str(configElementCounter)
                    configElementObjList.append(configElementObj)
                    self.configConfigElements(self.httpHeader+configElementObj, configElements[index])
                    if len(endpointSetObjList) == len(configElements):
                        index += 1
                    configElementCounter += 1

        # Cannot configure tracking until endpoints are created. This is why
        # tracking config is at the end here.
        if mode == 'create' and 'trackBy' in locals():
            self.patch(self.httpHeader+trafficItemObj+'/tracking', data={'trackBy': trackBy})

        if mode == 'create' and trafficItem != None:
            return [trafficItemObj, endpointSetObjList, configElementObjList]

    def configConfigElements(self, configElementObj, configElements):
        if 'transmissionType' in configElements:
            self.patch(configElementObj+'/transmissionControl', data={'type': configElements['transmissionType']})

        if 'burstPacketCount' in configElements:
            self.patch(configElementObj+'/transmissionControl', data={'burstPacketCount': int(configElements['burstPacketCount'])})

        if 'frameCount' in configElements:
            self.patch(configElementObj+'/transmissionControl', data={'frameCount': int(configElements['frameCount'])})

        if 'duration' in configElements:
            self.patch(configElementObj+'/transmissionControl', data={'duration': int(configElements['duration'])})

        if 'frameRate' in configElements:
            self.patch(configElementObj+'/frameRate', data={'rate': int(configElements['frameRate'])})

        if 'frameRateType' in configElements:
            self.patch(configElementObj+'/frameRate', data={'type': configElements['frameRateType']})

        if 'frameSize' in configElements:
            self.patch(configElementObj+'/frameSize', data={'fixedSize': int(configElements['frameSize'])})

    def getTransmissionType(self, configElement):
        # configElement: /api/v1/sessions/1/ixnetwork/traffic/trafficItem/1/configElement/1
        # Returns: fixedFrameCount, continuous

        response = self.get(self.httpHeader+configElement+'/transmissionControl')
        return response.json()['type']

    def configTrafficLatency(self, enabled=True, mode='storeForward'):
        # enabled = True False
        # mode    = storeForward cutThrough forwardDelay mef
        self.patch(self.sessionUrl+'/traffic/statistics/latency', data={'enabled':enabled, 'mode':mode})

    def showProtocolTemplates(self, configElementObj):
        """
        Description
           To show all the protocol template options. Mainly used for adding a protocol header
           to Traffic Item packets.

        Parameters
           configElementObj: /api/v1/sessions/1/ixnetwork/traffic/trafficItem/{id}/configElement/{id}
        """

        # Get a list of all the protocol templates:
        response = self.get(self.sessionUrl+'/traffic/protocolTemplate?skip=0&take=end')
        for eachProtocol in response.json()['data']:
            self.logInfo('%s: %s' % (eachProtocol['id'], eachProtocol['displayName']))

    def showTrafficItemPacketStack(self, configElementObj):
        """
        Description
           Display a list of the current packet stack in a Traffic Item

           1: Ethernet II
           2: VLAN
           3: IPv4
           4: UDP
           5: Frame Check Sequence CRC-32

        Parameters
           configElementObj: /api/v1/sessions/1/ixnetwork/traffic/trafficItem/{id}/configElement/{id}
       """
        print()
        response = self.get(self.httpHeader+configElementObj+'/stack')
        for (index, eachHeader) in enumerate(response.json()):
            self.logInfo('%s: %s' % (str(index+1), eachHeader['displayName']))

    def addTrafficItemPacketStack(self, configElementObj, protocolStackNameToAdd, stackNumber, action='append'):
        """
        Description
           To either append or insert a protocol stack to an existing packet.

           You must know the exact name of the protocolTemplate to add by calling
           showProtocolTemplates() API and get the exact name  as a value for the parameter protocolStackNameToAdd.

           You must also know where to add the new packet header stack.  Use showTrafficItemPacketStack() to see
           your current stack numbers.

           This API returns the protocol stack object handle so you could use it to config its settings.

         Parameters
           configElementObj: /api/v1/sessions/1/ixnetwork/traffic/trafficItem/{id}/configElement/{id}

           action:
               append: To add after the specified stackNumber
               insert: To add before the specified stackNumber

           protocolStackNameToAdd: The name of the protocol stack to add.  To get a list of options,
                                   use API showProtocolTemplates().
                                   Some common ones: MPLS, IPv4, TCP, UDP, VLAN, IGMPv1, IGMPv2, DHCP, VXLAN

           stackNumber: The stack number to append or insert into.
                        Use showTrafficItemPacketStack() to view the packet header stack in order to know
                        which stack number to insert your new stack before or after the stack number.

        Example:
            addTrafficItemPacketStack(configElement, protocolStackNameToAdd='UDP',
                                      stackNumber=3, action='append', apiKey=apiKey, verifySslCert=False

        Returns:
            /api/v1/sessions/1/ixnetwork/traffic/trafficItem/{id}/configElement/{id}/stack/{id}

        """

        if action == 'append':
            action = 'appendprotocol'
        if action == 'insert':
            action = 'insertprotocol'

        # /api/v1/sessions/1
        match = re.match('http.*(/api.*sessions/[0-9]).*', self.sessionUrl)
        if match:
            apiHeader = match.group(1)

        # /api/v1/sessions/1/ixnetwork/traffic/trafficItem/1/configElement/1
        arg1 = configElementObj+'/stack/' + str(stackNumber)

        # Display a list of the current packet stack
        response = self.get(self.httpHeader+configElementObj+'/stack')
        for (index, eachHeader) in enumerate(response.json()):
            self.logInfo('{0}: {1}'.format(index+1, eachHeader['displayName']))

        # Get a list of all the protocol templates:
        response = self.get(self.sessionUrl+'/traffic/protocolTemplate?skip=0&take=end')

        protocolTemplateId = None
        for eachProtocol in response.json()['data']:
            if bool(re.match('^%s$' % protocolStackNameToAdd, eachProtocol['displayName'].strip(), re.I)):
                # /api/v1/sessions/1/traffic/protocolTemplate/30
                protocolTemplateId =  eachProtocol['links'][0]['href']

        if protocolTemplateId == None:
            raise IxNetRestApiException('No such protocolTemplate name found: {0}'.format(protocolStackNameToAdd))
        self.logInfo('\nprotocolTemplateId: %s' % protocolTemplateId)
        data = {'arg1': arg1, 'arg2': protocolTemplateId}
        response = self.post(self.httpHeader+configElementObj+'/stack/operations/%s' % action, data=data)

        if self.waitForComplete(response, self.httpHeader+configElementObj+'/stack/operations/appendprotocol/'+response.json()['id']) == 1:
            raise IxNetRestApiException

        # /api/v1/sessions/1/ixnetwork/traffic/trafficItem/1/configElement/1/stack/4
        self.logInfo('\naddTrafficItemPacketStack: Returning: %s' % response.json()['result'])
        return response.json()['result']

    def showTrafficItemStackLinks(self, configElementObj):
        # Return a list of configured Traffic Item packet header in sequential order.
        #   1: Ethernet II
        #   2: MPLS
        #   3: MPLS
        #   4: MPLS
        #   5: MPLS
        #   6: IPv4
        #   7: UDP
        #   8: Frame Check Sequence CRC-32

        stackList = []
        response = self.get(self.httpHeader+configElementObj+'/stackLink')
        self.logInfo('\n')
        for eachStackLink in response.json():
            if eachStackLink['linkedTo'] != 'null':
                self.logInfo(eachStackLink['linkedTo'])
                stackList.append(eachStackLink['linkedTo'])
        return stackList

    def getPacketHeaderStackIdObj(self, configElementObj, stackId):
        """
        Desciption
           This API should be called after calling showTrafficItemPacketStack(configElementObj) in
           order to know the stack ID number to use.  Such as ...
            Stack1: Ethernet II
            Stack2: MPLS
            Stack3: MPLS
            Stack4: MPLS
            Stack5: MPLS
            Stack6: IPv4
            Stack7: UDP
            Stack8: Frame Check Sequence CRC-32

        Parameters
           configElementObj: /api/v1/sessions/1/ixnetwork/traffic/trafficItem/{id}/configElement/{id}
           stackId: In this example, IPv4 stack ID is 6.

         Return stack ID object: /api/v1/sessions/1/ixnetwork/traffic/trafficItem/{id}/configElement/{id}/stack/{id}
        """

        response = self.get(self.httpHeader+configElementObj+'/stack')
        for (index, eachHeader) in enumerate(response.json()):
            self.logInfo('{0}: {1}'.format(index+1, eachHeader['displayName']))
            if stackId == index+1:
                self.logInfo('\tReturning: %s' % self.httpHeader+eachHeader['links'][0]['href'])
                return eachHeader['links'][0]['href']

    def modifyTrafficItemDestMacAddress(self, trafficItemName, destMacAddress):
        trafficItemObj = self.getTrafficItemObjByName(trafficItemName)
        response = self.get(self.httpHeader+trafficItemObj)
        if response.json()['trafficType'] != 'raw':
            raise IxNetRestApiException('Traffic Item is not Raw type. Cannot modify Traffic Item: %s' % trafficItemName)

        configElementObj = trafficItemObj+'/configElement/1'
        stackObj = self.getPacketHeaderStackIdObj(configElementObj, stackId=1)
        self.configPacketHeaderField(stackObj,
                                    fieldName='Destination MAC Address',
                                    data={'valueType': 'increment',
                                        'startValue': destMacAddress,
                                        'stepValue': '00:00:00:00:00:00',
                                        'countValue': 1,
                                        'auto': False})

    def showPacketHeaderFieldNames(self, stackObj):
        """
        Description
           Get all the packet header field names.

        Parameters
           stackObj = /api/v1/sessions/1/ixnetwork/traffic/trafficItem/{id}/configElement/{id}/stack/{id}

        Example for Ethernet stack field names
           1: Destination MAC Address
           2: Source MAC Address
           3: Ethernet-Type
           4: PFC Queue
        """

        self.logInfo('\ngetPacketHeaderFieldNames: %s' % stackObj+'/field')
        response = self.get(self.httpHeader+stackObj+'/field')
        for eachField in  response.json():
            id = eachField['id']
            fieldName = eachField['displayName']
            self.logInfo('\t{0}: {1}'.format(id, fieldName))

    def convertTrafficItemToRaw(self, trafficItemName):
        """
        Description

        Parameter
        """
        trafficItemObj = self.getTrafficItemObjByName(trafficItemName)
        if trafficItemObj == 0:
            raise Exception('\nNo such Traffic Item name: %s' % trafficItemName)
        self.post(self.sessionUrl+'/traffic/trafficItem/operations/converttoraw', data={'arg1': trafficItemObj})

    def configPacketHeaderField(self, stackIdObj, fieldName, data):
        """
        Desciption
            Configure raw packets in a Traffic Item.
            In order to know the field names to modify, use getPacketHeaderFieldNames() to display the names:

        stackIdObj: /api/v1/sessions/1/ixnetwork/traffic/trafficItem/{id}/configElement/{id}/stack/{id}
        fieldName: The name of the field name in the packet header stack to modify.
                   You could use getPacketHeaderFieldNames(stackObj) API to dispaly your options
        data: Example:
             data={'valueType': 'valueList', 'valueList': ['1001', '1002'], auto': False}
             data={'valueType': 'increment', 'startValue': '1.1.1.1', 'stepValue': '0.0.0.1', 'countValue': 2}
             data={'valueType': 'increment', 'startValue': '00:01:01:01:00:01', 'stepValue': '00:00:00:00:00:01'}
             data={'valueType': 'increment', 'startValue': 1001, 'stepValue': 1, 'countValue': 2, 'auto': False}
        """
        fieldId = None
        # Get the field ID object by the user defined fieldName
        response = self.get(self.httpHeader+stackIdObj+'/field')
        for eachFieldId in response.json():
            if bool(re.match(fieldName, eachFieldId['displayName'], re.I)):
                fieldId = eachFieldId['id']

        if fieldId == None:
            raise IxNetRestApiException('Failed to located your provided fieldName:', fieldName)

        self.logInfo('\nconfigPacketHeaderFieldId:  fieldIdObj: %s' % stackIdObj+'/field/'+str(fieldId))
        response = self.patch(self.httpHeader+stackIdObj+'/field/'+str(fieldId), data=data)

    def configEgressCustomTracking(self, trafficItemObj, offsetBits, widthBits):
        """
        Description
           Configuring custom egress tracking. User must know the offset and the bits width to track.
           In most use cases, packets ingressing the DUT gets modified by the DUT and to track the
           correctness of the DUT's packet modification, use this API to verify the receiving port's packet
           offset and bit width.
        """
        # Safety check: Apply traffic or else configuring egress tracking won't work.
        self.applyTraffic()
        self.patch(self.httpHeader+trafficItemObj+'/tracking/egress',
                   data={'encapsulation': 'Any: Use Custom Settings',
                         'customOffsetBits': offsetBits,
                         'customWidthBits': widthBits
                     })
        self.patch(self.httpHeader+trafficItemObj, data={'egressEnabled': True})
        self.regenerateTrafficItems()
        self.applyTraffic()

    def createEgressStatView(self, trafficItemObj, egressTrackingPort, offsetBit, bitWidth,
                             egressStatViewName='EgressStatView', ingressTrackingFilterName=None):
        """
        Description
           Create egress statistic view for egress stats.

        """
        egressTrackingOffsetFilter = 'Custom: ({0}bits at offset {1})'.format(int(bitWidth), int(offsetBit))
        trafficItemName = self.getTrafficItemName(trafficItemObj)

        # Get EgressStats
        # Create Egress Stats
        self.logInfo('\nCreating new statview for egress stats...')
        response = self.post(self.sessionUrl+'/statistics/view',
                             data={'caption': egressStatViewName,
                                   'treeViewNodeName': 'Egress Custom Views',
                                   'type': 'layer23TrafficFlow',
                                   'visible': True})

        egressStatView = response.json()['links'][0]['href']
        self.logInfo('\negressStatView Object: %s' % egressStatView)
        # /api/v1/sessions/1/ixnetwork/statistics/view/12

        self.logInfo('\nCreating layer23TrafficFlowFilter')
        # Dynamically get the PortFilterId
        response = self.get(self.httpHeader+egressStatView+'/availablePortFilter')
        portFilterId = []
        for eachPortFilterId in response.json():
            #192.168.70.10/Card2/Port1
            self.logInfo('\tAvailable PortFilterId: %s' % eachPortFilterId['name'])
            if eachPortFilterId['name'] == egressTrackingPort:
                self.logInfo('\tLocated egressTrackingPort: %s' % egressTrackingPort)
                portFilterId.append(eachPortFilterId['links'][0]['href'])
                break
        if portFilterId == []:
            raise IxNetRestApiException('No port filter ID found')
        self.logInfo('\nPortFilterId: %s' % portFilterId)

        # Dynamically get the Traffic Item Filter ID
        response = self.get(self.httpHeader+egressStatView+'/availableTrafficItemFilter')
        availableTrafficItemFilterId = []
        for eachTrafficItemFilterId in response.json():
            if eachTrafficItemFilterId['name'] == trafficItemName:
                availableTrafficItemFilterId.append(eachTrafficItemFilterId['links'][0]['href'])
                break
        if availableTrafficItemFilterId == []:
            raise IxNetRestApiException('No traffic item filter ID found.')

        self.logInfo('\navailableTrafficItemFilterId: %s' % availableTrafficItemFilterId)
        # /api/v1/sessions/1/ixnetwork/statistics/view/12
        self.logInfo('\negressStatView: %s' % egressStatView)
        layer23TrafficFlowFilter = self.httpHeader+egressStatView+'/layer23TrafficFlowFilter'
        self.logInfo('\nlayer23TrafficFlowFilter: %s' % layer23TrafficFlowFilter)
        response = self.patch(layer23TrafficFlowFilter,
                              data={'egressLatencyBinDisplayOption': 'showEgressRows',
                                    'trafficItemFilterId': availableTrafficItemFilterId[0],
                                    'portFilterIds': portFilterId,
                                    'trafficItemFilterIds': availableTrafficItemFilterId})

        # Get the egress tracking filter
        egressTrackingFilter = None
        ingressTrackingFilter = None
        response = self.get(self.httpHeader+egressStatView+'/availableTrackingFilter')
        self.logInfo('\nAvailable tracking filters for both ingress and egress...')
        for eachTrackingFilter in response.json():
            self.logInfo('\tFilter Name: {0}: {1}'.format(eachTrackingFilter['id'], eachTrackingFilter['name']))
            if bool(re.match('Custom: *\([0-9]+ bits at offset [0-9]+\)', eachTrackingFilter['name'])):
                egressTrackingFilter = eachTrackingFilter['links'][0]['href']

            if ingressTrackingFilterName is not None:
                if eachTrackingFilter['name'] == ingressTrackingFilterName:
                    ingressTrackingFilter = eachTrackingFilter['links'][0]['href']

        if egressTrackingFilter is None:
            raise IxNetRestApiException('Failed to locate your defined custom offsets: {0}'.format(egressTrackingOffsetFilter))

        # /api/v1/sessions/1/ixnetwork/statistics/view/23/availableTrackingFilter/3
        self.logInfo('\nLocated egressTrackingFilter: %s' % egressTrackingFilter)
        enumerationFilter = layer23TrafficFlowFilter+'/enumerationFilter'
        response = self.post(enumerationFilter,
                             data={'sortDirection': 'ascending',
                                   'trackingFilterId': egressTrackingFilter})

        if ingressTrackingFilterName is not None:
            self.logInfo('\nLocated ingressTrackingFilter: %s' % egressTrackingFilter)
            response = self.post(enumerationFilter,
                                 data={'sortDirection': 'ascending',
                                       'trackingFilterId': ingressTrackingFilter})

        # Must enable one or more egress statistic counters in order to enable the
        # egress tracking stat view object next.
        #   Enabling: ::ixNet::OBJ-/statistics/view:"EgressStats"/statistic:"Tx Frames"
        #   Enabling: ::ixNet::OBJ-/statistics/view:"EgressStats"/statistic:"Rx Frames"
        #   Enabling: ::ixNet::OBJ-/statistics/view:"EgressStats"/statistic:"Frames Delta"
        #   Enabling: ::ixNet::OBJ-/statistics/view:"EgressStats"/statistic:"Loss %"
        response = self.get(self.httpHeader+egressStatView+'/statistic')
        for eachEgressStatCounter in response.json():
            eachStatCounterObject = eachEgressStatCounter['links'][0]['href']
            eachStatCounterName = eachEgressStatCounter['caption']
            self.logInfo('\tEnabling egress stat counter: %s' % eachStatCounterName)
            self.patch(self.httpHeader+eachStatCounterObject, data={'enabled': True})

        self.patch(self.httpHeader+egressStatView, data={'enabled': True})
        self.logInfo('\ncreateEgressCustomStatView: Done')
        return egressStatView

    def removeAllTclViews(self):
        """
        Description
           Removes all the additional created stat views.
        """
        removeAllTclViewsUrl = self.sessionUrl+'/operations/removealltclviews'
        response = self.post(removeAllTclViewsUrl)
        if self.waitForComplete(response, removeAllTclViewsUrl+'/'+response.json()['id']) == 1:
            raise IxNetRestApiException

    def enableTrafficItem(self, trafficItemNumber):
        url = self.sessionUrl+'/traffic/trafficItem/%s' % str(trafficItemNumber)
        response = self.patch(url, data={"enabled": "true"})

    def disableTrafficItem(self, trafficItemNumber):
        url = self.sessionUrl+'/traffic/trafficItem/%s' % str(trafficItemNumber)
        response = self.patch(url, data={"enabled": "false"})

    def isTrafficItemNameExists(self, trafficItemName):
        """
        Description
           Verify if the Traffic Item name exists in the configuration.

        Parameter
           trafficItemName: The Traffic Item name to verify
        """

        trafficItemNameExists = False
        response = self.get(self.sessionUrl+'/traffic/trafficItem')
        for eachTrafficItem in response.json():
            if eachTrafficItem['name'] == trafficItemName:
                return True
        return False

    def enablePacketLossDuration(self):
        self.patch(self.sessionUrl+'/traffic/statistics/packetLossDuration', data={'enabled': 'true'})

    def disablePacketLossDuration(self):
        self.patch(self.sessionUrl+'/traffic/statistics/packetLossDuration', data={'enabled': 'false'})

    def checkTrafficState(self, expectedState=['stopped'], timeout=45):
        """
        Description
            Check the traffic state for the expected state.
            This is best used to verify that traffic has started before calling getting stats.

        Traffic states are:
            startedWaitingForStats, startedWaitingForStreams, started, stopped,
            stoppedWaitingForStats, txStopWatchExpected, locked, unapplied

        Parameters
            expectedState = Input a list of expected traffic state.
                            Example: ['started', startedWaitingForStats'] <-- This will wait until stats has arrived.

            timeout = The amount of seconds you want to wait for the expected traffic state.
                      Defaults to 45 seconds.
                      In a situation where you have more than 10 pages of stats, you will
                      need to increase the timeout time.
        """
        if type(expectedState) != list:
            expectedState.split(' ')

        self.logInfo('\nExpecting traffic state: {0}\n'.format(expectedState))
        for counter in range(1,timeout+1):
            response = self.get(self.sessionUrl+'/traffic', silentMode=True)
            currentTrafficState = response.json()['state']
            self.logInfo('checkTrafficState: {trafficState}: Waited {counter}/{timeout} seconds'.format(
                trafficState=currentTrafficState,
                counter=counter,
                timeout=timeout))
            if counter < timeout and currentTrafficState not in expectedState:
                time.sleep(1)
                continue
            if counter < timeout and currentTrafficState in expectedState:
                time.sleep(8)
                self.logInfo('\ncheckTrafficState: Done\n')
                return 0

        raise IxNetRestApiException('checkTrafficState: Traffic state did not reach the expected state(s):', expectedState)

    def getStats(self, viewObject=None, viewName='Flow Statistics', csvFile=None, csvEnableFileTimestamp=False, displayStats=True,
                 silentMode=True, ignoreError=False):
        """
        Description
            Get stats by the statistic name or get stats by providing a view object handle.

        Parameters
            csvFile = None or <filename.csv>.
                      None will not create a CSV file.
                      Provide a <filename>.csv to record all stats to a CSV file.
                      Example: getStats(sessionUrl, csvFile='Flow_Statistics.csv')

            csvEnableFileTimestamp = True or False. If True, timestamp will be appended to the filename.

            displayStats: True or False. True=Display stats.

            ignoreError: True or False.  Returns None if viewName is not found.

            viewObject: The view object: http://{apiServerIp:port}/api/v1/sessions/2/ixnetwork/statistics/view/13
                        A view object handle could be obtained by calling getViewObject().

            viewName options (Not case sensitive):
               NOTE: Not all statistics are listed here.
                  You could get the statistic viewName directly from the IxNetwork GUI in the statistics.

            'Port Statistics'
            'Tx-Rx Frame Rate Statistics'
            'Port CPU Statistics'
            'Global Protocol Statistics'
            'Protocols Summary'
            'Port Summary'
            'BGP Peer Per Port'
            'OSPFv2-RTR Drill Down'
            'OSPFv2-RTR Per Port'
            'IPv4 Drill Down'
            'L2-L3 Test Summary Statistics'
            'Flow Statistics'
            'Traffic Item Statistics'
            'IGMP Host Drill Down'
            'IGMP Host Per Port'
            'IPv6 Drill Down'
            'MLD Host Drill Down'
            'MLD Host Per Port'
            'PIMv6 IF Drill Down'
            'PIMv6 IF Per Port'
            'Flow View'

         Note: Not all of the viewNames are listed here. You have to get the exact names from
               the IxNetwork GUI in statistics based on your protocol(s).

         Return a dictionary of all the stats: statDict[rowNumber][columnName] == statValue
           Get stats on row 2 for 'Tx Frames' = statDict[2]['Tx Frames']
        """
        if viewObject == None:
            viewList = self.get('%s/%s/%s' % (self.sessionUrl, 'statistics', 'view'), silentMode=silentMode)
            views = ['%s/%s/%s/%s' % (self.sessionUrl, 'statistics', 'view', str(i['id'])) for i in viewList.json()]
            if silentMode is False:
                self.logInfo('\ngetStats: Searching for viewObj for viewName: %s' % viewName)
            for view in views:
                # GetAttribute
                response = self.get('%s' % view, silentMode=silentMode)
                captionMatch = re.match(viewName, response.json()['caption'], re.I)
                if captionMatch:
                    # viewObj: sessionUrl + /statistics/view/11'
                    viewObject = view
                    break

            if viewObject == None and ignoreError == False:
                raise IxNetRestApiException("viewObj wasn't found for viewName: %s" % viewName)
            if viewObject == None and ignoreError == True:
                return None

        if silentMode is False:
            self.logInfo('\nviewObj: %s' % viewObject)

        for counter in range(0,31):
            response = self.get(viewObject+'/page', silentMode=silentMode)
            totalPages = response.json()['totalPages']
            if totalPages == 'null':
                self.logInfo('\nGetting total pages is not ready yet. Waiting %d/30 seconds' % counter)
                time.sleep(1)
            if totalPages != 'null':
                break
            if totalPages == 'null' and counter == 30:
                self.logInfo('\ngetStats failed: Getting total pages')
                return 1

        if csvFile != None:
            import csv
            csvFileName = csvFile.replace(' ', '_')
            if csvEnableFileTimestamp:
                import datetime
                timestamp = datetime.datetime.now().strftime('%H%M%S')
                if '.' in csvFileName:
                    csvFileNameTemp = csvFileName.split('.')[0]
                    csvFileNameExtension = csvFileName.split('.')[1]
                    csvFileName = csvFileNameTemp+'_'+timestamp+'.'+csvFileNameExtension
                else:
                    csvFileName = csvFileName+'_'+timestamp

            csvFile = open(csvFileName, 'w')
            csvWriteObj = csv.writer(csvFile)

        # Get the stat column names
        columnList = response.json()['columnCaptions']
        if csvFile != None:
            csvWriteObj.writerow(columnList)

        flowNumber = 1
        statDict = {}
        # Get the stat values
        for pageNumber in range(1,totalPages+1):
            self.patch(viewObject+'/page', data={'currentPage': pageNumber}, silentMode=silentMode)
            response = self.get(viewObject+'/page', silentMode=silentMode)
            statValueList = response.json()['pageValues']
            for statValue in statValueList:
                if csvFile != None:
                    csvWriteObj.writerow(statValue[0])
                if displayStats:
                    self.logInfo('\nRow: %d' % flowNumber)
                statDict[flowNumber] = {}
                index = 0
                for statValue in statValue[0]:
                    statName = columnList[index]
                    statDict[flowNumber].update({statName: statValue})
                    if displayStats:
                        self.logInfo('\t%s: %s' % (statName, statValue))
                    index += 1
                flowNumber += 1

        if csvFile != None:
            csvFile.close()
        return statDict

        # Flow Statistics dictionary output example
        '''
        Flow: 50
            Tx Port: Ethernet - 002
            Rx Port: Ethernet - 001
            Traffic Item: OSPF T1 to T2
            Source/Dest Value Pair: 2.0.21.1-1.0.21.1
            Flow Group: OSPF T1 to T2-FlowGroup-1 - Flow Group 0002
            Tx Frames: 35873
            Rx Frames: 35873
            Packet Loss Duration (ms):  11.106
            Frames Delta: 0
            Loss %: 0
            Tx Frame Rate: 3643.5
            Rx Frame Rate: 3643.5
            Tx L1 Rate (bps): 4313904
            Rx L1 Rate (bps): 4313904
            Rx Bytes: 4591744
            Tx Rate (Bps): 466368
            Rx Rate (Bps): 466368
            Tx Rate (bps): 3730944
            Rx Rate (bps): 3730944
            Tx Rate (Kbps): 3730.944
            Rx Rate (Kbps): 3730.944
            Tx Rate (Mbps): 3.731
            Rx Rate (Mbps): 3.731
            Store-Forward Avg Latency (ns): 0
            Store-Forward Min Latency (ns): 0
            Store-Forward Max Latency (ns): 0
            First TimeStamp: 00:00:00.722
            Last TimeStamp: 00:00:10.568
        '''

    def clearStats(self):
        """
        Description
           Clears all stats

        Syntax
           POST = https://{apiServerIp:port}/api/v1/sessions/<id>/ixnetwork/operations/clearstats
        """
        self.post(self.sessionUrl+'/operations/clearstats')

    def loadConfigFile(self, configFile):
        """
        Description
            Load a saved config file from a Linux machine.

        Parameter
            configFile: The full path including the saved config filename.
        """
        if os.path.exists(configFile) is False:
            raise IxNetRestApiException("Config file doesn't exists: %s" % configFile)

        if self.apiServerPlatform == 'linux':
            octetStreamHeader = {'content-type': 'application/octet-stream', 'x-api-key': self.apiKey}
        else:
            octetStreamHeader = self.jsonHeader

        # 1> Read the config file
        self.logInfo('\nReading saved config file')
        with open(configFile, mode='rb') as file:
            configContents = file.read()

        fileName = configFile.split('/')[-1]

        # 2> Upload it to the server and give it any name you want for the filename
        uploadFile = self.sessionUrl+'/files?filename='+fileName
        self.logInfo('\nUploading file to server: %s' % uploadFile)
        response = self.post(uploadFile, data=configContents, noDataJsonDumps=True, headers=octetStreamHeader, silentMode=True)

        # 3> Set the payload to load the given filename:  /api/v1/sessions/1/ixnetwork/files/ospfNgpf_8.10.ixncfg
        payload = {'arg1': '/api/v1/sessions/1/ixnetwork/files/%s' % fileName}

        loadConfigUrl = self.sessionUrl+'/operations/loadconfig'

        # 4> Tell the server to load the config file
        response = self.post(loadConfigUrl, data=payload, headers=octetStreamHeader)

        if self.waitForComplete(response, loadConfigUrl+'/'+response.json()['id'], timeout=140) == 1:
            raise IxNetRestApiException

    def assignPorts(self, portList, createVports=False, rawTraffic=False):
        """
        Description
            Assuming that you already connected to an ixia chassis and ports are available for usage.
            Use this API to assign physical ports to the virtual ports.

        Parameters
            portList: [ [ixChassisIp, '1','1'], [ixChassisIp, '1','2'] ]

            createVports: To automatically create virtual ports prior to assigning ports.
                          This must be set to True if you are building a configuration from scratch.

            rawTraffic: True|False.  If traffic config is raw, then vport needs to be /vport/{id}/protocols

        Syntaxes
            POST: http://{apiServerIp:port}/api/v1/sessions/{id}/ixnetwork/operations/assignports
                  data={arg1: [{arg1: ixChassisIp, arg2: 1, arg3: 1}, {arg1: ixChassisIp, arg2: 1, arg3: 2}],
                        arg2: [],
                        arg3: [http://{apiServerIp:port}/api/v1/sessions/{1}/ixnetwork/vport/1,
                               http://{apiServerIp:port}/api/v1/sessions/{1}/ixnetwork/vport/2],
                        arg4: true}
                  headers={'content-type': 'application/json'}
            GET:  http://{apiServerIp:port}/api/v1/sessions/{id}/ixnetwork/operations/assignports/1
                  data={}
                  headers={}
            Expecting:   RESPONSE:  SUCCESS
        """
        if createVports:
            self.createVports(portList)
        response = self.get(self.sessionUrl+'/vport')
        preamble = self.sessionUrl.split('/api')[1]
        #vportList = ["%s/vport/%s" % (self.sessionUrl, str(i["id"])) for i in response.json()]
        vportList = ["/api%s/vport/%s" % (preamble, str(i["id"])) for i in response.json()]
        if len(vportList) != len(portList):
            raise IxNetRestApiException('assignPorts: The amount of configured virtual ports:{0} is not equal to the amount of  portList:{1}'.format(len(vportList), len(portList)))

        data = {"arg1": [], "arg2": [], "arg3": vportList, "arg4": "true"}
        [data["arg1"].append({"arg1":str(chassis), "arg2":str(card), "arg3":str(port)}) for chassis,card,port in portList]
        response = self.post(self.sessionUrl+'/operations/assignports', data=data)
        if self.waitForComplete(response, self.sessionUrl+'/operations/assignports/'+response.json()['id'], timeout=120) == 1:
            raise IxNetRestApiException('assignPorts: Ports not coming up:', portList)
        if rawTraffic:
            vportProtocolList = []
            for vport in vportList:
                vportProtocolList.append(vport+'/protocols')
            return vportProtocolList
        else:
            return vportList

    def unassignPorts(self, portList='all', deletePorts=False):
        """
        Description
            Provide a list of ports to be unassigned or delete ports from the configuration.

        Parameters
            portList:  'all' = Automatically assign all ports.
                       You could provide a ist of ports in a list to be unassigned:
                       [[ixChassisIp, '1','1'], [ixChassisIp, '1','2']]

            deletePorts: True  = Delete the port from the configuration.
                         False = Unassign the port from the configuration.

        Syntaxes
            POST:  http://{apiServerIp:port}/api/v1/sessions/{id}/ixnetwork/vport/operations/unassignports
                   data={arg1: [http://{apiServerIp:port}/api/v1/sessions/{id}/ixnetwork/vport/1,
                                http://{apiServerIp:port}/api/v1/sessions/{id}/ixnetwork/vport/2],
                         arg2: true}
        """
        response = self.get(self.sessionUrl+'/vport')
        vportList = ["%s/vport/%s" % (sessionUrl, str(i["id"])) for i in response.json()]
        if portList == 'all':
            vports = vportList
        else:
            raise IxNetRestApiException('Unassigning ports selectively is currently not supported in this API. Needs to be enhanced')

        url = self.sessionUrl+'/vport/operations/unassignports'
        response = self.post(url, data={'arg1': vportList, 'arg2': False})
        if self.waitForComplete(response, self.sessionUrl+'/vport/operations/unassignports/'+response.json()['id'], timeout=120) == 1:
            raise IxNetRestApiException

    def releaseAllPorts(self):
        response = self.get(self.sessionUrl+'/vport')
        vportList = ["%s/vport/%s" % (self.sessionUrl, str(i["id"])) for i in response.json()]
        url = self.sessionUrl+'/vport/operations/releaseport'
        response = self.post(url, data={'arg1': vportList})
        if response.json()['state'] == 'SUCCESS': return 0
        if response.json()['id'] != '':
            if self.waitForComplete(response, url+'/'+response.json()['id'], timeout=120) == 1:
                raise IxNetRestApiException

    def releasePorts(self, portList):
        """
        Description
            Release specified ports in portList.

        Parameter
            portList: A list of ports to release in format of...
                      [[ixChassisIp, cardNum, portNum], [ixChassisIp, cardNum2, portNum2] ...]
        """
        for port in portList:
            vport = self.getVports([port])
            if vport == []:
                continue
            url = self.httpHeader+vport[0]+'/operations/releaseport'
            response = self.post(url, data={'arg1': vport})
            if response.json()['state'] == 'SUCCESS': continue
            if response.json()['id'] != '':
                if self.waitForComplete(response, url+'/'+response.json()['id'], timeout=120) == 1:
                    raise IxNetRestApiException('releasePorts failed')

    def clearPortOwnership(self, portList):
        """
            Description
                Clear port ownership on the portList

            Parameters
                portList: [[chassisIp, cardId, portId]]
        """
        response = self.get(self.sessionUrl+'/availableHardware/chassis')
        for eachChassis in response.json():
            chassisIp = eachChassis['ip']
            chassisHref = eachChassis['links'][0]['href']
 
            for userPort in portList:
                userChassisIp = userPort[0]
                userCardId = userPort[1]
                userPortId = userPort[2]
                url = self.httpHeader+chassisHref+'/card/'+str(userCardId)+'/port/'+str(userPortId)+'/operations/clearownership'
                data = {'arg1': [chassisHref+'/card/'+str(userCardId)+'/port/'+str(userPortId)]}
                self.post(url, data=data)

    def isPortConnected(self, portList):
        """
        Description
            Verify if the port is connected or released

        Parameters
            portList: [[ixChassisIp, str(cardNumber), str(portNumber)]]

        Return
            A list of 'connected' and 'released'.
        """
        returnValues = []
        for port in portList:
            vport = self.getVports([port])
            if vport == []:
                returnValues.append('released')
                continue
            response = self.get(self.httpHeader+vport[0])
            connectedStatus = response.json()['connectionStatus']
            print('\nisPortConnected:', port)
            if connectedStatus == 'Port Released':
                self.logInfo('\tFalse: %s' % connectedStatus)
                returnValues.append('released')
            else:
                self.logInfo('\tTrue: %s' % connectedStatus)
                returnValues.append('connected')
        return returnValues

    def arePortsAvailable(self, portList, raiseException=True):
        """
        Description: Verify if any of the portList is owned.

        Parameter:
           portList: Example: [ ['192.168.70.11', '1', '1'], ['192.168.70.11', '2', '1'] ]
    
        Return:
            - List of ports that are currently owned
            - 0: If portList are available
        """
        portOwnedList = []
        for port in portList:
            chassisIp = port[0]
            cardId = port[1]
            portId = port[2]
            try:
                queryData = {"from": "/availableHardware",
                                "nodes": [{"node": "chassis", "properties": ["ip"], "where": [{"property": "ip", "regex": chassisIp}]},
                                        {"node": "card", "properties": ["cardId"], "where": [{"property": "cardId", "regex": cardId}]},
                                        {"node": "port", "properties": ["portId", "owner"], "where": [{"property": "portId", "regex": portId}]}]}
                queryResponse = self.query(data=queryData, silentMode=False)
                queryResponse.json()['result'][0]['chassis'][0]['ip']
                queryResponse.json()['result'][0]['chassis'][0]['card'][0]['id']
                queryResponse.json()['result'][0]['chassis'][0]['card'][0]['port'][0]['portId']
            except:
                raise IxNetRestApiException('\nNot found:', chassisIp, cardId, portId)
            
            self.logInfo('\nPort currently owned by: %s' % queryResponse.json()['result'][0]['chassis'][0]['card'][0]['port'][0]['owner'])
            if queryResponse.json()['result'][0]['chassis'][0]['card'][0]['port'][0]['owner'] != '':
                self.logInfo('Port is still owned: {0}/cardId:{1}/portId:{2}'.format(chassisIp, cardId, portId))
                portOwnedList.append([chassisIp, cardId, portId])

        self.logInfo('\nPorts are still owned: %s' % portOwnedList)

        if portOwnedList != []:
            if raiseException:
                raise IxNetRestApiException
            else:
                return portOwnedList
        return 0

    def verifyPortState(self):
        timer = 70
        response = self.get(self.sessionUrl+'/vport')
        vportList = ["%s/vport/%s" % (self.sessionUrl, str(i["id"])) for i in response.json()]
        for eachVport in vportList:
            for counter in range(1,timer+1):
                response = self.get(eachVport, silentMode=True)
                self.logInfo('\nPort: %s' % response.json()['assignedTo'])
                self.logInfo('\tVerifyPortState: %s\n\tWaiting %s/%s seconds' % (response.json()['state'], counter, timer))
                if counter < timer and response.json()['state'] in ['down', 'busy']:
                    time.sleep(1)
                    continue
                if counter < timer and response.json()['state'] == 'up':
                    break
                if counter == timer and response.json()['state'] == 'down':
                    # Failed
                    raise IxNetRestApiException('Port failed to come up')

                    
    def startAllProtocols(self):
        """
        Description
            Start all protocols in NGPF

        Syntax
            POST:  http://{apiServerIp:port}/api/v1/sessions/{id}/ixnetwork/operations/startallprotocols
        """
        response = self.post(self.sessionUrl+'/operations/startallprotocols', data={'arg1': 'sync'})

    def stopAllProtocols(self):
        """
        Description
            Stop all protocols in NGPF

        Syntax
            POST:  http://{apiServerIp:port}/api/v1/sessions/{id}/ixnetwork/operations/stopallprotocols
        """
        response = self.post(self.sessionUrl+'/operations/stopallprotocols', data={'arg1': 'sync'})

    def startProtocol(self, protocolObj):
        """
        Description
            Start the specified protocol by its object handle.

        Parameters
            protocolObj: Ex: /api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv4/1/bgpIpv4Peer/1
        """
        self.post(self.httpHeader+protocolObj+'/operations/start', data={'arg1': [protocolObj]})

    def stopProtocol(self, protocolObj):
        """
        Description
            Stop the specified protocol by its object handle.

        Parameters
            protocolObj: Ex: /api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv4/1/bgpIpv4Peer/1
        """
        self.post(self.httpHeader+protocolObj+'/operations/stop', data={'arg1': [protocolObj]})

    def startTopology(self, topologyObjList='all'):
        """
        Description
            Start a Topology Group and all of its protocol stacks.
        
        Parameters
            topologyObjList: 'all' or a list of Topology Group href.
                             Ex: ['/api/v1/sessions/1/ixnetwork/topology/1']
        """
        if topologyObjList == 'all':
            queryData = {'from': '/',
                         'nodes': [{'node': 'topology', 'properties': ['href'], 'where': []}]
                        }

           # QUERY FOR THE BGP HOST ATTRIBITE OBJECTS
            queryResponse = self.query(data=queryData)
            try:
                topologyList = queryResponse.json()['result'][0]['topology']
            except IndexError:
                raise IxNetRestApiException('\nNo Topology Group objects  found')

            topologyObjList = [topology['href'] for topology in topologyList]

        url = self.sessionUrl+'/topology/operations/start'
        response = self.post(url, data={'arg1': topologyObjList})
        if self.waitForComplete(response, url+'/'+response.json()['id']) == 1:
            raise IxNetRestApiException

    def stopTopology(self, topologyObjList='all'):
        """
        Description
            Stop the running Topology and all protocol sessions.
        
        Parameters
            topologyObjList: A list of Topology Group href.
                             Ex: ['/api/v1/sessions/1/ixnetwork/topology/1']
        """
        if topologyObjList == 'all':
            queryData = {'from': '/',
                         'nodes': [{'node': 'topology', 'properties': ['href'], 'where': []}]
                        }

           # QUERY FOR THE BGP HOST ATTRIBITE OBJECTS
            queryResponse = self.query(data=queryData)
            try:
                topologyList = queryResponse.json()['result'][0]['topology']
            except IndexError:
                raise IxNetRestApiException('\nNo Topology Group objects  found')

            topologyObjList = [topology['href'] for topology in topologyList]

        self.post(self.sessionUrl+'/topology/operations/stop', data={'arg1': topologyObjList})
        if self.waitForComplete(response, url+'/'+response.json()['id']) == 1:
            raise IxNetRestApiException

    def startStopDeviceGroup(self, deviceGroupObjList='all', action='start'):
        """
        Description
            Start a Topology Group and all of its protocol stacks.
        
        Parameters
            topologyObjList: 'all' or a list of Topology Group href.
                             Ex: ['/api/v1/sessions/1/ixnetwork/topology/1']
        """
        if deviceGroupObjList == 'all':
            queryData = {'from': '/',
                         'nodes': [{'node': 'topology', 'properties': [], 'where': []},
                                   {'node': 'deviceGroup', 'properties': ['href'], 'where': []}]
                        }

           # QUERY FOR THE BGP HOST ATTRIBITE OBJECTS
            queryResponse = self.query(data=queryData)
            try:
                topologyGroupList = queryResponse.json()['result'][0]['topology']
            except IndexError:
                raise IxNetRestApiException('\nNo Device  Group objects  found')

            deviceGroupObjList = []
            for dg in topologyGroupList:
                for dgHref in  dg['deviceGroup']:
                    #deviceGroupObjList.append(dgHref['href'])
                    '''
                    url = self.sessionUrl+'/topology/deviceGroup/operations/stop'
                    response = self.post(url, data={'arg1': dgHref['href'].split(' ')})
                    if self.waitForComplete(response, url+'/'+response.json()['id']) == 1:
                        raise IxNetRestApiException

                    time.sleep(3)
                    '''
                    url = self.sessionUrl+'/topology/deviceGroup/operations/%s' % action
                    response = self.post(url, data={'arg1': dgHref['href'].split(' ')})
                    if self.waitForComplete(response, url+'/'+response.json()['id']) == 1:
                        raise IxNetRestApiException
                    time.sleep(3)

        #url = self.sessionUrl+'/topology/operations/start'
        #response = self.post(url, data={'arg1': topologyObjList})
        #if self.waitForComplete(response, url+'/'+response.json()['id']) == 1:
        #    raise IxNetRestApiException

    def verifyProtocolSessionsNgpf(self, protocolObjList=None, timeout=90):
        """
        Description
            Either verify the user specified protocol list to verify for session UP or verify
            the default object's self.configuredProtocols list that accumulates the emulation protocol object
            when it was configured.
            When verifying IPv4, this API will verify ARP failures and return you a list of IP interfaces
            that failed ARP.

        Syntaxes
            GET:  http://10.219.117.103:11009/api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1
            GET RESPONSE:  [u'notStarted', u'notStarted', u'notStarted', u'notStarted', u'notStarted', u'notStarted']
            GET:  http://10.219.117.103:11009/api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv4/1
            GET RESPONSE:  [u'up', u'up', u'up', u'up', u'up', u'up', u'up', u'up']
            GET:  http://10.219.117.103:11009/api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv4/1/bgpIpv4Peer/1

        Parameters
            protocolObjList: A list of protocol objects.  Default = None.  The class will automatically verify all
                             of the configured protocols.
            Ex: ['http://{apiServerIp:port}/api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1',
                 'http://{apiServerIp:port}/api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv4/1',
                 'http://{apiServerIp:port}/api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv4/1/bgpIpv4Peer/1',
                 'http://{apiServerIp:port}/api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv4/1/ospfv2/1',]
            timeout: Total wait time for all the protocols in the provided list to come up.
        """
        timerStop = timeout
        if protocolObjList is None:
            protocolObjList = self.configuredProtocols

        for eachProtocol in protocolObjList:
            # notStarted, up or down

            protocolName =  eachProtocol.split('/')[-2]
            self.logInfo('\nVerifyProtocolSessions: %s\n' % eachProtocol)
            for timer in range(1,timerStop+1):
                response = self.get(self.httpHeader+eachProtocol, silentMode=True)
                protocolSessionStatus = response.json()['sessionStatus']
                self.logInfo('\tStatus: Down : Wait %s/%s seconds' % (timer, timerStop))
                if timer < timerStop+1:
                    if 'down' in protocolSessionStatus or 'notStarted' in protocolSessionStatus:
                        time.sleep(1)
                if timer < timerStop+1:
                    if 'down' not in protocolSessionStatus and 'notStarted' not in protocolSessionStatus:
                        self.logInfo('\n\tStatus: All UP')
                        break
                if timer == timerStop:
                    if 'down' in protocolSessionStatus or 'notStarted' in protocolSessionStatus:

                        # Show ARP failures
                        if protocolName == 'ipv4':
                            ipInterfaceIndexList = []
                            index = 0
                            for eachSessionStatus in response.json()['sessionStatus']:
                                self.logInfo('eachSessionStatus index:', eachSessionStatus, index)
                                if eachSessionStatus == 'down':
                                    ipInterfaceIndexList.append(index)
                                index += 1

                            ipMultivalue = self.httpHeader + response.json()['address']
                            response = self.get(ipMultivalue)

                            self.logInfo('\nARP failed on IP interface:')
                            ipAddressList = response.json()['values']
                            for eachIpIndex in ipInterfaceIndexList:
                                self.logInfo('\t{0}'.format(ipAddressList[eachIpIndex]))
                        else:
                            self.logInfo('\nverifyProtocolSessions: {0} session failed'.format(protocolName))

                        raise IxNetRestApiException('Verify protocol sessions failed.')

    def verifyAllProtocolSessionsNgpf(self, timeout=120):
        """
        Description
            This API will loop through each created Topology Group and verify
            all the created protocols for session up for up to 120 seconds total.
            Will verify IPv4 and IPv6 also.
        """
        protocolList = ['ancp',
                        'bfdv4Interface',
                        'bgpIpv4Peer',
                        'bgpIpv6Peer',
                        'dhcpv4relayAgent',
                        'dhcpv6relayAgent',
                        'dhcpv4server',
                        'dhcpv6server',
                        'geneve',
                        'greoipv4',
                        'greoipv6',
                        'igmpHost',
                        'igmpQuerier',
                        'lac',
                        'ldpBasicRouter',
                        'ldpBasicRouterV6',
                        'ldpConnectedInterface',
                        'ldpv6ConnectedInterface',
                        'ldpTargetedRouter',
                        'ldpTargetedRouterV6',
                        'lns',
                        'mldHost',
                        'mldQuerier',
                        'ptp',
                        'ipv6sr',
                        'openFlowController',
                        'openFlowSwitch',
                        'ospfv2',
                        'ospfv3',
                        'ovsdbcontroller',
                        'ovsdbserver',
                        'pcc',
                        'pce',
                        'pcepBackupPCEs',
                        'pimV4Interface',
                        'pimV6Interface',
                        'ptp',
                        'rsvpteIf',
                        'rsvpteLsps',
                        'tag',
                        'vxlan'
                    ]

        sessionDownList = ['down', 'notStarted']
        startCounter = 1

        response = self.get(self.sessionUrl+'/topology')
        topologyList = ['%s/%s/%s' % (self.sessionUrl, 'topology', str(i["id"])) for i in response.json()]
        for topology in topologyList:
            response = self.get(topology+'/deviceGroup')
            deviceGroupList = ['%s/%s/%s' % (topology, 'deviceGroup', str(i["id"])) for i in response.json()]
            for deviceGroup in deviceGroupList:
                response = self.get(deviceGroup+'/ethernet')
                ethernetList = ['%s/%s/%s' % (deviceGroup, 'ethernet', str(i["id"])) for i in response.json()]
                for ethernet in ethernetList:
                    response = self.get(ethernet+'/ipv4')
                    ipv4List = ['%s/%s/%s' % (ethernet, 'ipv4', str(i["id"])) for i in response.json()]
                    response = self.get(ethernet+'/ipv6')
                    ipv6List = ['%s/%s/%s' % (ethernet, 'ipv6', str(i["id"])) for i in response.json()]
                    for layer3Ip in ipv4List+ipv6List:
                        for protocol in protocolList:
                            response = self.get(layer3Ip+'/'+protocol, silentMode=True, ignoreError=True)
                            if response.json() == [] or 'errors' in response.json():
                                continue

                            currentProtocolList = ['%s/%s/%s' % (layer3Ip, protocol, str(i["id"])) for i in response.json()]
                            for currentProtocol in currentProtocolList:
                                for timer in range(startCounter, timeout+1):
                                    response = self.get(currentProtocol, silentMode=True)
                                    currentStatus = response.json()['sessionStatus']
                                    self.logInfo('\n%s' % currentProtocol)
                                    self.logInfo('\tTotal sessions: %d' % len(currentStatus))
                                    totalDownSessions = 0
                                    for eachStatus in currentStatus:
                                        if eachStatus != 'up':
                                            totalDownSessions += 1
                                    self.logInfo('\tTotal sessions Down: %d' % totalDownSessions)

                                    if timer < timeout and [element for element in sessionDownList if element in currentStatus] == []:
                                        self.logInfo('\tProtocol sessions are all up')
                                        startCounter = timer
                                        break
                                    if timer < timeout and [element for element in sessionDownList if element in currentStatus] != []:
                                        self.logInfo('\tWait %d/%d seconds' % (timer, timeout))
                                        time.sleep(1)
                                        continue
                                    if timer == timeout and [element for element in sessionDownList if element in currentStatus] != []:
                                        raise IxNetRestApiException

    def sendArpNgpf(self, ipv4ObjList):
        """
        Description
            Send ARP out of all the IPv4 objects that you provide in a list.

        ipv4ObjList = Provide a list of one or more IPv4 object handles to send arp.
                      Ex: ["/api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv4/1"]
        """
        if type(ipv4ObjList) != list:
            raise IxNetRestApiException('sendArpNgpf error: The parameter ipv4ObjList must be a list of objects.')

        url = self.sessionUrl+'/topology/deviceGroup/ethernet/ipv4/operations/sendarp'
        data = {'arg1': ipv4ObjList}
        response = self.post(url, data=data)
        if self.waitForComplete(response, url+'/'+response.json()['id']) == 1:
            raise IxNetRestApiException

    def deviceGroupProtocolStackNgpf(self, deviceGroupObj, ipType):
        """
        Description
            This Proc is an internal API for VerifyArpNgpf.
            It's created because each deviceGroup has IPv4/IPv6 and
            a deviceGroup could have inner deviceGroup that has IPv4/IPv6.
            Therefore, you can loop device groups.
        """
        unresolvedArpList = []
        response = self.get(deviceGroupObj+'/ethernet')
        ethernetObjList = ['%s/%s/%s' % (deviceGroupObj, 'ethernet', str(i["id"])) for i in response.json()]
        for ethernetObj in ethernetObjList:
            response = self.get(ethernetObj+'/'+ipType, ignoreError=True)
            if response.status_code != 200:
                self.logInfo('deviceGroupProtocolStackNgpf: %s' % response.text); return 1
            ipProtocolList = ['%s/%s/%s' % (ethernetObj, ipType, str(i["id"])) for i in response.json()]
            for ipProtocol in ipProtocolList:
                # sessionStatus could be: down, up, notStarted
                response = self.get(ipProtocol, ignoreError=True)
                if response.status_code != 200:
                    self.logInfo('deviceGroupProtocolStackNgpf: %s' % response.text); return 1
                sessionStatus = response.json()['sessionStatus']
                resolvedGatewayMac = response.json()['resolvedGatewayMac']

                #print ('\tsessionStatus:', sessionStatus)
                #print ('\tresolvedGatewayMac', resolvedGatewayMac)
                # sessionStatus: ['up', 'up']
                # resolvedGatewayMac ['00:0c:29:8d:d8:35', '00:0c:29:8d:d8:35']

                # Only care for unresolved ARPs.
                # resolvedGatewayMac: 00:01:01:01:00:01 00:01:01:01:00:02 removePacket[Unresolved]
                # Search each mac to see if they're resolved or not.
                for index in range(0, len(resolvedGatewayMac)):
                    if (bool(re.search('.*Unresolved.*', resolvedGatewayMac[index]))):
                        #if sessionStatus[index] != 'notStarted':
                        multivalue = response.json()['address']
                        multivalueResponse = self.get(self.httpHeader+multivalue)
                        srcIpAddrNotResolved = multivalueResponse.json()['values'][index]
                        self.logInfo('\tFailed to resolve ARP: {0}'.format(srcIpAddrNotResolved))
                        unresolvedArpList.append(srcIpAddrNotResolved)

        if unresolvedArpList == []:
            self.logInfo('\tARP is resolved')
            return 0
        else:
            return unresolvedArpList

    def verifyArp(self, ipType='ipv4'):
        """
        Description
            This API will verify for ARP session resolvement on
            every Device Group including inner Device Groups.

            How it works?
               Each device group has a list of $sessionStatus: up, down or notStarted.
               If the deviceGroup has sessionStatus as "up", then ARP will be verified.
               It also has a list of $resolvedGatewayMac: MacAddress or removePacket[Unresolved]
               These two $sessionStatus and $resolvedGatewayMac lists are aligned.
               If lindex 0 on $sessionSatus is up, then $resolvedGatewayMac on index 0 expects
               to have a mac address.  Not removePacket[Unresolved].
               If not, then arp is not resolved.

         This API requires:
            DeviceGroupProtocolStacksNgpf()

        Parameter
            ipType:  ipv4 or ipv6
        """

        unresolvedArpList = []
        startFlag = 0

        response = self.get(self.sessionId+'/topology')
        topologyList = ['%s/%s/%s' % (self.sessionId, 'topology', str(i["id"])) for i in response.json()]
        for topologyObj in topologyList:
            topologyResponse = self.get(topologyObj)
            deviceGroupResponse = self.get(topologyObj+'/deviceGroup')
            deviceGroupList = ['%s/%s/%s' % (topologyObj, 'deviceGroup', str(i["id"])) for i in deviceGroupResponse.json()]
            for deviceGroupObj in deviceGroupList:
                response = self.get(deviceGroupObj)
                deviceGroupStatus = response.json()['status']
                self.logInfo('\n%s' % deviceGroupObj)
                self.logInfo('\tdeviceGroup Status: %s' % deviceGroupStatus)

                if deviceGroupStatus in ['started', 'mixed']:
                    startFlag = 1
                    arpResult = self.deviceGroupProtocolStackNgpf(deviceGroupObj, ipType)
                    if arpResult != 0:
                        unresolvedArpList = unresolvedArpList + arpResult

                    response = self.get(deviceGroupObj+'/deviceGroup')
                    if response.status_code == 200 and response.json() != []:
                        innerDeviceGroupObj = response.json()[0]['links'][0]['href']
                        self.logInfo('\n%s' % self.httpHeader+innerDeviceGroupObj)
                        response = self.get(self.httpHeader+innerDeviceGroupObj)
                        deviceGroupStatus1 = response.json()['status']
                        self.logInfo('\tdeviceGroup Status: %s' % deviceGroupStatus1)

                        if deviceGroupStatus == 'started':
                            arpResult = self.deviceGroupProtocolStackNgpf(self.httpHeader+innerDeviceGroupObj, ipType)
                            if arpResult != 0:
                                unresolvedArpList = unresolvedArpList + arpResult

        if unresolvedArpList == [] and startFlag == 1:
            return 0
        if unresolvedArpList == [] and startFlag == 0:
            return 1
        if unresolvedArpList != [] and startFlag == 1:
            print()
            for ip in unresolvedArpList:
                self.logInfo('verifyArpNgpf: UnresolvedArps: %s' % ip, end='\n')
            raise IxNetRestApiException

    def getNgpfGatewayIpMacAddress(self, gatewayIp):
        """
        Description
            Get the NGPF gateway IP Mac Address. The condition is that the IPv4 
            session status must be UP. 

        Parameter
            gatewayIp: The gateway IP address. 

        Return: 
            - 0: No Gateway IP address found. 
            - removePacket[Unresolved]
            - The Gateway IP's Mac Address.
        """
        queryData = {'from': '/',
                    'nodes': [{'node': 'topology',    'properties': [], 'where': []},
                              {'node': 'deviceGroup', 'properties': [], 'where': []},
                              {'node': 'ethernet',  'properties': [], 'where': []},
                              {'node': 'ipv4',  'properties': ['gatewayIp', 'sessionStatus'],
                               'where': [{'property': 'sessionStatus', 'regex': '.*up'}]}
                    ]}
        queryResponse = self.query(data=queryData, silentMode=False)
        for topology in queryResponse.json()['result'][0]['topology']:
            for deviceGroup in topology['deviceGroup']:
                #print('\ndeviceG:', deviceGroup)
                try:
                    # Getting in here means IPv4 session status is UP.
                    ipv4Href = deviceGroup['ethernet'][0]['ipv4'][0]['href']
                    gatewayIpMultivalue = deviceGroup['ethernet'][0]['ipv4'][0]['gatewayIp']
                    self.logInfo('\n\t%s' % ipv4Href)
                    self.logInfo('\tIPv4 sessionStatus: %s' % deviceGroup['ethernet'][0]['ipv4'][0]['sessionStatus'])
                    self.logInfo('\tGatewayIpMultivalue: %s' % gatewayIpMultivalue)

                    response = self.get(self.httpHeader+gatewayIpMultivalue)
                    valueList = response.json()['values']
                    self.logInfo('gateway IP: %s' % valueList)
                    if gatewayIp in valueList:
                        gatewayIpIndex = valueList.index(gatewayIp)
                        self.logInfo('\nFound gateway: %s ; Index:%s' % (gatewayIp, gatewayIpIndex))
                        # Get the IPv4 gateway mac address with the "gatewayIpMultivalue"
                        queryData = {'from': deviceGroup['ethernet'][0]['href'],
                                    'nodes': [{'node': 'ipv4',  'properties': ['gatewayIp', 'resolvedGatewayMac'], 
                                            'where': [{'property': 'gatewayIp', 'regex': gatewayIpMultivalue}]}
                                    ]}
                        queryResponse = self.query(data=queryData, silentMode=False)
                        gatewayMacAddress = queryResponse.json()['result'][0]['ipv4'][0]['resolvedGatewayMac'][gatewayIpIndex]
                        self.logInfo('\ngatewayIpMacAddress: %s' % gatewayMacAddress)
                        if 'Unresolved' in gatewayMacAddress:
                            raise IxNetRestApiException('Gateway Mac Address is unresolved.')
                        return gatewayMacAddress
                except:
                    pass
        return 0

    def getNgpfGatewayIpMacAddress_backup(self, gatewayIp):
        """
        Description
            Get the NGPF gateway IP Mac Address. 

        Parameter
            gatewayIp: The gateway IP address. 

        Return: 
            - 0: No Gateway IP address found. 
            - removePacket[Unresolved]
            - The Gateway IP's Mac Address.
        """
        queryData = {'from': '/',
                    'nodes': [{'node': 'topology',    'properties': [], 'where': []},
                              {'node': 'deviceGroup', 'properties': [], 'where': []},
                              {'node': 'ethernet',  'properties': [], 'where': []},
                              {'node': 'ipv4',  'properties': ['gatewayIp'], 'where': []}
                    ]}
        queryResponse = self.query(data=queryData, silentMode=False)
        for topology in queryResponse.json()['result'][0]['topology']:
            gatewayIpMultivalue = topology['deviceGroup'][0]['ethernet'][0]['ipv4'][0]['gatewayIp']
            ipv4Href = topology['deviceGroup'][0]['ethernet'][0]['ipv4'][0]
            self.logInfo('IPv4 obj:', ipv4Href)
            self.logInfo('Gateway multivalue: %s' % gatewayIpMultivalue)
            response = self.get(self.httpHeader+gatewayIpMultivalue)
            valueList = response.json()['values']
            self.logInfo(valueList)
            if gatewayIp in valueList:
                gatewayIpIndex = valueList.index(gatewayIp)
                self.logInfo('Found gateway: %s ; Index:%s' % (gatewayIp, gatewayIpIndex))
                queryData = {'from': '/',
                            'nodes': [{'node': 'topology',    'properties': [], 'where': []},
                                    {'node': 'deviceGroup', 'properties': [], 'where': []},
                                    {'node': 'ethernet',  'properties': [], 'where': []},
                                    {'node': 'ipv4',  'properties': ['gatewayIp', 'resolvedGatewayMac'], 
                                    'where': [{'property': 'gatewayIp', 'regex': gatewayIpMultivalue}]}
                            ]}
       
                queryResponse = self.query(data=queryData, silentMode=False)
                for topologyNode in queryResponse.json()['result'][0]['topology']:
                    try:
                        gatewayMacAddress = topologyNode['deviceGroup'][0]['ethernet'][0]['ipv4'][0]['resolvedGatewayMac'][gatewayIpIndex]
                        self.logInfo('\ngatewayIpMacAddress: %s' % gatewayMacAddress)
                        if 'Unresolved' in gatewayMacAddress:
                            raise IxNetRestApiException('Gateway Mac Address is unresolved.')
                        return gatewayMacAddress
                    except:
                        pass
        return 0

    def getIpAddrIndexNumber(self, ipAddress):
        """
        Description
            Get the index ID of the IP address.

        Parameter
            ipAddress: The IP address to search for its index .
        """
        queryData = {'from': '/',
                    'nodes': [{'node': 'topology',    'properties': [], 'where': []},
                              {'node': 'deviceGroup', 'properties': [], 'where': []},
                              {'node': 'ethernet',  'properties': [], 'where': []},
                              {'node': 'ipv4',  'properties': ['address'], 'where': []},
                              {'node': 'ipv6',  'properties': ['address'], 'where': []},
                              ]}

        queryResponse = self.query(data=queryData, silentMode=False)       
        if '.' in ipAddress:
            multivalue = queryResponse.json()['result'][0]['topology'][0]['deviceGroup'][0]['ethernet'][0]['ipv4'][0]['address']
        if ':' in ipAddress:
            multivalue = queryResponse.json()['result'][0]['topology'][0]['deviceGroup'][0]['ethernet'][0]['ipv6'][0]['address']

        response = self.get(self.httpHeader+multivalue)
        valueList = response.json()['values']
        index = response.json()['values'].index(ipAddress)
        return index

    def getIpv4ObjByPortName(self, portName=None):
        """
        Description
            Get the IPv4 object by the port name. 
        
        Parameter
            portName: The name of the port.
        """
        # Step 1 of 3: Get the Vport by the portName.
        queryData = {'from': '/',
                    'nodes': [{'node': 'vport', 'properties': ['name'], 'where': [{'property': 'name', 'regex': portName}]}]}

        queryResponse = self.query(data=queryData, silentMode=False)
        if queryResponse.json()['result'][0]['vport'] == []:
            raise IxNetRestApiException('\nNo such vport name: %s\n' % portName)

        # /api/v1/sessions/1/ixnetwork/vport/2
        vport = queryResponse.json()['result'][0]['vport'][0]['href']
        self.logInfo(vport)

        # Step 2 of 3: Query the API tree for the IPv4 object
        queryData = {'from': '/',
                    'nodes': [{'node': 'topology',    'properties': ['vports'], 'where': []},
                              {'node': 'deviceGroup', 'properties': [], 'where': []},
                              {'node': 'ethernet',  'properties': [], 'where': []},
                              {'node': 'ipv4',  'properties': [], 'where': []},
                              ]}

        queryResponse = self.query(data=queryData, silentMode=False)

        # Step 3 of 3: Loop through each Topology looking for the vport.
        #              If found, get its IPv4 object
        for topology in queryResponse.json()['result'][0]['topology']:
            if vport in topology['vports']:
                # Get the IPv4 object: /api/v1/sessions/1/ixnetwork/topology/2/deviceGroup/1/ethernet/1/ipv4/1
                ipv4Obj = topology['deviceGroup'][0]['ethernet'][0]['ipv4'][0]['href']
                return ipv4Obj
    
    def activateIgmpHostSession(self, portName=None, ipAddress=None, activate=True):
        """
        Description
            Active or deactivate the IGMP host session ID by the portName and IPv4 host address. 
        
        Parameters:
            portName: The name of the port in which this API will search in all the Topology Groups.
            ipAddress: Within the Topology Group, the IPv4 address for the IGMP host.
            activate:  True|False
        """
        # Get the IPv4 address index.  This index position is the same index position for the IGMP host sessionID.
        # Will use this variable to change the value of the IGMP host object's active valueList.
        ipv4AddressIndex = self.getIpAddrIndexNumber(ipAddress)

        # Get the IPv4 object by the port name. This will search through all the Topology Groups for the portName.
        ipv4Obj = self.getIpv4ObjByPortName(portName=portName)

        # With the ipv4Obj, get the IGMP host object's "active" multivalue so we could modify the active valueList.
        queryData = {'from': ipv4Obj,
                    'nodes': [{'node': 'igmpHost', 'properties': ['active'], 'where': []}]}

        queryResponse = self.query(data=queryData, silentMode=False)
        if queryResponse.json()['result'][0]['igmpHost'] == []:
            raise IxNetRestApiException('\nNo IGMP HOST found\n')

        igmpHostActiveMultivalue = queryResponse.json()['result'][0]['igmpHost'][0]['active']

        response = self.get(self.httpHeader+igmpHostActiveMultivalue)
        valueList = response.json()['values']
        # Using the ipv4 address index, activate the IGMP session ID which is the same index position.
        valueList[ipv4AddressIndex] = activate
        self.configMultivalue(igmpHostActiveMultivalue, multivalueType='valueList', data={'values': valueList})

    def enableDeviceGroup(self, deviceGroupObj=None, enable=True):
        """
        Description
            Enable or disable a Device Group by the object handle.  A Device Group could contain many interfaces.
            This API will enable or disable all the interfaces.
            
        Parameters
            deviceGroupObj: The Device Group object handle: /api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1

            enable: True|False
        """
        response = self.get(self.httpHeader + deviceGroupObj)
        enabledMultivalue = response.json()['enabled']
        self.configMultivalue(enabledMultivalue, multivalueType='singleValue', data={'value': enable})
    
    def activateRouterIdProtocols(self, routerId, activate=True, protocol=None):
        """
        Description
            Activate the protocols based on the RouterId.
            This API will disabled all Device Groups within a Topology Group and enable only the
            Device Group that has the specified router ID in it.

        Parameter
            routerId: The router Id address to enable|disable
            activate: True|False. The protocol to activate|disactivate.
            protocol: The protocol to activate.
                      Current choices: bgpIpv4Peer, bgpIpv6Peer, igmpHost, pimV6Interface, ospfv2, ospfv3, isisL3
        """
        queryData = {'from': '/',
                    'nodes': [{'node': 'topology',    'properties': [], 'where': []},
                              {'node': 'deviceGroup', 'properties': [], 'where': []},
                              {'node': 'routerData',  'properties': ['routerId'], 'where': []},
                              {'node': 'ethernet',  'properties': [], 'where': []},
                              {'node': 'ipv4',  'properties': [], 'where': []},
                              {'node': 'ipv6',  'properties': [], 'where': []},
                              {'node': protocol,  'properties': ['active'], 'where': []}
                          ]}

        queryResponse = self.query(data=queryData, silentMode=False)

        # Get the Device Group object that contains the RouterId
        # and search for configured protocols.
        protocolList = []
        foundRouterIdFlag = 0
        for topology in queryResponse.json()['result'][0]['topology']:
            for deviceGroup in topology['deviceGroup']:
                deviceGroupHref = deviceGroup['href']
                self.logInfo('\nactivateRouterIdProtocols: Querying DeviceGroup for routerId: %s' % routerId)
                self.logInfo('Disabling DeviceGroup Obj: %s' % deviceGroupHref)
                self.enableDeviceGroup(deviceGroupObj=deviceGroupHref, enable=False)
                routerIdMultivalue = deviceGroup['routerData'][0]['routerId']
                response = self.get(self.httpHeader+routerIdMultivalue)

                #"values": ["192.0.0.1", "192.0.0.2", "192.0.0.3", "192.0.0.4","192.1.0.1"]
                if routerId in response.json()['values']:
                    foundRouterIdFlag = 1
                    self.logInfo('\nFound routerId %s' %  routerId)
                    self.enableDeviceGroup(deviceGroupObj=deviceGroupHref, enable=True)
                    routerIdIndex = response.json()['values'].index(routerId)
                    self.logInfo('routerId index: %s' % routerIdIndex)

                    if protocol == 'isisL3' and deviceGroup['ethernet'][0]['isisL3'] != []:
                        protocolList.append(deviceGroup['ethernet'][0]['isisL3'][0]['active'])

                    if deviceGroup['ethernet'][0]['ipv4'] != []:
                        if protocol == 'igmpHost' and deviceGroup['ethernet'][0]['ipv4'][0]['igmpHost'] != []:
                            protocolList.append(deviceGroup['ethernet'][0]['ipv4'][0]['igmpHost'][0]['active'])
                        if protocol == 'bgpIpv4Peer' and deviceGroup['ethernet'][0]['ipv4'][0]['bgpIpv4Peer'] != []:
                            protocolList.append(deviceGroup['ethernet'][0]['ipv4'][0]['bgpIpv4Peer'][0]['active'])
                        if protocol == 'ospfv2' and deviceGroup['ethernet'][0]['ipv4'][0]['ospfv2'] != []:
                            protocolList.append(deviceGroup['ethernet'][0]['ipv4'][0]['ospfv2'][0]['active'])

                    if deviceGroup['ethernet'][0]['ipv6'] != []:
                        if protocol == 'pimV6Interface' and deviceGroup['ethernet'][0]['ipv6'][0]['pimV6Interface'] != []:
                            protocolList.append(deviceGroup['ethernet'][0]['ipv6'][0]['pimV6Interface'][0]['active'])                       
                        if protocol == 'bgpIpv6Peer' and deviceGroup['ethernet'][0]['ipv6'][0]['bgpIpv6Peer'] != []:
                            protocolList.append(deviceGroup['ethernet'][0]['ipv6'][0]['bgpIpv6Peer'][0]['active'])
                        if protocol == 'ospfv3' and deviceGroup['ethernet'][0]['ipv6'][0]['ospfv3'] != []:
                            protocolList.append(deviceGroup['ethernet'][0]['ipv6'][0]['ospfv3'][0]['active'])

                    for protocolActiveMultivalue in protocolList:
                        #self.logInfo('\nmultivalue: %s' % protocolActiveMultivalue)
                        try:
                            response = self.get(self.httpHeader+protocolActiveMultivalue)
                            valueList = response.json()['values']
                            self.logInfo('\ncurrentValueList: %s' % valueList)
                            # va
                            valueList[routerIdIndex] = str(activate).lower()
                            self.logInfo('updatedValueList: %s' % valueList)
                            self.configMultivalue(protocolActiveMultivalue, multivalueType='valueList',
                                                  data={'values': valueList})
                        except:
                            pass

        if foundRouterIdFlag == 0:
            raise Exception ('\nNo RouterID found in any Device Group: %s' % routerId)

    def enableTrafficItemByName(self, trafficItemName, enable=True):
        """
        Description
            Enable or Disable a Traffic Item by its name.

        Parameter
            trafficItemName: The exact spelling of the Traffic Item name.
            enable: True | False
                    True: Enable Traffic Item
                    False: Disable Traffic Item
        """
        trafficItemObj = self.getTrafficItemObjByName(trafficItemName)
        if trafficItemObj == 0:
            raise IxNetRestApiException('No such Traffic Item name: %s' % trafficItemName)
        
        self.patch(self.httpHeader+trafficItemObj, data={"enabled": enable})

    def getTrafficItemName(self, trafficItemObj):
        """
        Description
            Get the Traffic Item name by its object.

        Parameter
            trafficItemObj: The Traffic Item object.
                            /api/v1/sessions/1/ixnetwork/traffic/trafficItem/1
        """
        response = self.get(self.httpHeader+trafficItemObj)
        return response.json()['name']

    def getAllTrafficItemNames(self):
        """
        Description
            Return all of the Traffic Item names.
        """
        trafficItemUrl = self.sessionUrl+'/traffic/trafficItem'
        response = self.get(trafficItemUrl)
        trafficItemNameList = []
        for eachTrafficItemId in response.json():
            trafficItemNameList.append(eachTrafficItemId['name'])
        return trafficItemNameList

    def getTrafficItemObjByName(self, trafficItemName):
        """
        Description
            Get the Traffic Item object by the Traffic Item name.
        
        Parameter
            trafficItemName: Name of the Traffic Item. 
        
        Return
            0: No Traffic Item name found. Return 0.
            traffic item object:  /api/v1/sessions/1/ixnetwork/traffic/trafficItem/2
        """
        queryData = {'from': '/traffic',
                    'nodes': [{'node': 'trafficItem', 'properties': ['name'], 'where': [{"property": "name", "regex": trafficItemName}]}
                    ]}
        queryResponse = self.query(data=queryData, silentMode=False)
        try:
            return queryResponse.json()['result'][0]['trafficItem'][0]['href']
        except:
            return 0

    def applyTraffic(self):
        """
        Description
            Apply the configured traffic.
        """
        restApiHeader = '/api'+self.sessionUrl.split('/api')[1]
        response = self.post(self.sessionUrl+'/traffic/operations/apply', data={'arg1': restApiHeader+'/traffic'})
        if self.waitForComplete(response, self.sessionUrl+'/traffic/operations/apply/'+response.json()['id']) == 1:
            raise IxNetRestApiException

    def applyOnTheFly(self):
        """
         Description
            Apply configuration changes on the fly while Topology is running.
        """
        response = self.post(self.sessionUrl+'/globals/topology/operations/applyonthefly',
                             data={'arg1': '/api/v1/sessions/1/ixnetwork/globals/topology'})
        if self.waitForComplete(response, self.sessionUrl+'/globals/topology/operations/applyonthefly'+response.json()['id']) == 1:
            raise IxNetRestApiException

    def regenerateTrafficItems(self, trafficItemList='all'):
        """
        Description
            Performs regenerate on Traffic Items.

        Parameter
            trafficItemList: 'all' will automatically regenerate from all Traffic Items.
                             Or provide a list of Traffic Items.
                             ['/api/v1/sessions/1/ixnetwork/traffic/trafficItem/1', ...]
        """
        if trafficItemList == 'all':
            response = self.get(self.sessionUrl + "/traffic/trafficItem")
            trafficItemList = ["%s" % (str(i["links"][0]["href"])) for i in response.json()]
        else:
            if type(trafficItemList) != list:
                trafficItemList = trafficItemList.split(' ')

        url = self.sessionUrl+"/traffic/trafficItem/operations/generate"
        data = {"arg1": trafficItemList}
        self.logInfo('\nRegenerating traffic items: %s' % trafficItemList)
        response = self.post(url, data=data)
        if self.waitForComplete(response, url+'/'+response.json()['id']) == 1:
            raise IxNetRestApiException

    def startTraffic(self, blocking=True):
        """
        Description
            Start traffic and verify traffic is started.

        Parameter
            blocking: True|False: Blocking doesn't return until the server has 
                      started traffic and ready for stats.  Unblocking is the opposite.

        Syntax
            POST: http://{apiServerIp:port}/api/v1/sessions/1/ixnetwork/traffic/operations/start
                  data={arg1: http://{apiServerIp:port}/api/v1/sessions/1/ixnetwork/traffic}
        """
        self.logInfo('\nstartTraffic: %s' % self.sessionUrl+'/traffic/operations/start')
        if blocking == False:
            response = self.post(self.sessionUrl+'/traffic/operations/start', data={'arg1': self.sessionUrl+'/traffic'})
            self.checkTrafficState(expectedState=['started', 'startedWaitingForStats'], timeout=45)

        if blocking == True:
            queryData = {"from": "/traffic",
                "nodes": [{"node": "trafficItem", "properties": ["enabled"], "where": [{"property": "enabled", "regex": "true"}]}]}
            queryResponse = self.query(data=queryData, silentMode=False)
            enabledTrafficItemHrefList = [trafficItem['href'] for trafficItem in queryResponse.json()['result'][0]['trafficItem']]
            response = self.post(self.sessionUrl+'/traffic/operations/startstatelesstrafficblocking', data={'arg1': enabledTrafficItemHrefList})
            # Wait a few seconds before calling getStats() or else viewObj is not created.
            time.sleep(2)
        self.logInfo('startTraffic: Successfully started')

    def stopTraffic(self):
        """
        Description
            Stop traffic and verify traffic has stopped.

        Syntax
            POST: http://{apiServerIp:port}/api/v1/sessions/1/ixnetwork/traffic/operations/stop
                  data={arg1: http://{apiServerIp:port}/api/v1/sessions/1/ixnetwork/traffic}
        """
        self.logInfo('\nstopTraffic: %s' % self.sessionUrl+'/traffic/operations/stop')
        response = self.post(self.sessionUrl+'/traffic/operations/stop', data={'arg1': self.sessionUrl+'/traffic'})
        self.checkTrafficState(expectedState=['stopped', 'stoppedWaitingForStats'])
        time.sleep(3)

    def copyFileWindowsToRemoteWindows(self, windowsPathAndFileName, localPath, renameDestinationFile=None, includeTimestamp=False):
        """
        Description
            Copy files from the IxNetwork API Server c: drive to local Linux filesystem.
            The filename to be copied will remain the same filename unless you set renameDestinationFile to something you otherwise preferred.
            You could also include a timestamp for the destination file.

        Parameters
            windowsPathAndFileName: The full path and filename to retrieve from Windows API server.
            localPath: The remote Windows destination path to put the file to.
            renameDestinationFile: You could rename the destination file.
            includeTimestamp: True|False.  If False, each time you copy the same file will be overwritten.
        """
        import datetime

        self.logInfo('\ncopyFileWindowsToRemoteWindows: From: %s to %s\n' % (windowsPathAndFileName, localPath))
        windowsPathAndFileName = windowsPathAndFileName.replace('\\', '\\\\')
        fileName = windowsPathAndFileName.split('\\')[-1]
        fileName = fileName.replace(' ', '_')
        # Default location: "C:\\Users\\<user name>\\AppData\\Local\\sdmStreamManager\\common"
        destinationPath = '/api/v1/sessions/1/ixnetwork/files/'+fileName
        currentTimestamp = datetime.datetime.now().strftime('%H%M%S')

        # Step 1 of 2:
        response = self.post(self.sessionUrl+'/operations/copyfile',
                             data={"arg1": windowsPathAndFileName, "arg2": destinationPath})

        # curl http://{apiServerIp:port}/api/v1/sessions/1/ixnetwork/files/AggregateResults.csv -O -H "Content-Type: application/octet-stream" -output /home/hgee/AggregateResults.csv

        # Step 2 of 2:
        requestStatus = self.get(self.sessionUrl+'/files/%s' % (fileName), stream=True, ignoreError=True)
        if requestStatus.status_code == 200:
            if renameDestinationFile is not None:
                fileName = renameDestinationFile

            contents = requestStatus.raw.read()

            if includeTimestamp:
                tempFileName = fileName.split('.')
                if len(tempFileName) > 1:
                    extension = fileName.split('.')[-1]
                    fileName = tempFileName[0]+'_' + currentTimestamp + '.' + extension
                else:
                    fileName = tempFileName[0]+'_' + currentTimestamp

                localPath = localPath+'/'+fileName
            else:
                localPath = localPath+'/'+fileName

            with open(localPath, 'wb') as downloadedFileContents:
                downloadedFileContents.write(contents)

            response = self.get(self.sessionUrl+'/files')

            self.logInfo('\nA copy of your saved file/report is in:\n\t%s' % (windowsPathAndFileName))
            self.logInfo('\ncopyFileWindowsToLocalLinux: %s' % localPath)
        else:
            self.logInfo('\ncopyFileWindowsToLocalLinux Error: Failed to download file from IxNetwork API Server.')

    def copyFileWindowsToLocalLinux(self, windowsPathAndFileName, localPath, renameDestinationFile=None, includeTimestamp=False):
        """
        Description
            Copy files from the IxNetwork API Server c: drive to local Linux filesystem.
            The filename to be copied will remain the same filename unless you set renameDestinationFile to something you otherwise preferred.
            You could also include a timestamp for the destination file.

        Parameters
            windowsPathAndFileName: The full path and filename to retrieve from Windows client.
            localPath: The Linux destination path to put the file to.
            renameDestinationFile: You could rename the destination file.
            includeTimestamp: True|False.  If False, each time you copy the same file will be overwritten.
        
        Syntax
            post: /api/v0/sessions/1/ixnetwork/operations/copyfile
            data: {'arg1': windowsPathAndFileName, 'arg2': '/api/v1/sessions/1/ixnetwork/files/'+fileName'}

            Note: 
               To get the Windows path dynamically:
                    
        """
        import datetime

        self.logInfo('\ncopyFileWindowsToLocalLinux: From: %s to %s\n' % (windowsPathAndFileName, localPath))
        fileName = windowsPathAndFileName.split('\\')[-1]
        fileName = fileName.replace(' ', '_')
        destinationPath = '/api/v1/sessions/1/ixnetwork/files/'+fileName
        currentTimestamp = datetime.datetime.now().strftime('%H%M%S')

        # Step 1 of 2:
        response = self.post(self.sessionUrl+'/operations/copyfile',
                             data={"arg1": windowsPathAndFileName, "arg2": destinationPath})

        # curl http://{apiServerIp:port}/api/v1/sessions/1/ixnetwork/files/AggregateResults.csv -O -H "Content-Type: application/octet-stream" -output /home/hgee/AggregateResults.csv

        # Step 2 of 2:
        requestStatus = self.get(self.sessionUrl+'/files/%s' % (fileName), stream=True, ignoreError=True)
        if requestStatus.status_code == 200:
            if renameDestinationFile is not None:
                fileName = renameDestinationFile

            contents = requestStatus.raw.read()

            if includeTimestamp:
                tempFileName = fileName.split('.')
                if len(tempFileName) > 1:
                    extension = fileName.split('.')[-1]
                    fileName = tempFileName[0]+'_' + currentTimestamp + '.' + extension
                else:
                    fileName = tempFileName[0]+'_' + currentTimestamp

                localPath = localPath+'/'+fileName
            else:
                localPath = localPath+'/'+fileName

            with open(localPath, 'wb') as downloadedFileContents:
                downloadedFileContents.write(contents)

            response = self.get(self.sessionUrl+'/files')

            self.logInfo('\nA copy of your saved file/report is in:\n\t%s' % (windowsPathAndFileName))
            self.logInfo('\ncopyFileWindowsToLocalLinux: %s' % localPath)
        else:
            self.logInfo('\ncopyFileWindowsToLocalLinux Error: Failed to download file from IxNetwork API Server.')

    def copyFileWindowsToLocalWindows(self, windowsPathAndFileName, localPath, renameDestinationFile=None, includeTimestamp=False):
        """
        Description
            Copy files from the Windows IxNetwork API Server to a local c: drive destination.
            The filename to be copied will remain the same filename unless you set renameDestinationFile to something you otherwise preferred.
            You could include a timestamp for the destination file.

        Parameters
            windowsPathAndFileName: The full path and filename to retrieve from Windows client.
            localPath: The Windows local filesystem. Ex: C:\\Results.
            renameDestinationFile: You could name the destination file.
            includeTimestamp: True|False.  If False, each time you copy the same file will be overwritten.

        Example:  WindowsPathAndFileName =  'C:\\Users\\hgee\\AppData\\Local\\Ixia\\IxNetwork\\data\\result\\DP.Rfc2544Tput\\9e1a1f04-fca5-42a8-b3f3-74e5d165e68c\\Run0001\\TestReport.pdf'
                  localPath = 'C:\\Results'
        """
        import datetime

        self.logInfo('\ncopyFileWindowsToLocalWindows: From: %s to %s\n' % (windowsPathAndFileName, localPath))
        self.logInfo('\nYou need to manually remove the saved copy in: %s' % windowsPathAndFileName)
        fileName = windowsPathAndFileName.split('\\')[-1]
        if renameDestinationFile:
            fileName = renameDestinationFile

        fileName = fileName.replace(' ', '_')
        if includeTimestamp:
            currentTimestamp = datetime.datetime.now().strftime('%H%M%S')
            tempFileName = fileName.split('.')
            if len(tempFileName) > 1:
                extension = fileName.split('.')[-1]
                fileName = tempFileName[0]+'_' + currentTimestamp + '.' + extension
            else:
                fileName = tempFileName[0]+'_' + currentTimestamp

        destinationPath = localPath+'\\'+fileName
        response = self.post(self.sessionUrl+'/operations/copyfile',
                             data={"arg1": windowsPathAndFileName, "arg2": destinationPath})

    def takeSnapshot(self, viewName='Flow Statistics', windowsPath=None, localLinuxPath=None,
                    renameDestinationFile=None, includeTimestamp=False):
        """
        Description
            Take a snapshot of the vieweName statistics.  This is a two step process.
            1> Take a snapshot of the statistics and store it in the C: drive.
            2> Copy the statistics from the c: drive to remote Linux.

        Parameters
            viewName: The name of the statistics to get.
            windowsPath: A C: drive + path to store the snapshot: c:\\Results
            localLinuxPath: None|A path. If None, this API won't copy the stat file to local Linux.
                       The stat file will remain on Windows c: drive.
            renameDestinationFile: None or a name of the file other than the viewName.
            includeTimestamp: True|False: To include a timestamp at the end of the file.

        Example:
            takeSnapshot(viewName='Flow Statistics', windowsPath='C:\\Results', localLinuxPath='/home/hgee',
                        renameDestinationFile='my_renamed_stat_file.csv', includeTimestamp=True)
        """
        # TODO: For Linux API server
        #    POST /api/v1/sessions/1/ixnetwork/operations/getdefaultsnapshotsettings
        #    "Snapshot.View.Csv.Location: \"/root/.local/share/Ixia/IxNetwork/data/logs/Snapshot CSV\""

        if windowsPath is None: raise IxNetRestApiException('\nMust include windowsPath\n')

        data = {'arg1': [viewName], 'arg2': [
                            "Snapshot.View.Contents: \"allPages\"",
                            "Snapshot.View.Csv.Location: \"{0}\"".format(windowsPath),
                            "Snapshot.View.Csv.GeneratingMode: \"kOverwriteCSVFile\"",
                            "Snapshot.View.Csv.StringQuotes: \"True\"",
                            "Snapshot.View.Csv.SupportsCSVSorting: \"False\"",
                            "Snapshot.View.Csv.FormatTimestamp: \"True\"",
                            "Snapshot.View.Csv.DumpTxPortLabelMap: \"False\"",
                            "Snapshot.View.Csv.DecimalPrecision: \"3\""
                            ]
                }
        url = self.sessionUrl+'/operations/takeviewcsvsnapshot'
        response = self.post(url, data=data)
        if self.waitForComplete(response, url+'/'+response.json()['id']) == 1:
            raise IxNetRestApiException

        #response = self.get(self.sessionUrl+'/files?filename=Flow Statistics.csv&absolute=c:\\Results', ignoreError=True)
        if localLinuxPath:
            # Get the snapshot. Use the csvFilename that was specified and the location
            self.copyFileWindowsToLocalLinux('{0}\\{1}.csv'.format(windowsPath, viewName), localLinuxPath,
                                            renameDestinationFile=renameDestinationFile, includeTimestamp=includeTimestamp)

    def getViewObject(self, viewName='Flow Statistics'):
        """
        Description
            To get just the statistic view object.
            Mainly used by internal APIs such as takeCsvSnapshot that
            requires the statistics view object handle.

        Parameter
         viewName:  Options (case sensitive):
            "Port Statistics"
            "Tx-Rx Frame Rate Statistics"
            "Port CPU Statistics"
            "Global Protocol Statistics"
            "Protocols Summary"
            "Port Summary"
            "OSPFv2-RTR Drill Down"
            "OSPFv2-RTR Per Port"
            "IPv4 Drill Down"
            "L2-L3 Test Summary Statistics"
            "Flow Statistics"
            "Traffic Item Statistics"
        """
        self.logInfo('\ngetStats: %s' % viewName)
        viewList = self.get("%s/%s/%s" % (self.sessionUrl, "statistics", "view"))
        views = ["%s/%s/%s/%s" % (self.sessionUrl, "statistics", "view", str(i["id"])) for i in viewList.json()]
        for view in views:
            # GetAttribute
            response = self.get(view)
            caption = response.json()["caption"]
            if viewName == caption:
                # viewObj: sessionUrl + "/statistics/view/11"
                viewObj = view
                return viewObj
        return None

    def getProtocolListByPort(self, port):
        """
        Description
            For IxNetwork Classic Framework only:
            Get all enabled protocolss by the specified port.

        Parameter
            port: (chassisIp, cardNumber, portNumber) -> ('10.10.10.1', '2', '8')
        """
        chassis = str(port[0])
        card = str(port[1])
        port = str(port[2])
        specifiedPort = (chassis, card, port)
        enabledProtocolList = []
        response = self.get(self.sessionUrl+'/vport')
        vportList = ['%s/%s/%s' % (self.sessionUrl, 'vport', str(i["id"])) for i in response.json()]
        for vport in vportList:
            response = self.get(vport, 'assignedTo')
            # 10.219.117.101:1:5
            assignedTo = response.json()['assignedTo']
            currentChassisIp  = str(assignedTo.split(':')[0])
            currentCardNumber = str(assignedTo.split(':')[1])
            currentPortNumber = str(assignedTo.split(':')[2])
            currentPort = (currentChassisIp, currentCardNumber, currentPortNumber)
            if currentPort != specifiedPort:
                continue
            else:
                response = self.get(vport+'/protocols?links=true')
                if response.status_code == 200:
                     #print 'json', response.json()['links']
                    for protocol in response.json()['links']:
                        currentProtocol = protocol['href']
                        url = self.httpHeader+currentProtocol
                        response = self.get(url)
                        if 'enabled' in response.json() and response.json()['enabled'] == True:
                            # Exclude ARP object
                            if 'arp' not in currentProtocol:
                                enabledProtocolList.append(str(currentProtocol))

        return enabledProtocolList

    def getProtocolListByPortNgpf(self, port):
        """
        Description
            For IxNetwork NGPF only:
            This API will get all enabled protocolss by the specified port.

        Parameter
            port: [chassisIp, cardNumber, portNumber]
                  Example: ['10.10.10.1', '2', '8']

        Returns
            [] = If no protocol is configured.
            A list of configured protocols associated with the specified port.
                 Ex: ['/api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv4/1/ospfv2',
                      '/api/v1/sessions/1/ixnetwork/topology/2/deviceGroup/1/ethernet/1/ipv4/1/ospfv2']
        """
        chassis = str(port[0])
        card = str(port[1])
        port = str(port[2])
        specifiedPort = (chassis, card, port)
        enabledProtocolList = []
        response = self.get(self.sessionUrl+'/topology')
        topologyList = ['%s/%s/%s' % (self.sessionUrl, 'topology', str(i["id"])) for i in response.json()]
        for topology in topologyList:
            response = self.get(topology+'/deviceGroup')
            deviceGroupList = ['%s/%s/%s' % (topology, 'deviceGroup', str(i["id"])) for i in response.json()]
            for deviceGroup in deviceGroupList:
                response = self.get(deviceGroup+'/ethernet')
                ethernetList = ['%s/%s/%s' % (deviceGroup, 'ethernet', str(i["id"])) for i in response.json()]
                for ethernet in ethernetList:
                    response = self.get(ethernet+'/ipv4')
                    ipv4List = ['%s/%s/%s' % (ethernet, 'ipv4', str(i["id"])) for i in response.json()]
                    response = self.get(ethernet+'/ipv6')
                    ipv6List = ['%s/%s/%s' % (ethernet, 'ipv6', str(i["id"])) for i in response.json()]
                    for layer3Ip in ipv4List+ipv6List:
                        url = layer3Ip+'?links=true'
                        response = self.get(url)
                        for protocol in response.json()['links']:
                            currentProtocol = protocol['href']
                            print('\nProtocol URL:', currentProtocol)

                            if (bool(re.match('^/api/.*(ipv4|ipv6)/[0-9]+$', currentProtocol))):
                                continue
                            if (bool(re.match('^/api/.*(ipv4|ipv6)/[0-9]+/port$', currentProtocol))):
                                continue
                            url = self.httpHeader+currentProtocol
                            response = self.get(url)
                            if response.json() == []:
                                # The currentProtocol is not configured.
                                continue
                            else:
                                enabledProtocolList.append(str(currentProtocol))

        return enabledProtocolList

    def getPortsByProtocol(self, protocolName):
        """
        Description
            For IxNetwork Classic Framework only:
            Based on the specified protocol, return all ports associated withe the protocol.

        Parameter
           protocolName options:
              bfd, bgp, cfm, eigrp, elmi, igmp, isis, lacp, ldp, linkOam, lisp, mld,
              mplsOam, mplsTp, openFlow, ospf, ospfV3, pimsm, ping, rip, ripng, rsvp,
              static, stp

         Returns: [chassisIp, cardNumber, portNumber]
                  Example: [('10.219.117.101', '1', '1'), ('10.219.117.101', '1', '2')]

         Returns [] if no port is configured with the specified protocolName
        """
        portList = []
        response = self.get(self.sessionUrl+'/vport')
        # ['http://{apiServerIp:port}/api/v1/sessions/1/ixnetwork/vport/1']
        vportList = ['%s/%s/%s' % (self.sessionUrl, 'vport', str(i["id"])) for i in response.json()]

        # Go through each port that has the protocol enabled.
        for vport in vportList:
            # http://{apiServerIp:port}/api/v1/sessions/1/ixnetwork/vport/1/protocols/ospf
            currentProtocol = vport+'/protocols/'+protocolName
            response = self.get(currentProtocol)
            if response.json()['enabled'] == True:
                # 10.219.117.101:1:5
                response = self.get(vport)
                assignedTo = response.json()['assignedTo']
                currentChassisIp  = str(assignedTo.split(':')[0])
                currentCardNumber = str(assignedTo.split(':')[1])
                currentPortNumber = str(assignedTo.split(':')[2])
                currentPort = (currentChassisIp, currentCardNumber, currentPortNumber)
                portList.append(currentPort)

        return portList

    def getPortsByProtocolNgpf(self, protocolName):
        """
        Description
            For IxNetwork NGPF only:
            Based on the specified protocol, return all ports associated with the protocol.

         Returns
            [chassisIp, cardNumber, portNumber]
            Example: [['10.219.117.101', '1', '1'], ['10.219.117.101', '1', '2']]

            Returns [] if no port is configured with the specified protocolName

         protocolName options:
            ['ancp',
            'bfdv4Interface',
            'bgpIpv4Peer',
            'bgpIpv6Peer',
            'dhcpv4relayAgent',
            'dhcpv6relayAgent',
            'dhcpv4server',
            'dhcpv6server',
            'geneve',
            'greoipv4',
            'greoipv6',
            'igmpHost',
            'igmpQuerier',
            'lac',
            'ldpBasicRouter',
            'ldpBasicRouterV6',
            'ldpConnectedInterface',
            'ldpv6ConnectedInterface',
            'ldpTargetedRouter',
            'ldpTargetedRouterV6',
            'lns',
            'mldHost',
            'mldQuerier',
            'ptp',
            'ipv6sr',
            'openFlowController',
            'openFlowSwitch',
            'ospfv2',
            'ospfv3',
            'ovsdbcontroller',
            'ovsdbserver',
            'pcc',
            'pce',
            'pcepBackupPCEs',
            'pimV4Interface',
            'pimV6Interface',
            'ptp',
            'rsvpteIf',
            'rsvpteLsps',
            'tag',
            'vxlan'
        """
        portList = []
        response = self.get(self.sessionUrl+'/topology')
        topologyList = ['%s/%s/%s' % (self.sessionUrl, 'topology', str(i["id"])) for i in response.json()]
        for topology in topologyList:
            response = self.get(topology+'/deviceGroup')
            deviceGroupList = ['%s/%s/%s' % (topology, 'deviceGroup', str(i["id"])) for i in response.json()]
            for deviceGroup in deviceGroupList:
                response = self.get(deviceGroup+'/ethernet')
                ethernetList = ['%s/%s/%s' % (deviceGroup, 'ethernet', str(i["id"])) for i in response.json()]
                for ethernet in ethernetList:
                    response = self.get(ethernet+'/ipv4')
                    ipv4List = ['%s/%s/%s' % (ethernet, 'ipv4', str(i["id"])) for i in response.json()]
                    response = self.get(ethernet+'/ipv6')
                    ipv6List = ['%s/%s/%s' % (ethernet, 'ipv6', str(i["id"])) for i in response.json()]
                    for layer3Ip in ipv4List+ipv6List:
                        url = layer3Ip+'/'+protocolName
                        print('\nProtocol URL:', url)
                        response = self.get(url)
                        if response.json() == []:
                            continue
                        response = self.get(topology)
                        vportList = response.json()['vports']
                        for vport in vportList:
                            response = self.get(self.httpHeader+vport)
                            assignedTo = response.json()['assignedTo']
                            currentChassisIp  = str(assignedTo.split(':')[0])
                            currentCardNumber = str(assignedTo.split(':')[1])
                            currentPortNumber = str(assignedTo.split(':')[2])
                            currentPort = [currentChassisIp, currentCardNumber, currentPortNumber]
                            portList.append(currentPort)
                            self.logInfo('\tFound port configured: %s' % currentPort)
        return portList

    def flapBgpPeerNgpf(self, bgpObjHandle, enable=True, flapList='all', uptime=0, downtime=0):
        """
        Description
           This API will enable or disable flapping on either all or a list of BGP IP routes.
           If you are configuring routes to enable, you could also set the uptime and downtime in seconds.

        Parameters
            bgpObjHandle: The bgp object handle.
                         /api/v1/sessions/<int>/ixnetwork/topology/<int>/deviceGroup/<int>/ethernet/<int>/ipv4/<int>/bgpIpv4Peer/<int>
            enable: True or False
                - Default = True
            flapList: 'all' or a list of IP route addresses to enable/disable.
                      [['160.1.0.1', '160.1.0.2',...]
                - Default = 'all'
            uptime: In seconds.
                - Defaults = 0
            downtime: In seconds.
                - Defaults = 0

        Syntax
           POST = /api/v1/sessions/<int>/ixnetwork/topology/<int>/deviceGroup/<int>/ethernet/<int>/ipv4/<int>/bgpIpv4Peer/<int>
        """
        if flapList != 'all' and type(flapList) != list:
            ipRouteListToFlap = flapList.split(' ')

        response = self.get(self.httpHeader+bgpObjHandle)
        networkAddressList = response.json()['localIpv4Ver2']
        count = len(networkAddressList)

        # Recreate an index list based on user defined ip route to enable/disable
        indexToFlapList = []
        if flapList != 'all':
            for ipRouteAddress in flapList:
                # A custom list of indexes to enable/disable flapping based on the IP address index number.
                indexToFlapList.append(networkAddressList.index(ipRouteAddress))

        # Copy the same index list for uptime and downtime
        indexUptimeList = indexToFlapList
        indexDowntimeList = indexToFlapList
        response = self.get(self.httpHeader+bgpObjHandle)
        enableFlappingMultivalue = response.json()['flap']
        upTimeMultivalue = response.json()['uptimeInSec']
        downTimeMultivalue = response.json()['downtimeInSec']
        flappingResponse = self.get(self.httpHeader + enableFlappingMultivalue)
        uptimeResponse = self.get(self.httpHeader + upTimeMultivalue)
        downtimeResponse = self.get(self.httpHeader + downTimeMultivalue)

        # Flapping IP addresses
        flapOverlayList = []
        uptimeOverlayList = []
        downtimeOverlayList = []
        # Build a valueList of either "true" or "false"
        if flapList == 'all':
            for counter in range(0,count):
                if enable == True:
                    flapOverlayList.append("true")
                if enable == False:
                    flapOverlayList.append("false")
                uptimeOverlayList.append(str(uptime))
                downtimeOverlayList.append(str(downtime))

        if flapList != 'all':
            currentFlappingValueList = flappingResponse.json()['values']
            currentUptimeValueList   = uptimeResponse.json()['values']
            currentDowntimeValueList = downtimeResponse.json()['values']

            indexCounter = 0
            for (eachFlapValue, eachUptimeValue, eachDowntimeValue) in zip(currentFlappingValueList, currentUptimeValueList,
                                                                           currentDowntimeValueList):
                # Leave the setting alone on this index position. User did not care to change this value.
                if indexCounter not in indexToFlapList:
                    flapOverlayList.append(eachFlapValue)
                    uptimeOverlayList.append(eachUptimeValue)
                    downtimeOverlayList.append(eachDowntimeValue)
                else:
                    # Change the value on this index position.
                    if enable == True:
                        flapOverlayList.append("true")
                    else:
                        flapOverlayList.append("false")
                    uptimeOverlayList.append(str(uptime))
                    downtimeOverlayList.append(str(downtime))
                indexCounter += 1

        self.patch(self.httpHeader + enableFlappingMultivalue+'/valueList', data={'values': flapOverlayList})
        self.patch(self.httpHeader + upTimeMultivalue+'/valueList', data={'values': uptimeOverlayList})
        self.patch(self.httpHeader + downTimeMultivalue+'/valueList', data={'values': downtimeOverlayList})

    def flapBgpRoutesNgpf(self, prefixPoolObj, enable=True, ipRouteListToFlap='all', uptime=0, downtime=0, ip='ipv4'):
        """
        Description
           This API will enable or disable flapping on either all or a list of BGP IP routes.
           If you are configuring routes to enable, you could also set the uptime and downtime in seconds.

        Parameters
            prefixPoolObj = The Network Group PrefixPool object that was returned by configNetworkGroup()
                            /api/v1/sessions/<int>/ixnetwork/topology/<int>/deviceGroup/<int>/networkGroup/<int>/ipv4PrefixPools/<int>
            enable: True or False
                - Default = True
            ipRouteListToFlap: 'all' or a list of IP route addresses to enable/disable.
                                 [['160.1.0.1', '160.1.0.2',...]
                - Default = 'all'
            upTime: In seconds.
                - Defaults = 0
            downTime: In seconds.
                - Defaults = 0
            ip: ipv4 or ipv6
                - Defaults = ipv4

        Syntax
           POST = For IPv4: http://{apiServerIp:port}/api/v1/sessions/<int>/ixnetwork/topology/<int>/deviceGroup/<int>/networkGroup/<int>/ipv4PrefixPools/<int>/bgpIPRouteProperty

                  For IPv6: http://{apiServerIp:port}/api/v1/sessions/<int>/ixnetwork/topology/<int>/deviceGroup/<int>/networkGroup/<int>/ipv4PrefixPools/<int>/bgpV6IPRouteProperty
        """

        if ipRouteListToFlap != 'all' and type(ipRouteListToFlap) != list:
            ipRouteListToFlap = ipRouteListToFlap.split(' ')

        # Get a list of configured IP route addresses
        response = self.get(self.httpHeader+prefixPoolObj)
        networkAddressList = response.json()['lastNetworkAddress']
        count = len(networkAddressList)

        # Recreate an index list based on user defined ip route to enable/disable
        indexToFlapList = []
        if ipRouteListToFlap != 'all':
            for ipRouteAddress in ipRouteListToFlap:
                # A custom list of indexes to enable/disable flapping based on the IP address index number.
                indexToFlapList.append(networkAddressList.index(ipRouteAddress))

        # Copy the same index list for uptime and downtime
        indexUptimeList = indexToFlapList
        indexDowntimeList = indexToFlapList

        if ip == 'ipv4':
            response = self.get(self.httpHeader+prefixPoolObj+'/bgpIPRouteProperty')
        if ip == 'ipv6':
            response = self.get(self.httpHeader+prefixPoolObj+'/bgpV6IPRouteProperty')

        enableFlappingMultivalue = response.json()[0]['enableFlapping']
        upTimeMultivalue = response.json()[0]['uptime']
        downTimeMultivalue = response.json()[0]['downtime']
        flappingResponse = self.get(self.httpHeader + enableFlappingMultivalue)
        uptimeResponse = self.get(self.httpHeader + upTimeMultivalue)
        downtimeResponse = self.get(self.httpHeader + downTimeMultivalue)

        # Flapping IP addresses
        flapOverlayList = []
        uptimeOverlayList = []
        downtimeOverlayList = []
        # Build a valueList of either "true" or "false"
        if ipRouteListToFlap == 'all':
            for counter in range(0,count):
                if enable == True:
                    flapOverlayList.append("true")
                if enable == False:
                    flapOverlayList.append("false")
                uptimeOverlayList.append(str(uptime))
                downtimeOverlayList.append(str(downtime))

        if ipRouteListToFlap != 'all':
            currentFlappingValueList = flappingResponse.json()['values']
            currentUptimeValueList   = uptimeResponse.json()['values']
            currentDowntimeValueList = downtimeResponse.json()['values']

            indexCounter = 0
            for (eachFlapValue, eachUptimeValue, eachDowntimeValue) in zip(currentFlappingValueList,
                                                                           currentUptimeValueList, currentDowntimeValueList):
                # Leave the setting alone on this index position. User did not care to change this value.
                if indexCounter not in indexToFlapList:
                    flapOverlayList.append(eachFlapValue)
                    uptimeOverlayList.append(eachUptimeValue)
                    downtimeOverlayList.append(eachDowntimeValue)
                else:
                    # Change the value on this index position.
                    if enable == True:
                        flapOverlayList.append("true")
                    else:
                        flapOverlayList.append("false")
                    uptimeOverlayList.append(str(uptime))
                    downtimeOverlayList.append(str(downtime))
                indexCounter += 1

        self.patch(self.httpHeader + enableFlappingMultivalue+'/valueList', data={'values': flapOverlayList})
        self.patch(self.httpHeader + upTimeMultivalue+'/valueList', data={'values': uptimeOverlayList})
        self.patch(self.httpHeader + downTimeMultivalue+'/valueList', data={'values': downtimeOverlayList})

    def startStopIpv4Ngpf(self, ipv4ObjList, action='start'):
        """
        Description
           Start or stop IPv4 header.

        Parameters
            ipv4ObjList: Provide a list of one or more IPv4 object handles to start or stop.
                 Ex: ["/api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv4/1", ...]

            action: start or stop
        """
        if type(ipv4ObjList) != list:
            raise IxNetRestApiException('startStopIpv4Ngpf error: The parameter ipv4ObjList must be a list of objects.')

        url = self.sessionUrl+'/topology/deviceGroup/ethernet/ipv4/operations/'+action
        data = {'arg1': ipv4ObjList}
        self.logInfo('\nstartStopIpv4Ngpf: {0}'.format(action))
        response = self.post(url, data=data)
        if self.waitForComplete(response, url+'/'+response.json()['id']) == 1:
            raise IxNetRestApiException

    def startStopBgpNgpf(self, bgpObjList, action='start'):
        """
        Description
            Start or stop BGP protocol

        Parameters
            bgpObjList: Provide a list of one or more BGP object handles to start or stop.
                 Ex: ["/api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv4/1/bgpIpv4Peer", ...]

            action: start or stop
        """
        if type(bgpObjList) != list:
            raise IxNetRestApiException('startStopBgpNgpf error: The parameter bgpObjList must be a list of objects.')

        url = self.sessionUrl+'/topology/deviceGroup/ethernet/ipv4/bgpIpv4Peer/operations/'+action
        data = {'arg1': bgpObjList}
        self.logInfo('\nstartStopBgpNgpf: {0}'.format(action))
        response = self.post(url, data=data)
        if self.waitForComplete(response, url+'/'+response.json()['id']) == 1:
            raise IxNetRestApiException

    def startStopIgmpHostNgpf(self, igmpHostObjList, action='start'):
        """
        Description
            Start or stop IGMP Host protocol

        Parameters
            igmpHostObjList: Provide a list of one or more IGMP host object handles to start or stop.
                 Ex: ["/api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv4/1/igmpHost/1", ...]

        action: start or stop
        """
        if type(igmpHostObjList) != list:
            raise IxNetRestApiException('igmpHostObjNgpf error: The parameter igmpHostObjList must be a list of objects.')

        url = self.sessionUrl+'/topology/deviceGroup/ethernet/ipv4/igmpHost/operations/'+action
        data = {'arg1': igmpHostObjList}
        self.logInfo('\nstartStopIgmpHostNgpf: {0}'.format(action))
        response = self.post(url, data=data)
        if self.waitForComplete(response, url+'/'+response.json()['id']) == 1:
            raise IxNetRestApiException

    def startStopPimV4InterfaceNgpf(self, pimV4ObjList, action='start'):
        """
        Description
            Start or stop PIM IPv4 interface.

        Parameters
            pimV4ObjList: Provide a list of one or more PIMv4 object handles to start or stop.
                       Ex: ["/api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv4/1/pimV4Interface/1", ...]

            action: start or stop
        """
        if type(pimV4ObjList) != list:
            raise IxNetRestApiException('startStopPimV4InterfaceNgpf error: The parameter pimv4ObjList must be a list of objects.')

        url = self.sessionUrl+'/topology/deviceGroup/ethernet/ipv4/pimV4Interface/operations/'+action
        data = {'arg1': pimV4ObjList}
        self.logInfo('\nstartStopPimV4InterfaceNgpf: {0}'.format(action))
        self.logInfo('\t%s' % pimV4ObjList)
        response = self.post(url, data=data)
        if self.waitForComplete(response, url+'/'+response.json()['id']) == 1:
            raise IxNetRestApiException

    def startStopMldHostNgpf(self, mldHostObjList, action='start'):
        """
        Description
            Start or stop MLD Host.  For IPv6 only.

        Parameters
            mldHostObjList: Provide a list of one or more mldHost object handles to start or stop.
                         Ex: ["/api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv6/2/mldHost/1", ...]

            action: start or stop
        """
        if type(mldHostObjList) != list:
            raise IxNetRestApiException('startStopMldHostNgpf error: The parameter mldHostObjList must be a list of objects.')

        url = self.sessionUrl+'/topology/deviceGroup/ethernet/ipv6/mldHost/operations/'+action
        data = {'arg1': mldHostObjList}
        self.logInfo('\nstartStopMldHostNgpf: {0}'.format(action))
        self.logInfo('\t%s' % mldHostObjList)
        response = self.post(url, data=data)
        if self.waitForComplete(response, url+'/'+response.json()['id']) == 1:
            raise IxNetRestApiException

    def startStopIsisL3Ngpf(self, isisObjList, action='start'):
        """
        Description
            Start or stop ISIS protocol.

        Parameters
            isisObjList: Provide a list of one or more mldHost object handles to start or stop.
                      Ex: ["/api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/isisL3/3", ...]

        action = start or stop
        """
        if type(isisObjList) != list:
            raise IxNetRestApiException('startStopIsisL3Ngpf error: The parameter isisObjList must be a list of objects.')

        url = self.sessionUrl+'/topology/deviceGroup/ethernet/isisL3/operations/'+action
        data = {'arg1': isisObjList}
        self.logInfo('\nstartStopIsisL3Ngpf: {0}'.format(action))
        self.logInfo('\t%s' % isisObjList)
        response = self.post(url, data=data)
        if self.waitForComplete(response, url+'/'+response.json()['id']) == 1:
            raise IxNetRestApiException

    def enableDisableIgmpGroupRangeNgpf(self, protocolSessionUrl, groupRangeList, action='disable'):
        """
         Description:
             To enable or disable specific multicast group range IP addresses by using overlay.

             1> Get a list of all the Multicast group range IP addresses.
             2> Get the multivalue list of ACTIVE STATE group ranges.
             3> Loop through the user list "groupRangeList" and look
                for the index position of the specified group range IP address.
             4> Using overlay to enable|disable the index value.

             Note: If an overlay is not created, then create one by:
                   - Creating a "ValueList" for overlay pattern.
                   - And add an Overlay.

        Parameters
            protocolSessionUrl: http://{apiServerIp:port}/api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv4/1/igmpHost/1
            groupRangeList: A list of multicast group range addresses to disable.
                                Example: ['225.0.0.1', '225.0.0.5']
            action: disable or enable

        """
        if action == 'disable':
            enableDisable = 'false'
        else:
            enableDisable = 'true'

        url = protocolSessionUrl+'/igmpMcastIPv4GroupList'
        response = self.get(url)
        # /api/v1/sessions/1/ixnetwork/multivalue/59

        # Get startMcastAddr multivalue to get a list of all the configured Group Range IP addresses.
        groupRangeAddressMultivalue = response.json()['startMcastAddr']
        # Get the active multivalue to do the overlay on top of.
        activeMultivalue = response.json()['active']

        # Getting the list of Group Range IP addresses.
        response = self.get(self.httpHeader+groupRangeAddressMultivalue)

        # groupRangeValues are multicast group ranges:
        # [u'225.0.0.1', u'225.0.0.2', u'225.0.0.3', u'225.0.0.4', u'225.0.0.5']
        groupRangeValues = response.json()['values']
        print('\nConfigured groupRangeValues:', groupRangeValues)

        listOfIndexesToDisable = []
        # Loop through user list of specified group ranges to disable.
        for groupRangeIp in groupRangeList:
            index = groupRangeValues.index(groupRangeIp)
            listOfIndexesToDisable.append(index)

        if listOfIndexesToDisable == []:
            raise IxNetRestApiException('disableIgmpGroupRangeNgpf Error: No multicast group range ip address found on your list')

        for index in listOfIndexesToDisable:
            currentOverlayUrl = self.httpHeader+activeMultivalue+'/overlay'
            # http://192.168.70.127:11009/api/v1/sessions/1/ixnetwork/multivalue/5/overlay
            # NOTE:  Index IS NOT zero based.
            self.logInfo('enableDisableIgmpGroupRangeNgpf: %s: %s' % (action, groupRangeValues[index]))
            response = self.post(currentOverlayUrl, data={'index': index+1, 'value': enableDisable})

    def enableDisableMldGroupNgpf(self, protocolSessionUrl, groupRangeList, action='disable'):
        """
         Description:
             For IPv6 only. To enable or disable specific multicast group range IP addresses by using
             overlay.

             1> Get a list of all the Multicast group range IP addresses.
             2> Get the multivalue list of ACTIVE STATE group ranges.
             3> Loop through the user list "groupRangeList" and look
                for the index position of the specified group range IP address.
             4> Using overlay to enable|disable the index value.

             Note: If an overlay is not created, then create one by:
                   - Creating a "ValueList" for overlay pattern.
                   - And add an Overlay.

        Parameters
            protocolSessionUrl: http://{apiServerIp:port}/api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv4/1/igmpHost/1
            groupRangeList: A list of multicast group range addresses to disable.
                                Example: ['ff03::1', 'ff03::2']
            action: disable or enable
        """
        if action == 'disable':
            enableDisable = 'false'
        else:
            enableDisable = 'true'

        url = protocolSessionUrl+'/mldMcastIPv6GroupList'
        response = self.get(url)
        # /api/v1/sessions/1/ixnetwork/multivalue/59

        # Get startMcastAddr multivalue to get a list of all the configured Group Range IP addresses.
        groupRangeAddressMultivalue = response.json()['startMcastAddr']
        # Get the active multivalue to do the overlay on top of.
        activeMultivalue = response.json()['active']

        # Getting the list of Group Range IP addresses.
        response = self.get(self.httpHeader+groupRangeAddressMultivalue)

        # groupRangeValues are multicast group ranges:
        # ['ff03::1', 'ff03::2']
        groupRangeValues = response.json()['values']
        self.logInfo('\nConfigured groupRangeValues: %s' % groupRangeValues)

        listOfIndexesToDisable = []
        # Loop through user list of specified group ranges to disable.
        for groupRangeIp in groupRangeList:
            index = groupRangeValues.index(groupRangeIp)
            listOfIndexesToDisable.append(index)

        if listOfIndexesToDisable == []:
            raise IxNetRestApiException('disableMldGroupNgpf Error: No multicast group range ip address found on your list')

        for index in listOfIndexesToDisable:
            currentOverlayUrl = self.httpHeader+activeMultivalue+'/overlay'
            # http://192.168.70.127:11009/api/v1/sessions/1/ixnetwork/multivalue/5/overlay
            # NOTE:  Index IS NOT zero based.
            self.logInfo('enableDisableMldGroupNgpf: %s: %s' % (action, groupRangeValues[index]))
            response = self.post(currentOverlayUrl, data={'index': index+1, 'value': enableDisable})

    def sendIgmpJoinNgpf(self, igmpHostUrl, multicastIpAddress):
        """
        Description
            Send IGMP join.
            If multicastIpAddress is 'all', this will send IGMP join on all multicast addresses.
            Else, provide a list of multicast IP addresses to send join.

        Parameters
            igmpHostUrl: 'http://{apiServerIp:port}/api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv4/1/igmpHost/1'
            multicastIpAddress: 'all' or a list of multicast IP addresses to send join.
                                 Example: ['225.0.0.3', '225.0.0.4']
        """
        # Based on the list of multicastIpAddress, get all their indexes.
        response = self.get(igmpHostUrl+'/igmpMcastIPv4GroupList')
        startMcastAddrMultivalue = response.json()['startMcastAddr']

        response = self.get(self.httpHeader+startMcastAddrMultivalue)
        listOfConfiguredMcastIpAddresses = response.json()['values']
        self.logInfo('\nsendIgmpJoinNgpf: List of configured Mcast IP addresses: %s' % listOfConfiguredMcastIpAddresses)
        if listOfConfiguredMcastIpAddresses == []:
            raise IxNetRestApiException('sendIgmpJoinNgpf: No Mcast IP address configured')

        if multicastIpAddress == 'all':
            listOfMcastAddresses = listOfConfiguredMcastIpAddresses
        else:
            listOfMcastAddresses = multicastIpAddress

        # Note: Index position is not zero based.
        indexListToSend = []
        for eachMcastAddress in listOfMcastAddresses:
            index = listOfConfiguredMcastIpAddresses.index(eachMcastAddress)
            indexListToSend.append(index+1)

        url = igmpHostUrl+'/igmpMcastIPv4GroupList/operations/igmpjoingroup'
        data = {'arg1': [igmpHostUrl+'/igmpMcastIPv4GroupList'], 'arg2': indexListToSend}

        self.logInfo('\nsendIgmpJoinNgpf: %s' % url)
        self.logInfo('\t%s' % multicastIpAddress)
        response = self.post(url, data=data)
        if self.waitForComplete(response, url+response.json()['id']) == 1:
            raise IxNetRestApiException

    def sendIgmpLeaveNgpf(self, igmpHostUrl, multicastIpAddress):
        """
        Description
            Snd IGMP leaves.
            If multicastIpAddress is 'all', this will send IGMP leaves on all multicast addresses.
            Else, provide a list of multicast IP addresses to send leaves.

        Parameters
            igmpHostUrl: 'http://{apiServerIp:port}/api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv4/1/igmpHost/1'
            multicastIpAddress: 'all' or a list of multicast IP addresses to send leaves
                                Example: ['225.0.0.3', '225.0.0.4']
        """
        # Based on the list of multicastIpAddress, get all their indexes.
        response = self.get(igmpHostUrl+'/igmpMcastIPv4GroupList')
        startMcastAddrMultivalue = response.json()['startMcastAddr']

        response = self.get(self.httpHeader+startMcastAddrMultivalue)
        listOfConfiguredMcastIpAddresses = response.json()['values']
        self.logInfo('\nsendIgmpLeaveNgpf: List of configured Mcast IP addresses: %s' % listOfConfiguredMcastIpAddresses)
        if listOfConfiguredMcastIpAddresses == []:
            raise IxNetRestApiException('sendIgmpLeaveNgpf: No Mcast IP address configured')

        if multicastIpAddress == 'all':
            listOfMcastAddresses = listOfConfiguredMcastIpAddresses
        else:
            listOfMcastAddresses = multicastIpAddress

        # Note: Index position is not zero based.
        indexListToSend = []
        for eachMcastAddress in listOfMcastAddresses:
            index = listOfConfiguredMcastIpAddresses.index(eachMcastAddress)
            indexListToSend.append(index+1)

        url = igmpHostUrl+'/igmpMcastIPv4GroupList/operations/igmpleavegroup'
        data = {'arg1': [igmpHostUrl+'/igmpMcastIPv4GroupList'], 'arg2': indexListToSend}
        self.logInfo('\nsendIgmpLeaveNgpf: %s' % url)
        self.logInfo('\t%s' % multicastIpAddress)
        response = self.post(url, data=data)
        if self.waitForComplete(response, url+response.json()['id']) == 1:
            raise IxNetRestApiException

    def sendMldJoinNgpf(self, mldObj, ipv6AddressList):
        """
        Description
            For IPv6 only.
            This API will take the MLD object and loop through all the configured ports
            looking for the specified ipv6Address to send a join.

        Parameter
            ipv6AddressList: 'all' or a list of IPv6 addresses that must be EXACTLY how it is configured on the GUI.
        """
        # Loop all port objects to get user specified IPv6 address to send the join.
        portObjectList = mldObj+'/mldMcastIPv6GroupList/port'
        response = self.get(portObjectList)

        for eachPortIdDetails in response.json():
            currentPortId = eachPortIdDetails['id']
            # For each ID, get the 'startMcastAddr' multivalue
            startMcastAddrMultivalue = eachPortIdDetails['startMcastAddr']

            # Go to the multivalue and get the 'values'
            response = self.get(self.httpHeader+startMcastAddrMultivalue)
            listOfConfiguredGroupIpAddresses = response.json()['values']
            if ipv6AddressList == 'all':
                listOfGroupAddresses = listOfConfiguredGroupIpAddresses
            else:
                listOfGroupAddresses = ipv6AddressList

            for eachSpecifiedIpv6Addr in listOfGroupAddresses:
                if eachSpecifiedIpv6Addr in listOfConfiguredGroupIpAddresses:
                    # if 'values' match ipv4Address, do a join on:
                    #      http://192.168.70.127.:11009/api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv6/2/mldHost/1/mldMcastIPv6GroupList/port/1/operations/mldjoingroup
                    #    arg1: port/1 object
                    url = mldObj+'/mldMcastIPv6GroupList/port/%s/operations/mldjoingroup' % currentPortId
                    portIdObj = mldObj+'/mldMcastIPv6GroupList/port/%s' % currentPortId
                    # portIdObj = http:/{apiServerIp:port}/api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv6/2/mldHost/1/mldMcastIPv6GroupList/port/1
                    response = self.post(url, data={'arg1': [portIdObj]})
                    if self.waitForComplete(response, url+response.json()['id']) == 1:
                        raise IxNetRestApiException

    def sendMldLeaveNgpf(self, mldObj, ipv6AddressList):
        """
        Description
            For IPv6 only.
            This API will take the mld sessionUrl object and loop through all the configured ports
            looking for the specified ipv6Address to send a leave.

        Parameters
            mldObj: http://{apiServerIp:port}/api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv6/2/mldHost/1
            ipv6AddressList: 'all' or a list of IPv6 addresses that must be EXACTLY how it is configured on the GUI.
        """
        # Loop all port objects to get user specified IPv6 address to send the leave.
        portObjectList = mldObj+'/mldMcastIPv6GroupList/port'
        response = post.get(portObjectList)
        for eachPortIdDetails in response.json():
            currentPortId = eachPortIdDetails['id']
            # For each ID, get the 'startMcastAddr' multivalue
            startMcastAddrMultivalue = eachPortIdDetails['startMcastAddr']

            # Go to the multivalue and get the 'values'
            response = self.get(self.httpHeader+startMcastAddrMultivalue)
            listOfConfiguredGroupIpAddresses = response.json()['values']
            if ipv6AddressList == 'all':
                listOfGroupAddresses = listOfConfiguredGroupIpAddresses
            else:
                listOfGroupAddresses = ipv6AddressList

            for eachSpecifiedIpv6Addr in listOfGroupAddresses:
                if eachSpecifiedIpv6Addr in listOfConfiguredGroupIpAddresses:
                    # if 'values' match ipv4Address, do a join on:
                    #      http://{apiServerIp:port}/api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv6/2/mldHost/1/mldMcastIPv6GroupList/port/1/operations/mldjoingroup
                    #    arg1: port/1 object
                    url = mldObj+'/mldMcastIPv6GroupList/port/%s/operations/mldleavegroup' % currentPortId
                    portIdObj = mldObj+'/mldMcastIPv6GroupList/port/%s' % currentPortId
                    # portIdObj = http://{apiServerIp:port}/api/v1/sessions/1/ixnetwork/topology/1/deviceGroup/1/ethernet/1/ipv6/2/mldHost/1/mldMcastIPv6GroupList/port/1
                    response = self.post(url, data={'arg1': [portIdObj]})
                    if self.waitForComplete(response, url+response.json()['id']) == 1:
                        raise IxNetRestApiException

    def ixVmCreateHypervisor(self, enabled='true', serverIp='',
                             hypervisorType='vmware', userLoginName='admin', userPassword='admin'):
        """
        Description
            Create a hypervisor.

        Syntax
            http://{apiServerIp:11009}/api/v1/sessions/1/ixnetwork/availableHardware/virtualChassis

        Parameters
           enabled: true or false.
           serverIp: The vChassis IP address.
           hypervisorType:  vmware or qemu.
           userLoginName: Default = admin
           userPassword:  Default = admin
        """
        vChassisObj = self.sessionUrl+'/availableHardware/virtualChassis'
        url = self.sessionUrl+'/availableHardware/virtualChassis/hypervisor'
        data = {'enabled': enabled,
                'serverIp': serverIp,
                'type': hypervisorType,
                'user': userLoginName,
                'password': userPassword
            }
        response = self.post(url, data=data, ignoreError=True)
        if response.status_code != 201:
            errorMsg = response.json()['errors'][0]['detail']
            if errorMsg == 'Hypervisor already added.':
                response = self.get(url)
                existingHypervisor = response.json()[0]['links'][0]['href']
                self.logInfo('ixVmCreateHypervisor: Hypervisor already added. Returning: %s' % existingHypervisor)
                return existingHypervisor
            else:
                raise IxNetRestApiException('ixVmCreateHypervisor failed:', errorMsg)
        else:
            # http://192.168.70.127:11009/api/v1/sessions/1/ixnetwork/availableHardware/virtualChassis/hypervisor/1
            hypervisorObj = response.json()['links'][0]['href']
            return hypervisorObj

    def ixVmDeleteHypervisor(self, hypervisorServerIp):
        """
        Description
           Delete a hypervisor.

        Syntax
            http://{apiServerIp:11009}/api/v1/sessions/1/ixnetwork/availableHardware/virtualChassis/hypervisor/1

        Parameter
           hypervisorServerIp: The hypervisor's IP address. Mainly the virtual chassis IP.
        """
        response = self.get(self.sessionUrl+'/availableHardware/virtualChassis/hypervisor')
        for eachHypervisor in response.json():
            if eachHypervisor['serverIp'] == hypervisorServerIp:
                self.delete(self.httpHeader+eachHypervisor['links'][0]['href'])

    def ixVmClearPortOwnershipByCardId(self, cardId):
        """
        Description
           Clear ownership on all virtual ports from the provided IxVM cardId.

        Syntax
            http://{apiServerIp:11009}/api/v1/sessions/1/ixnetwork/operations/clearcardownershipbyid"
            data={'arg1': str(cardId)}

         Returns 0 if success
         Returns 1 if failed
        """
        url = self.sessionUrl+'/operations/clearcardownershipbyid'
        data = {"arg1": str(cardId)}
        response = self.post(url, data=data)
        if response.status_code == 202:
            state = response.json()['state']
            result = response.json()['result']
            # state: SUCCESS, ERROR
            # result: Selected card does not exist
            if state == 'ERROR' and result == 'Selected card does not exist':
                return 0 ;# Good
            if state == 'ERROR' and result != 'Selected card does not exist':
                return 1
            if state == 'SUCCESS':
                return 0
        else:
            return 1

    def ixVmAddCardIdPortId(self, cardIdPortIdList):
        """
        Description
           A wrapper API to call ixVmConfigCardId and ixVmConfigPortId.

        Parameter
            cardIdPortIdList: A list of virtual Card and virtual port parameters.

               Example:
               ixvmCardPortList = [{'cardId': 1, 'portId': 1, 'mgmtIp': '192.168.70.12', 'interface': 'eth1',
                                   'promiscuousMode': False, 'mtu': '1500', 'keepAlive': '300', 'portName': 'myPort1'},

                                   {'cardId': 2, 'portId': 1, 'mgmtIp': '192.168.70.13', 'interface': 'eth1',
                                     'promiscuousMode': False, 'mtu': '1500', 'keepAlive': '300', 'portName': 'myPort2'}
                                  ]

        """
        mandatoryCardIdParams = ['cardId', 'mgmtIp']

        for eachList in cardIdPortIdList:
            for eachMandatoryParam in mandatoryCardIdParams:
                if eachMandatoryParam not in eachList:
                    raise IxNetRestApiException('Missing mandatory param for ixVm cardId: {0}\n\n{1}'.format(eachMandatoryParam, eachList))

        for eachList in cardIdPortIdList:
            # cardId config
            cardId = eachList['cardId']
            mgmtIp = eachList['mgmtIp']

            if 'portId' not in eachList: portId = '1'
            else: portId = eachList['portId']

            if 'cardName' not in eachList: cardName = None
            else: cardName = eachList['cardName']

            if 'keepAlive' in eachList:
                keepAlive = eachList['keepAlive']
            else:
                keepAlive = '300'

            # portId config
            if 'interface' in eachList:
                interface = eachList['interface']
            else:
                interface = 'eth1'

            if 'portName' in eachList:
                portName = eachList['portName']
            else:
                portName = None

            if 'promiscuousMode' in eachList:
                promiscuousMode = eachList['promiscuousMode']
            else:
                promiscuousMode = 'false'

            if 'mtu' in eachList:
                mtu = eachList['mtu']
            else:
                mtu = '1500'

            cardObj = self.ixVmConfigCardId(cardId=cardId, cardName=cardName, mgmtIp=mgmtIp, keepAlive=keepAlive)
            if cardObj != 1:
                # /api/v1/sessions/1/ixnetwork/availableHardware/virtualChassis/ixVmCard/1
                cardPortObj = self.ixVmConfigPortId(cardObj, interface=interface, portId=portId,
                                                    portName=portName, promiscuousMode=promiscuousMode, mtu=mtu)

        for eachCard in self.ixVmGetListCardId():
            self.logInfo('\tCreated:%s' % eachCard)

    def ixVmConfigCardId(self, cardId=1, cardName=None, mgmtIp='', keepAlive=300):
        """
        Description
           Add/Configure a virtual line card.

        Syntax
           http://{apiServerIp:11009}/availableHardware/virtualChassis/ixVmCard

        Parameters
           cardId:   The cardId.  Must begin with 1 and in sequential order.
           cardName: Optional: Specify a name for the card.
           mgmtIp:   The virtual line card's management IP address.
           keepAlive: Integer in seconds
        """
        url = self.sessionUrl+'/availableHardware/virtualChassis/ixVmCard'
        data = {"cardId": str(cardId),
                "managementIp": str(mgmtIp),
                "keepAliveTimeout": int(keepAlive)
                }
        response = self.post(url, data=data, ignoreError=True)
        if response.status_code == 400:
            self.logInfo('\n')
            for error in response.json()['errors']:
                self.logInfo('\t%s' % error['detail'])
            raise IxNetRestApiException

        if cardName is not None:
            self.patch(url, data={'cardName': cardName})

        ixVmCardObj = response.json()['links'][0]['href']
        return ixVmCardObj

    def ixVmConfigPortId(self, cardUrl, interface='eth1', portId='1', portName=None, promiscuousMode='false', mtu='1500'):
        """
        Description
            Add/Configure a virtual port to the cardId.

        Parameters
            cardUrl:    The cardId object: /api/v1/sessions/1/ixnetwork/availableHardware/virtualChassis/ixVmCard/1
            interface:  eth1|eth2|eth3 ...
            portId:     Optional: The portId. Must begin with 1. Warning! You will have a misconfiguration if you don't begin with ID 1.
            portName:   Optional: Specify the name of the virtual port.
            promiscuousMode: true|false
            mtu:        Optional: The MTU frame size.
        """
        url = self.httpHeader+cardUrl+'/ixVmPort'
        data = {'interface': str(interface),
                'portId': str(portId),
                'promiscMode': str(promiscuousMode),
                'mtu': str(mtu),
                }
        response = self.post(url, data=data)
        # /api/v1/sessions/1/ixnetwork/availableHardware/virtualChassis/ixVmCard/2/ixVmPort/1
        if portName is not None:
            self.patch(url, data={'portName': portName})

        return response.json()['links'][0]['href']

    def refreshHardware(self, chassisObj):
        """
        Description
            Refresh the chassis

        Syntax
            http://{apiServerIp:11009}/availableHardware/chassis/operations/refreshinfo

        Parameter
            chassisObj:  The chassis object
                         Ex: '/api/v1/sessions/1/ixnetwork/availableHardware/chassis/1'
        """
        response = self.post(self.sessionUrl+'/availableHardware/chassis/operations/refreshinfo', data={'arg1': [chassisObj]})
        if self.waitForComplete(response, self.sessionUrl+'/availableHardware/chassis/operations/refreshinfo') == 1:
            raise IxNetRestApiException

    def ixVmRediscoverAppliances(self):
        """
        Description
            Assuming that the virtual load module appliances (VM) are already created.
            Now you want to add them. This is step 1 of 2.
            Next step is to add them as useable ports.

        Returns
            Returns XML data format
        """
        url = self.sessionUrl+'/operations/rediscoverappliances'
        self.logInfo('\nixVmRediscoverAppliances URL: %s' % url)
        response = self.post(url)
        # XML format
        if self.waitForComplete(response, url+'/'+response.json()['id']) == 1:
            raise IxNetRestApiException

    def ixVmRebuildChassisTopology(self, ixNetworkVersion):
        """
        Description
            Remove all connected IxVM CardId/PortIds

        Parameter
            ixNetworkVersion: The version of IxNetwork.  Ex: 8.20

        Syntax
            POST: http://{apiServerIp:port}/api/v1/sessions/1/ixnetwork/operations/rebuildchassistopology
            arg1: IxNetwork version that should be used to filter appliances.
            arg2: Flag that enables reconfiguration on the same slots for the previous cards. (true|false)
            arg3: Promiscuous Mode (true|false)
        """
        url = self.sessionUrl+'/operations/rebuildchassistopology'
        data = {"arg1": str(ixNetworkVersion), "arg2": "false", "arg3": "false"}
        self.logInfo('\nixVmRebuildChassisTopology')
        response = self.post(url, data=data)
        if self.waitForComplete(response, url+'/'+response.json()['id']) == 1:
            raise IxNetRestApiException
            # Returns a list of discovered machines in XML format.

    def verifyAllQuickTestNames(self, quickTestNameList):
        """
        Verify the list quickTestNameList to see if all the Quick Test names are configured in IxNetwork.
        quickTestNameList: A list of Quick Test names.
        """
        noSuchQuickTestName = []
        allConfiguredQuickTestNames = []
        response = self.get(self.sessionUrl+'/quickTest')
        allConfiguredQuickTestHandles = response.json()['testIds']

        for qtHandle in allConfiguredQuickTestHandles:
            #allConfiguredQuickTestNames.append(ixNet.getAttribute(qtHandle, 'name'))
            response = self.get(self.httpHeader+qtHandle)
            allConfiguredQuickTestNames.append(response.json()['name'])

        for userDefinedQuickTestName in quickTestNameList:
            if userDefinedQuickTestName not in allConfiguredQuickTestNames:
                noSuchQuickTestName.append(userDefinedQuickTestName)

        if noSuchQuickTestName != '':
            for noSuchTestName in noSuchQuickTestName:
                raise IxNetRestApiException('No such Quick Test name:', noSuchTestName)

    def getAllQuickTestHandles(self):
        """
        Description
            Get all the Quick Test object handles

        Returns:
            ['/api/v1/sessions/1/ixnetwork/quickTest/rfc2544throughput/2',
             '/api/v1/sessions/1/ixnetwork/quickTest/rfc2889broadcastRate/1',
             '/api/v1/sessions/1/ixnetwork/quickTest/rfc2889broadcastRate/2']
        """
        response = self.get(self.sessionUrl+'/quickTest')
        quickTestHandles = []
        for eachTestId in response.json()['testIds']:
            quickTestHandles.append(eachTestId)
        return quickTestHandles

    def getAllQuickTestNames(self):
        quickTestNameList = []
        for eachQtHandle in self.getAllQuickTestHandles():
            response = self.get(self.httpHeader+eachQtHandle)
            quickTestNameList.append(response.json()['name'])
        return quickTestNameList

    def getQuickTestHandleByName(self, quickTestName):
        """
        Description
            Get the Quick Test object handle by the name.

        Parameter
            quickTestName: The name of the Quick Test.
        """
        for quickTestHandle in self.getAllQuickTestHandles():
            response = self.get(self.httpHeader+quickTestHandle)
            currentQtName = response.json()['name']
            if (bool(re.match(quickTestName, currentQtName, re.I))):
                return quickTestHandle

    def getQuickTestNameByHandle(self, quickTestHandle):
        """
        quickTestHandle = /api/v1/sessions/1/ixnetwork/quickTest/rfc2544throughput/2
        """
        response = self.get(self.httpHeader + quickTestHandle)
        return response.json()['name']

    def getQuickTestDuration(self, quickTestHandle):
        """
        quickTestHandle = /api/v1/sessions/1/ixnetwork/quickTest/rfc2544throughput/2
        """
        response = self.get(self.httpHeader + quickTestHandle + '/testConfig')
        return response.json()['duration']

    def getQuickTestTotalFrameSizesToTest(self, quickTestHandle):
        """
        quickTestHandle = /api/v1/sessions/1/ixnetwork/quickTest/rfc2544throughput/2
        """
        response = self.get(self.httpHeader + quickTestHandle + '/testConfig')
        return response.json()['framesizeList']

    def applyQuickTest(self, qtHandle):
        """
        Description
            Apply Quick Test configurations

        Parameter
            qtHandle: The Quick Test object handle
        """
        response = self.post(self.sessionUrl+'/quickTest/operations/apply', data={'arg1': qtHandle})
        if self.waitForComplete(response, self.sessionUrl+'/quickTest/operations/apply/'+response.json()['id']) == 1:
            raise IxNetRestApiException('applyTraffic: waitForComplete failed')

    def getQuickTestCurrentAction(self, quickTestHandle):
        """
        quickTestHandle = /api/v1/sessions/1/ixnetwork/quickTest/rfc2544throughput/2
        """
        ixNetworkVersion = self.getIxNetworkVersion()
        match = re.match('([0-9]+)\.[^ ]+ *', ixNetworkVersion)
        if int(match.group(1)) >= 8:
            timer = 10
            for counter in range(1,timer+1):
                response = self.get(self.httpHeader+quickTestHandle+'/results', silentMode=True)
                if counter < timer and response.json()['currentActions'] == []:
                    self.logInfo('getQuickTestCurrentAction is empty. Waiting %s/%s' % (counter, timer))
                    time.sleep(1)
                    continue
                if counter < timer and response.json()['currentActions'] != []:
                    break
                if counter == timer and response.json()['currentActions'] == []:
                    IxNetRestApiException('getQuickTestCurrentActions: Has no action')

            return response.json()['currentActions'][-1]['arg2']
        else:
            response = self.get(self.httpHeader+quickTestHandle+'/results')
            return response.json()['progress']

    def verifyQuickTestInitialization(self, quickTestHandle):
        """
        quickTestHandle = /api/v1/sessions/1/ixnetwork/quickTest/rfc2544throughput/2
        """
        for timer in range(1,20+1):
            currentAction = self.getQuickTestCurrentAction(quickTestHandle)
            print('verifyQuickTestInitialization currentState: %s' % currentAction)
            if timer < 20:
                if currentAction == 'TestEnded' or currentAction == 'None':
                    self.logInfo('\nverifyQuickTestInitialization CurrentState = %s\n\tWaiting %s/20 seconds to change state' % (currentAction, timer))
                    time.sleep(1)
                    continue
                else:
                    break
            if timer >= 20:
                if currentAction == 'TestEnded' or currentAction == 'None':
                    self.showErrorMessage()
                    raise IxNetRestApiException('Quick Test is stuck at TestEnded.')

        ixNetworkVersionNumber = int(self.getIxNetworkVersion().split('.')[0])
        applyQuickTestCounter = 60
        for counter in range(1,applyQuickTestCounter+1):
            quickTestApplyStates = ['InitializingTest', 'ApplyFlowGroups', 'SetupStatisticsCollection']
            currentAction = self.getQuickTestCurrentAction(quickTestHandle)
            if currentAction == None:
                currentAction = 'ApplyingAndInitializing'

            print('\nverifyQuickTestInitialization: %s  Expecting: TransmittingFrames\n\tWaiting %s/%s seconds' % (currentAction, counter, applyQuickTestCounter))
            if ixNetworkVersionNumber >= 8:
                if counter < applyQuickTestCounter and currentAction != 'TransmittingFrames':
                    time.sleep(1)
                    continue

                if counter < applyQuickTestCounter and currentAction == 'TransmittingFrames':
                    self.logInfo('\nVerifyQuickTestInitialization is done applying configuration and has started transmitting frames\n')
                break

            if ixNetworkVersionNumber < 8:
                if counter < applyQuickTestCounter and currentAction == 'ApplyingAndInitializing':
                    time.sleep(1)
                    continue

                if counter < applyQuickTestCounter and currentAction == 'ApplyingAndInitializing':
                    self.logInfo('\nVerifyQuickTestInitialization is done applying configuration and has started transmitting frames\n')
                break

            if counter == applyQuickTestCounter:
                if ixNetworkVersionNumber >= 8 and currentAction != 'TransmittingFrames':
                    self.showErrorMessage()
                    if currentAction == 'ApplyFlowGroups':
                        self.logInfo('\nIxNetwork is stuck on Applying Flow Groups. You need to go to the session to FORCE QUIT it.\n')
                    raise IxNetRestApiException('\nVerifyQuickTestInitialization is stuck on %s. Waited %s/%s seconds' % (
                            currentAction, counter, applyQuickTestCounter))

                if ixNetworkVersionNumber < 8 and currentAction != 'Trial':
                    self.showErrorMessage()
                    raise IxNetRestApiException('\nVerifyQuickTestInitialization is stuck on %s. Waited %s/%s seconds' % (
                            currentAction, counter, applyQuickTestCounter))

    def startQuickTest(self, quickTestHandle):
        """
        Description
            Start a Quick Test

        Parameter
            quickTestHandle: The Quick Test object handle.
            /api/v1/sessions/{id}/ixnetwork/quickTest/rfc2544throughput/2

        Syntax
           POST: http://{apiServerIp:port}/api/v1/sessions/{1}/ixnetwork/quickTest/operations/start
                 data={arg1: '/api/v1/sessions/{id}/ixnetwork/quickTest/rfc2544throughput/2'}
                 headers={'content-type': 'application/json'}
        """
        url = self.sessionUrl+'/quickTest/operations/start'
        self.logInfo('\nstartQuickTest:%s' % url)
        response = self.post(url, data={'arg1': quickTestHandle})
        if self.waitForComplete(response, url+'/'+response.json()['id']) == 1:
            raise IxNetRestApiException

    def stopQuickTest(self, quickTestHandle):
        """
        Description
            Stop the Quick Test.

        Parameter
            quickTestHandle: The Quick Test object handle.
            /api/v1/sessions/{id}/ixnetwork/quickTest/rfc2544throughput/2

        Syntax
           POST: http://{apiServerIp:port}/api/v1/sessions/{1}/ixnetwork/quickTest/operations/stop
                 data={arg1: '/api/v1/sessions/{id}/ixnetwork/quickTest/rfc2544throughput/2'}
                 headers={'content-type': 'application/json'}
        """
        url = self.sessionUrl+'/quickTest/operations/stop'
        response = self.post(url, data={'arg1': quickTestHandle})
        if self.waitForComplete(response, url+'/'+response.json()['id']) == 1:
            raise IxNetRestApiException

    def monitorQuickTestRunningProgress(self, quickTestHandle, getProgressInterval=10):
        """
        Description
            monitor the Quick Test running progress.
            For Linux API server only, it must be a NGPF configuration. (Classic Framework is not supported in REST)

        Parameters
            quickTestHandle: /api/v1/sessions/{1}/ixnetwork/quickTest/rfc2544throughput/2
        """

        isRunningBreakFlag = 0
        trafficStartedFlag = 0
        waitForRunningProgressCounter = 0
        counter = 1

        while True:
            response = self.get(self.httpHeader+quickTestHandle+'/results', silentMode=True)
            isRunning = response.json()['isRunning']
            if isRunning == True:
                response = self.get(self.httpHeader+quickTestHandle+'/results', silentMode=True)
                currentRunningProgress = response.json()['progress']
                if bool(re.match('^Trial.*', currentRunningProgress)) == False:
                    if waitForRunningProgressCounter < 30:
                        self.logInfo('isRunning=True. Waiting for trial runs {0}/30 seconds'.format(waitForRunningProgressCounter))
                        waitForRunningProgressCounter += 1
                        time.sleep(1)
                    if waitForRunningProgressCounter == 30:
                        raise IxNetRestApiException('isRunning=True. No quick test stats showing.')
                else:
                    trafficStartedFlag = 1
                    self.logInfo(currentRunningProgress)
                    counter += 1
                    time.sleep(getProgressInterval)
                    continue
            else:
                if trafficStartedFlag == 1:
                    # We only care about traffic not running in the beginning.
                    # If traffic ran and stopped, then break out.
                    self.logInfo('\nisRunning=False. Quick Test is complete')
                    return 0
                if isRunningBreakFlag < 20:
                    print('isRunning=False. Wait {0}/20 seconds'.format(isRunningBreakFlag))
                    isRunningBreakFlag += 1
                    time.sleep(1)
                    continue
                if isRunningBreakFlag == 20:
                    raise IxNetRestApiException('Quick Test failed to start:', response.json()['status'])

    def getQuickTestResultPath(self, quickTestHandle):
        """
        quickTestHandle = /api/v1/sessions/1/ixnetwork/quickTest/rfc2544throughput/2
        """
        response = self.get(self.httpHeader + quickTestHandle + '/results')
        # "resultPath": "C:\\Users\\hgee\\AppData\\Local\\Ixia\\IxNetwork\\data\\result\\DP.Rfc2544Tput\\10694b39-6a8a-4e70-b1cd-52ec756910c3\\Run0001"
        return response.json()['resultPath']

    def getQuickTestResult(self, quickTestHandle, attribute):
        """
        Description
            Get Quick Test result attributes

        Parameter
            quickTestHandle: The Quick Test object handle

        attribute options to get:
           result - Returns pass
           status - Returns none
           progress - blank or Trial 1/1 Iteration 1, Size 64, Rate 10 % Wait for 2 seconds Wait 70.5169449%complete
           startTime - Returns 04/21/17 14:35:42
           currentActions
           waitingStatus
           resultPath
           isRunning - Returns True or False
           trafficStatus
           duration - Returns 00:01:03
           currentViews
        """
        response = self.get(quickTestHandle+'/results')
        return response.json()[attribute]

    def getQuickTestCsvFiles(self, quickTestHandle, copyToPath, csvFile='all'):
        """
        Description
            Copy Quick Test CSV result files to a specified path on either Windows or Linux.
            Note: Currently only supports copying from Windows.
                  Copy from Linux is coming in November.

        quickTestHandle: The Quick Test handle.
        copyToPath: The destination path to copy to.
                    If copy to Windows: c:\\Results\\Path
                    If copy to Linux: /home/user1/results/path

        csvFile: A list of CSV files to get: 'all', one or more CSV files to get:
                 AggregateResults.csv, iteration.csv, results.csv, logFile.txt, portMap.csv
        """
        resultsPath = self.getQuickTestResultPath(quickTestHandle)
        self.logInfo('\ngetQuickTestCsvFiles: %s' % resultsPath)
        if csvFile == 'all':
            getCsvFiles = ['AggregateResults.csv', 'iteration.csv', 'results.csv', 'logFile.txt', 'portMap.csv']
        else:
            if type(csvFile) is not list:
                getCsvFiles = [csvFile]
            else:
                getCsvFiles = csvFile

        for eachCsvFile in getCsvFiles:
            # Backslash indicates the results resides on a Windows OS.
            if '\\' in resultsPath:
                if bool(re.match('[a-z]:.*', copyToPath, re.I)):
                    self.copyFileWindowsToLocalWindows(resultsPath+'\\{0}'.format(eachCsvFile), copyToPath)
                else:
                    self.copyFileWindowsToLocalLinux(resultsPath+'\\{0}'.format(eachCsvFile), copyToPath)
            else:
                # TODO: Copy from Linux to Windows and Linux to Linux.
                pass

    def getQuickTestPdf(self, quickTestHandle, copyToLocalPath, where='remoteLinux', renameDestinationFile=None, includeTimestamp=False):
        """
        Description
           Generate Quick Test result to PDF and retrieve the PDF result file.

        Parameter
           where: localWindows|remoteWindows|remoteLinux. The destination.
           copyToLocalPath: The local destination path to store the PDF result file.
           renameDestinationFile: Rename the PDF file.
           includeTimestamp: True|False.  Set to True if you don't want to overwrite previous result file.
        """
        response = self.post(self.httpHeader+quickTestHandle+'/operations/generateReport', data={'arg1': quickTestHandle})
        if response.json()['url'] != '':
            if self.waitForComplete(response, self.httpHeader+response.json()['url']) == 1:
                raise IxNetRestApiException

            if where == 'localWindows':
                response = self.get(self.httpHeader+response.json()['url'])
                self.copyFileWindowsToLocalWindows(response.json()['result'], copyToLocalPath, renameDestinationFile, includeTimestamp)
            if where == 'remoteWindows':
                # TODO: Work in progress.  Not sure if this is possible.
                resultPath = self.getQuickTestResultPath(quickTestHandle)
                #self.copyFileWindowsToRemoteWindows(response.json()['result'], copyToLocalPath, renameDestinationFile, includeTimestamp)
                self.copyFileWindowsToRemoteWindows(resultPath, copyToLocalPath, renameDestinationFile, includeTimestamp)
            if where == 'remoteLinux':
                linuxResultPath = self.getQuickTestResultPath(quickTestHandle)
                self.copyFileWindowsToLocalLinux(linuxResultPath+'\\TestReport.pdf', copyToLocalPath, renameDestinationFile, includeTimestamp)
        else:
            self.logInfo('\ngetQuickTestPdf failed. Result path = %s' % response.json()['result'])

    def query(self, data, silentMode=True):
        """
        Description
           To query for the object in order to modify the configuration.

        Parameter
            # Assuming this is a BGP configuration, which has two Topologies. Below demonstrates how to query the BGP host object by
            # drilling down the Topology by its name and the specific the BGP attributes to modify at the
            # BGPIpv4Peer node: flap, downtimeInSec, uptimeInSec.
            # The from '/' is the entry point to the API tree.
            # Notice all the node. This represents the API tree from the / entry point and starting at Topology level to the BGP
            # host level.
            # NOTE: Use the API Browser tool on the IxNetwork GUI to view the API tree.
            data: {'from': '/',
                    'nodes': [{'node': 'topology',    'properties': ['name'], 'where': [{'property': 'name', 'regex': 'Topo1'}]},
                              {'node': 'deviceGroup', 'properties': [], 'where': []},
                              {'node': 'ethernet',    'properties': [], 'where': []},
                              {'node': 'ipv4',        'properties': [], 'where': []},
                              {'node': 'bgpIpv4Peer', 'properties': ['flap', 'downtimeInSec', 'uptimeInSec'], 'where': []}]
                }

        Example:
            response = restObj.query(data=queryData)
            bgpHostAttributes = response.json()['result'][0]['topology'][0]['deviceGroup'][0]['ethernet'][0]['ipv4'][0]['bgpIpv4Peer'][0]

            # GET THE BGP ATTRIBUTES TO MODIFY
            bgpHostFlapMultivalue = bgpHostAttributes['flap']
            bgpHostFlapUpTimeMultivalue = bgpHostAttributes['uptimeInSec']
            bgpHostFlapDownTimeMultivalue = bgpHostAttributes['downtimeInSec']

            restObj.configMultivalue(bgpHostFlapMultivalue, multivalueType='valueList', data={'values': ['true', 'true']})
            restObj.configMultivalue(bgpHostFlapUpTimeMultivalue, multivalueType='singleValue', data={'value': '60'})
            restObj.configMultivalue(bgpHostFlapDownTimeMultivalue, multivalueType='singleValue', data={'value': '30'})
        """

        url = self.sessionUrl+'/operations/query'
        reformattedData = {'selects': [data]}
        response = self.post(url, data=reformattedData, silentMode=silentMode)
        if self.waitForComplete(response, url+'/'+response.json()['id']) == 1:
            raise IxNetRestApiException
        return response

    def showTopologies(self):
        """
        Description
            Show the NGPF scenario.
        """

        queryData = {'from': '/',
                    'nodes': [{'node': 'topology',      'properties': ['name', 'status', 'vports'], 'where': []},
                                {'node': 'deviceGroup', 'properties': ['name', 'status'], 'where': []},
                                {'node': 'networkGroup','properties': ['name', 'multiplier'], 'where': []},
                                {'node': 'ethernet',    'properties': ['name', 'status', 'sessionStatus', 'enableVlans', 'mac'], 'where': []},
                                {'node': 'vlan',        'properties': ['name', 'vlanId', 'priority'], 'where': []},
                                {'node': 'ipv4',        'properties': ['name', 'status', 'sessionStatus', 'address', 'gatewayIp', 'prefix'], 'where': []},
                                {'node': 'ipv6',        'properties': ['name', 'status', 'sessionStatus'], 'where': []},
                                {'node': 'bgpIpv4Peer', 'properties': ['name', 'status', 'sessionStatus', 'dutIp', 'type', 'localIpv4Ver2', 'localAs2Bytes',
                                                                        'holdTimer', 'flap', 'uptimeInSec', 'downtimeInSec'], 'where': []},
                                {'node': 'bgpIpv6Peer', 'properties': ['name', 'status', 'sessionStatus'], 'where': []},
                                {'node': 'ospfv2',      'properties': ['name', 'status', 'sessionStatus'], 'where': []},
                                {'node': 'ospfv3',      'properties': ['name', 'status', 'sessionStatus'], 'where': []},
                                {'node': 'igmpHost',    'properties': ['name', 'status', 'sessionStatus'], 'where': []},
                                {'node': 'igmpQuerier', 'properties': ['name', 'status', 'sessionStatus'], 'where': []},
                                {'node': 'vxlan',       'properties': ['name', 'status', 'sessionStatus'], 'where': []},
                            ]
                    }
 
        queryResponse = self.query(data=queryData)
        #print('\n', queryResponse.json(), '\n')
        self.logInfo('\n')
        for topology in queryResponse.json()['result'][0]['topology']:
            self.logInfo('TopologyGroup: {0}   Name: {1}'.format(topology['id'], topology['name']))
            self.logInfo('    Status: {0}'.format(topology['status']))
            vportMultiValue = topology['vports']
            for multivalue in vportMultiValue:
                vportResponse = self.get(self.httpHeader+multivalue, silentMode=True)
                self.logInfo('    VportId: {0} Name: {1}  AssignedTo: {2}  State: {3}'.format(vportResponse.json()['id'], vportResponse.json()['name'],
                                                                                    vportResponse.json()['assignedTo'], vportResponse.json()['state']))
            self.logInfo('\n')

            for deviceGroup in topology['deviceGroup']:
                self.logInf0('    DeviceGroup:{0}  Name:{1}'.format(deviceGroup['id'], deviceGroup['name']))
                self.logInfo('\tStatus: {0}'.format(deviceGroup['status']), end='\n\n')
                for ethernet in deviceGroup['ethernet']:
                    self.logInfo('\tEthernet:{0}  Name:{1}'.format(ethernet['id'], ethernet['name']))
                    self.logInfo('\t    Status: {0}'.format(ethernet['status']))
                    enableVlansResponse = self.get(self.httpHeader+ethernet['enableVlans'], silentMode=True)
                    enableVlansValues = enableVlansResponse.json()['values'][0] ;# true|false
                    self.logInfo('\t    Vlan: Disabled\n')
                    for mac,vlan,ipv4 in zip(ethernet['mac'], ethernet['vlan'], ethernet['ipv4']):
                        self.logInfo('\tIPv4:{0} Status: {1}'.format(ipv4['id'], ipv4['status']))
                        macResponse = self.get(self.httpHeader+ethernet['mac'], silentMode=True)
                        vlanResponse = self.get(self.httpHeader+vlan['vlanId'], silentMode=True)
                        priorityResponse = self.get(self.httpHeader+vlan['priority'], silentMode=True)
                        ipResponse = self.get(self.httpHeader+ipv4['address'], silentMode=True)
                        gatewayResponse = self.get(self.httpHeader+ipv4['gatewayIp'], silentMode=True)
                        prefixResponse = self.get(self.httpHeader+ipv4['prefix'], silentMode=True)
                        index = 1
                        self.logInfo('\t    {0:8} {1:14} {2:7} {3:9} {4:12} {5:16} {6:12} {7:7} {8:7}'.format('Index', 'MacAddress', 'VlanId', 'VlanPri', 'EthSession',
                                                                                                        'IPv4Address', 'Gateway', 'Prefix', 'Ipv4Session'))
                        self.logInfo('\t   %s' % '-'*104)
                        for mac,vlanId,vlanPriority,ethSession,ip,gateway,prefix,ipv4Session in zip(macResponse.json()['values'], vlanResponse.json()['values'],
                                                                        priorityResponse.json()['values'],
                                                                        ethernet['sessionStatus'],
                                                                        ipResponse.json()['values'], gatewayResponse.json()['values'],
                                                                        prefixResponse.json()['values'], ipv4['sessionStatus']):
                            self.logInfo('\t    {0:^5} {1:18} {2:^6} {3:^9} {4:13} {5:<15} {6:<13} {7:6} {8:7}'.format(index, mac, vlanId, vlanPriority,
                                                                                                    ethSession, ip, gateway, prefix, ipv4Session))
                            index += 1
                        self.logInfo('\n')
                        
                        for bgpIpv4Peer in ipv4['bgpIpv4Peer']:
                            self.logInfo('\tBGPIpv4Peer:{0}  Name:{1}'.format(bgpIpv4Peer['id'], bgpIpv4Peer['name'], bgpIpv4Peer['status']))
                            dutIpResponse = self.get(self.httpHeader+bgpIpv4Peer['dutIp'], silentMode=True)
                            localIpAddresses = bgpIpv4Peer['localIpv4Ver2']
                            typeResponse = self.get(self.httpHeader+bgpIpv4Peer['type'], silentMode=True)
                            localAs2BytesResponse = self.get(self.httpHeader+bgpIpv4Peer['localAs2Bytes'], silentMode=True)
                            flapResponse = self.get(self.httpHeader+bgpIpv4Peer['flap'], silentMode=True)
                            uptimeResponse = self.get(self.httpHeader+bgpIpv4Peer['uptimeInSec'], silentMode=True)
                            downtimeResponse = self.get(self.httpHeader+bgpIpv4Peer['downtimeInSec'], silentMode=True)
                            self.logInfo('\t    Type: {0}  localAs2Bytes: {1}'.format(typeResponse.json()['values'][0], localAs2BytesResponse.json()['values'][0]))
                            self.logInfo('\t    Status: {0}'.format(bgpIpv4Peer['status']))
                            index = 1
                            for localIp,dutIp,bgpSession,flap,uptime,downtime in zip(localIpAddresses, dutIpResponse.json()['values'], bgpIpv4Peer['sessionStatus'],
                                                                                    flapResponse.json()['values'], uptimeResponse.json()['values'],
                                                                                     downtimeResponse.json()['values']):
                                self.logInfo('\t\t{0}: LocalIp: {1}  DutIp: {2}  SessionStatus: {3}  Flap:{4}  upTime:{5} downTime:{6}'.format(index, localIp, dutIp, bgpSession,
                                                                                                                                        flap, uptime, downtime))
                                index += 1
                        self.logInfo('\n')

                        for ospfv2 in ipv4['ospfv2']:
                            self.logInfo('\t\tOSPFv2:{0}  Name:{1}'.format(ospfv2['id'], ospfv2['name'], ospfv2['status']))
                            self.logInfo('\t\t    Status: {0}'.format(ospfv2['status']), end='\n\n')
                        for igmpHost in ipv4['igmpHost']:
                            self.logInfo('\t\tigmpHost:{0}  Name:{1}'.format(igmpHost['id'], igmpHost['name'], igmpHost['status']))
                            self.logInfo('\t\t    Status: {0}'.format(igmpHost['status']), end='\n\n')
                        for igmpQuerier in ipv4['igmpQuerier']:
                            self.logInfo('\t\tigmpQuerier:{0}  Name:{1}'.format(igmpQuerier['id'], igmpQuerier['name'], igmpQuerier['status']))
                            self.logInfo('\t\t    Status: {0}'.format(igmpQuerier['status']), end='\n\n')
                        for vxlan in ipv4['vxlan']:
                            self.logInfo('\t\tvxlan:{0}  Name:{1}'.format(vxlan['id'], vxlan['name'], vxlan['status']))
                            self.logInfo('\t    Status: {0}'.format(vxlan['status']), end='\n\n')

                for networkGroup in deviceGroup['networkGroup']:
                    self.logInfo('\tNetworkGroup:{0}  Name:{1}'.format(networkGroup['id'], networkGroup['name']))
                    self.logInfo('\t    Multiplier:{0}'.format(networkGroup['multiplier']))                   
                    response = self.get(self.httpHeader+networkGroup['href']+'/ipv4PrefixPools', silentMode=True)
                    response = self.get(self.httpHeader+response.json()[0]['networkAddress'], silentMode=True)
                    self.logInfo('\t    StartingAddress:{0}  EndingAddress:{1}  Prefix:{2}'.format(response.json()['values'][0], response.json()['values'][-1],
                                                                                            response.json()['formatLength']))
                    for ipv6 in ethernet['ipv6']:
                        self.logInfo('\t    IPv6:{0}  Name:{1}'.format(ipv6['id'], ipv6['name']))
                        for bgpIpv6Peer in ipv6['bgpIpv6Peer']:
                            self.logInfo('\t    BGPIpv6Peer:{0}  Name:{1}'.format(bgpIpv6Peer['id'], bgpIpv6Peer['name']))
                        for ospfv3 in ipv6['ospfv3']:
                            self.logInfo('\t    OSPFv3:{0}  Name:{1}'.format(ospfv3['id'], ospfv3['name']))
                        for mldHost in ipv6['mldHost']:
                            self.logInfo('\t    mldHost:{0}  Name:{1}'.format(mldHost['id'], mldHost['name']))
                        for mldQuerier in ipv6['mldQuerier']:
                            self.logInfo('\t    mldQuerier:{0}  Name:{1}'.format(mldQuerier['id'], mldQuerier['name']))
            self.logInfo('\n\n')

    def showTrafficItems(self):
        """
        Description
            Show All Traffic Item details.
        """
        queryData = {'from': '/traffic',
                    'nodes': [{'node': 'trafficItem',    'properties': ['name', 'enabled', 'state', 'biDirectional', 'trafficType', 'warning', 'errors'], 'where': []},
                                {'node': 'endpointSet',   'properties': ['name', 'sources', 'destinations'], 'where': []},
                                {'node': 'configElement', 'properties': ['name', 'endpointSetId', ], 'where': []},
                                {'node': 'frameSize',     'properties': ['type', 'fixedSize'], 'where': []},
                                {'node': 'framePayload',     'properties': ['type', 'customRepeat'], 'where': []},
                                {'node': 'frameRate',     'properties': ['type', 'rate'], 'where': []},
                                {'node': 'frameRateDistribution', 'properties': ['streamDistribution', 'portDistribution'], 'where': []},
                                {'node': 'transmissionControl', 'properties': ['type', 'frameCount', 'burstPacketCount'], 'where': []},
                                {'node': 'tracking',      'properties': ['trackBy'], 'where': []}, 
                            ]   
                    }
 
        queryResponse = self.query(data=queryData)
        #self.logInfo('\n', queryResponse.json(), '\n')
        self.logInfo()
        for ti  in queryResponse.json()['result'][0]['trafficItem']:
            #self.logInfo('\n%s\n', ti)
            self.logInfo('TrafficItem: {0}  Name: {1}  Enabled: {2}  State: {3}'.format(ti['id'], ti['name'], ti['enabled'], ti['state']))
            self.logInfo('\tTrafficType: {0}  BiDirectional: {1}'.format(ti['trafficType'], ti['biDirectional']))
            for tracking in ti['tracking']:
                self.logInfo('\tTrackings: {0}'.format(tracking['trackBy']))

            for endpointSet, cElement in zip(ti['endpointSet'], ti['configElement']):
                self.logInfo('\n\tEndpointSetId: {0}  EndpointSetName: {1}'.format(endpointSet['id'], endpointSet['name']))
                srcList = []
                for src in endpointSet['sources']:
                    srcList.append(src.split('/ixnetwork')[1])
                dstList = []
                for dest in endpointSet['destinations']:
                    dstList.append(dest.split('/ixnetwork')[1]) 
                self.logInfo('\t    Sources: {0}'.format(srcList))
                self.logInfo('\t    Destinations: {0}'.format(dstList))

            #for cElement in ti['configElement']:
                #self.logInfo('\ncElement: %s\n\n' % cElement)
                #self.logInfo('\t    ConfigElement EndpointSetId: {0}'.format(cElement['endpointSetId']))
                self.logInfo('\t    FrameType: {0}  FrameSize: {1}'.format(cElement['frameSize']['type'], cElement['frameSize']['fixedSize']))
                self.logInfo('\t    TranmissionType: {0}  FrameCount: {1}  BurstPacketCount: {2}'.format(cElement['transmissionControl']['type'],
                                                                                                cElement['transmissionControl']['frameCount'],
                                                                                                cElement['transmissionControl']['burstPacketCount']))
                self.logInfo('\t    FrameRateType: {0}  FrameRate: {1}'.format(cElement['frameRate']['type'], cElement['frameRate']['rate']))
            self.logInfo()

    def configMultivalue(self, multivalueUrl, multivalueType, data):
        """
        Description
            Configure multivalues.

        Parameters
            multivalueUrl: The multivalue href. Ex: /api/v1/sessions/1/ixnetwork/multivalue/1
            multivalueType: counter|singleValue|valueList
            data = In Python Dict format. Ex:
                   If singleValue, data={'value': '1.1.1.1'})
                   If valueList,   data needs to be in a [list]:  data={'valueList': [list]}
                   If counter,     data={'start': value, 'direction': increment|decrement, 'step': value}
        """
        if multivalueType == 'counter':
            # Example: macAddress = {'start': '00:01:01:00:00:01', 'direction': 'increment', 'step': '00:00:00:00:00:01'}
            #          data=macAddress)
            self.patch(self.httpHeader+multivalueUrl+'/counter', data=data)

        if multivalueType == 'singleValue':
            # data={'value': value}
            self.patch(self.httpHeader+multivalueUrl+'/singleValue', data=data)

        if multivalueType == 'valueList':
            # data={'values': ['item1', 'item2']}
            self.patch(self.httpHeader+multivalueUrl+'/valueList', data=data)

    def getBgpObject(self, topologyName=None, bgpAttributeList=None):
        queryData = {'from': '/',
                    'nodes': [{'node': 'topology',    'properties': ['name'], 'where': [{'property': 'name', 'regex': topologyName}]},
                              {'node': 'deviceGroup', 'properties': [], 'where': []},
                              {'node': 'ethernet',    'properties': [], 'where': []},
                              {'node': 'ipv4',        'properties': [], 'where': []},
                              {'node': 'bgpIpv4Peer', 'properties': bgpAttributeList, 'where': []}]
                    }
        # QUERY FOR THE BGP HOST ATTRIBITE OBJECTS
        queryResponse = self.query(data=queryData)
        try:
            bgpHostAttributes = queryResponse.json()['result'][0]['topology'][0]['deviceGroup'][0]['ethernet'][0]['ipv4'][0]['bgpIpv4Peer'][0]
            return bgpHostAttributes
        except IndexError:
            raise IxNetRestApiException('\nVerify the topologyName and bgpAttributeList input: {0} / {1}\n'.format(topologyName, bgpAttributeList))
       
    def packetCaptureConfigPortMode(self, port, enableControlPlane=True, enableDataPlane=True):
        """
        Description
           Enable|Disable port capturing for control plane and data plane.

           Values are true or false
             -softwareEnabled == Control Plane
              -hardwareEnabled == Data Plane

        Parameters
            port: [ixChassisIp, 1, 3] => [ixChasssisIp, str(cardNumber), str(portNumber)] 
        """
        vport = self.getVports([port])[0]
        print('\n--- vport:', port, vport)
        self.patch(self.httpHeader+vport, data={'rxMode': 'capture'})
        self.patch(self.httpHeader+vport+'/capture', data={'softwareEnabled': enableControlPlane, 'hardwareEnabled': enableDataPlane}) 

    def packetCaptureStart(self):
        self.post(self.sessionUrl+'/operations/startcapture')

    def packetCaptureStop(self):
        self.post(self.sessionUrl+'/operations/stopcapture')

    def packetCaptureClearTabs(self):
        """
        Description
           Remove all captured tabs
        """
        self.post(self.sessionUrl+'/operations/closeAllTabs')

    def packetCaptureGetCurrentPackets(self, vport):
        """
        Description
           Work in progress
        """
        response = self.get(vport+'/capture/currentPacket')
    
    def convertIxncfgToJson(self, ixncfgFile, destinationPath):
        """
        Description
            This function takes the input .ixncfg config file to be loaded and then convert it
            to json format. The filename will be the same as the input .ixncfg filename, but the
            extension will be .json.  The converted .json file will be saved in the path 
            variable destinationPath.
        
        Parameter
            ixncfgFile: The binary IxNetwork .ixncfg file.
            destinationPath: The destination path to save the .json config file.
        """
        self.loadConfigFile(ixncfgFile)
        filename = ixncfgFile.split('/')[-1]
        match = re.match('(.*).ixncfg', filename)
        if  match:
            filename = match.group(1)

        jsonFilename = destinationPath+'/'+filename+'.json'
        self.exportJsonConfigFile(jsonFilename)  

    def importJsonConfigObj(self, dataObj, type='modify'):
        """
        Description
            For newConfig:
                This is an equivalent to loading a saved .ixncfg file.
                To use this API, your script should have read a JSON config into an object variable.
                Then pass in the json object to the data parameter.

            For modify:
                Import the modified JSON data object to make a configuration modification on the API server.
                Supports one xpath at a time.
                    Example: {"xpath": "/traffic/trafficItem[1]",
                              "enabled": True,
                              "name": "Topo-BGP"}

        Parameter
            data: The JSON config object.
            type: newConfig|modify

        Note
            arg2 value must be a string of JSON data: '{"xpath": "/traffic/trafficItem[1]", "enabled": false}'
        """
        if type is 'modify':
            arg3 = False
            silentMode = False
        if type is 'newConfig':
            arg3 = True
            silentMode = True

        dataReformatted = {"arg1": "/api/v1/sessions/1/ixnetwork/resourceManager",
                           "arg2": json.dumps(dataObj),
                           "arg3": arg3}
        url = self.sessionUrl+'/resourceManager/operations/importconfig'
        response = self.post(url, data=dataReformatted, silentMode=silentMode)
        if self.waitForComplete(response, url+'/'+response.json()['id']) == 1:
            raise IxNetRestApiException

    def importJsonConfigFile(self, jsonFileName, type='modify'):
        """
        Description
            To import a JSON config file to IxNetwork.
            You could state it to import as a modified config or creating a new config.

            The benefit of importing an actual JSON config file is so you could manually use
            IxNetwork Resource Manager to edit any part of the JSON config and add to the
            current configuration

        Parameters
            jsonFileName: The JSON config file. Could include absolute path also.
            type: newConfig|modify
        """

        if type is 'modify':
            arg3 = False
        if type is 'newConfig':
            arg3 = True

        # 1> Read the config file
        self.logInfo('\nReading saved config file')
        with open(jsonFileName, mode='r') as file:
            configContents = file.read()

        fileName = jsonFileName.split('/')[-1]

        # 2> Upload it to the server and give it any name you want for the filename
        if self.apiServerPlatform == 'linux':
            octetStreamHeader = {'content-type': 'application/octet-stream', 'x-api-key': self.apiKey}
        else:
            octetStreamHeader = self.jsonHeader

        uploadFile = self.sessionUrl+'/files?filename='+fileName
        self.logInfo('\nUploading file to server:', uploadFile)
        response = self.post(uploadFile, data=configContents, noDataJsonDumps=True, headers=octetStreamHeader, silentMode=True)

        # 3> Tell IxNetwork to import the JSON config file
        data = {"arg1": "/api/v1/sessions/1/ixnetwork/resourceManager",
                "arg2": "/api/v1/sessions/1/ixnetwork/files/{0}".format(fileName),
                "arg3": arg3}
        url = self.sessionUrl+'/resourceManager/operations/importconfigfile'
        response = self.post(url, data=data)
        if self.waitForComplete(response, url+'/'+response.json()['id']) == 1:
            raise IxNetRestApiException

    def exportJsonConfigFile(self, jsonFileName):
        """
        Description
            Export the current configuration to a JSON format config file.

        Parameters
            jsonFileName: The JSON config file name to create. Could include absolute path also.
        
        Example
            restObj.exportJsonConfigFile(jsonFileName='/path/exportedJsonConfig.json')
        """
        if len(jsonFileName.split(' ')) > 1:
            localPath = jsonFileName.split('/')[:-1]
            localPath = '/'.join(localPath)
        else:
            localPath = '.'
        fileName = jsonFileName.split('/')[-1]
        data = {'arg1': "/api/v1/sessions/1/ixnetwork/resourceManager",
                'arg2': ['/descendant-or-self::*'],
                'arg3': True,
                'arg4': 'json',
                'arg5': '/api/v1/sessions/1/ixnetwork/files/'+fileName
        }
        url = self.sessionUrl+'/resourceManager/operations/exportconfigfile'
        response = self.post(url, data=data)
        if self.waitForComplete(response, url+'/'+response.json()['id']) == 1:
            raise IxNetRestApiException

        response = self.get(self.sessionUrl+'/files')
        absolutePath = response.json()['absolute']
        self.copyFileWindowsToLocalLinux(absolutePath.replace('\\', '\\\\')+'\\\\'+fileName, 
                                        localPath=localPath, 
                                        renameDestinationFile=None,
                                        includeTimestamp=False)
        
        # Indent the serialized json config file
        jsonObj = self.jsonReadConfig(jsonFileName)
        self.jsonWriteToFile(jsonObj, jsonFileName)

    def exportJsonConfigToDict(self):
        """
        Description
            Export the current configuration to a JSON config format and convert to a
            Python Dict.

        Return
            JSON config in a dictionary format.
        """
        data = {'arg1': "/api/v1/sessions/1/ixnetwork/resourceManager",
                'arg2': ['/descendant-or-self::*'],
                'arg3': True,
                'arg4': 'json'
        }
        url = self.sessionUrl+'/resourceManager/operations/exportconfig'
        response = self.post(url, data=data)
        if self.waitForComplete(response, url+'/'+response.json()['id']) == 1:
            raise IxNetRestApiException
        return json.loads(response.json()['result'])

    def getJsonConfigPortList(self, jsonData):
        """
        Description
            Read an exported json data and create a list of all the vports from the json configuration. 
        
        Parameter
            jsonData: The json data after calling: jsonData = jsonReadConfig(jsonConfigFile)
        """
        portList = []
        for vport in jsonData['vport']:
            # /availableHardware/chassis[@alias = '172.28.95.60']/card[1]/port[2]"
            connectedTo = vport['connectedTo']
            match = re.match("/availableHardware/.*'([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)']/card\[([0-9]+)]/port\[([0-9]+)", connectedTo)
            portList.append([match.group(1), match.group(2), match.group(3)])
        return portList

    def jsonAssignPorts(self, jsonObject, portList):
        """
        Description
            Reassign ports.  Will remove the existing JSON config datas: availableHardware, cardId, portId.
            Then recreate JSON datas for availableHardware based on the portList input.

        Parameters
            jsonObject: The JSON config object.
            portList: Example: 
                        portList = [[ixChassisIp, '1', '1'], [ixChassisIp, '2', '1']]
        """
        # Since it is reassigning ports, remove existing chassis's and add what users want.
        jsonObject.pop("availableHardware")
        jsonObject.update({"availableHardware": {
                            "xpath": "/availableHardware",
                            "chassis": []
                        }})

        ixChassisId = 1
        chassisIpList = []
        vportId = 1
        for ports in portList:
            ixChassisIp = ports[0]
            cardId = ports[1]
            portId = ports[2]
            if ixChassisIp not in chassisIpList:
                jsonObject["availableHardware"]["chassis"].insert(0, {"xpath": "/availableHardware/chassis[{0}]".format(ixChassisId),
                                                                        "hostname": ixChassisIp,
                                                                        "card": []
                                                                    })
            cardList = []
            if cardId not in cardList:
                # If card doesn't exist in list, create a new card.
                jsonObject["availableHardware"]["chassis"][0]["card"].insert(0, {"xpath": "/availableHardware/chassis[@alias = {0}/card[{1}]".format(ixChassisIp, cardId)})
                jsonObject["availableHardware"]["chassis"][0]["card"][0].update({"port": []})         
                cardList.append(cardId)
            self.logInfo('\njsonAssignPorts: %s %s %s' % (ixChassisIp, cardId, portId))
            jsonObject["availableHardware"]["chassis"][0]["card"][0]["port"].insert(0, {"xpath": "/availableHardware/chassis[@alias = {0}/card[{1}]/port[{2}]".format(ixChassisIp, cardId, portId)})
            jsonObject["vport"][vportId-1].update({"connectedTo": "/availableHardware/chassis[@alias = {0}]/card[{1}]/port[{2}]".format(ixChassisIp, cardId, portId),
                                            "xpath": "/vport[{0}]".format(vportId)
                                          })
            vportId += 1
            ixChassisId += 1
        return jsonObject

    def jsonReadConfig(self, jsonFile):
        #if os.path.exists(jsonFile) is False:
        #    raise IxNetRestApiException("JSON file doesn't exists: %s" % jsonFile)
        with open(jsonFile.strip()) as inFile:
            jsonData = json.load(inFile)
        return jsonData

    @staticmethod
    def jsonWriteToFile(dataObj, jsonFile, sortKeys=False):
        print('\njsonWriteToFile ...')
        with open(jsonFile, 'w') as outFile:
            json.dump(dataObj, outFile, sort_keys=sortKeys, indent=4)

    @staticmethod
    def jsonPrettyprint(data, sortKeys=False):
        self.logInfo('\n', json.dumps(data, indent=4, sort_keys=sortKeys))

    @staticmethod
    def prettyprintAllOperations(sessionUrl):
        # Dispaly all the operation commands and its description:
        #    http://192.168.70.127:11009/api/v1/sessions/1/ixnetwork/operations

        response = requests.get(sessionUrl+'/operations')
        for item in response.json():
            if 'operation' in item.keys():
                self.logInfo('\n', item['operation'])
                self.logInfo('\t%s' % item['description'])
                if 'args' in item.keys():
                    for nestedKey,nestedValue in item['args'][0].items():
                        self.logInfo('\t\t%s: %s' % (nestedKey, nestedValue))

    @staticmethod
    def printDict(obj, nested_level=0, output=sys.stdout):
        """
        Self.LogInfo each dict key with indentions for readability.
        """
        spacing = '   '
        spacing2 = ' '
        if type(obj) == dict:
            print( '%s' % ((nested_level) * spacing), file=output)
            for k, v in obj.items():
                if hasattr(v, '__iter__'):
                    print('%s%s:' % ( (nested_level+1) * spacing, k), file=output, end='')
                    IxNetRestMain.printDict(v, nested_level+1, output)
                else:
                    print('%s%s: %s' % ( (nested_level + 1) * spacing, k, v), file=output)

            print('%s' % (nested_level * spacing), file=output)
        elif type(obj) == list:
            print('%s[' % ((nested_level) * spacing), file=output)
            for v in obj:
                if hasattr(v, '__iter__'):
                    IxNetRestMain.printDict(v, nested_level + 1, file=output)
                else:
                    print('%s%s' % ((nested_level + 1) * spacing, v), file=output)
            print('%s]' % ((nested_level) * spacing), output)
        else:
            print('%s%s' % ((nested_level * spacing2), obj), file=output)

    def placeholder():
        pass


