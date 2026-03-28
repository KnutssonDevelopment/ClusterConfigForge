# =================================================================
# Cluster Config Forge - Core Backend
# Author: Brian Knutsson - CRIT Solutions ApS
# License: Custom MIT (Non-Commercial, Attribution Required)
# Description: Flask backend for parsing and generating VMware
# Host Profile desired-state configurations.
# This tool is provided AS-IS. Use at your own risk.
# =================================================================

import json
import io
import copy
from datetime import datetime
from flask import Flask, render_template, request, send_file, session, flash
import helpers

app = Flask(__name__)
# In production, this should be an environment variable
app.secret_key = 'vmware_config_forge_secure_key'


def extract_host_data(data):
    """
    Parses VMware Host Profile JSON and extracts unique host data.
    Looks in both host-override and host-specific sections to identify all hosts.
    Returns sorted hosts and a list of all unique VMkernel devices found.
    """
    hosts_dict = {}
    all_vmks = set()

    sections = ['host-override', 'host-specific']
    for section in sections:
        section_data = data.get(section, {})
        for uuid, content in section_data.items():
            # Safely navigate the JSON structure
            esx_net = content.get('esx', {}).get('network', {})
            net_stacks = esx_net.get('net_stacks', [])

            # Identify Hostname (fallback to UUID if not found)
            hostname = uuid
            if isinstance(net_stacks, list) and len(net_stacks) > 0:
                hostname = net_stacks[0].get('host_name', uuid)

            # Map VMKNICs into a dictionary for easy lookup in the template
            vmknics = esx_net.get('vmknics', [])
            host_vmks = {}
            for vmk in vmknics:
                name = vmk.get('device', 'unknown')
                all_vmks.add(name)
                ip_data = vmk.get('ip', {})
                host_vmks[name] = {
                    "ipv4": ip_data.get('ipv4_address', ""),
                    "netmask": ip_data.get('ipv4_subnet_mask', "")
                }

            hosts_dict[uuid] = {
                "uuid": uuid,
                "hostname": hostname,
                "vmknics": host_vmks
            }

    # Ensure standard management nics are always visible as context
    for i in range(2):
        all_vmks.add(f"vmk{i}")

    sorted_hosts = sorted(hosts_dict.values(), key=lambda x: x['hostname'].lower())
    return sorted_hosts, sorted(list(all_vmks))


@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Combined route for the Main UI and JSON Upload.
    Handles the initial landing page and the processing of uploaded reference files.
    """
    hosts = None
    vmk_columns = []

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part in the request')
            return render_template('index.html', hosts=None, vmk_columns=[], now=datetime.now())

        file = request.files['file']
        if file.filename == '':
            flash('No file selected')
            return render_template('index.html', hosts=None, vmk_columns=[], now=datetime.now())

        if file and file.filename.endswith('.json'):
            try:
                # Read and parse the JSON file
                content = file.read()
                data = json.loads(content)

                # Store the original structure in session for later generation
                session['original_json'] = data

                # Extract host list and the global list of VMkernel columns
                hosts, vmk_columns = extract_host_data(data)

                if not hosts:
                    flash('No host configurations found in the uploaded file.')

            except Exception as e:
                flash(f'Error processing JSON: {str(e)}')
        else:
            flash('Invalid file format. Please upload a .json file.')

    return render_template('index.html', hosts=hosts, vmk_columns=vmk_columns, now=datetime.now())


@app.route('/generate-json', methods=['POST'])
def generate_json():
    """
    Processes the Configuration Matrix form and generates a new JSON.
    Uses helpers.get_biggest_dict to find the best master template from existing hosts.
    """
    if 'original_json' not in session:
        flash('Session expired or no reference data found.')
        return render_template('index.html', hosts=None, vmk_columns=[], now=datetime.now())

    original = session['original_json']
    new_json = copy.deepcopy(original)

    # Clean up host-override as we are generating a clean host-specific set
    if 'host-override' in new_json:
        del new_json['host-override']

    # Reset host-specific to populate it with new entries
    new_json['host-specific'] = {}

    # Identify Master Template from the most descriptive host-specific entry
    host_spec_data = original.get('host-specific', {})
    if not host_spec_data:
        flash('No host-specific templates found in reference.')
        return render_template('index.html', hosts=None, vmk_columns=[], now=datetime.now())

    sections_to_compare = list(host_spec_data.values())
    master_template = copy.deepcopy(helpers.get_biggest_dict(sections_to_compare))

    if not master_template:
        flash('Could not determine a valid master template.')
        return render_template('index.html', hosts=None, vmk_columns=[], now=datetime.now())

    form_data = request.form
    # Identify unique host UUIDs from the form keys
    uuids = set(key.split('[')[1].split(']')[0] for key in form_data.keys() if key.startswith('host['))

    for uuid in uuids:
        host_entry = copy.deepcopy(master_template)
        net = host_entry.get('esx', {}).get('network', {})

        # Update Hostname
        new_hostname = form_data.get(f'host[{uuid}][hostname]')
        net_stacks = net.get('net_stacks', [])
        if net_stacks:
            net_stacks[0]['host_name'] = new_hostname

        # Update VMkernel Interfaces
        vmknics = net.get('vmknics', [])
        for vmk in vmknics:
            dev = vmk.get('device')
            ip = form_data.get(f'host[{uuid}][{dev}][ip]')
            mask = form_data.get(f'host[{uuid}][{dev}][mask]')

            # Ensure IP structure exists before assignment
            if 'ip' not in vmk:
                vmk['ip'] = {}

            # Apply updates if data exists in form, defaulting to 0.0.0.0
            if ip is not None:
                vmk['ip']['ipv4_address'] = ip.strip() if ip.strip() else "0.0.0.0"
            if mask is not None:
                vmk['ip']['ipv4_subnet_mask'] = mask.strip() if mask.strip() else "0.0.0.0"

        # Inject the modified entry into host-specific
        new_json['host-specific'][uuid] = host_entry

    # Prepare file for download
    try:
        json_output = json.dumps(new_json, indent=4)
        mem_file = io.BytesIO()
        mem_file.write(json_output.encode('utf-8'))
        mem_file.seek(0)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        return send_file(
            mem_file,
            mimetype='application/json',
            as_attachment=True,
            download_name=f'cluster_config_{timestamp}.json'
        )
    except Exception as e:
        flash(f'Generation failed: {str(e)}')
        return render_template('index.html', hosts=None, vmk_columns=[], now=datetime.now())


if __name__ == '__main__':
    app.run(debug=True)