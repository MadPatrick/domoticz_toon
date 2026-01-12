# Toon Plugin for Domoticz
"""
<plugin key="RootedToonPlug" name="Toon Rooted" author="MadPatrick" version="2.6.3" externallink="https://github.com/MadPatrick/domoticz_toon">
      <description>
          <br/><h2>Domoticz Plugin for Toon (Rooted)</h2>
          <br/>Version: 2.6.3
          <br/><br/>
          This plugin allows Domoticz to communicate with a Rooted Toon thermostat. Its main functionalities are:
          <ul>
              <li>Control and synchronize Scenes, Programs, and Setpoints between Domoticz and Toon.</li>
              <li>Read and update temperature and energy data from the Toon device.</li>
              <li>Set refresh intervals for Scenes and real-time data independently.</li>
              <li>Read P1 smart meter data, with configurable device addresses for selective monitoring.</li>
              <li>Support for different Toon versions: v1, v2, or user-defined.</li>
              <li>Enable or disable debug logging for troubleshooting purposes.</li>
          </ul>
          <br/>
          The plugin creates the following Domoticz devices:
          <ul>
              <li>Current temperature and setpoint</li>
              <li>Heating/cooling status</li>
              <li>Active Scenes and Programs</li>
              <li>Energy consumption (electricity and gas) from P1 meter</li>
              <li>Individual P1 devices as defined in the plugin configuration</li>
          </ul>
          <br/>
          Fields left empty, such as P1 addresses, will be automatically detected by the plugin.
      </description>
      <params>
        <param field="Address" label="IP Address" width="150px" required="true" default="192.168.1.200" />
        <param field="Port" label="Port" width="150px" required="true" default="80" />
        <param field="Mode1" label="Refresh Interval Scenes" width="150px">
            <options>
                <option label="30m" value="1800"/>
                <option label="1hr" value="3600" default="true"/>
                <option label="2hr" value="7200"/>
                <option label="6hr" value="2160"/>
            </options>
        </param>
        <param field="Mode2" label="Refresh interval" width="150px">
            <options>
                <option label="10s" value="10"/>
                <option label="20s" value="20"/>
                <option label="30s" value="30"/>
                <option label="1m" value="60" default="true"/>
                <option label="5m" value="300"/>
                <option label="10m" value="600"/>
                <option label="15m" value="900"/>
            </options>
        </param>
        <param field="Mode3" label="P1 data" width="150px">
            <options>
                <option label="Yes" value="Yes"/>
                <option label="No" value="No" default="true"/>
            </options>
        </param>
        <param field="Mode4" label="Toon version" width="150px" required="true">
            <options>
                <option label="v1" value="v1"/>
                <option label="v2" value="v2" default="true" />
                <option label="user defined" value="user"/>
            </options>
        </param>
        <param field="Mode5" label="P1 addresses" width="300px" default="2.1;2.4;2.6;2.5;2.7">
        <description><br/>Fill in the P1 devicenumbers separated by ;  (2.1;2.4;2.6;2.5;2.7)
                     <br/><span style="color: yellow;">Leave empty for auto detection</span></description>
        </param>
        <param field="Mode6" label="Debug logging" width="150px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal" default="true"/>
            </options>
        </param>
    </params>
</plugin>
"""

import Domoticz
import requests
import json
from datetime import datetime
from time import time

# --- Constants ---
programStates = ['10','20','30']
burnerInfos = ['10','20','30']
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

# --- Helper functions ---
def cleanError(e):
    msg = str(e).lower()
    if "refused" in msg: return "Verbinding geweigerd"
    if "timeout" in msg: return "Timeout"
    if "max retries" in msg: return "Max retries bereikt"
    if "not found" in msg: return "Niet gevonden"
    return msg.split('(')[0].strip()

def SafeInt(value):
    try: return int(value)
    except (ValueError, TypeError): return None

def UpdateDevice(Unit, nValue, sValue, TimedOut=0):
    try:
        if Unit in Devices:
            dev = Devices[Unit]
            if dev.nValue != nValue or dev.sValue != str(sValue):
                dev.Update(nValue=nValue, sValue=str(sValue), TimedOut=TimedOut)
                Domoticz.Debug(f"{dev.Name}: {dev.sValue}")
    except Exception as e:
        Domoticz.Log(f"Update of device {Unit} failed: {e}")

