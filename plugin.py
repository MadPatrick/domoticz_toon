# Toon Plugin for Domoticz

"""
<plugin key="RootedToonPlug" name="Toon Rooted" author="MadPatrick" version="2.1.0" externallink="https://github.com/MadPatrick/domoticz_toon">
    <description>
        <br/><h2>Domoticz Toon Rooted plugin</h2><br/>
        version: 2.1.0
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
        <param field="Address" label="IP Address" width="200px" required="true" default="192.168.1.200" />
        <param field="Port" label="Port" width="50px" required="true" default="80" />
        <param field="Mode6" label="Toon version" width="200px" required="true">
            <options>
                <option label="v1" value="v1"/>
                <option label="v2" value="v2" default="true" />
                <option label="user defined" value="user"/>
            </options>
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
        <param field="Mode3" label="P1 data" width="100px">
            <options>
                <option label="Yes" value="Yes"/>
                <option label="No" value="No" default="true"/>
            </options>
        </param>
        <param field="Mode5" label="P1 adresses" width="200px" default="2.1;2.4;2.6;2.5;2.7"/>
        <param field="Mode4" label="Debug logging" width="100px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal" default="true"/>
            </options>
        </param>
    </params>
</plugin>
"""

import Domoticz
import json
import requests

# --- Constants and device definitions ---
programStates = ['10','20','30']
rProgramStates = ['0','1','2']
strProgramStates = ['Uit', 'Aan', 'Tijdelijk']

burnerInfos = ['10','20','30']
rBurnerInfos = ['0','1','2']
strBurnerInfos = ['Uit', 'CV', 'WW']

programs = ['10','20','30','40','50']
rPrograms = ['3','2','1','0','4']
strPrograms = ['Weg', 'Slapen', 'Thuis', 'Comfort','Manual']

# Device unit numbers
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

zwaveAdress = {
    "v1": ["2.1", "2.3", "2.5", "2.4", "2.6"],
    "v2": ["2.1", "2.4", "2.6", "2.5", "2.7"],
    "user": ["3.1", "3.4", "3.6", "3.5", "3.7"]
}

