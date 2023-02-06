# Toon Plugin for Domoticz
#
# 
#
"""
<plugin key="RootedToonPlug" name="Toon Rooted" author="MadPatrick" version="1.4.21" externallink="https://github.com/MadPatrick/domoticz_toon">
    <description>
        <br/><h2>Domoticz Toon Rooted plugin</h2><br/>
        version: 1.4.21
        <br/>The configuration contains the following sections:
        <ul style="list-style-type:square">
        <li>Interfacing between Domoticz and a rooted Toon</li>
        <li>The rooted toon is directly queried via http json commands</li>
        <li>Toon Setpoint</li>
        <li>Toon Scenes</li>
        <li>Toon Auto Program and Program info</li>
        <li>Boiler mode</li>
        <li>Boiler pressure   (App installed on Toon)</li>
        <li>Boiler Setpoint   (App installed on Toon)</li>
        <li>Boiler modulation (App installed on Toon)</li>
        <li>Toon P1 data      (P1 connected)</li>
        <li>Toon Gas data     (P1 connected)</li>
        </ul>
        <br/>
        </description>
    <params>
            <param field="Address" label="IP Address" width="200px" required="true" default="192.168.1.200" >
            <description><h2>General configuration</h2>
            IP address and port of your Toon device</description>
        </param>
            <param field="Port" label="Port" width="50px" required="true" default="80" >
        </param>
            <param field="Mode6" label="Toon version" width="200px" required="true" >
            <description>
            <br/>Which Toon version is installed :
            <ul style="list-style-type:square">
            <li>Toon v1 P1_dev default values: 2.1, 2.3, 2.5, 2.4 & 2.6</li>
            <li>Toon v2 P1_dev default values: 2.1, 2.4, 2.6, 2.5 & 2.7</li>
            <li>Otherwise "user defined" and fill in your _dev values in below field</li>
            </ul>
            </description>
            <options>
            <option label="v1" value="v1"/>
            <option label="v2" value="v2"  default="true" />
            <option label="user defined" value="user"/>
            </options>
        </param>
            <param field="Mode1" label="Scene temp " width="200px" required="true" default="18.0;17.0;19.5;20.0" >
            <description><br/>Scene configuration (default=18.0;17.0;19.5;20.0)
            <br/>The order is as follows:   Away;Sleep;Home;Comfort
            <br/>Check on your Toon which temperature value corresponds to which Scene</description>
        </param>
            <param field="Mode2" label="Refresh interval" width="100px">
            <options>
            <option label="20s" value="20"/>
            <option label="30s" value="30"/>
            <option label="1m" value="60" default="true"/>
            <option label="5m" value="300"/>
            <option label="10m" value="600"/>
            <option label="15m" value="900"/>
            </options>
        </param>
            <param field = "Mode3" label="P1 data" width="100px">
            <description><br/>Enable the P1 data
            <br/>Power measurement consumed and returned (solar power)</description>
            <options>
            <option label="Yes" value="Yes"/>
            <option label="No" value="No" default="true"/>
            </options>
        </param>
            <param field="Mode5" label="P1 adresses" width="200px" default="2.1;2.4;2.6;2.5;2.7" >
            <description><br/>Enter user defined P1 adresses separated by ';', example: 2.1;2.4;2.6;2.5;2.7
            <br/><p style="color:red">Get the internalAddress of the device via : <a>http://TOONIP/hdrv_zwave?action=getDevices.json</a>
            <br/>Check your JSON output as described in the readme file for which dev_x.x value you must use</p></description>
        </param>
            <param field = "Mode4" label="Debug logging" width="100px">
            <description><br/>Enable Debug logging</description>
            <options>
            <option label="True" value="Debug"/>
            <option label="False" value="Normal" default="true" />
            </options>
        </param>
    </params>
</plugin>

"""

programStates = ['10','20','30']
rProgramStates = ['0','1','2']
strProgramStates = ['Uit', 'Aan', 'Tijdelijk']

burnerInfos = ['10','20','30']
rBurnerInfos = ['0','1','2']
strBurnerInfos = ['Uit', 'CV', 'WW']

programs = ['40','30','20','10','50']
rPrograms = ['3','2','1','0','4']
strPrograms = ['Weg', 'Slapen', 'Thuis', 'Comfort','Manual']