# --- BasePlugin class ---
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
        self.errorCooldown = 0
        self.lastErrorTime = None

    # --- Device helper ---
    def createDeviceIfNotExists(self, unit, name, typeName=None, type_=None, subtype=None, options=None, used=1):
        if unit not in Devices:
            if options:
                Domoticz.Device(Name=name, Unit=unit, TypeName=typeName, Options=options, Used=used).Create()
            elif type_ is not None:
                Domoticz.Device(Name=name, Unit=unit, Type=type_, Subtype=subtype or 0, Used=used).Create()
            else:
                Domoticz.Device(Name=name, Unit=unit, TypeName=typeName, Used=used).Create()
            Domoticz.Log(f"Device '{name}' created")

    # --- P1 / Zwave helper ---
    def setupP1Devices(self):
        paramList = []
        detected_version = None

        # --- Handmatige Mode5 check ---
        if Parameters["Mode5"]:
            paramList = Parameters["Mode5"].split(";")
            if len(paramList) == 5:
                self.ia_gas, self.ia_ednt, self.ia_edlt, self.ia_ernt, self.ia_erlt = paramList
                detected_version = "user (Mode5)"
                Domoticz.Log(f"Manual P1-addresses used: {paramList}")
            else:
                Domoticz.Log("Mode5 set, but wrong number of addresses (5 expected)")
                paramList = []

        # --- Automatische detectie ---
        if not paramList:
            detected_version = "niet gedetecteerd"
            try:
                zwave_json = self.fetchJson("/hdrv_zwave?action=getDevices.json")
                if zwave_json:
                    internal_addresses = [
                        dev["internalAddress"] for dev in zwave_json.values()
                        if "internalAddress" in dev
                    ]

                    # --- Alleen geldige meter-adressen gebruiken (cijfer of cijfer.cijfer) ---
                    valid_addresses = [
                        addr for addr in internal_addresses
                        if addr.replace(".", "").isdigit()
                    ]

                    if not valid_addresses:
                        Domoticz.Log("WARNING: No valid meter addresses detected")
                        return

                    # --- Verzamel unieke prefixes ---
                    prefixes = set(addr.split(".")[0] if "." in addr else addr for addr in valid_addresses)

                    # --- Verzamel unieke prefixes ---
                    prefixes = set(addr.split(".")[0] if "." in addr else addr for addr in valid_addresses)

                    # Kies de prefix met de meeste meters
                    detected_prefix = max(prefixes, key=lambda p: sum(1 for a in valid_addresses if a.startswith(p + ".")))

                    # --- Suffixes per Mode4 (orde = gas, ednt, edlt, ernt, erlt) ---
                    if Parameters["Mode4"] == "v1":
                        suffixes = ["1","3","5","4","6"]
                    else:  # v2
                        suffixes = ["1","4","6","5","7"]

                    # --- Maak volledige paramList ---
                    paramList = [f"{detected_prefix}.{s}" for s in suffixes]

                    # --- Koppel devices ---
                    if len(paramList) == 5:
                        self.ia_gas, self.ia_ednt, self.ia_edlt, self.ia_ernt, self.ia_erlt = paramList
                        detected_version = f"{Parameters['Mode4']} ({detected_prefix}.x)"
                        Domoticz.Log(f"Automatic P1-detection used: {detected_version}")

            except Exception as e:
                detected_version = "error"
                Domoticz.Log(f"Error with automatic detection of Zwave versie: {e}")

        # --- Log de uiteindelijke P1-devices ---
        Domoticz.Log(f"P1-devices used: Gas={self.ia_gas}, DeliveredNT={self.ia_ednt}, DeliveredLT={self.ia_edlt}, ReceivedNT={self.ia_ernt}, ReceivedLT={self.ia_erlt}")
        Domoticz.Log(f"Zwave P1 addresses detected: {detected_version}")

        # --- Devices aanmaken (Gas, Electriciteit, etc.) ---
        p1_devices = [
            {"unit": gas, "name": "Gas", "typeName": "Gas"},
            {"unit": electricity, "name": "Electriciteit", "typeName": "kWh", "used": 0},
            {"unit": genElectricity, "name": "Opgewekte Electriciteit", "typeName": "Usage", "used": 0},
            {"unit": p1electricity, "name": "P1 Electriciteit", "type": 250, "subtype": 1}
        ]
        for dev in p1_devices:
            self.createDeviceIfNotExists(
                unit=dev["unit"],
                name=dev["name"],
                typeName=dev.get("typeName"),
                type_=dev.get("type"),
                subtype=dev.get("subtype"),
                used=dev.get("used", 1)
            )

    # --- onStart ---
    def onStart(self):
        Domoticz.Log(f"Plugin started, version {Parameters['Version']}")
        if Parameters["Mode3"] == "Yes":
            self.useZwave = True
            Domoticz.Log("P1-data will be used (Mode3=Yes)")

        devices_to_create = [
            {"unit": curTemp, "name": "Temperatuur", "typeName": "Temperature"},
            {"unit": setTemp, "name": "Setpunt Temperatuur", "type": 242, "subtype": 1},
            {"unit": autoProgram, "name": "Auto Program", "typeName": "Selector Switch", "options": {"LevelActions": "||", "LevelNames": "|Uit|Aan|Tijdelijk", "LevelOffHidden": "true", "SelectorStyle": "0"}},
            {"unit": scene, "name": "Scene", "typeName": "Selector Switch", "options": {"LevelActions": "||||", "LevelNames": "|Weg|Slapen|Thuis|Comfort|Manual", "LevelOffHidden": "true", "SelectorStyle": "0"}},
            {"unit": boilerPressure, "name": "Keteldruk", "typeName": "Pressure"},
            {"unit": boilerState, "name": "Ketelmode", "typeName": "Selector Switch", "options": {"LevelActions": "||", "LevelNames": "|Uit|CV|WW", "LevelOffHidden": "true", "SelectorStyle": "0"}},
            {"unit": boilerModulation, "name": "Ketel modulatie", "type": 243, "subtype": 6},
            {"unit": boilerSetPoint, "name": "Ketel setpoint", "type": 80, "subtype": 5, "used": 0},
            {"unit": programInfo, "name": "ProgramInfo", "typeName": "Text"}
        ]

        for dev in devices_to_create:
            self.createDeviceIfNotExists(
                unit=dev["unit"],
                name=dev["name"],
                typeName=dev.get("typeName"),
                type_=dev.get("type"),
                subtype=dev.get("subtype"),
                options=dev.get("options"),
                used=dev.get("used", 1)
            )

        if self.useZwave:
            self.setupP1Devices()

        self.fetchScenes()
        Domoticz.Heartbeat(int(Parameters['Mode2']))

    def onStop(self):
        Domoticz.Log("Plugin stopped")

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
            current_scene_val = SafeInt(Devices[scene].sValue) if scene in Devices else None
            if current_scene_val != scene_level:
                UpdateDevice(scene, 0, str(scene_level))

    def startCooldown(self, seconds=300):
        self.errorCooldown = seconds
        self.lastErrorTime = time()
        Domoticz.Log(f"Error detected and cooldown activated for {seconds} seconds.")

    def onHeartbeat(self):
        # --- Cooldown check ---
        if self.lastErrorTime and self.errorCooldown > 0:
            elapsed = time() - self.lastErrorTime
            if elapsed < self.errorCooldown:
                # Nog in wachttijd -> heartbeat wordt overgeslagen
                Domoticz.Debug(f"In cooldown ({int(self.errorCooldown - elapsed)}s resterend), heartbeat overgeslagen.")
                return
            else:
                # Cooldown voorbij -> reset
                Domoticz.Log("Toon: cooldown ended, trying to reconnect.")
                self.errorCooldown = 0
                self.lastErrorTime = None

        data = self.fetchJson("/happ_thermstat?action=getThermostatInfo")
        if data:
            self.updateThermostatDevices(data)

        # TEXT fetch for boiler
        data = self.fetchText("/boilerstatus/boilervalues.txt")
        if data:
            self.updateBoilerDevices(data)

        if self.useZwave:
            zw = self.fetchJson("/hdrv_zwave?action=getDevices.json")
            if zw:
                self.updateZwaveDevices(zw)

        self.sceneCounter += int(Parameters['Mode2'])
        if self.sceneCounter >= int(Parameters['Mode1']):
            self.fetchScenes()
            self.sceneCounter = 0

    # --- Fetch functies met nette logging ---
    def fetchJson(self, path):
        try:
            url = f"http://{Parameters['Address']}:{Parameters['Port']}{path}"
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            Domoticz.Log(f"Cannot fetch '{path}': {cleanError(e)}. Cooldown 300s.")
            self.startCooldown()
            return None

    def fetchText(self, path):
        try:
            url = f"http://{Parameters['Address']}:{Parameters['Port']}{path}"
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            return r.text
        except Exception as e:
            Domoticz.Log(f"Cannot fetch '{path}': {cleanError(e)}. Cooldown 300s.")
            self.startCooldown()
            return None

    # --- Scenes ophalen ---
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
            toon_scene = self.getActiveSceneFromToon()
            if toon_scene is not None:
                current_scene_val = SafeInt(Devices[scene].sValue) if scene in Devices else None
                if current_scene_val != toon_scene:
                    UpdateDevice(scene, 0, str(toon_scene))

    def idToScene(self, id_):
        mapping = {0: 40, 1: 30, 2: 20, 3: 10}
        return mapping.get(id_, 50)

    def getActiveSceneFromToon(self):
        data = self.fetchJson("/happ_thermstat?action=getActiveState")
        if data and "state" in data:
            try:
                toon_state = int(data["state"])
                return self.idToScene(toon_state)
            except:
                pass
        return None

    def updateSceneFromSetpoint(self, setpoint):
        matched_scene_id = None
        for scene_id, temp in self.scene_map.items():
            if abs(temp - setpoint) < 0.05:
                matched_scene_id = int(scene_id)
                break
        current_scene_val = SafeInt(Devices[scene].sValue) if scene in Devices else None
        if matched_scene_id is not None and current_scene_val != matched_scene_id:
            UpdateDevice(scene, 0, str(matched_scene_id))
            state_map = {10: 3, 20: 2, 30: 1, 40: 0}
            newState = state_map.get(matched_scene_id, None)
            if newState is not None:
                self.fetchJson(f"/happ_thermstat?action=changeSchemeState&state=2&temperatureState={newState}")
        elif matched_scene_id is None and current_scene_val != 50:
            UpdateDevice(scene, 50, "50")

    # --- Devices bijwerken ---
    def updateThermostatDevices(self, Response):
        if 'currentTemp' in Response:
            UpdateDevice(curTemp, 0, "%.1f" % (float(Response['currentTemp']) / 100))
        if 'currentSetpoint' in Response:
            setpoint = float(Response['currentSetpoint']) / 100
            UpdateDevice(setTemp, 0, "%.1f" % setpoint)
            toon_scene = self.getActiveSceneFromToon()
            if toon_scene is not None:
                current_scene_val = SafeInt(Devices[scene].sValue) if scene in Devices else None
                if current_scene_val != toon_scene:
                    UpdateDevice(scene, 0, str(toon_scene))
            self.updateSceneFromSetpoint(setpoint)
            self.updateProgramInfo(Response)
        if 'programState' in Response:
            UpdateDevice(autoProgram, 0, programStates[int(Response['programState'])])
        if 'burnerInfo' in Response:
            UpdateDevice(boilerState, 0, burnerInfos[int(Response['burnerInfo'])])
        if 'currentModulationLevel' in Response:
            UpdateDevice(boilerModulation, 0, int(Response['currentModulationLevel']))
        if 'currentInternalBoilerSetpoint' in Response:
            UpdateDevice(boilerSetPoint, 0, float(Response['currentInternalBoilerSetpoint']))

    def updateProgramInfo(self, Response):
        if all(k in Response for k in ("nextProgram","nextSetpoint","nextTime","nextState")):
            nextProgram = int(Response["nextProgram"])
            if nextProgram == -1:
                strInfo = "No program scheduled"
            elif nextProgram == 0:
                strInfo = "Program is off"
            else:
                dt = datetime.fromtimestamp(int(Response["nextTime"]))
