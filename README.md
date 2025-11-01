# domoticz-rooted-toon

A  python plugin to interface Domoticz with a rooted version of the Tooon thermostat


### install plugin
1. Go in your Domoticz directory using a command line and open the plugins directory:
 ```cd domoticz/plugins```
2. clone the plugin:
 ```git clone https://github.com/MadPatrick/domoticz_toon```
2. Restart Domoticz:
 ```sudo systemctl restart domoticz```
 
 
Currently the follow functionality is being available:
- Setpoint
- Boiler pressure
- Gas consumption
- Power Consumption
- Boiler modulation
- Room Temperatuur
- Toon Programs
- Toon Scenes
- Toon Boiler status
- Toon Program information

**Use at your own risk.**

The P1 values are predefined for most common Toons.
It is possible that your Toon has different values. 
You can check this via the JSON link

```http://TOON_IP/hdrv_zwave?action=getDevices.json```
 
Unfortunately, there is no good information in the JSON to determine which number belongs to which device.
Also, there are different numbers between different Toon's, such as dev_2.x or dev_3.x.......
So basically it's a bit of trail and error

For example:
<br>You can see at dev_2.4 values in the field  "CurrentElectricityFlow" and "CurrentElectricityQuantity"
<br>The correct sequence is :

```Gas ; elec_delivered_normal ; elec_delivered_low ; elec_received_normal ; elec_received_low```

![image](https://user-images.githubusercontent.com/81873830/214092186-e73b1482-96ec-4488-b056-1754836a0d1b.png)

You can fill in these numbers in the user defined field seperated by ;

### Configuration menu
<img width="1071" height="624" alt="image" src="https://github.com/user-attachments/assets/54d0739f-9640-4805-b80f-0449b9631667" />

### installed devices
<img width="1234" height="620" alt="image" src="https://github.com/user-attachments/assets/0bacf665-80a5-4b56-9bfc-918ffdda77dc" />



