# domoticz-rooted-toon 🏠🌡️

A Python plugin to interface Domoticz with a **rooted Toon thermostat**.

This plugin enables full control over setpoints and program synchronization, while providing extensive monitoring of energy data (via P1 port or Z-Wave) and boiler status.

## 📥 Installation

Follow these steps to install the plugin in your Domoticz environment.

1.  Navigate to the `plugins` directory in your Domoticz installation:
    ```bash
    cd domoticz/plugins
    ```
2.  Clone the repository:
    ```bash
    git clone https://github.com/MadPatrick/domoticz_toon
    ```
3.  **Restart** Domoticz to load the plugin:
    ```bash
    sudo systemctl restart domoticz
    ```

---

## ⚙️ Key Functionality Overview

The plugin provides **bidirectional synchronization** and comprehensive monitoring of your Toon:

### Thermostat & Programs
* **Room Temperature** 🌡️: Displays the current measured temperature.
* **Setpoint** (Read & Write): Allows reading and writing the desired temperature.
* **Scene Synchronization**: Automatic synchronization between the setpoint and Toon Scenes:
    * **Away / Sleep / Home / Comfort / Manual**
* **Program Status**: Shows the current program mode:
    * **Off / On / Temporary**
* **Program Info**: Detailed information on the next scheduled program (time, setpoint, and state).

### Boiler & Heating System
* **Boiler Status**: Displays the current burner activity:
    * **Off / CH** (Central Heating) / **HW** (Hot Water)
* **Boiler Pressure**
* **Boiler Modulation Percentage**
* **Boiler Internal Setpoint**

### Energy Monitoring (P1 / Z-Wave)
* **Gas Consumption** (Z-Wave / P1 port).
* **Power Consumption**: Delivered (normal and low tariff).
* **Power Production**: Generated/Received (normal and low tariff, for solar PV).
* **Combined P1 Electricity Meter**: A single Domoticz device combining all flows.

### System & Compatibility
* Support for **Toon v1, v2, and user-defined** Z-Wave/P1 address mappings.
* **Automatic Cooldown**: Implements a pause/timeout mechanism when the Toon becomes unreachable, preventing Domoticz error spam.

---

## 🔌 P1 / Z-Wave Address Configuration (Advanced)

**⚠️ Use at your own risk.** The internal Z-Wave/P1 device addresses may vary across Toon versions and installations.

The plugin provides default mappings, but if they are incorrect, you may need to specify the addresses manually:

1.  **Find the Addresses**: Open the JSON link in your browser to view the live internal addresses:
    ```
    http://TOON_IP/hdrv_zwave?action=getDevices.json
    ```
2.  **Identification**: Search the JSON output for the Z-Wave devices (*e.g., dev\_2.1, dev\_2.4, dev\_3.1*) and identify which contain relevant values (e.g., `CurrentElectricityFlow`, `CurrentGasQuantity`). Note that different Toons might use `dev_2.x` or `dev_3.x` structures.

    **Example for an Electricity Meter:**
    If `dev_2.4` shows values in the fields **CurrentElectricityFlow** and **CurrentElectricityQuantity**, it is likely one of the electricity meters.

    ![image](https://user-images.githubusercontent.com/81873830/214092186-e73b1482-96ec-4488-b056-1754836a0d1b.png)

3.  **Address Sequence**: Enter the internal Z-Wave/P1 addresses into the plugin's configuration in the following **required order**, separated by a semicolon (**;**):

    ```
    Gas ; elec_delivered_normal ; elec_delivered_low ; elec_received_normal ; elec_received_low
    ```
    *Example: `2.1;2.4;2.6;2.5;2.7`*

---

## 📟 Configuration Menu in Domoticz

Set up the connection details and Z-Wave/P1 behavior of the plugin via the Domoticz hardware setup menu.

<img width="1079" height="616" alt="image" src="https://github.com/user-attachments/assets/005c0ddd-ba8c-4a7b-9347-783454adae42" />


## 📲 Installed Domoticz Devices

A list of the devices created by the plugin in your Domoticz Devices tab.

![image](https://user-images.githubusercontent.com/81873830/210851429-d6085416-cc71-4519-8603-94d8226793e3.png)