#                strNextTime = dt.strftime("%Y-%d-%m %H:%M:%S")
                strNextTime = dt.strftime("%d-%m-%Y %H:%M:%S")
                strNextProgram = strPrograms[int(Response["nextState"])]
                strNextSetpoint = "%.1f" % (float(Response["nextSetpoint"]) / 100)
                strInfo = f"Next program {strNextProgram} ({strNextSetpoint} C) at {strNextTime}"
            if Devices[programInfo].sValue != strInfo:
                UpdateDevice(Unit=programInfo, nValue=0, sValue=strInfo)
                Domoticz.Debug(f"ProgramInfo bijgewerkt: {strInfo}")

    def updateBoilerDevices(self, Response):
    #Verwerkt de boilerstatus vanuit JSON en update alleen als de waarde verandert.
        try:
            data = json.loads(Response)

            # Helper functie: update alleen als waarde verandert
            def safe_update(unit, value):
                if unit in Devices:
                    dev = Devices[unit]
                    # Alleen update als de nieuwe waarde anders is
                    if dev.sValue != str(value):
                        UpdateDevice(unit, 0, value)

            # Boiler waarden bijwerken
            if 'boilerPressure' in data and data['boilerPressure'] is not None:
                safe_update(boilerPressure, float(data['boilerPressure']))

            if 'boilerSetpoint' in data and data['boilerSetpoint'] is not None:
                safe_update(boilerSetPoint, float(data['boilerSetpoint']))

            if 'boilerModulationLevel' in data and data['boilerModulationLevel'] is not None:
                safe_update(boilerModulation, int(data['boilerModulationLevel']))

        except Exception as e:
            Domoticz.Error(f"Fout bij verwerken boiler JSON: {e}")

    # --- Zwave bijwerken ---
    def updateZwaveDevices(self, Response):
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
            zwaveDeliveredFlow = str(int(float(zwaveDeliveredNtFlow)) + int(float(zwaveDeliveredLtFlow)))
            zwaveDeliveredQ = str(int(float(zwaveDeliveredNtQ)) + int(float(zwaveDeliveredLtQ)))
            UpdateDevice(Unit=electricity, nValue=0, sValue=zwaveDeliveredFlow + ";" + zwaveDeliveredQ)
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