# --- Plugin class ---
class BasePlugin:

    def __init__(self):
        self.useZwave = False
        self.scene_map = {}
        self.ia_gas = ''
        self.ia_ednt = ''
        self.ia_edlt = ''
        self.ia_ernt = ''
        self.ia_erlt = ''

    # --- Domoticz callbacks ---
    def onStart(self):
        Domoticz.Log("onStart called")
        if Parameters["Mode3"] == "Yes":
            self.useZwave = True

        # Devices creation
        if curTemp not in Devices:
            Domoticz.Device(Name="Temperatuur", Unit=curTemp, TypeName="Temperature", Used=1).Create()
        if setTemp not in Devices:
            Domoticz.Device(Name="Setpunt Temperatuur", Unit=setTemp, Type=242, Subtype=1, Used=1).Create()
        if autoProgram not in Devices:
            options = {"LevelActions": "||", "LevelNames": "|Uit|Aan|Tijdelijk", "LevelOffHidden": "true", "SelectorStyle": "0"}
            Domoticz.Device(Name="Auto Program", Unit=autoProgram, TypeName="Selector Switch", Options=options, Used=1).Create()
        if scene not in Devices:
            options = {"LevelActions": "||||", "LevelNames": "|Weg|Slapen|Thuis|Comfort|Manual", "LevelOffHidden": "true", "SelectorStyle": "0"}
            Domoticz.Device(Name="Scene", Unit=scene, TypeName="Selector Switch", Options=options, Used=1).Create()
        if boilerPressure not in Devices:
            Domoticz.Device(Name="Keteldruk", Unit=boilerPressure, TypeName="Pressure", Used=0).Create()
        if programInfo not in Devices:
            Domoticz.Device(Name="Programma info", Unit=programInfo, TypeName="Text", Used=0).Create()
        if boilerState not in Devices:
            options = {"LevelActions": "||", "LevelNames": "|Uit|CV|WW", "LevelOffHidden": "true", "SelectorStyle": "0"}
            Domoticz.Device(Name="Ketelmode", Unit=boilerState, TypeName="Selector Switch", Options=options, Used=1).Create()
        if boilerModulation not in Devices:
            Domoticz.Device(Name="Ketel modulatie", Unit=boilerModulation, Type=243, Subtype=6, Used=0).Create()
        if boilerSetPoint not in Devices:
            Domoticz.Device(Name="Ketel setpoint", Unit=boilerSetPoint, Type=80, Subtype=5, Used=0).Create()

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
        else:
            Domoticz.Debugging(0)

        # ZWave addresses
        if self.useZwave:
            if Parameters["Mode6"] == "user":
                paramList = Parameters["Mode5"].split(';')
                if len(paramList) != 5:
                    Domoticz.Error("Invalid list of user defined P1 addresses")
                    return
            else:
                paramList = zwaveAdress[Parameters["Mode6"]]
            self.ia_gas, self.ia_ednt, self.ia_edlt, self.ia_ernt, self.ia_erlt = paramList

        # Scenes ophalen bij opstart
        self.fetchScenes()

        Domoticz.Heartbeat(int(Parameters['Mode2']))

    def onStop(self):
        Domoticz.Log("onStop called")

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug(f"onCommand Unit {Unit} Command {Command} Level {Level}")
        if Unit == setTemp:
            setpoint = int(Level*100)
            url = f"/happ_thermstat?action=setSetpoint&Setpoint={setpoint}"
            self.fetchJson(url)
            UpdateDevice(setTemp,0,str(Level))
            self.updateSceneFromSetpoint(Level)
        elif Unit == autoProgram:
            idx = int(Level//10)-1
            url = f"/happ_thermstat?action=changeSchemeState&state={rProgramStates[idx]}"
            self.fetchJson(url)
            UpdateDevice(autoProgram,0,str(Level))
        elif Unit == scene:
            # Scene naar setpoint
            temp = self.scene_map.get(str(int(Level)), None)
            if temp:
                url = f"/happ_thermstat?action=setSetpoint&Setpoint={int(temp*100)}"
                self.fetchJson(url)
                UpdateDevice(setTemp,0,str(temp))
            UpdateDevice(scene,0,str(Level))

    def onHeartbeat(self):
        Domoticz.Debug("onHeartbeat called")

        # Thermostat info
        data = self.fetchJson("/happ_thermstat?action=getThermostatInfo")
        if data:
            self.updateThermostatDevices(data)

        # Boiler info
        data = self.fetchJson("/boilerstatus/boilervalues.txt")
        if data:
            self.updateBoilerDevices(data)

        # ZWave / P1 data
        if self.useZwave:
            data = self.fetchJson("/hdrv_zwave?action=getDevices.json")
            if data:
                self.updateZwaveDevices(data)

        # Scenes ophalen bij elke heartbeat
        self.fetchScenes()

    # --- Helper functions ---
    def fetchJson(self, path):
        try:
            url = f"http://{Parameters['Address']}:{Parameters['Port']}{path}"
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            Domoticz.Log(f"Error fetching {path}: {e}")
            return None

    def fetchScenes(self):
        data = self.fetchJson("/hcb_config?action=getObjectConfigTree&package=happ_thermstat&internalAddress=thermostatStates")
        if data and 'states' in data and len(data['states'])>0:
            state_list = data['states'][0]['state']
            self.scene_map = {}
            for s in state_list:
                id_ = int(s['id'][0])
                temp = float(s['tempValue'][0])/100
                # alleen id 0..3 gebruiken
                if id_ <=3:
                    self.scene_map[str(self.idToScene(id_))] = temp
            Domoticz.Debug(f"Scenes fetched from Toon: {list(self.scene_map.values())}")

    def idToScene(self,id_):
        # id 0=Comfort,1=Thuis,2=Slapen,3=Weg
        mapping = {0:40,1:30,2:20,3:10}
        return mapping.get(id_,50)

    def updateSceneFromSetpoint(self, setpoint):
        matched = False
        for scene_id, temp in self.scene_map.items():
            if abs(temp - setpoint) < 0.05:
                currentSceneValue = Devices[scene].nValue if scene in Devices else None
                if currentSceneValue != int(scene_id):
                    Domoticz.Debug(f"Updating scene based on setpoint {setpoint}: {scene_id}")
                    UpdateDevice(scene, int(scene_id), str(scene_id))
                matched = True
                break

        if not matched:
            # Geen scene gevonden: zet op Manual (50)
            currentSceneValue = Devices[scene].nValue if scene in Devices else None
            if currentSceneValue != 50:
                Domoticz.Debug(f"Setpoint {setpoint} does not match a scene, setting Scene to Manual (50)")
                UpdateDevice(scene, 50, "50")

    def updateThermostatDevices(self, Response):
        if 'currentTemp' in Response:
            currentTemp = float(Response['currentTemp']) / 100
            UpdateDevice(curTemp, 0, "%.1f" % currentTemp)

        if 'currentSetpoint' in Response:
            setpoint = float(Response['currentSetpoint']) / 100
            UpdateDevice(setTemp, 0, "%.1f" % setpoint)
            self.updateSceneFromSetpoint(setpoint)

        if 'programState' in Response:
            UpdateDevice(autoProgram, 0, programStates[int(Response['programState'])])

        if 'burnerInfo' in Response:
            UpdateDevice(boilerState, 0, burnerInfos[int(Response['burnerInfo'])])

        if 'currentModulationLevel' in Response:
            UpdateDevice(boilerModulation, 0, int(Response['currentModulationLevel']))

        if 'currentInternalBoilerSetpoint' in Response:
            UpdateDevice(boilerSetPoint, 0, float(Response['currentInternalBoilerSetpoint']))

    def updateBoilerDevices(self, Response):
        if 'boilerPressure' in Response:
            UpdateDevice(boilerPressure, 0, float(Response['boilerPressure']))

    def updateZwaveDevices(self, Response):
        try:
            zwaveDeliveredLtFlow = zwaveDeliveredNtFlow = '0'
            zwaveDeliveredLtQ = zwaveDeliveredNtQ = '0'
            zwaveReceivedLtFlow = zwaveReceivedNtFlow = '0'
            zwaveReceivedLtQ = zwaveReceivedNtQ = '0'

            for dev in Response:
                info = Response[dev]
                if 'internalAddress' not in info:
                    continue
                ia = info['internalAddress']

                if ia == self.ia_gas:
                    gas_value = str(int(float(info.get('CurrentGasQuantity', 0))))
                    currentValue = Devices[gas].sValue if gas in Devices else None
                    if currentValue != gas_value:
                       Domoticz.Debug(f"Zwave Gas: {gas_value} m3")
                       UpdateDevice(gas, 0, gas_value)
                elif ia == self.ia_ednt:
                    zwaveDeliveredNtFlow = info.get('CurrentElectricityFlow', '0')
                    zwaveDeliveredNtQ = info.get('CurrentElectricityQuantity', '0')
                elif ia == self.ia_edlt:
                    zwaveDeliveredLtFlow = info.get('CurrentElectricityFlow', '0')
                    zwaveDeliveredLtQ = info.get('CurrentElectricityQuantity', '0')
                elif ia == self.ia_ernt:
                    zwaveReceivedNtFlow = info.get('CurrentElectricityFlow', '0')
                    zwaveReceivedNtQ = info.get('CurrentElectricityQuantity', '0')
                elif ia == self.ia_erlt:
                    zwaveReceivedLtFlow = info.get('CurrentElectricityFlow', '0')
                    zwaveReceivedLtQ = info.get('CurrentElectricityQuantity', '0')

            # Fix empty or invalid values
            for var_name in ['zwaveDeliveredNtFlow','zwaveDeliveredLtFlow','zwaveDeliveredNtQ','zwaveDeliveredLtQ',
                             'zwaveReceivedNtFlow','zwaveReceivedLtFlow','zwaveReceivedNtQ','zwaveReceivedLtQ']:
                val = locals()[var_name]
                if val in [None,'','NaN']:
                    locals()[var_name] = '0'

            zwaveDeliveredFlow = str(int(float(zwaveDeliveredNtFlow)) + int(float(zwaveDeliveredLtFlow)))
            zwaveDeliveredQ = str(int(float(zwaveDeliveredNtQ)) + int(float(zwaveDeliveredLtQ)))
            zwaveReceivedFlow = str(int(float(zwaveReceivedNtFlow)) + int(float(zwaveReceivedLtFlow)))
            zwaveReceivedQ = str(int(float(zwaveReceivedNtQ)) + int(float(zwaveReceivedLtQ)))

            UpdateDevice(electricity, 0, zwaveDeliveredFlow + ";" + zwaveDeliveredQ)
            UpdateDevice(genElectricity, 0, zwaveReceivedFlow + ";" + zwaveReceivedQ)
            UpdateDevice(p1electricity, 0,
                         f"{int(float(zwaveDeliveredNtQ))};{int(float(zwaveDeliveredLtQ))};"
                         f"{int(float(zwaveReceivedNtQ))};{int(float(zwaveReceivedLtQ))};"
                         f"{zwaveDeliveredFlow};{zwaveReceivedFlow}")

        except Exception as e:
            Domoticz.Log(f"Error updating ZWave devices: {e}")

# --- Global plugin instance ---
global _plugin
_plugin = BasePlugin()

def onStart(): _plugin.onStart()
def onStop(): _plugin.onStop()
def onConnect(Connection, Status, Description): _plugin.onConnect(Connection, Status, Description)
def onMessage(Connection, Data): _plugin.onMessage(Connection, Data)
def onCommand(Unit, Command, Level, Hue): _plugin.onCommand(Unit, Command, Level, Hue)
def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile): _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)
def onDisconnect(Connection): _plugin.onDisconnect(Connection)
def onHeartbeat(): _plugin.onHeartbeat()

# --- Helpers ---
def DumpConfigToLog():
    Domoticz.Debug("Parameters count: " + str(len(Parameters)))
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug(f"Parameter: '{x}':'{Parameters[x]}'")
    Configurations = Domoticz.Configuration()
    Domoticz.Debug("Configuration count: " + str(len(Configurations)))
    for x in Configurations:
        if Configurations[x] != "":
            Domoticz.Debug(f"Configuration '{x}':'{Configurations[x]}'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug(f"Device: {x} - {Devices[x]}")

def UpdateDevice(Unit, nValue, sValue, TimedOut=0):
    if Unit in Devices:
        if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != str(sValue)) or (Devices[Unit].TimedOut != TimedOut):
            try:
                Devices[Unit].Update(nValue=nValue, sValue=str(sValue), TimedOut=TimedOut)
                Domoticz.Debug(f"Update {nValue}:'{sValue}' ({Devices[Unit].Name})")
            except:
                Domoticz.Log(f"Update of device failed: {Unit}!")
    return
