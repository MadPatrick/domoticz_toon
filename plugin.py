"""
<plugin key="RootedToonPlug" name="Toon Rooted" author="MadPatrick" version="2.7.3" externallink="https://github.com/MadPatrick/domoticz_toon">
      <description>
          <br/><h2>Domoticz Plugin for Toon (Rooted)</h2>
          <br/>Version: 2.7.3
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
                <option label="30s" value="30"/>
                <option label="30m" value="1800"/>
                <option label="1hr" value="3600" default="true"/>
                <option label="2hr" value="7200"/>
                <option label="6hr" value="21600"/>
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
        <param field="Mode5" label="P1 addresses" width="300px" default="">
        <description><br/>Fill in the P1 devicenumbers separated by ;  (2.1;2.4;2.6;2.5;2.7)
                     <br/><span style="color: yellow;">Leave empty for auto detection</span></description>
        </param>
        <param field="Mode6" label="Debug logging" width="150px">
            <options>
                <option label="On" value="Debug"/>
                <option label="Off" value="Normal" default="true"/>
            </options>
        </param>
    </params>
</plugin>
"""

import Domoticz
import requests
import json
import os
from datetime import datetime
from time import time

# --- Constants ---
programStates = ['10','20','30','40']  # index 3 = vacation mode = "Vakantie"
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
        self.imageID = 0
        self.imageInvID = 0
        self.heartbeat_interval = 60
        self.scene_interval = 3600
        # Expecte daily reboot window
        self.expectedDowntimeStart = "03:00"
        self.expectedDowntimeEnd   = "04:00"
        self.expectedDowntimeLogged = False

    # --- Config laden ---
    def loadConfig(self):
        config_path = os.path.join(Parameters["HomeFolder"], "config.txt")
        if not os.path.isfile(config_path):
            Domoticz.Log(f"config.txt not found ({config_path}), default values used.")
            return
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip()
                        if key == "DowntimeStart":
                            if len(value) == 5 and value[2] == ":" and value[:2].isdigit() and value[3:].isdigit():
                                self.expectedDowntimeStart = value
                            else:
                                Domoticz.Log(f"Invalid format for DowntimeStart: '{value}', default values used.")
                        elif key == "DowntimeEnd":
                            if len(value) == 5 and value[2] == ":" and value[:2].isdigit() and value[3:].isdigit():
                                self.expectedDowntimeEnd = value
                            else:
                                Domoticz.Log(f"Invalid format for DowntimeEnd: '{value}', default values used.")
            Domoticz.Log(f"Expected downtime window: {self.expectedDowntimeStart} - {self.expectedDowntimeEnd}")
        except Exception as e:
            Domoticz.Log(f"Error reading config.txt: {e}")

    # --- Device helper ---
    def createDeviceIfNotExists(self, unit, name, typeName=None, type_=None,
                                subtype=None, options=None, used=1, image=None):
        if unit not in Devices:
            params = {
                "Name": name,
                "Unit": unit,
                "Used": used
            }
            if typeName: params["TypeName"] = typeName
            if type_ is not None: params["Type"] = type_
            if subtype is not None: params["Subtype"] = subtype
            if options: params["Options"] = options
            if image is not None: params["Image"] = image

            Domoticz.Device(**params).Create()

            if unit in Devices:
                initialValue = "0"
                if unit == p1electricity:
                    initialValue = "0;0;0;0;0;0"
                Devices[unit].Update(nValue=0, sValue=initialValue)
                Domoticz.Log(f"Device '{name}' (Unit {unit}) initialized to 0")

    # --- P1 / Zwave helper ---
    def setupP1Devices(self):
        paramList = []
        detected_version = None

        if Parameters["Mode5"]:
            paramList = Parameters["Mode5"].split(";")
            if len(paramList) == 5:
                self.ia_gas, self.ia_ednt, self.ia_edlt, self.ia_ernt, self.ia_erlt = paramList
                detected_version = "Usermode"
                Domoticz.Log(f"Manual P1-addresses used: {paramList}")
            else:
                Domoticz.Log("Mode5 set, but wrong number of addresses (5 expected)")
                paramList = []

        if not paramList:
            detected_version = "niet gedetecteerd"
            try:
                zwave_json = self.fetchJson("/hdrv_zwave?action=getDevices.json")
                if zwave_json:
                    internal_addresses = [
                        dev["internalAddress"] for dev in zwave_json.values()
                        if "internalAddress" in dev
                    ]

                    valid_addresses = [
                        addr for addr in internal_addresses
                        if addr.replace(".", "").isdigit()
                    ]

                    if not valid_addresses:
                        Domoticz.Log("WARNING: No valid meter addresses detected")
                        return

                    prefixes = set(addr.split(".")[0] if "." in addr else addr for addr in valid_addresses)

                    detected_prefix = max(prefixes, key=lambda p: sum(1 for a in valid_addresses if a.startswith(p + ".")))

                    if Parameters["Mode4"] == "v1":
                        suffixes = ["1","3","5","4","6"]
                    else:  # v2
                        suffixes = ["1","4","6","5","7"]

                    paramList = [f"{detected_prefix}.{s}" for s in suffixes]

                    if len(paramList) == 5:
                        self.ia_gas, self.ia_ednt, self.ia_edlt, self.ia_ernt, self.ia_erlt = paramList
                        detected_version = f"{Parameters['Mode4']} ({detected_prefix}.x)"

            except Exception as e:
                detected_version = "error"
                Domoticz.Log(f"Error with automatic detection of Zwave versie: {e}")

        Domoticz.Log(
            f"P1-devices {detected_version} : Gas={self.ia_gas}, DeliveredNT={self.ia_ednt}, "
            f"DeliveredLT={self.ia_edlt}, ReceivedNT={self.ia_ernt}, "
            f"ReceivedLT={self.ia_erlt}"
        )

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
        Domoticz.Log(f"Starting Plugin")

        self.heartbeat_interval = int(Parameters['Mode2'])
        self.scene_interval = int(Parameters['Mode1'])

        self.loadConfig()

        if Parameters["Mode3"] == "Yes":
            self.useZwave = True
            Domoticz.Log("P1-data Collection Enabled")

        if Parameters["Mode6"] == "Debug":
            Domoticz.Debugging(1)
            Domoticz.Log("Debug logging enabled")
            self._dumpConfigToLog()
        else:
            Domoticz.Debugging(0)

        # --- Icon Packs ---
        icon_packs = {
            "Toon": "imageID",
            "Toon_inv": "imageInvID"
        }

        for pack_name, attr_name in icon_packs.items():
            creating_new_icon = pack_name not in Images
            try:
                if creating_new_icon:
                    Domoticz.Image(f"{pack_name}.zip").Create()
                if pack_name in Images:
                    setattr(self, attr_name, Images[pack_name].ID)
                else:
                    Domoticz.Error(f"Unable to load icon pack '{pack_name}.zip'")
            except Exception as e:
                Domoticz.Error(f"Error loading icon pack '{pack_name}': {e}")

        devices_to_create = [
            {"unit": curTemp, "name": "Temperatuur", "typeName": "Temperature", "image": self.imageID},
            {"unit": setTemp, "name": "Setpunt Temperatuur", "type": 242, "subtype": 1, "image": self.imageID},
            {"unit": autoProgram, "name": "Auto Program", "typeName": "Selector Switch", "options": {"LevelActions": "|||", "LevelNames": "|Uit|Aan|Tijdelijk|Vakantie", "LevelOffHidden": "true", "SelectorStyle": "0"}, "image": self.imageInvID},
            {"unit": scene, "name": "Scene", "typeName": "Selector Switch", "options": {"LevelActions": "||||", "LevelNames": "|Weg|Slapen|Thuis|Comfort|Manual", "LevelOffHidden": "true", "SelectorStyle": "0"}, "image": self.imageInvID},
            {"unit": boilerPressure, "name": "Keteldruk", "typeName": "Pressure", "image": self.imageID},
            {"unit": boilerState, "name": "Ketelmode", "typeName": "Selector Switch", "options": {"LevelActions": "||", "LevelNames": "|Uit|CV|WW", "LevelOffHidden": "true", "SelectorStyle": "0"}, "image": self.imageInvID},
            {"unit": boilerModulation, "name": "Ketel modulatie", "type": 243, "subtype": 6, "image": self.imageID},
            {"unit": boilerSetPoint, "name": "Ketel setpoint", "type": 80, "subtype": 5, "used": 0, "image": self.imageID},
            {"unit": programInfo, "name": "ProgramInfo", "typeName": "Text", "image": self.imageID}
        ]

        for dev in devices_to_create:
            self.createDeviceIfNotExists(
                unit=dev["unit"],
                name=dev["name"],
                typeName=dev.get("typeName"),
                type_=dev.get("type"),
                subtype=dev.get("subtype"),
                options=dev.get("options"),
                used=dev.get("used", 1),
                image=dev.get("image")
            )

        if self.useZwave:
            self.setupP1Devices()

        self.fetchScenes()
        Domoticz.Heartbeat(self.heartbeat_interval)

        Domoticz.Log(f"Heartbeat interval: {self.heartbeat_interval} sec")
        Domoticz.Log(f"Scenes refresh interval: {self.scene_interval // 60} min")

    def onStop(self):
        Domoticz.Log("Plugin stopped")

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug(f"onCommand Unit {Unit} Command {Command} Level {Level}")
        if Unit == setTemp:
            setpoint = int(round(Level * 100))
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
        elif Unit == autoProgram:
            prog_level = int(Level)
            # Map selector level (10=Uit, 20=Aan, 30=Tijdelijk, 40=Vakantie) to Toon state (0,1,2,3)
            prog_state_map = {10: 0, 20: 1, 30: 2, 40: 3}
            prog_state = prog_state_map.get(prog_level, None)
            if prog_state is not None:
                self.fetchJson(f"/happ_thermstat?action=changeSchemeState&state={prog_state}")
                UpdateDevice(autoProgram, 0, str(prog_level))

    def startCooldown(self, seconds=300):
        self.errorCooldown = seconds
        self.lastErrorTime = time()
        Domoticz.Log(f"Connection failed. Cooldown started of {seconds}s, next attempt in {seconds // 60} minutes.")

    def isExpectedDowntime(self):
        now = datetime.now().strftime("%H:%M")
        return self.expectedDowntimeStart <= now <= self.expectedDowntimeEnd

    def onHeartbeat(self):
        # --- Cooldown check ---
        if self.lastErrorTime and self.errorCooldown > 0:
            elapsed = time() - self.lastErrorTime
            if elapsed < self.errorCooldown:
                Domoticz.Debug(f"Cooldown mode({int(self.errorCooldown - elapsed)}s remaining), heartbeat skipped.")
                return
            else:
                Domoticz.Log("Cooldown ended, connection tested...")
                self.errorCooldown = 0
                self.lastErrorTime = None

                test = self.fetchJson("/happ_thermstat?action=getThermostatInfo")
                if test is None:
                    Domoticz.Error("No connection after cooldown. Check the device.")
                    return
                else:
                    Domoticz.Log("Connection restored after cooldown.")
                    self.updateThermostatDevices(test)
                    self._doBoilerAndZwave()
                    self.sceneCounter += self.heartbeat_interval
                    if self.sceneCounter >= self.scene_interval:
                        self.fetchScenes(thermostat_data=test)
                        self.sceneCounter = 0
                    return

        results = []

        thermostat_data = self.fetchJson("/happ_thermstat?action=getThermostatInfo")
        results.append(thermostat_data is not None)
        if thermostat_data:
            self.updateThermostatDevices(thermostat_data)

        self._doBoilerAndZwave(results)

        if all(results) and self.expectedDowntimeLogged:
            Domoticz.Log("Connection restored after expected restart.")
            self.expectedDowntimeLogged = False

        self.sceneCounter += self.heartbeat_interval
        if self.sceneCounter >= self.scene_interval:
            self.fetchScenes(thermostat_data=thermostat_data)
            self.sceneCounter = 0

    def _doBoilerAndZwave(self, results=None):
        """Retrieve boiler and Z-Wave data and process it. Optionally keep a results list."""
        boiler_data = self.fetchJson("/boilerstatus/boilervalues.txt")
        if results is not None:
            results.append(boiler_data is not None)
        if boiler_data:
            self.updateBoilerDevices(boiler_data)

        if self.useZwave:
            zw = self.fetchJson("/hdrv_zwave?action=getDevices.json")
            if results is not None:
                results.append(zw is not None)
            if zw:
                self.updateZwaveDevices(zw)

    # --- Fetch functies ---
    def fetchJson(self, path):
        try:
            url = f"http://{Parameters['Address']}:{Parameters['Port']}{path}"
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if self.isExpectedDowntime():
                if not self.expectedDowntimeLogged:
                    Domoticz.Debug(f"Expected downtime, fetch skipped ({path})")
                    self.expectedDowntimeLogged = True
                return None
            else:
                self.startCooldown()
                return None

    # --- Scenes ophalen ---
    def fetchScenes(self, thermostat_data=None):
        old_scene_map = self.scene_map.copy()

        data = self.fetchJson("/hcb_config?action=getObjectConfigTree&package=happ_thermstat&internalAddress=thermostatStates")
        if data and 'states' in data and len(data['states']) > 0:
            state_list = data['states'][0]['state']
            self.scene_map = {}
            for s in state_list:
                id_ = int(s['id'][0])
                temp = float(s['tempValue'][0]) / 100
                if id_ <= 3:
                    self.scene_map[str(self.idToScene(id_))] = temp

            if self.scene_map != old_scene_map:
                Domoticz.Log("Toon Scene settings updated:")
                for scene_id, temp in sorted(self.scene_map.items()):
                    scene_name = {10: "Weg", 20: "Slapen", 30: "Thuis", 40: "Comfort", 50: "Manual"}.get(int(scene_id), str(scene_id))
                    Domoticz.Log(f"  {scene_name}: {temp:.1f}\u00B0C")
            else:
                Domoticz.Debug("Toon scene settings retrieved, no changes")

        if thermostat_data is None:
            thermostat_data = self.fetchJson("/happ_thermstat?action=getThermostatInfo")

        if thermostat_data and 'activeState' in thermostat_data:
            toon_scene = self.idToScene(int(thermostat_data['activeState']))
            current_scene_val = SafeInt(Devices[scene].sValue) if scene in Devices else None
            if current_scene_val != toon_scene:
                UpdateDevice(scene, 0, str(toon_scene))

    def idToScene(self, id_):
        mapping = {0: 40, 1: 30, 2: 20, 3: 10}
        return mapping.get(id_, 50)

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
            UpdateDevice(scene, 0, "50")

    def updateThermostatDevices(self, Response):
        if 'currentTemp' in Response:
            UpdateDevice(curTemp, 0, "%.1f" % (float(Response['currentTemp']) / 100))
        if 'currentSetpoint' in Response:
            setpoint = float(Response['currentSetpoint']) / 100
            UpdateDevice(setTemp, 0, "%.1f" % setpoint)

            if 'activeState' in Response:
                toon_scene = self.idToScene(int(Response['activeState']))
                current_scene_val = SafeInt(Devices[scene].sValue) if scene in Devices else None
                if current_scene_val != toon_scene:
                    UpdateDevice(scene, 0, str(toon_scene))

            self.updateSceneFromSetpoint(setpoint)
            self.updateProgramInfo(Response)
        if 'programState' in Response:
            prog_idx = int(Response['programState'])
            if 0 <= prog_idx < len(programStates):
                UpdateDevice(autoProgram, 0, programStates[prog_idx])
        if 'burnerInfo' in Response:
            burner_idx = int(Response['burnerInfo'])
            if 0 <= burner_idx < len(burnerInfos):
                UpdateDevice(boilerState, 0, burnerInfos[burner_idx])
        if 'currentModulationLevel' in Response:
            UpdateDevice(boilerModulation, 0, str(int(Response['currentModulationLevel'])))

    def updateProgramInfo(self, Response):
        if all(k in Response for k in ("nextProgram","nextSetpoint","nextTime","nextState")):
            nextProgram = int(Response["nextProgram"])
            if nextProgram == -1:
                strInfo = "No program scheduled"
            elif nextProgram == 0:
                strInfo = "Program is off"
            else:
                dt = datetime.fromtimestamp(int(Response["nextTime"]))
                strNextTime = dt.strftime("%d-%m-%Y %H:%M:%S")
                strNextProgram = strPrograms[int(Response["nextState"])]
                strNextSetpoint = "%.1f" % (float(Response["nextSetpoint"]) / 100)
                strInfo = f"Next program {strNextProgram} ({strNextSetpoint} C) at {strNextTime}"
            if programInfo in Devices and Devices[programInfo].sValue != strInfo:
                UpdateDevice(Unit=programInfo, nValue=0, sValue=strInfo)
                Domoticz.Debug(f"ProgramInfo bijgewerkt: {strInfo}")

    def updateBoilerDevices(self, data):
        try:
            def safe_update(unit, value):
                if unit in Devices:
                    dev = Devices[unit]
                    if dev.sValue != str(value):
                        UpdateDevice(unit, 0, str(value))

            if 'boilerPressure' in data and data['boilerPressure'] is not None:
                safe_update(boilerPressure, float(data['boilerPressure']))

            if 'boilerSetpoint' in data and data['boilerSetpoint'] is not None:
                safe_update(boilerSetPoint, float(data['boilerSetpoint']))

            if 'boilerModulationLevel' in data and data['boilerModulationLevel'] is not None:
                safe_update(boilerModulation, int(data['boilerModulationLevel']))

        except Exception as e:
            Domoticz.Error(f"Fout bij verwerken boiler data: {e}")

    def updateZwaveDevices(self, Response):
        def safe_float(value, fallback=0.0):
            try:
                result = float(value)
                if result != result:  # NaN check
                    return fallback
                return result
            except (ValueError, TypeError):
                return fallback

        zwaveDeliveredNtFlow = 0.0
        zwaveDeliveredLtFlow = 0.0
        zwaveDeliveredNtQ = 0.0
        zwaveDeliveredLtQ = 0.0
        zwaveReceivedNtFlow = 0.0
        zwaveReceivedLtFlow = 0.0
        zwaveReceivedNtQ = 0.0
        zwaveReceivedLtQ = 0.0

        for zwaveDev in Response:
            info = Response[zwaveDev]
            if 'internalAddress' not in info:
                continue
            ia = info['internalAddress']
            if ia == self.ia_gas:
                gas_val = safe_float(info.get('CurrentGasQuantity', 0))
                UpdateDevice(Unit=gas, nValue=0, sValue=str(int(gas_val)))
            elif ia == self.ia_ednt:
                zwaveDeliveredNtFlow = safe_float(info.get('CurrentElectricityFlow', 0))
                zwaveDeliveredNtQ    = safe_float(info.get('CurrentElectricityQuantity', 0))
            elif ia == self.ia_edlt:
                zwaveDeliveredLtFlow = safe_float(info.get('CurrentElectricityFlow', 0))
                zwaveDeliveredLtQ    = safe_float(info.get('CurrentElectricityQuantity', 0))
            elif ia == self.ia_ernt:
                zwaveReceivedNtFlow = safe_float(info.get('CurrentElectricityFlow', 0))
                zwaveReceivedNtQ    = safe_float(info.get('CurrentElectricityQuantity', 0))
            elif ia == self.ia_erlt:
                zwaveReceivedLtFlow = safe_float(info.get('CurrentElectricityFlow', 0))
                zwaveReceivedLtQ    = safe_float(info.get('CurrentElectricityQuantity', 0))

        try:
            zwaveDeliveredFlow = int(zwaveDeliveredNtFlow) + int(zwaveDeliveredLtFlow)
            zwaveDeliveredQ    = int(zwaveDeliveredNtQ)    + int(zwaveDeliveredLtQ)
            UpdateDevice(Unit=electricity, nValue=0, sValue=f"{zwaveDeliveredFlow};{zwaveDeliveredQ}")

            zwaveReceivedFlow = int(zwaveReceivedNtFlow) + int(zwaveReceivedLtFlow)
            zwaveReceivedQ    = int(zwaveReceivedNtQ)    + int(zwaveReceivedLtQ)
            UpdateDevice(Unit=genElectricity, nValue=0, sValue=f"{zwaveReceivedFlow};{zwaveReceivedQ}")

            UpdateDevice(Unit=p1electricity, nValue=0, sValue="{};{};{};{};{};{}".format(
                int(zwaveDeliveredNtQ),
                int(zwaveDeliveredLtQ),
                int(zwaveReceivedNtQ),
                int(zwaveReceivedLtQ),
                zwaveDeliveredFlow,
                zwaveReceivedFlow
            ))
        except Exception as e:
            Domoticz.Log(f"Error processing P1 values: {e}")

    # --- Debug helper ---
    def _dumpConfigToLog(self):
        Domoticz.Debug("Parameters:")
        for x in Parameters:
            Domoticz.Debug(f"'{x}':'{Parameters[x]}'")