def SafeInt(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def UpdateDevice(Unit, nValue, sValue, TimedOut=0):
    try:
        if Unit in Devices:
            dev = Devices[Unit]
            if (dev.nValue != nValue) or (dev.sValue != str(sValue)):
                old_s = dev.sValue
                readable_new = sValue
                readable_old = old_s

                # Leesbare namen
                if Unit == scene:
                    scene_labels = {"10": "Weg", "20": "Slapen", "30": "Thuis", "40": "Comfort", "50": "Manual"}
                    readable_new = scene_labels.get(str(sValue), str(sValue))
                    readable_old = scene_labels.get(str(old_s), str(old_s))

                if Unit == autoProgram:
                    prog_labels = {"10": "Uit", "20": "Aan", "30": "Tijdelijk"}
                    readable_new = prog_labels.get(str(sValue), str(sValue))
                    readable_old = prog_labels.get(str(old_s), str(old_s))

                if Unit == boilerState:
                    boiler_labels = {"10": "Uit", "20": "CV", "30": "WW"}
                    readable_new = boiler_labels.get(str(sValue), str(sValue))
                    readable_old = boiler_labels.get(str(old_s), str(old_s))

                dev.Update(nValue=nValue, sValue=str(sValue), TimedOut=TimedOut)

                silent_units = [
                    gas, electricity, genElectricity, p1electricity,
                    boilerSetPoint,
                    curTemp,
                    boilerModulation,
                    boilerPressure
                ]

                if Unit not in silent_units:
                    Domoticz.Log(f"{dev.Name}: {readable_old} -> '{readable_new}'")

                Domoticz.Debug(f"{dev.Name}: {readable_old} -> '{readable_new}'")
    except Exception as e:
        Domoticz.Log(f"Update of device {Unit} failed: {e}")
