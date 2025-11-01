# Toon Plugin for Domoticz

"""
<plugin key="RootedToonPlug" name="Toon Rooted" author="MadPatrick" version="2.4.0" externallink="https://github.com/MadPatrick/domoticz_toon">
    <description>
        <br/><h2>Domoticz Toon Rooted plugin</h2><br/>
        version: 2.4.0
        <br/>Volledige synchronisatie van Scenes en Setpoints tussen Domoticz en Toon.
    </description>
    <params>
        <param field="Address" label="IP Address" width="200px" required="true" default="192.168.1.200" />
        <param field="Port" label="Port" width="50px" required="true" default="80" />
        <param field="Mode1" label="Refresh Interval Scenes" width="100px" required="true" default="300" />
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

zwaveAdress = {
    "v1": ["2.1", "2.3", "2.5", "2.4", "2.6"],
    "v2": ["2.1", "2.4", "2.6", "2.5", "2.7"],
    "user": ["3.1", "3.4", "3.6", "3.5", "3.7"]
}

class BasePlugin:
    def __init__(self):
        self.useZwave = False
        self.scene_map = {}
        self.ia_gas = ''
        self.ia_ednt = ''
        self.ia_edlt = ''
        self.ia_ernt = ''
        self.ia_erlt = ''
        self.sceneCounter = 0

    # --- Domoticz lifecycle ---
    def onStart(self):
        Domoticz.Log("Toon: Starting version: " + Parameters["Version"])
        if Parameters["Mode3"] == "Yes":
            self.useZwave = True

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

        if self.useZwave:
            paramList = zwaveAdress.get(Parameters["Mode6"], [])
            if len(paramList) == 5:
                self.ia_gas, self.ia_ednt, self.ia_edlt, self.ia_ernt, self.ia_erlt = paramList

        # Eerste scene fetch bij start
        self.fetchScenes()
        Domoticz.Heartbeat(int(Parameters['Mode2']))

    def onStop(self):
        Domoticz.Log("Toon plugin gestopt")

    # --- Commands ---
    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug(f"onCommand Unit {Unit} Command {Command} Level {Level}")

        if Unit == setTemp:
            setpoint = int(Level * 100)
            self.fetchJson(f"/happ_thermstat?action=setSetpoint&Setpoint={setpoint}")
            UpdateDevice(setTemp, 0, str(Level))
            self.updateSceneFromSetpoint(Level)

        elif Unit == scene:
            scene_level = int(Level)
            temp = self.scene_map.get(str(scene_level), None)

            if temp is not None:
                self.fetchJson(f"/happ_thermstat?action=setSetpoint&Setpoint={int(temp*100)}")
                UpdateDevice(setTemp, 0, str(temp))

            state_map = {10: 3, 20: 2, 30: 1, 40: 0}
            newState = state_map.get(scene_level, None)
            if newState is not None:
                self.fetchJson(f"/happ_thermstat?action=changeSchemeState&state=2&temperatureState={newState}")
                Domoticz.Debug(f"Scene {scene_level} ingesteld op Toon met state {newState}")

            current_scene_val = int(Devices[scene].sValue) if scene in Devices else None
            if current_scene_val != scene_level:
                UpdateDevice(scene, 0, str(scene_level))

    # --- Heartbeat ---
    def onHeartbeat(self):
        Domoticz.Debug("onHeartbeat called")
        
        data = self.fetchJson("/happ_thermstat?action=getThermostatInfo")
        if data:
            self.updateThermostatDevices(data)
        data = self.fetchJson("/boilerstatus/boilervalues.txt")
        if data:
            self.updateBoilerDevices(data)
        if self.useZwave:
            zw = self.fetchJson("/hdrv_zwave?action=getDevices.json")
            if zw:
                self.updateZwaveDevices(zw)

        # Scene update volgens Mode1 interval
        self.sceneCounter += int(Parameters['Mode2'])
        if self.sceneCounter >= int(Parameters['Mode1']):
            self.fetchScenes()
            self.sceneCounter = 0

    # --- Toon / Domoticz Synchronisatie ---
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
        if data and 'states' in data and len(data['states']) > 0:
            state_list = data['states'][0]['state']
            self.scene_map = {}
            for s in state_list:
                id_ = int(s['id'][0])
                temp = float(s['tempValue'][0]) / 100
                if id_ <= 3:
                    self.scene_map[str(self.idToScene(id_))] = temp
            Domoticz.Debug(f"Scenes fetched from Toon: {list(self.scene_map.values())}")

            # Active scene meteen bijwerken in Domoticz
            toon_scene = self.getActiveSceneFromToon()
            if toon_scene is not None:
                current_scene_val = int(Devices[scene].sValue) if scene in Devices else None
                if current_scene_val != toon_scene:
                    Domoticz.Debug(f"Toon scene gewijzigd ? update Domoticz naar {toon_scene}")
                    UpdateDevice(scene, 0, str(toon_scene))

    def idToScene(self, id_):
        mapping = {0: 40, 1: 30, 2: 20, 3: 10}
        return mapping.get(id_, 50)

    def getActiveSceneFromToon(self):
        data = self.fetchJson("/happ_thermstat?action=getActiveState")
        if data and "state" in data:
            try:
                toon_state = int(data["state"])
                scene_level = self.idToScene(toon_state)
                Domoticz.Debug(f"Actieve Toon scene: {toon_state} -> {scene_level}")
                return scene_level
            except:
                pass
        return None

    def updateSceneFromSetpoint(self, setpoint):
        matched_scene_id = None
        for scene_id, temp in self.scene_map.items():
            if abs(temp - setpoint) < 0.05:
                matched_scene_id = int(scene_id)
                break

        current_scene_val = int(Devices[scene].sValue) if scene in Devices else None

        if matched_scene_id is not None:
            if current_scene_val != matched_scene_id:
                UpdateDevice(scene, 0, str(matched_scene_id))
                state_map = {10: 3, 20: 2, 30: 1, 40: 0}
                newState = state_map.get(matched_scene_id, None)
                if newState is not None:
                    self.fetchJson(f"/happ_thermstat?action=changeSchemeState&state=2&temperatureState={newState}")
                    Domoticz.Debug(f"Scene {matched_scene_id} ingesteld op Toon met state {newState}")
        else:
            if current_scene_val != 50:
                UpdateDevice(scene, 50, "50")  # Geen match

    # --- Updates ---
    def updateThermostatDevices(self, Response):
        if 'currentTemp' in Response:
            UpdateDevice(curTemp, 0, "%.1f" % (float(Response['currentTemp']) / 100))
        if 'currentSetpoint' in Response:
            setpoint = float(Response['currentSetpoint']) / 100
            UpdateDevice(setTemp, 0, "%.1f" % setpoint)
            toon_scene = self.getActiveSceneFromToon()
            if toon_scene is not None:
                current_scene_val = int(Devices[scene].sValue) if scene in Devices else None
                if current_scene_val != toon_scene:
                    Domoticz.Debug(f"Toon scene gewijzigd ? update Domoticz naar {toon_scene}")
                    UpdateDevice(scene, 0, str(toon_scene))

            # --- update scene automatisch op basis van setpoint ---
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
        Domoticz.Debug("updateZwaveDevices called")
        zwaveDeliveredNtFlow = '0'
        zwaveDeliveredLtFlow = '0'
        zwaveDeliveredNtQ = '0'
        zwaveDeliveredLtQ = '0'
        zwaveReceivedNtFlow = '0'
        zwaveReceivedLtFlow = '0'
        zwaveReceivedNtQ = '0'
        zwaveReceivedLtQ = '0'

        for zwaveDev in Response:
            info = Response[zwaveDev]
            if 'internalAddress' not in info:
                continue
            ia = info['internalAddress']
            if ia == self.ia_gas:
                UpdateDevice(Unit=gas, nValue=0, sValue=str(int(float(info.get('CurrentGasQuantity', 0)))))
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

        try:
            if zwaveDeliveredNtFlow == 'NaN': zwaveDeliveredNtFlow = '0'
            if zwaveDeliveredLtFlow == 'NaN': zwaveDeliveredLtFlow = '0'
            zwaveDeliveredFlow = str(int(float(zwaveDeliveredNtFlow)) + int(float(zwaveDeliveredLtFlow)))
            zwaveDeliveredQ = str(int(float(zwaveDeliveredNtQ)) + int(float(zwaveDeliveredLtQ)))
            UpdateDevice(Unit=electricity, nValue=0, sValue=zwaveDeliveredFlow + ";" + zwaveDeliveredQ)

            if zwaveReceivedNtFlow == 'NaN': zwaveReceivedNtFlow = '0'
            if zwaveReceivedLtFlow == 'NaN': zwaveReceivedLtFlow = '0'
            zwaveReceivedFlow = str(int(float(zwaveReceivedNtFlow)) + int(float(zwaveReceivedLtFlow)))
            zwaveReceivedQ = str(int(float(zwaveReceivedNtQ)) + int(float(zwaveReceivedLtQ)))
            UpdateDevice(Unit=genElectricity, nValue=0, sValue=zwaveReceivedFlow + ";" + zwaveReceivedQ)

            UpdateDevice(Unit=p1electricity, nValue=0, sValue="{};{};{};{};{};{}".format(
                int(float(zwaveDeliveredNtQ)),
                int(float(zwaveDeliveredLtQ)),
                int(float(zwaveReceivedNtQ)),
                int(float(zwaveReceivedLtQ)),
                zwaveDeliveredFlow,
                zwaveReceivedFlow
            ))

        except Exception as e:
            Domoticz.Log(f"Error processing P1 values: {e}")


# --- Global instance ---
global _plugin
_plugin = BasePlugin()

def onStart(): _plugin.onStart()
def onStop(): _plugin.onStop()
def onCommand(Unit, Command, Level, Hue): _plugin.onCommand(Unit, Command, Level, Hue)
def onHeartbeat(): _plugin.onHeartbeat()


# --- Helpers ---
def DumpConfigToLog():
    Domoticz.Debug("Parameters:")
    for x in Parameters:
        Domoticz.Debug(f"'{x}':'{Parameters[x]}'")

def UpdateDevice(Unit, nValue, sValue, TimedOut=0):
    try:
        if Unit in Devices:
            if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != str(sValue)):
                Devices[Unit].Update(nValue=nValue, sValue=str(sValue), TimedOut=TimedOut)
                Domoticz.Debug(f"Update {nValue}:'{sValue}' ({Devices[Unit].Name})")
    except Exception as e:
        Domoticz.Log(f"Update of device {Unit} failed: {e}")
    return
