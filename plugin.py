# Toon Plugin for Domoticz
#
# 
#
"""
<plugin key="RootedToonPlug" name="Toon Rooted" author="MadPatrick" version="1.1.0" externallink="https://www.domoticz.com/forum/viewtopic.php?f=34&t=34986">
    <description>
	<br/><h2>Domoticz Toon Rooted plugin</h2><br/>
        version: 1.1.0
        <br/>The configuration contains the following sections:
        <ul style="list-style-type:square">
            <li>Interfacing between Domoticz and a rooted Toon</li>
            <li>The rooted toon is directly queried via http json commands</li>
            <li>Toon v1 Zwave values: 2.1, 2.3, 2.5, 2.4 & 2.6</li>
            <li>Toon v2 Zwave values: 2.1, 2.4, 2.6, 2.5 & 2.7</li>
        </ul>
        Get the internalAddress of the device via : http://TOONIP/hdrv_zwave?action=getDevices.json
       <br/>
       <br/>
    </description>
    <params>
        <param field="Address" label="IP Address" width="200px" required="true" default="192.168.1.200" >
        <description>==== general configuration ====</description>
        </param>
        <param field="Port" label="Port" width="50px" required="true" default="80" />
        <param field="Mode1" label="Gas " width="50px" required="true" default="2.1" >
        <description>==== Port configuration ====</description>
        </param>
        <param field="Mode2" label="Elec Normal " width="50px" required="true" default="2.4" />
        <param field="Mode3" label="Elec Low " width="50px" required="true" default="2.6" />
        <param field="Mode4" label="Elec Normal return " width="50px" required="true" default="2.5" />
        <param field="Mode5" label="Elec Low return " width="50px" required="true" default="2.7" />
    </params>
</plugin>

"""


#found URLs:
#happ_pwrusage?action=GetProfileInfo # house and family profile
#happ_thermstat?action=printTableInfo

#Hervat programma
#happ_thermstat?action=changeSchemeState&state=1&temperatureState=

#hdrv_zwave?action=getDevices.json
#hdrv_zwave?action=getContollerInfo
#hdrv_zwave?action=GetContolStatus
#hdrv_zwave?action=GetLinkQuality

#no: 0 -> '10'
#yes = 1 -> '20'
#temporary 2 -> '30'
programStates = ['10','20','30']
rProgramStates = ['0','1','2']
strProgramStates = ['No', 'Yes', 'Manual']

burnerInfos = ['10','20','30']
rBurnerInfos = ['0','1','2']
strBurnerInfos = ['Off', 'CV', 'WW']

#ComfortLevelValue: 0 ->'40'
#HomeLevelValue: 1 -> '30'
#SleepLevelValue: 2 ->  '20'
#AwayLevelValue: 3 -> '10'
#Holiday: 4 ->'60'
#programs = ['40','30','20','10','60']
programs = ['40','30','20','10','50']
rPrograms = ['3','2','1','0','4']
strPrograms = ['Comfort', 'Home', 'Sleep', 'Away','Manual']

import Domoticz
import json
from datetime import datetime

