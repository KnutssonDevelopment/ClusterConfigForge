# =================================================================
# Cluster Config Forge
# Author: Brian Knutsson - CRIT Solutions ApS
# License: Custom MIT (Non-Commercial, Attribution Required)
# This tool is provided AS-IS. Use at your own risk.
# =================================================================

import json
import io
import copy
from flask import Flask, render_template, request, send_file, session, flash
import helpers

app = Flask(__name__)
app.secret_key = 'vmware_secret_key_change_this_in_production'


def extract_host_data(data):
    """
    Parses VMware Host Profile JSON and extracts unique host data.
    Looks in both host-override and host-specific sections.
    """
    hosts_dict = {}
    vmknic_set = set()

    sections = ['host-override', 'host-specific']
    for section in sections:
        section_data = data.get(section, {})
        for uuid, content in section_data.items():
            # Safely navigate the JSON structure
            esx_net = content.get('esx', {}).get('network', {})
            net_stacks = esx_net.get('net_stacks', [])

            # Identify Hostname
            hostname = uuid
            if isinstance(net_stacks, list) and len(net_stacks) > 0:
                hostname = net_stacks[0].get('host_name', uuid)

            # Map VMKNICs
            vmknics = esx_net.get('vmknics', [])
            host_vmks = {}
            for vmk in vmknics:
                name = vmk.get('device', 'unknown')
                vmknic_set.add(name)
                host_vmks[name] = {
                    "ipv4_address": vmk.get('ip', {}).get('ipv4_address', ""),
                    "ipv4_subnet_mask": vmk.get('ip', {}).get('ipv4_subnet_mask', "")
                }

            hosts_dict[uuid] = {
                "uuid": uuid,
                "hostname": hostname,
                "vmknics": host_vmks
            }

    # Ensure standard management nics are always visible columns
    for i in range(5):
        vmknic_set.add(f"vmk{i}")

    sorted_hosts = sorted(hosts_dict.values(), key=lambda x: x['hostname'].lower())
    return sorted_hosts, sorted(list(vmknic_set))


@app.route('/')
def index():
    return render_template('index.html', hosts=[], vmk_columns=[])


@app.route('/load-json', methods=['POST'])
def load_json():
    file = request.files.get('file')
    if not file or file.filename == '':
        flash("No file selected.")
        return render_template('index.html', hosts=[], vmk_columns=[])

    try:
        raw_data = json.load(file)
        session['original_json'] = raw_data
        hosts, vmk_columns = extract_host_data(raw_data)
        return render_template('index.html', hosts=hosts, vmk_columns=vmk_columns)
    except Exception as e:
        flash(f"Error parsing JSON: {str(e)}")
        return render_template('index.html', hosts=[], vmk_columns=[])


@app.route('/generate-json', methods=['POST'])
def generate_json():
    if 'original_json' not in session:
        return "No session data found", 400

    original = session['original_json']

    # Create a new dictionary for later export
    new_json = copy.deepcopy(original)

    # Remove the host overrides
    try:
        del new_json['host-override']
    except KeyError:
        pass

    form = request.form

    # Identify Master Template from most descriptive host-specific
    uuids = original.get('host-specific')
    sections = [original.get('host-specific')[u] for u in uuids]
    master_template = copy.deepcopy(helpers.get_biggest_dict(sections))

    # TODO: We might have to generate a master template
    if not master_template:
        return "No valid host template found in JSON", 400

    # Process hosts from form
    uuids = set(key.split('[')[1].split(']')[0] for key in form.keys() if key.startswith('host['))

    for uuid in uuids:
        host_entry = copy.deepcopy(master_template)
        net = host_entry.setdefault('esx', {}).setdefault('network', {})

        # Update Hostname
        new_hostname = form.get(f'host[{uuid}][hostname]')
        if 'net_stacks' in net and len(net['net_stacks']) > 0:
            net['net_stacks'][0]['host_name'] = new_hostname

        # Update/Inject VMKNICs
        existing_vmks = host_entry.get('esx', {}).get('network', {}).get('vmknics', [])
        #existing_vmks = net.setdefault('vmknics', [])

        # Go trough all vmkernel adaptors
        for vmk in existing_vmks:
            dev = vmk.get('device')
            ip = form.get(f'host[{uuid}][{dev}][ip]')
            mask = form.get(f'host[{uuid}][{dev}][mask]')

            # If user touched these fields or it's a core vmk
            if ip is not None or mask is not None or i < 2:
                target_vmk = next((v for v in existing_vmks if v['device'] == dev), None)

                # Default to 0.0.0.0 as requested
                final_ip = ip.strip() if (ip and ip.strip()) else "0.0.0.0"
                final_mask = mask.strip() if (mask and mask.strip()) else "0.0.0.0"

                if target_vmk:
                    target_vmk['ip']['ipv4_address'] = final_ip
                    target_vmk['ip']['ipv4_subnet_mask'] = final_mask
                else:
                    existing_vmks.append({
                        "device": dev,
                        "ip": {"ipv4_address": final_ip, "ipv4_subnet_mask": final_mask},
                        "enabled_services": {"management": (dev == "vmk0")},
                        "key": f"key-vim.host.VirtualNic-{dev}"
                    })

        new_json['host-specific'][uuid] = host_entry

    output = io.BytesIO()
    output.write(json.dumps(new_json, indent=4).encode('utf-8'))
    output.seek(0)
    return send_file(output, mimetype='application/json', as_attachment=True, download_name='updated_host_profile.json')


if __name__ == '__main__':
    app.run(debug=True)