# --- Global instance ---
global _plugin
_plugin = BasePlugin()
def onStart(): _plugin.onStart()
def onStop(): _plugin.onStop()
def onCommand(Unit, Command, Level, Hue): _plugin.onCommand(Unit, Command, Level, Hue)
def onHeartbeat(): _plugin.onHeartbeat()

# --- Helpers ---
def cleanError(e):
    msg = str(e).lower()
    if "refused" in msg: return "Connection refused"
    if "timeout" in msg: return "Timeout"
    if "max retries" in msg: return "Max retries reached"
    if "not found" in msg: return "Now found"
    return msg.split('(')[0].strip()

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

                if Unit == scene:
                    scene_labels = {"10": "Weg", "20": "Slapen", "30": "Thuis", "40": "Comfort", "50": "Manual"}
                    readable_new = scene_labels.get(str(sValue), str(sValue))
                    readable_old = scene_labels.get(str(old_s), str(old_s))

                if Unit == autoProgram:
                    prog_labels = {"10": "Uit", "20": "Aan", "30": "Tijdelijk", "40": "Vakantie"}
                    readable_new = prog_labels.get(str(sValue), str(sValue))
                    readable_old = prog_labels.get(str(old_s), str(old_s))

                if Unit == boilerState:
                    boiler_labels = {"10": "Uit", "20": "CV", "30": "WW"}
                    readable_new = boiler_labels.get(str(sValue), str(sValue))
                    readable_old = boiler_labels.get(str(old_s), str(old_s))

                dev.Update(nValue=nValue, sValue=str(sValue), TimedOut=TimedOut)

                silent_units = [
                    gas, electricity, genElectricity, p1electricity,
                    boilerSetPoint, curTemp, boilerModulation, boilerPressure
                ]

                if Unit not in silent_units:
                    Domoticz.Log(f"{dev.Name}: {readable_old} -> '{readable_new}'")
                Domoticz.Debug(f"{dev.Name}: {readable_old} -> '{readable_new}'")

    except Exception as e:
        Domoticz.Log(f"Update of device {Unit} failed: {e}")
