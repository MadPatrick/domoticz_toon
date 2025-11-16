# domoticz-rooted-toon

A  python plugin to interface Domoticz with a rooted version of the Toon thermostat


### 📥 Install plugin
1. Go in your Domoticz directory using a command line and open the plugins directory:  
   ```cd domoticz/plugins```
2. Clone the plugin:  
   ```git clone https://github.com/MadPatrick/domoticz_toon```
3. Restart Domoticz:  
   ```sudo systemctl restart domoticz```
 
---

### ⚙️ Currently the following functionality is available:
-   Room Temperature  
-   Setpoint (read & write)  
-   Synchronisation between Setpoint and Toon Scenes  
-   Toon Scenes (Weg / Slapen / Thuis / Comfort / Manual)  
-   Toon Programs (Uit / Aan / Tijdelijk)  
-   Program state synchronisation  
-   Toon Program information (next program, time, setpoint, state)  
-   Toon Boiler status (Uit / CV / WW)  
-   Boiler pressure  
-   Boiler modulation percentage  
-   Boiler internal setpoint  
-   Gas consumption (Z-Wave / P1)  
-   Power consumption (delivered normal / delivered low)  
-   Power production (solar / received normal / received low)  
-   Combined P1 electricity meter  
-   Support for Toon v1, v2 and user-defined Z-Wave address mappings  
-   Automatic cooldown when Toon is unreachable (prevents Domoticz error spam)

---

**⚠️ Use at your own risk.**

The P1 values are predefined for most common Toons.  
It is possible that your Toon uses different values.  
You can check this using the JSON link:

http://TOON_IP/hdrv_zwave?action=getDevices.json
 
Unfortunately, there is no clear information in the JSON that identifies which device each internal address belongs to.  
Different Toons may also use different structures (e.g., dev_2.x or dev_3.x).  
So it often requires some trial and error.

For example:<br>
You can see at *dev_2.4* values in the fields **CurrentElectricityFlow** and **CurrentElectricityQuantity**.  
The correct P1 sequence is:

```Gas ; elec_delivered_normal ; elec_delivered_low ; elec_received_normal ; elec_received_low```

![image](https://user-images.githubusercontent.com/81873830/214092186-e73b1482-96ec-4488-b056-1754836a0d1b.png)

You can fill in these numbers in the user-defined P1 address field, separated by a semicolon (`;`).

---

### 📟 Configuration menu
<img width="1079" height="616" alt="image" src="https://github.com/user-attachments/assets/005c0ddd-ba8c-4a7b-9347-783454adae42" />


### 📲 Installed devices
![image](https://user-images.githubusercontent.com/81873830/210851429-d6085416-cc71-4519-8603-94d8226793e3.png)
