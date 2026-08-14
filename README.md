# Home Assistant MyLight150 Integration

[![GitHub Release][releases-shield]][releases] 
[![hacs][hacsbadge]][hacs] 
[![License][license-shield]](LICENSE)

[![GitHub Activity][commits-shield]][commits] 
![Project Maintenance][maintenance-shield]

🌐 [English](README_EN.md) | **Français**


## Description

Le composant `MyLight150` permet une intégration avec le service cloud MyLight150. Il ajoute des capteurs tels que la puissance, l'état de la batterie, etc., que vous pouvez retrouver dans les applications mobiles.

**Remarque :** Cette intégration ne permet pas de gérer des actions sur votre système, mais uniquement de récupérer des données pour les intégrer dans votre environnement **Home Assistant**.
Le tableau de bord énergie peut être alimenté par les capteurs fournis par l'intégration.


## Installation

Il existe deux méthodes pour installer cette intégration dans [Home Assistant](https://www.home-assistant.io) :

### Méthode recommandée : Via HACS
La méthode la plus simple et recommandée est d'utiliser [HACS](https://hacs.xyz), qui facilite le suivi et l'installation des mises à jour futures.

### Méthode manuelle
Sinon, vous pouvez installer manuellement l'intégration en copiant les fichiers de ce dépôt dans le répertoire `custom_components` de votre installation Home Assistant :

1. Ouvrez le répertoire de configuration de votre installation **Home Assistant**.
2. Si vous n'avez pas de répertoire `custom_components`, créez-le.
3. Dans le répertoire `custom_components`, créez un nouveau répertoire nommé `mylight150`.
4. Copiez tous les fichiers du répertoire `custom_components/mylight150_ha/` de ce dépôt dans le répertoire `mylight150`.
5. Redémarrez Home Assistant.
6. Ajoutez l'intégration à Home Assistant (voir **Configuration**).


## Configuration

La configuration se fait via l'interface utilisateur de **Home Assistant**.
Pour ajouter l'intégration, allez dans **Paramètres ➤ Appareils et services ➤ Intégrations**, cliquez sur **➕ Ajouter une intégration**, puis recherchez **"MyLight150"**.

| Nom                     | Type     | Défaut  | Description                                                                                                                                               |
| ----------------------- | -------- | ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------  |
| `Username`              | `string` | –       | Nom d'utilisateur associé à votre compte MyLight150.                                                                                                      |
| `Password`              | `string` | –       | Mot de passe de votre compte MyLight150.                                                                                                                  |
| `Update Interval`       | `int`    | `10`    | Fréquence (min) de récupération des données depuis MyLight.<br>Min. autorisé : 10 mins.<br>\* _Peut être modifié ultérieurement via le menu CONFIGURER._  |
| `Scan at startup`       | `bool`   | `True`  | Permet d'effectuer une mise à jour complète des données à chaque redémarrage de Home Assistant.                                                           |
| `Peak hours pricing`    | `float`   | `0.23` | Tarif de base ou tarif des heures pleines, si un tarif heures pleines/heures creuses est détecté.                                                         |
| `Offpeak hours pricing` | `float`   | `0.14` | Tarif des heures creuses, si un tarif heures pleines/heures creuses est détecté.                                                                          |


## Options

Vous trouverez les options de configuration sous **Paramètres ➤ Appareils et services ➤ Intégrations ➤ MyLight150 ➤ Configurer** :

| Nom                     | Type      | Défaut  | Description                                                                                                                                                 |
| ----------------------- | --------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Update Interval`       | `int`     | `10`    | Fréquence (min) pour récupérer les données depuis MyLight.<br>Le minimum autorisé est 10 minutes.<br>* _Modifiable ultérieurement via le menu CONFIGURER._  |
| `Scan at startup`       | `bool`    | `True`  | Permet d'effectuer une mise à jour complète des données à chaque redémarrage de Home Assistant.                                                             |
| `Peak hours pricing`    | `float`   | `0.23`  | Tarif de base ou tarif des heures pleines, si un tarif heures pleines/heures creuses est détecté.                                                           |
| `Offpeak hours pricing` | `float`   | `0.14`  | Tarif des heures creuses, si un tarif heures pleines/heures creuses est détecté.                                                                            |


## Entités fournies

L'appareil portera le nom "MyLight150 <installation_code>", où installation_code est un identifiant unique généré par MyLight150 pour votre installation.
Cela servira de base pour la structure des identifiants des entités : mylight150_<installation_code>_entity_name.


### Capteurs

| ID de l'entité                                                  | Description                                                                        | Unité | State Class        |
| --------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ----- | ------------------ |
| `sensor.mylight150_<installation_code>_solar_production`        | Production solaire actuelle                                                        | kW    | `measurement`      |
| `sensor.mylight150_<installation_code>_grid`                    | Puissance actuelle du réseau                                                       | kW    | `measurement`      |
| `sensor.mylight150_<installation_code>_injection`               | Puissance actuelle injectée sur le réseau                                          | kW    | `measurement`      |
| `sensor.mylight150_<installation_code>_load`                    | Consommation électrique actuelle                                                   | kW    | `measurement`      |
| `sensor.mylight150_<installation_code>_msb_state`               | État de la batterie virtuelle                                                      |   -   | `text`             |
| `sensor.mylight150_<installation_code>_msb_power`               | Puissance de la batterie virtuelle                                                 | kW    | `measurement`      |
| `sensor.mylight150_<installation_code>_msb_autonomy`            | Autonomie de la batterie virtuelle                                                 | kWh   | `measurement`      |
| `sensor.mylight150_<installation_code>_msb_capacity`            | Capacité de la batterie virtuelle                                                  | kWh   | `measurement`      |
| `sensor.mylight150_<installation_code>_money_pot`               | Valeur actuelle de votre cagnotte                                                  | EUR   | `measurement`      |
| | | | |
| `sensor.mylight150_<installation_code>_heatPump_mode`           | Mode actuel de la pompe à chaleur                                                  |   -   | `text`             |
| `sensor.mylight150_<installation_code>_waterHeater_mode`        | Mode actuel du chauffe-eau                                                         |   -   | `text`             |
| | | | |
| `sensor.mylight150_<installation_code>_energy_prod_from_solar ` | Production d'énergie solaire depuis l'installation de l'intégration                | kWh   | `total_increasing` |
| `sensor.mylight150_<installation_code>_energy_prod_to_msb`      | Énergie stockée dans la batterie virtuelle depuis l'installation de l'intégration  | kWh   | `total_increasing` |
| `sensor.mylight150_<installation_code>_energy_prod_to_grid`     | Injection d'énergie dans le réseau depuis l'installation de l'intégration          | kWh   | `total_increasing` |
| `sensor.mylight150_<installation_code>_energy_consumption`      | Consommation totale d'énergie depuis l'installation de l'intégration               | kWh   | `total_increasing` |
| `sensor.mylight150_<installation_code>_energy_conso_from_solar` | Autoconsommation d'énergie solaire depuis l'installation de l'intégration          | kWh   | `total_increasing` |
| `sensor.mylight150_<installation_code>_energy_conso_from_msb`   | Énergie restituée par la batterie virtuelle depuis l'installation de l'intégration | kWh   | `total_increasing` |
| `sensor.mylight150_<installation_code>_energy_conso_from_grid`  | Consommation d'énergie du réseau depuis l'installation de l'intégration            | kWh   | `total_increasing` |
| | | | |
| `sensor.mylight150_<installation_code>_pricing_mode`            | Mode tarifaire actuel, selon le contrat.                                           |  -    | `text`             |
| `sensor.mylight150_<installation_code>_current_pricing`         | Valeur tarifaire actuelle. Les tarifs doivent être configurés.                     | €/kWh | `measurement`      |


## Informations recherchées
⚠️ **Certaines fonctionnalités nécessitent des données utilisateurs pour être implémentées.**
Les développeurs n'ont pas accès à toutes les options de MyLight150. Si vous possédez des fonctionnalités non implémentées, n'hésitez pas à nous contacter. Des données de diagnostic seront nécessaires.
* MyBattery :<br> Intégration de l'option MyBattery.
* evCharger :br Intégration de l'équipement de charge pour voiture électrique.


## Remerciements
* [Home Assistant](https://github.com/home-assistant) : Plateforme domotique open-source puissante.
* [HACS](https://hacs.xyz/) : Home Assistant Community Store offre une interface puissante pour gérer les téléchargements de tous vos besoins personnalisés.
* [MyLight150] : Fournisseur d'électricité avec support de batterie virtuelle.
* [hassio MyLight integration](https://github.com/acesyde/hassio_mylight_integration) : Intégration de MyLight System pour l'ancienne API de MyLight System (MyHome).


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
