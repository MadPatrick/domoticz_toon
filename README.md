# domoticz-rooted-toon 🏠🌡️

Een Python-plugin voor Domoticz om te communiceren met een **geroote Toon-thermostaat**.

Deze plugin biedt volledige controle over setpoints en programmasynchronisatie, plus uitgebreide monitoring van energiegegevens (via de P1-poort of Z-Wave) en ketelstatus.

## 📥 Installatie

Volg deze stappen om de plugin te installeren in je Domoticz-omgeving.

1.  Ga naar de `plugins` map in je Domoticz-directory:
    ```bash
    cd domoticz/plugins
    ```
2.  Kloon de repository:
    ```bash
    git clone [https://github.com/MadPatrick/domoticz_toon](https://github.com/MadPatrick/domoticz_toon)
    ```
3.  **Herstart** Domoticz om de plugin te activeren:
    ```bash
    sudo systemctl restart domoticz
    ```

---

## ⚙️ Overzicht van Functionaliteit

De plugin biedt **bidirectionele synchronisatie** en uitgebreide monitoring:

### Thermostaat & Programma's
* **Kamertemperatuur** 🌡️: Weergave van de huidige temperatuur.
* **Setpunt** (Lezen & Schrijven): Instellen en uitlezen van de gewenste temperatuur.
* **Scène Synchronisatie**: Automatische synchronisatie tussen het setpunt en de Toon Scènes:
    * **Weg / Slapen / Thuis / Comfort / Manual**
* **Programmastatus**: Weergave van de automatische programmamodus:
    * **Uit / Aan / Tijdelijk**
* **Programma-Info**: Gedetailleerde informatie over het volgende geplande programma (tijd, setpunt en status).

### Ketel & Verwarming
* **Ketelstatus**: Weergave van de huidige branderactiviteit:
    * **Uit / CV** (Centrale Verwarming) / **WW** (Warm Water)
* **Keteldruk**
* **Modulatiepercentage** (Ketel)
* **Intern Ketel Setpunt**

### Energie Monitoring (P1 / Z-Wave)
* **Gasverbruik** (Z-Wave / P1-poort).
* **Elektriciteitsverbruik**: Geleverd (normaal en laag tarief).
* **Elektriciteitsproductie**: Opwekt (normaal en laag tarief, voor bijv. zonnepanelen).
* **Gecombineerde P1 Meter**: Een Domoticz-apparaat dat alle tarieven en flows combineert.

### Systeem & Compatibiliteit
* Ondersteuning voor Toon-versies **v1, v2 en door de gebruiker gedefinieerde** Z-Wave/P1-adresmappings.
* **Automatische Cooldown**: Activeert een pauze in het ophalen van data wanneer de Toon onbereikbaar is. Dit voorkomt overbelasting en Domoticz foutmeldingen.

---

## 🔌 P1 / Z-Wave Adres Configuratie (Expert)

**⚠️ Gebruik op Eigen Risico:** De interne adressen van de Z-Wave/P1-apparaten kunnen verschillen per Toon-versie en installatie.

De plugin biedt standaardmappings voor Toon v1 en v2. Als deze niet werken, moet je mogelijk handmatig de adressen opgeven:

1.  **Vind de Adressen**: Open de JSON-link in je browser om de actuele interne adressen te zien:
    ```
    http://<TOON_IP>/hdrv_zwave?action=getDevices.json
    ```
2.  **Identificatie**: Zoek in de JSON-output naar de Z-Wave apparaten (*bv. dev\_2.1, dev\_2.4, dev\_3.1*) en identificeer welke waarden ze bevatten (bijv. `CurrentElectricityFlow`, `CurrentGasQuantity`). Verschillende Toons kunnen de structuur `dev_2.x` of `dev_3.x` gebruiken.

    **Voorbeeld van een elektriciteitsmeter:**
    Als `dev_2.4` waarden in de velden `CurrentElectricityFlow` en `CurrentElectricityQuantity` bevat, is dit waarschijnlijk een van de elektriciteitsmeters.

    ![image](https://user-images.githubusercontent.com/81873830/214092186-e73b1482-96ec-4488-b056-1754836a0d1b.png)

3.  **Adresreeks**: Voer de interne adressen in de plugin-configuratie in de volgende verplichte volgorde in, gescheiden door een puntkomma (**;**):

    ```
    Gas ; Geleverd_Normaal ; Geleverd_Laag ; Ontvangen_Normaal ; Ontvangen_Laag
    ```
    *Bijvoorbeeld: `2.1;2.4;2.6;2.5;2.7`*

---

## 📟 Configuratiemenu in Domoticz

Configureer de verbindingsgegevens en het Z-Wave/P1-gedrag van de plugin via het Domoticz-menu.



---

## 📲 Geïnstalleerde Domoticz Apparaten

Een overzicht van de apparaten die door de plugin in Domoticz worden aangemaakt.