class BasePlugin:
    toonConnThermostatInfo = None
    toonConnBoilerInfo=None
    toonConnSetControl=None
    toonConnZwaveInfo=None
    toonSetControlUrl=""

    ia_gas=''
    ia_ednt=''
    ia_edlt=''
    ia_ernt=''
    ia_erlt=''

    strToonInformation='Waiting for first communication with Toon'

    enabled = False
    def __init__(self):
        #self.var = 123
        return

    def onStart(self):
        Domoticz.Log("onStart called")

        if 1 not in Devices:
            Domoticz.Device(Name="Current Temperature", Unit=1, TypeName="Temperature", Used=1).Create()
        if 2 not in Devices:
            Domoticz.Device(Name="Setpoint Temperature", Unit=2, Type=242, Subtype=1, Used=1).Create()
        if 3 not in Devices:
            programStateOptions= {"LevelActions": "||", "LevelNames": "|No|Yes|Temporary", "LevelOffHidden": "true", "SelectorStyle": "0"}
            Domoticz.Device(Name="Auto Program", Unit=3, Image=15, TypeName="Selector Switch", Options=programStateOptions, Used=1).Create()
        if 4 not in Devices:
            programOptions= {"LevelActions": "||||", "LevelNames": "|Away|Sleep|Home|Comfort|Manual", "LevelOffHidden": "true", "SelectorStyle": "0"}
            Domoticz.Device(Name="Scene", Unit=4, Image=15, TypeName="Selector Switch", Options=programOptions, Used=1).Create()
        if 5 not in Devices:
            Domoticz.Device(Name="Boiler pressure", Unit=5, TypeName="Pressure", Used=1).Create()
        if 6 not in Devices:
            Domoticz.Device(Name="Program info", Unit=6, TypeName="Text", Used=1).Create()
        if 7 not in Devices:
            Domoticz.Device(Name="Gas", Unit=7, TypeName="Gas", Used=1).Create()
            #Domoticz.Device(Name="Gas", Unit=7, Type=243, Subtype=33, Switchtype=1).Create()
        if 8 not in Devices:
            #Domoticz.Device(Name="Electricity", Unit=8, TypeName="Usage").Create()
            Domoticz.Device(Name="Electricity", Unit=8, TypeName="kWh", Used=1).Create()
        if 9 not in Devices:
            Domoticz.Device(Name="Generated Electricity", Unit=9, TypeName="Usage", Used=1).Create()
            #Domoticz.Device(Name="Generated Electricity", Unit=9, Type=243, Subtype=33, Switchtype=4).Create()
        if 10 not in Devices:
            Domoticz.Device(Name="P1 Electricity", Unit=10, Type=250, Subtype=1, Used=1).Create()
        if 11 not in Devices:
            burnerInfoOptions= {"LevelActions": "||", "LevelNames": "|Off|CV|WW", "LevelOffHidden": "true", "SelectorStyle": "0"}
            Domoticz.Device(Name="Boiler State", Unit=11, Image=15, TypeName="Selector Switch", Options=burnerInfoOptions, Used=1).Create()

        self.toonConnThermostatInfo = Domoticz.Connection(Name="Toon Connection", Transport="TCP/IP", Protocol="HTTP", Address=Parameters["Address"], Port=Parameters["Port"])
        self.toonConnThermostatInfo.Connect()

        self.toonConnBoilerInfo = Domoticz.Connection(Name="Toon Connection", Transport="TCP/IP", Protocol="HTTP", Address=Parameters["Address"], Port=Parameters["Port"])
        self.toonConnBoilerInfo.Connect()

        self.toonConnZwaveInfo = Domoticz.Connection(Name="Toon Connection", Transport="TCP/IP", Protocol="HTTP", Address=Parameters["Address"], Port=Parameters["Port"])
        self.toonConnZwaveInfo.Connect()

        self.toonConnSetControl= Domoticz.Connection(Name="Toon Connection", Transport="TCP/IP", Protocol="HTTP", Address=Parameters["Address"], Port=Parameters["Port"])

        Domoticz.Log(json.dumps(Parameters))
        self.ia_gas=Parameters["Mode1"]
        self.ia_ednt=Parameters["Mode2"]
        self.ia_edlt=Parameters["Mode3"]
        self.ia_ernt=Parameters["Mode4"]
        self.ia_erlt=Parameters["Mode5"]

        Domoticz.Heartbeat(5)
        return True


    def onStop(self):
        Domoticz.Debug("onStop called")

    def onConnect(self, Connection, Status, Description):
        Domoticz.Debug("onConnect called")
        requestUrl="/happ_thermstat?action=getThermostatInfo"

        if (Status==0):
            #Domoticz.Log("Connected successfully to: "+Parameters["Address"]+":"+Parameters["Port"])

            headers = { 'Content-Type': 'text/xml; charset=utf-8', \
                          'Connection': 'keep-alive', \
                          'Accept': 'Content-Type: text/html; charset=UTF-8', \
                          'Host': Parameters["Address"], \
                          'User-Agent':'Domoticz/1.0' }

            if (Connection == self.toonConnThermostatInfo):
                Domoticz.Debug("getThermostatInfo created")
                requestUrl="/happ_thermstat?action=getThermostatInfo"
            if (Connection == self.toonConnBoilerInfo):
                Domoticz.Debug("getBoilerInfo created")
                requestUrl="/boilerstatus/boilervalues.txt"
            if (Connection == self.toonConnZwaveInfo):
                Domoticz.Debug("getZwaveInfo created")
                requestUrl="/hdrv_zwave?action=getDevices.json"
            if (Connection == self.toonConnSetControl):
                Domoticz.Debug("getConnSetControl created")
                requestUrl=self.toonSetControlUrl

            Domoticz.Debug("Connecting to: "+Parameters["Address"]+":"+Parameters["Port"] + requestUrl)
            Connection.Send({"Verb":"GET", "URL":requestUrl, "Headers": headers})


        else:
            Domoticz.Log("Failed to connect ("+str(Status)+":"+Description+") to "+Parameters["Address"]+":"+Parameters["Port"])

        return True

    def onMessageThermostatInfo(self, Connection, Response):
        Domoticz.Debug("onMessageThermostatInfo called")
        result='error'
        if 'result' in Response:
            result=Response['result']

        Domoticz.Debug("Toon getThermostatInfo command executed with status: " + result)
        if result!='ok':
            return

        toonInformation={}

        #From toon API info
        #"currentSetpoint": 1050, // Current target temperature for the thermostat
        #"currentDisplayTemp": 2150, // Temperature that is currently on the display
        #"programState": 0, // State of the weekly thermostat schedule (see below)
        #"activeState": -1, // Which programmed setting is active (see below)
        #"nextProgram": -1, // Program type that will be active after the current entry ends.
        #"nextState": -1, // Which programmed setting will be used after the current one ends
        #"nextTime": 0, // Time next programmed setting starts
        #"nextSetpoint": 0, // Which target temperature will be used by the next activeState
        #"errorFound": 255, // 255 means everything ok. Anything else means there is trouble
        #"boilerModuleConnected": 1, // Boilermodule connected or not
        #"realSetpoint": 1050, // The setpoint that is really active based on the program or manual setting
        #"burnerInfo": "0", // Burner state (see below)
        #"otCommError": "0", // info if there is an issue between the boilerModule and the boiler. Will only work for OpenTherm boilers
        #"currentModulationLevel": 0, // Value between 0% and 100% indicating the level that the boiler is heating at. Will only work for OpenTherm boilers
        #"haveOTBoiler": 0 // Value that indicated if a OT boiler is connected.

        if 'currentTemp' in Response:
            currentTemp=float(Response['currentTemp'])/100
            strCurrentTemp="%.1f" % currentTemp
            UpdateDevice(Unit=1, nValue=0, sValue=strCurrentTemp)
            #if (strCurrentTemp!=self.strCurrentTemp):
            #    self.strCurrentTemp=strCurrentTemp
            #    Domoticz.Debug("Updating current Temperature = "+strCurrentTemp)
            #    Devices[1].Update(nValue=0, sValue=strCurrentTemp)

        if 'currentSetpoint' in Response:
            currentSetpoint=float(Response['currentSetpoint'])/100
            strCurrentSetpoint="%.1f" % currentSetpoint
            UpdateDevice(Unit=2, nValue=0, sValue=strCurrentSetpoint)

        if 'programState' in Response:
            programState=int(Response['programState'])
            UpdateDevice(Unit=3, nValue=0, sValue=programStates[programState])

        if 'activeState' in Response:
            program=int(Response['activeState'])
            UpdateDevice(Unit=4, nValue=0, sValue=programs[program])
            
        if 'burnerInfo' in Response:
            burnerInfo=int(Response['burnerInfo'])
            UpdateDevice(Unit=11, nValue=0, sValue=burnerInfos[burnerInfo])

        if 'nextTime' in Response:
            toonInformation['nextTime']=Response['nextTime']

        if 'nextState' in Response:
            toonInformation['nextState']=Response['nextState']

        if 'nextProgram' in Response:
            toonInformation['nextProgram']=Response['nextProgram']

        if 'nextSetpoint'in Response:
            toonInformation['nextSetpoint']=Response['nextSetpoint']


        if (len(toonInformation)==4):
            strToonInformation='No information received from Toon yet (%s)' % toonInformation['nextProgram']
            if int(toonInformation['nextProgram']==-1):
                strToonInformation="No program information available"

            if int(toonInformation['nextProgram'])==0:
                strToonInformation="Progam is off"

            elif int(toonInformation['nextProgram'])>0:
                dt=datetime.fromtimestamp(int(toonInformation['nextTime']))
                strNextTime=dt.strftime("%Y-%d-%m %H:%M:%S")
                strNextProgram=strPrograms[int(toonInformation['nextState'])]
                strNextSetpoint="%.1f" % (float(toonInformation['nextSetpoint'])/100)
                strToonInformation="Next program %s (%s C) at %s" % (strNextProgram, strNextSetpoint, strNextTime)

            UpdateDevice(Unit=6, nValue=0, sValue=strToonInformation)

        return

    def onMessageBoilerInfo(self, Connection, Response):
        Domoticz.Debug("onMessageBoilerInfo called")
        if 'boilerPressure' in Response:
            Domoticz.Debug("boilerpressure: "+("%.1f" % Response['boilerPressure']))
            strBoilerPressure="%.1f" % Response['boilerPressure']
            UpdateDevice(Unit=5, nValue=0, sValue=strBoilerPressure)

        return


    def onMessageZwaveInfo(self, Connection, Response):
        Domoticz.Debug("onMessageZwaveInfo called")
        zwaveDeliveredLtFlow='0'
        zwaveDeliveredNtFlow='0'
        zwaveDeliveredLtQ='0'
        zwaveDeliveredNtQ='0'

        zwaveReceivedLtFlow='0'
        zwaveReceivedNtFlow='0'
        zwaveReceivedLtQ='0'
        zwaveReceivedNtQ='0'


        for zwaveDev in Response:
            zwaveDevInfo=Response[zwaveDev]


            if 'type' in zwaveDevInfo:
                if (zwaveDevInfo['internalAddress']==self.ia_gas):
                    Domoticz.Debug("Zwave Gas usage: "+ zwaveDevInfo['CurrentGasFlow'])
                    Domoticz.Debug("Zwave Gas counter: "+ zwaveDevInfo['CurrentGasQuantity'])
                    UpdateDevice(Unit=7, nValue=0, sValue="%.0f" % (float(zwaveDevInfo['CurrentGasQuantity']) ))

                if (zwaveDevInfo['internalAddress']==self.ia_ednt):
                    zwaveDeliveredNtFlow=zwaveDevInfo['CurrentElectricityFlow']
                    zwaveDeliveredNtQ=zwaveDevInfo['CurrentElectricityQuantity']
                    Domoticz.Debug('elec_delivered_nt: %s, %s' % (zwaveDeliveredNtFlow,zwaveDeliveredNtQ) )

                if (zwaveDevInfo['internalAddress']==self.ia_edlt):
                    zwaveDeliveredLtFlow=zwaveDevInfo['CurrentElectricityFlow']
                    zwaveDeliveredLtQ=zwaveDevInfo['CurrentElectricityQuantity']
                    Domoticz.Debug('elec_delivered_lt: %s, %s' % (zwaveDeliveredLtFlow,zwaveDeliveredLtQ) )

                if (zwaveDevInfo['internalAddress']==self.ia_ernt):
                    zwaveReceivedNtFlow=zwaveDevInfo['CurrentElectricityFlow']
                    zwaveReceivedNtQ=zwaveDevInfo['CurrentElectricityQuantity']
                    Domoticz.Debug('elec_received_nt: %s, %s' % (zwaveReceivedNtFlow,zwaveReceivedNtQ) )

                if (zwaveDevInfo['internalAddress']==self.ia_erlt):
                    zwaveReceivedLtFlow=zwaveDevInfo['CurrentElectricityFlow']
                    zwaveReceivedLtQ=zwaveDevInfo['CurrentElectricityQuantity']
                    Domoticz.Debug('elec_received_lt: %s, %s' % (zwaveReceivedLtFlow,zwaveReceivedLtQ) )


        try:
            zwaveDeliveredFlow=str(int(float(zwaveDeliveredNtFlow))+int(float(zwaveDeliveredLtFlow)))
            zwaveDeliveredQ=str(int(float(zwaveDeliveredNtQ))+int(float(zwaveDeliveredLtQ)))
        except:
            Domoticz.Log("One or more Zwave internal address not configured correctly?")
            return

        Domoticz.Debug("zwaveDelivered: " + zwaveDeliveredFlow+";"+zwaveDeliveredQ)
        UpdateDevice(Unit=8, nValue=0, sValue=zwaveDeliveredFlow+";"+zwaveDeliveredQ)

        zwaveReceivedFlow=str(int(float(zwaveReceivedNtFlow))+int(float(zwaveReceivedLtFlow)))
        zwaveReceivedQ=str(int(float(zwaveReceivedNtQ))+int(float(zwaveReceivedLtQ)))
        Domoticz.Debug("zwaveReceived: " + zwaveReceivedFlow+";"+zwaveReceivedQ)

        UpdateDevice(Unit=9, nValue=0, sValue=zwaveReceivedFlow+";"+zwaveReceivedQ)
        UpdateDevice(Unit=10, nValue=0, sValue=str(int(float(zwaveDeliveredNtQ)))+";"+str(int(float(zwaveDeliveredLtQ)))+";"+str(int(float(zwaveReceivedNtQ)))+";"+str(int(float(zwaveReceivedLtQ)))+";"+zwaveDeliveredFlow+";"+zwaveReceivedFlow)

        return


    def onMessage(self, Connection, Data):
        Domoticz.Debug("onMessage called")

        try:
            strData = Data["Data"].decode("utf-8", "ignore")
        except:
            if (Connection==self.toonConnThermostatInfo):
                Domoticz.Log("Something unexpected while onMessage: ThermostatInfo")
                return
            if (Connection==self.toonConnBoilerInfo):
                Domoticz.Log("Something unexpected while onMessage: BoilerInfo")
                return
            if (Connection==self.toonConnZwaveInfo):
                Domoticz.Log("Something unexpected while onMessage: toonConnZwaveInfo")
                return
            if (Connection==self.toonConnSetControl):
                Domoticz.Log("Something unexpected while onMessage: toonConnSetControl")
                return

            Domoticz.Log("Unknown connection")
            return

        Domoticz.Debug(strData)
        if (strData[0]!='{'):
            Domoticz.Log("onMessage aborted, response format not JSON")
            Domoticz.Log(strData)
            return
        Response = json.loads(strData)

        if (Connection==self.toonConnSetControl):
            Domoticz.Log("onMessage: toonConnSetControl")
            result='error'
            if 'result' in Response:
                result=Response['result']

            Domoticz.Log("Toon set command executed with status: " + result)
            return

        if (Connection==self.toonConnThermostatInfo):
            self.onMessageThermostatInfo(Connection, Response)

        if (Connection==self.toonConnBoilerInfo):
            self.onMessageBoilerInfo(Connection, Response)

        if (Connection==self.toonConnZwaveInfo):
            self.onMessageZwaveInfo(Connection, Response)

        return


    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

        if (Unit == 2):
            strLevel=str(int(Level*100))
            Domoticz.Debug("Toon New setpoint: %s" % str(Level))
            self.strCurrentSetpoint=str(Level)
            Devices[Unit].Update(nValue=0, sValue=str(Level))
            self.toonSetControlUrl="/happ_thermstat?action=setSetpoint&Setpoint=" + strLevel
            self.toonConnSetControl.Connect()

        if (Unit == 3):
            Domoticz.Log("Toon ProgramState")
            Domoticz.Log(str(Level)+" -> " + rProgramStates[int((Level//10)-1)])
            self.programState=str(Level)
            Devices[3].Update(nValue = 0, sValue = str(Level))
            self.toonSetControlUrl="/happ_thermstat?action=changeSchemeState&state="+rProgramStates[int((Level//10)-1)]
            self.toonConnSetControl.Connect()

        if (Unit == 4):
            Domoticz.Debug("Toon Program")
            Domoticz.Debug(str(Level)+" -> "+rPrograms[int((Level//10)-1)])
            self.program=str(Level)
            Devices[4].Update(nValue = 0, sValue = str(Level))
            self.toonSetControlUrl="/happ_thermstat?action=changeSchemeState&state=2&temperatureState="+rPrograms[int((Level//10)-1)]
            Domoticz.Debug(self.toonSetControlUrl)
            self.toonConnSetControl.Connect()

        if (Unit == 11):
            Domoticz.Debug("Toon Boiler")
            Domoticz.Debug(str(Level)+" -> "+rBurnerInfos[int((Level//10)-1)])
            self.burnerInfo=str(Level)
            Devices[11].Update(nValue = 0, sValue = str(Level))
            self.toonSetControlUrl="/happ_thermstat?action=changeSchemeState&state=2&temperatureState="+rBurnerInfos[int((Level//10)-1)]
            Domoticz.Debug(self.toonSetControlUrl)
            self.toonConnSetControl.Connect()

        #tbd send to Toon

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Debug("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Domoticz.Debug("onDisconnect called")

    def onHeartbeat(self):
        Domoticz.Debug("onHeartbeat called")

        if (self.toonConnThermostatInfo.Connected()==False):
            self.toonConnThermostatInfo.Connect()

        if (self.toonConnBoilerInfo.Connected()==False):
            self.toonConnBoilerInfo.Connect()

        if (self.toonConnZwaveInfo.Connected()==False):
            self.toonConnZwaveInfo.Connect()


global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

    # Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return


def UpdateDevice(Unit, nValue, sValue, TimedOut=0, AlwaysUpdate=False):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it
    if (Unit in Devices):
        if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue) or (Devices[Unit].TimedOut != TimedOut):
            try:
                Devices[Unit].Update(nValue=nValue, sValue=str(sValue), TimedOut=TimedOut)
                Domoticz.Debug("Update "+str(nValue)+":'"+str(sValue)+"' ("+Devices[Unit].Name+")")
            except:
                Domoticz.Log("Update of device failed: "+str(Unit)+"!")
    return
