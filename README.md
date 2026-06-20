# Home Assistant MyLight150 Integration

[![GitHub Release][releases-shield]][releases] 
[![hacs][hacsbadge]][hacs] 
[![License][license-shield]](LICENSE)

[![GitHub Activity][commits-shield]][commits] 
![Project Maintenance][maintenance-shield]


## Description

The `MyLight150` component provides an integration with the MyLight150 cloud service. It adds sensors such as power, battery status, ... that you can find on the mobile applications.

**Note:** This integration will not manage actions on the system, but retrieve data to integrate them into your domotic environment.

## Installation

There are two ways this integration can be installed into [Home Assistant](https://www.home-assistant.io).

The easiest and recommended way is to install the integration using [HACS](https://hacs.xyz), which makes future updates easy to track and install.

Alternatively, installation can be done manually by copying the files in this repository into the `custom_components` directory in the Home Assistant configuration directory:

1. Open the configuration directory of your Home Assistant installation.
2. If you do not have a `custom_components` directory, create it.
3. In the `custom_components` directory, create a new directory called `mylight150`.
4. Copy all files from the `custom_components/mylight150/` directory in this repository into the `mylight150` directory.
5. Restart Home Assistant.
6. Add the integration to Home Assistant (see **Configuration**).

## Configuration

Configuration is done through the Home Assistant UI.

To add the integration, go to **Settings ➤ Devices & Services ➤ Integrations**, click **➕ Add Integration**, and search for "MyLight150".

### Configuration Variables

| Name              | Type     | Default | Description                                                                                                                                       |
| ----------------- | -------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Username`        | `string` | –       | The username associated with your MyLight150 account.                                                                                             |
| `Password`        | `string` | –       | The password for your MyLight150 account.                                                                                                         |
| `Update Interval` | `int`    | `10`    | Frequency (in minutes) to fetch status data from MyLight.<br>Minimum allowed is 10 minutes.<br>\* _Can be updated later via the CONFIGURE menu._  |
| `Scan at startup` | `bool`   | `True`  | Aloow to do a full data update at every restart of Home Assistant._                                                                               |


## Options

Find configuration options under **Settings ➤ Devices & Services ➤ Integrations ➤ MyLight150 ➤ Configure**:


| Name              | Type     | Default | Description                                                                                                                                       |
| ----------------- | -------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Update Interval` | `int`    | `10`    | Frequency (in minutes) to fetch status data from MyLight.<br>Minimum allowed is 10 minutes.<br>\* _Can be updated later via the CONFIGURE menu._  |
| `Scan at startup` | `bool`   | `True`  | Allow to do a full data update at every restart of Home Assistant._                                                                               |



## Provided Entities

The device will take the name of 'MyLight150 <installation_code>' where the installation code is a unique ID that MyLight150 generate for your own installation.
This will be the base of all entity ID structure : mylight150_<installation_code>_entity_name

### Sensors

| Entity ID                                                       | Description                                                  | Unit | State Class        |
| --------------------------------------------------------------- | ------------------------------------------------------------ | ---- | ------------------ |
| `sensor.mylight150_<installation_code>_solar_production`        | Current solar production                                     | kW   | `measurement`      |
| `sensor.mylight150_<installation_code>_grid`                    | Current grid power                                           | kW   | `measurement`      |
| `sensor.mylight150_<installation_code>_injection`               | Current power injected on the grid                           | kW   | `measurement`      |
| `sensor.mylight150_<installation_code>_load`                    | Current power consumption                                    | kW   | `measurement`      |
| `sensor.mylight150_<installation_code>_msb_state`               | Virtual battery status                                       |  -   | `text`             |
| `sensor.mylight150_<installation_code>_msb_power`               | Virtual battery power                                        | kW   | `measurement`      |
| `sensor.mylight150_<installation_code>_msb_autonomy`            | Virtual battery autonomy                                     | kWh  | `measurement`      |
| `sensor.mylight150_<installation_code>_msb_capacity`            | Virtual battery capacity                                     | kWh  | `measurement`      |
| `sensor.mylight150_<installation_code>_savings`                 | Monthly money saved                                          | EUR  | `total_increasing` |
| | | | |
| `sensor.mylight150_<installation_code>_heatPump_mode`           | Current heat pump mode                                       |  -   | `text`             |
| `sensor.mylight150_<installation_code>_waterHeater_mode`        | Current water heater mode                                    |  -   | `text`             |
| | | | |
| `sensor.mylight150_<installation_code>_energy_prod_from_solar ` | Solar energy production since integration installation       | kWh  | `total_increasing` |
| `sensor.mylight150_<installation_code>_energy_prod_to_msb`      | MSB energy in since integration installation                 | kWh  | `total_increasing` |
| `sensor.mylight150_<installation_code>_energy_prod_to_grid`     | Grid energy injection since integration installation         | kWh  | `total_increasing` |
| `sensor.mylight150_<installation_code>_energy_consumption`      | Total energy consumption since integration installation      | kWh  | `total_increasing` |
| `sensor.mylight150_<installation_code>_energy_conso_from_solar` | Solar energy self-consumption since integration installation | kWh  | `total_increasing` |
| `sensor.mylight150_<installation_code>_energy_conso_from_msb`   | MSB energy out since integration installation                | kWh  | `total_increasing` |
| `sensor.mylight150_<installation_code>_energy_conso_from_grid`  | Grid energy consumption since integration installation       | kWh  | `total_increasing` |


## Features roadmap
* **0.3.x : Energy sensors** (production, consumptions) with total sensors to get the cumulative value for each sensors in the long term.
* 0.4.x : Pricing timeline and pricing value for each mode (HP/HC)
* 0.5.x : MyBattery (support and logs needed from owners)
* 0.6.x : evCharger (support and logs needed from owners)


## Credits
* [Home Assistant](https://github.com/home-assistant) : Home Assistant open-source powerful domotic plateform.
* [HACS](https://hacs.xyz/) : Home Assistant Community Store gives you a powerful UI to handle downloads of all your custom needs.
* [MyLight150] : Electricity provider with virtual battery support.
* [hassio MyLight integration](https://github.com/acesyde/hassio_mylight_integration) : MyLight system integration for previous API from MtLight System

---

[MyLight150]: https://www.mylight-systems.com/
[commits-shield]: https://img.shields.io/github/commit-activity/y/Racailloux/mylight150_ha.svg?style=for-the-badge
[commits]: https://github.com/Racailloux/mylight150_ha/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/Racailloux/mylight150_ha.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Racailloux-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/Racailloux/mylight150_ha.svg?style=for-the-badge
[releases]: https://github.com/Racailloux/mylight150_ha/releases