#device unit number definitions
curTemp = 1
setTemp = 2
autoProgram = 3
scene = 4
boilerPressure = 5
programInfo = 6
gas = 7
electricity = 8
genElectricity = 9
p1electricity = 10
boilerState = 11
boilerModulation = 12
boilerSetPoint = 13
roomHumidity = 14

#zwave device adresses
zwaveAdress = {
    "v1": ["2.1", "2.3", "2.5", "2.4", "2.6"],
    "v2": ["2.1", "2.4", "2.6", "2.5", "2.7"],
    "user": ["3.1", "3.4", "3.6", "3.5", "3.7"]
}

import Domoticz
import json
import requests
from datetime import datetime

class BasePlugin:
    toonConnThermostatInfo = None
    toonConnBoilerInfo=None
    toonConnSetControl=None
    toonConnZwaveInfo=None
    toonSetControlUrl=""
    useZwave = False

    ia_gas=''
    ia_ednt=''
    ia_edlt=''
    ia_ernt=''
    ia_erlt=''

    strToonInformation='Waiting for first communication with Toon'

    def __init__(self):
        #self.var = 123
        return

    def onStart(self):
        Domoticz.Log("onStart called")

        if Parameters["Mode3"] == "Yes":
            self.useZwave = True

        if curTemp not in Devices:
            Domoticz.Device(Name="Temperatuur", Unit=curTemp, TypeName="Temperature", Used=1).Create()
        if setTemp not in Devices:
            Domoticz.Device(Name="Setpunt Temperatuur", Unit=setTemp, Type=242, Subtype=1, Used=1).Create()
        if autoProgram not in Devices:
            programStateOptions= {"LevelActions": "||", "LevelNames": "|Uit|Aan|Tijdelijk", "LevelOffHidden": "true", "SelectorStyle": "0"}
            Domoticz.Device(Name="Auto Program", Unit=autoProgram, Image=15, TypeName="Selector Switch", Options=programStateOptions, Used=1).Create()
        if scene not in Devices:
            programOptions= {"LevelActions": "||||", "LevelNames": "|Weg|Slapen|Thuis|Comfort|Manual", "LevelOffHidden": "true", "SelectorStyle": "0"}
            Domoticz.Device(Name="Scene", Unit=scene, Image=15, TypeName="Selector Switch", Options=programOptions, Used=1).Create()
        if boilerPressure not in Devices:
            Domoticz.Device(Name="Keteldruk", Unit=boilerPressure, TypeName="Pressure", Used=0).Create()
        if programInfo not in Devices:
            Domoticz.Device(Name="Programma info", Unit=programInfo, TypeName="Text", Used=0).Create()
        if boilerState not in Devices:
            burnerInfoOptions= {"LevelActions": "||", "LevelNames": "|Uit|CV|WW", "LevelOffHidden": "true", "SelectorStyle": "0"}
            Domoticz.Device(Name="Ketelmode", Unit=boilerState, Image=15, TypeName="Selector Switch", Options=burnerInfoOptions, Used=1).Create()
        if boilerModulation not in Devices:
            Domoticz.Device(Name="Ketel modulatie", Unit=boilerModulation, Type=243, Subtype=6, Used=0).Create()
        if boilerSetPoint not in Devices:
            Domoticz.Device(Name="Ketel setpoint", Unit=boilerSetPoint, Type=80, Subtype=5, Used=0).Create()
        #TSC        if roomHumidity not in Devices:
        #TSC            Domoticz.Device(Name="Luchtvochtigheid", Unit=roomHumidity, Type=82, Subtype=1, Used=0).Create()

        if self.useZwave:
            if gas not in Devices:
                Domoticz.Device(Name="Gas", Unit=gas, TypeName="Gas", Used=0).Create()
            if electricity not in Devices:
                Domoticz.Device(Name="Electriciteit", Unit=electricity, TypeName="kWh", Used=0).Create()
            if genElectricity not in Devices:
                Domoticz.Device(Name="Opgewekte Electriciteit", Unit=genElectricity, TypeName="Usage", Used=0).Create()
            if p1electricity not in Devices:
                Domoticz.Device(Name="P1 Electriciteit", Unit=p1electricity, Type=250, Subtype=1, Used=0).Create()

        if Parameters["Mode4"] == "Debug":
            Domoticz.Debugging(2)
            DumpConfigToLog()

        self.toonConnThermostatInfo = Domoticz.Connection(Name="Toon Connection", Transport="TCP/IP", Protocol="HTTP", Address=Parameters["Address"], Port=Parameters["Port"])
        self.toonConnThermostatInfo.Connect()

        self.toonConnBoilerInfo = Domoticz.Connection(Name="Toon Connection", Transport="TCP/IP", Protocol="HTTP", Address=Parameters["Address"], Port=Parameters["Port"])
        self.toonConnBoilerInfo.Connect()

        if self.useZwave:
            self.toonConnZwaveInfo = Domoticz.Connection(Name="Toon Connection", Transport="TCP/IP", Protocol="HTTP", Address=Parameters["Address"], Port=Parameters["Port"])
            self.toonConnZwaveInfo.Connect()

        self.toonConnSetControl= Domoticz.Connection(Name="Toon Connection", Transport="TCP/IP", Protocol="HTTP", Address=Parameters["Address"], Port=Parameters["Port"])
        
        #TSC        self.toonTSCinfo= Domoticz.Connection(Name="Toon Connection", Transport="TCP/IP", Protocol="HTTP", Address=Parameters["Address"], Port=Parameters["Port"])
        
        sceneList = Parameters["Mode1"].split(';')
        self.scene0=sceneList[0]
        self.scene1=sceneList[1]
        self.scene2=sceneList[2]
        self.scene3=sceneList[3]
        self.scenes = []
        
        #Domoticz.Log(json.dumps(Parameters))
        if self.useZwave:
            if Parameters["Mode6"] == "user":
                paramList = Parameters["Mode5"].split(';')
                if len(paramList) != 5:
                    Domoticz.Error("Invalid list of user defined, please provide exactly 5 adresses, separated by semi colon ';'")
                    return
            else:
                paramList = zwaveAdress[Parameters["Mode6"]]
            self.ia_gas=paramList[0]
            self.ia_ednt=paramList[1]
            self.ia_edlt=paramList[2]
            self.ia_ernt=paramList[3]
            self.ia_erlt=paramList[4]
        
        heartBeat = int(Parameters['Mode2'])
        Domoticz.Heartbeat(heartBeat)
        return True

        #fetch scenes config
        self.getScenesConfig(self.toonConnThermostatInfo)

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
            #TSC            if (Connection == self.toonTSCinfo):
            #TSC                Domoticz.Debug("toonTSCinfo created")
            #TSC                requestUrl="/tsc/sensors"

            Domoticz.Debug("Connecting to: "+Parameters["Address"]+":"+Parameters["Port"] + requestUrl)
            Connection.Send({"Verb":"GET", "URL":requestUrl, "Headers": headers})

        else:
            Domoticz.Log("Failed to connect ("+str(Status)+":"+Description+") to "+Parameters["Address"]+":"+Parameters["Port"])

        return True

    def onMessageThermostatInfo(self, Connection, Response):
        Domoticz.Debug("onMessageThermostatInfo called with response: '" + str(Response) +"'")
        result='error'
        if 'result' in Response:
            result=Response['result']
        elif 'states' in Response:
            self.onMessageToonSceneinfo(Connection, Response)
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
            UpdateDevice(Unit=curTemp, nValue=0, sValue=strCurrentTemp)

        if 'programState' in Response:
            programState=int(Response['programState'])
            UpdateDevice(Unit=autoProgram, nValue=0, sValue=programStates[programState])

        if 'activeState' in Response:
            program=int(Response['activeState'])
            UpdateDevice(Unit=scene, nValue=0, sValue=programs[program])
            
        if 'burnerInfo' in Response:
            burnerInfo=int(Response['burnerInfo'])
            UpdateDevice(Unit=boilerState, nValue=0, sValue=burnerInfos[burnerInfo])
	
        if 'currentModulationLevel' in Response:
            currentModulationLevel=int(Response['currentModulationLevel'])
            strcurrentModulationLevel="%.0f" % currentModulationLevel
            UpdateDevice(Unit=boilerModulation, nValue=0, sValue=strcurrentModulationLevel)

        if 'nextTime' in Response:
            toonInformation['nextTime']=Response['nextTime']

        if 'nextState' in Response:
            toonInformation['nextState']=Response['nextState']

        if 'nextProgram' in Response:
            toonInformation['nextProgram']=Response['nextProgram']

        if 'nextSetpoint'in Response:
            toonInformation['nextSetpoint']=Response['nextSetpoint']

        if 'currentInternalBoilerSetpoint' in Response:
            currentInternalBoilerSetpoint=float(Response['currentInternalBoilerSetpoint'])
            strcurrentInternalBoilerSetpoint="%.1f" % currentInternalBoilerSetpoint
            UpdateDevice(Unit=boilerSetPoint, nValue=0, sValue=strcurrentInternalBoilerSetpoint)

        if 'currentSetpoint' in Response:
            currentSetpoint=float(Response['currentSetpoint'])/100
            strCurrentSetpoint="%.1f" % currentSetpoint
            currentScene=Response['activeState']
            UpdateDevice(Unit=setTemp, nValue=0, sValue=strCurrentSetpoint)
            if (strCurrentSetpoint == self.scene0) and (currentScene !='3'):
                Domoticz.Log("Scene changed :  Weg")
                UpdateDevice(Unit=scene, nValue=0, sValue=programs[3])
                self.toonSetControlUrl="/happ_thermstat?action=changeSchemeState&state=2&temperatureState=3"
                self.toonConnSetControl.Connect()
            if (strCurrentSetpoint == self.scene1) and (currentScene !='2'):
                Domoticz.Log("Scene changed : Slapen")
                UpdateDevice(Unit=scene, nValue=0, sValue=programs[2])
                self.toonSetControlUrl="/happ_thermstat?action=changeSchemeState&state=2&temperatureState=2"
                self.toonConnSetControl.Connect()
            if (strCurrentSetpoint == self.scene2) and (currentScene !='1'):
                UpdateDevice(Unit=scene, nValue=0, sValue=programs[1])
                Domoticz.Log("Scene changed : Thuis")
                self.toonSetControlUrl="/happ_thermstat?action=changeSchemeState&state=2&temperatureState=1"
                self.toonConnSetControl.Connect()
            if (strCurrentSetpoint == self.scene3) and (currentScene !='0'):
                Domoticz.Log("Scene changed : Comfort")
                UpdateDevice(Unit=scene, nValue=0, sValue=programs[0])
                self.toonSetControlUrl="/happ_thermstat?action=changeSchemeState&state=2&temperatureState=0"
                self.toonConnSetControl.Connect()

        if (len(toonInformation)==4):
            strToonInformation='No information received from Toon yet (%s)' % toonInformation['nextProgram']
            if int(toonInformation['nextProgram'])==-1:
                strToonInformation="No program scheduled"

            if int(toonInformation['nextProgram'])==0:
                strToonInformation="Progam is off"

            elif int(toonInformation['nextProgram'])>0:
                dt=datetime.fromtimestamp(int(toonInformation['nextTime']))
                strNextTime=dt.strftime("%Y-%d-%m %H:%M:%S")
                strNextProgram=strPrograms[int(toonInformation['nextState'])]
                strNextSetpoint="%.1f" % (float(toonInformation['nextSetpoint'])/100)
                strToonInformation="Next program %s (%s C) at %s" % (strNextProgram, strNextSetpoint, strNextTime)
            
            UpdateDevice(Unit=programInfo, nValue=0, sValue=strToonInformation)

        return

    def onMessageToonSceneinfo(self, Connection, Response):	
        Domoticz.Debug("onMessagetoonSceneinfo called")
        if 'states' in Response:
            #this message contains the scenes
            Domoticz.Debug("onMessagetoonSceneinfo processing list of scenes")
            for state in Response["states"][0]["state"]:
                Domoticz.Debug("id ="+ state["id"][0] + " Temp =" + state["tempValue"][0])
                #self.scenes[int(state["id"][0])] = int(state["tempValue"][0])
                self.scenes[int(state["tempValue"][0])] = int(state["id"][0])

    def onMessageBoilerInfo(self, Connection, Response):
        Domoticz.Debug("onMessageBoilerInfo called")
        if 'boilerPressure' in Response:
            Domoticz.Debug("boilerpressure: "+("%.1f" % Response['boilerPressure']))
            strBoilerPressure="%.1f" % Response['boilerPressure']
            UpdateDevice(Unit=boilerPressure, nValue=0, sValue=strBoilerPressure)

        return
        
        #TSC    def onMessagetoonTSCinfo(self, Connection, Response):	
        #TSC        Domoticz.Debug("onMessagetoonTSCinfo called")
        #TSC        if 'humidity' in Response:
        #TSC            humidity=float(Response['humidity'])
        #TSC            strhumidity="%.1f" % humidity
        #TSC            temperature=float(Response['temperature'])
        #TSC            strtemperature="%.1f" % temperature
        #TSC            dewpoint = (temperature-((100-humidity)/5))
        #TSC            if dewpoint > 2: humstat = 2
        #TSC            if dewpoint > 5: humstat = 1
        #TSC            if dewpoint > 8: humstat = 0
        #TSC            if dewpoint > 10: humstat = 3
        #TSC            strhumstat="%.0f" % humstat
        #TSC            UpdateDevice(Unit=roomHumidity, nValue=0, sValue=strtemperature+";"+strhumidity+";"+strhumstat)
                    
                    #TVOC: total volatile compounds (how bad is the air in your house poluted with other gases)
                    #ECO2: equivalent CO2 
                    #intensity: the light intensity of the surrounding of the toon
                    ### HUMSTAT            
                    #0=Normal
                    #1=Comfortable
                    #2=Dry
                    #3=Wet

        #TSC        return

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
                Domoticz.Debug("Zwave message: "+ str(zwaveDevInfo))
                if (zwaveDevInfo['internalAddress']==self.ia_gas):
                    Domoticz.Debug("Zwave Gas usage: "+ zwaveDevInfo['CurrentGasFlow'] + " Gas counter: "+ zwaveDevInfo['CurrentGasQuantity'])
                    UpdateDevice(Unit=gas, nValue=0, sValue="%.0f" % (float(zwaveDevInfo['CurrentGasQuantity']) ))

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
            if zwaveDeliveredNtFlow == 'NaN': zwaveDeliveredNtFlow = '0'
            if zwaveDeliveredLtFlow == 'NaN': zwaveDeliveredLtFlow = '0'
            zwaveDeliveredFlow=str(int(float(zwaveDeliveredNtFlow))+int(float(zwaveDeliveredLtFlow)))
            zwaveDeliveredQ=str(int(float(zwaveDeliveredNtQ))+int(float(zwaveDeliveredLtQ)))
        except:
            Domoticz.Log("One or more P1 internal address not configured correctly?")
            return

        Domoticz.Debug("zwaveDelivered: " + zwaveDeliveredFlow+";"+zwaveDeliveredQ)
        UpdateDevice(Unit=electricity, nValue=0, sValue=zwaveDeliveredFlow+";"+zwaveDeliveredQ)

        if zwaveReceivedNtFlow == 'NaN': zwaveReceivedNtFlow = '0'
        if zwaveReceivedLtFlow == 'NaN': zwaveReceivedLtFlow = '0'
        zwaveReceivedFlow=str(int(float(zwaveReceivedNtFlow))+int(float(zwaveReceivedLtFlow)))
        zwaveReceivedQ=str(int(float(zwaveReceivedNtQ))+int(float(zwaveReceivedLtQ)))
        Domoticz.Debug("zwaveReceived: " + zwaveReceivedFlow+";"+zwaveReceivedQ)

        UpdateDevice(Unit=genElectricity, nValue=0, sValue=zwaveReceivedFlow+";"+zwaveReceivedQ)
        UpdateDevice(Unit=p1electricity, nValue=0, sValue=str(int(float(zwaveDeliveredNtQ)))+";"+str(int(float(zwaveDeliveredLtQ)))+";"+str(int(float(zwaveReceivedNtQ)))+";"+str(int(float(zwaveReceivedLtQ)))+";"+zwaveDeliveredFlow+";"+zwaveReceivedFlow)

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
            #TSC            if (Connection==self.toonTSCinfo):	
            #TSC                Domoticz.Log("Something unexpected while onMessage: toonTSCinfo")
            #TSC                return

            Domoticz.Log("Unknown connection")
            return

        Domoticz.Debug(strData)
        if (strData[0]!='{'):
            Domoticz.Log("onMessage aborted, response format not JSON")
            Domoticz.Log(strData)
            return
        Response = json.loads(strData)

        if (Connection==self.toonConnSetControl):
            Domoticz.Debug("onMessage: toonConnSetControl")
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

        #TSC        if (Connection==self.toonTSCinfo):	
        #TSC            self.onMessagetoonTSCinfo(Connection, Response)

        if Connection.Connected() == True:
            # try to disconnect after use to avoid overload on the Toon
            Connection.Disconnect()

        return


    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

        if (Unit == setTemp):
            strLevel=str(int(Level*100))
            Domoticz.Log("New setpoint: %s" % str(Level))
            self.strCurrentSetpoint=str(Level)
            Devices[Unit].Update(nValue=0, sValue=str(Level))
            self.toonSetControlUrl="/happ_thermstat?action=setSetpoint&Setpoint=" + strLevel
            self.toonConnSetControl.Connect()

        if (Unit == autoProgram):
            Domoticz.Log("Auto Program : " + strProgramStates[(Level//10)-1])
            #Domoticz.Log(str(Level)+" -> "+rPrograms[int((Level//10)-1)])
            self.programState=str(Level)
            Devices[Unit].Update(nValue = 0, sValue = str(Level))
            self.toonSetControlUrl="/happ_thermstat?action=changeSchemeState&state="+rProgramStates[int((Level//10)-1)]
            self.toonConnSetControl.Connect()

        if (Unit == scene):
            Domoticz.Log("Scene : " +strPrograms[(Level//10)-1])
            #Domoticz.Log(str(Level)+" -> "+rPrograms[int((Level//10)-1)])
            self.program=str(Level)
            Devices[Unit].Update(nValue = 0, sValue = str(Level))
            self.toonSetControlUrl="/happ_thermstat?action=changeSchemeState&state=2&temperatureState="+rPrograms[int((Level//10)-1)]
            Domoticz.Debug(self.toonSetControlUrl)
            self.toonConnSetControl.Connect()

            ##        if (Unit == boilerState):
            ##            Domoticz.Log("Boiler")
            ##            Domoticz.Log(str(Level)+" -> "+rBurnerInfos[int((Level//10)-1)])
            ##            self.burnerInfo=str(Level)
            ##            Devices[Unit].Update(nValue = 0, sValue = str(Level))
            ##            self.toonSetControlUrl="/happ_thermstat?action=changeSchemeState&state=2&temperatureState="+rBurnerInfos[int((Level//10)-1)]
            ##            Domoticz.Debug(self.toonSetControlUrl)
            ##            self.toonConnSetControl.Connect()

        #tbd send to Toon

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Debug("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        if (Connection==self.toonConnThermostatInfo):
            Domoticz.Debug("onDisconnect called: ThermostatInfo")
            return
        if (Connection==self.toonConnBoilerInfo):
            Domoticz.Debug("onDisconnect called: BoilerInfo")
            return
        if (Connection==self.toonConnZwaveInfo):
            Domoticz.Debug("onDisconnect called: toonConnZwaveInfo")
            return
        if (Connection==self.toonConnSetControl):
            Domoticz.Debug("onDisconnect called: toonConnSetControl")
            return
        #TSC        if (Connection==self.toonTSCinfo):	
        #TSC            Domoticz.Debug("onDisconnect called: toonTSCinfo")
        #TSC            return
        Domoticz.Debug("onDisconnect called for other connection (this is rather strange......")

    def onHeartbeat(self):
        Domoticz.Debug("onHeartbeat called")

        if (self.toonConnThermostatInfo.Connected()==False):
            self.toonConnThermostatInfo.Connect()

        if (self.toonConnBoilerInfo.Connected()==False):
            self.toonConnBoilerInfo.Connect()

        if self.useZwave:
            if (self.toonConnZwaveInfo.Connected()==False):
                self.toonConnZwaveInfo.Connect()
            
        #TSC        if (self.toonTSCinfo.Connected()==False):	
        #TSC            self.toonTSCinfo.Connect()

    def processScenesConfig(self, json_response):
        Domoticz.Debug("processing scenes config on data: "+str(json_response))

    def getScenesConfig(self, connection):
        requestUrl = "/hcb_config?action=getObjectConfigTree&package=happ_thermstat&internalAddress=thermostatStates"
        if connection.Connected() == False:
            connection.Connect()
        connection.Send({"Verb":"GET", "URL":requestUrl, "Headers": headers})
        return

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
    Domoticz.Debug("Parameters count: " + str(len(Parameters)))
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug("Parameter: '" + x + "':'" + str(Parameters[x]) + "'")
    Configurations = Domoticz.Configuration()
    Domoticz.Debug("Configuration count: " + str(len(Configurations)))
    for x in Configurations:
        if Configurations[x] != "":
            Domoticz.Debug( "Configuration '" + x + "':'" + str(Configurations[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
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
