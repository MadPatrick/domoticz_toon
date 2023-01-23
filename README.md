# domoticz-rooted-toon

A Domoticz python plugin to interface with a rooted version of the Tooon thermostat


### install plugin
1. Go in your Domoticz directory using a command line and open the plugins directory:
 ```cd domoticz/plugins```
2. clone the plugin:
 ```git clone https://github.com/MadPatrick/domoticz_toon```
2. Restart Domoticz:
 ```sudo systemctl restart domoticz```
 
 
Currently the follow functionality is being added:
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

Use at your own risk.

The P1 values are predefined for most common Toons
It is possible that your Toon has different values. 
You can check this this the JSON link

http://TOON_IP/hdrv_zwave?action=getDevices.json
 
Unfortunately, there is no good information in the JSON to determine which number belongs to which device.
Also, there is a variety of numbers between different Toon's, Like dev_2.x or dev_3.x...... 

For example:
![image](https://user-images.githubusercontent.com/81873830/214092186-e73b1482-96ec-4488-b056-1754836a0d1b.png)

fill in these numbers in the user defined field
### Configuration menu
![image](https://user-images.githubusercontent.com/81873830/214091415-6063c7d8-8e4b-46f3-b1e6-c2dfb01d9e1e.png)

### installed devices
![image](https://user-images.githubusercontent.com/81873830/210851429-d6085416-cc71-4519-8603-94d8226793e3.png)

