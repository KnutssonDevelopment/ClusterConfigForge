# Cluster Config Forge

A Flask-based web tool to batch-edit vSphere Cluster Configuration JSON files. 

## Features
- **Auto-Sequence IPs:** Increment IP addresses automatically.
- **Bulk Mask Copy:** Copy subnet masks across all hosts.
- **Hostname Increment:** Automatically name hosts (esx01, esx02, etc.).
- **Smart Merge:** Preserves all other profile settings (DNS, NTP, vSwitch) from the master profile.
- **Force Host-Specific:** Automatically cleans up `host-override` and moves data to `host-specific` for consistency.

## Installation
1. `pip install flask`
2. `python main.py`
3. Open `http://127.0.0.1:5000`

## 🐳 Run with Docker

If you don't want to install Python locally, you can run the Forge using Docker:

### 1. Run the container

1. Pull and run the latest image directly from Docker Hub:

```docker run -d --rm -p 5000:5000 --name ccf knutssondevelopment/cluster-config-forge:latest```

2. Open your browser at `http://127.0.0.1:5000`

## Workflow
1. Configure the first host with advanced settings, vmknic and ip configuration
2. Create a Cluster Configuration based on that host
3. Export the initial configuration
4. Import the configuration into Cluster Config Forge
5. Setup all ip adresses
6. Export the json file from Cluster Config Forge
7. Import the json file into the vSphere Cluster Configurator
8. Validate and apply the configuration

## Disclaimer
Use at your own risk. This tool is provided "as-is" without any warranty of any kind, either expressed or implied.

Not an official VMware product: This is a community-driven tool and is not affiliated with VMware by Broadcom.

Infrastructure Impact: Incorrect JSON configurations can lead to host disconnects or network outages. Always go through the the settings the configurator intents to implement on the hosts before applying the configuration- 

Backup: Always keep a backup of your original configuration JSON file before using this editor.

## Known Issues
There are no known issues. If you find any please create an issue report on github: https://github.com/KnutssonDevelopment/ClusterConfigForge/issues