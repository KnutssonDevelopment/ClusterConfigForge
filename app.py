import json
from flask import Flask, render_template, request, jsonify, send_file
import io

app = Flask(__name__)

# Global storage for the loaded config (in-memory for local use)
current_config = {}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    global current_config
    file = request.files.get('file')
    if not file:
        return "No file uploaded", 400

    current_config = json.load(file)

    # Extract existing data for the UI
    hosts_data = []

    # Check host-override for IP data
    overrides = current_config.get('host-override', {})
    for host_uuid, data in overrides.items():
        host_info = {
            "uuid": host_uuid,
            "hostname": "",
            "vnics": []
        }

        # Try to find a hostname in net_stacks
        net_stacks = data.get('esx', {}).get('network', {}).get('net_stacks', [])
        if isinstance(net_stacks, list) and len(net_stacks) > 0:
            host_info['hostname'] = net_stacks[0].get('host_name', 'Unknown')

        # Get VMKNICs
        vmknics = data.get('esx', {}).get('network', {}).get('vmknics', [])
        for vmk in vmknics:
            ip_data = vmk.get('ip', {})
            host_info['vnics'].append({
                "device": vmk.get('device', 'unknown'),
                "ipv4": ip_data.get('ipv4_address', ''),
                "mask": ip_data.get('ipv4_subnet_mask', '')
            })

        hosts_data.append(host_info)

    return jsonify(hosts_data)


@app.route('/process', methods=['POST'])
def process():
    global current_config
    form_data = request.json

    # Ensure host-specific section exists
    if 'host-specific' not in current_config:
        current_config['host-specific'] = {}

    for host_entry in form_data:
        uuid = host_entry['uuid']

        # Initialize the specific structure vCenter expects
        if uuid not in current_config['host-specific']:
            current_config['host-specific'][uuid] = {"esx": {"network": {"vmknics": []}}}

        new_vmknics = []
        for vnic in host_entry['vnics']:
            new_vmknics.append({
                "device": vnic['device'],
                "ip": {
                    "ipv4_address": vnic['ipv4'],
                    "ipv4_subnet_mask": vnic['mask']
                }
            })

        current_config['host-specific'][uuid]['esx']['network']['vmknics'] = new_vmknics

        # Optional: Clean the host-override section for these specific IP keys
        # to prevent conflicts, or leave it if you want to keep other overrides.
        if uuid in current_config.get('host-override', {}):
            # Logic here to strip out IP addresses from override if moved to specific
            pass

    # Create a file-like object for the download
    mem = io.BytesIO()
    mem.write(json.dumps(current_config, indent=4).encode('utf-8'))
    mem.seek(0)

    return send_file(
        mem,
        mimetype='application/json',
        as_attachment=True,
        download_name='converted_vcenter_config.json'
    )

