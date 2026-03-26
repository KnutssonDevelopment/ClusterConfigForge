from flask import Flask, render_template, request, send_file, session
import json
import io
import copy

app = Flask(__name__)
app.secret_key = 'vmware_secret_key'


def extract_host_data(data):
    hosts_dict = {}
    vmknic_set = set()
    # Check both sections to find hosts for the UI
    for section in ['host-override', 'host-specific']:
        section_data = data.get(section, {})
        for uuid, content in section_data.items():
            esx_net = content.get('esx', {}).get('network', {})
            net_stacks = esx_net.get('net_stacks', [])

            hostname = uuid
            if isinstance(net_stacks, list) and len(net_stacks) > 0:
                hostname = net_stacks[0].get('host_name', uuid)

            vmknics = esx_net.get('vmknics', [])
            host_vmks = {}
            for vmk in vmknics:
                name = vmk['device']
                vmknic_set.add(name)
                host_vmks[name] = {
                    "ipv4_address": vmk.get('ip', {}).get('ipv4_address', ""),
                    "ipv4_subnet_mask": vmk.get('ip', {}).get('ipv4_subnet_mask', "")
                }

            hosts_dict[uuid] = {"uuid": uuid, "hostname": hostname, "vmknics": host_vmks}

    # Ensure we show at least vmk0 to vmk4
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
    if not file: return "No file", 400
    raw_data = json.load(file)
    session['original_json'] = raw_data
    hosts, vmk_columns = extract_host_data(raw_data)
    return render_template('index.html', hosts=hosts, vmk_columns=vmk_columns)


@app.route('/generate-json', methods=['POST'])
def generate_json():
    if 'original_json' not in session:
        return "No session data found", 400

    original = session['original_json']
    form = request.form

    # 1. FIND MASTER TEMPLATE
    # We find the first host-specific entry to use as a base for all others
    master_template = {}
    for section in ['host-specific', 'host-override']:
        if section in original and original[section]:
            first_uuid = next(iter(original[section]))
            master_template = copy.deepcopy(original[section][first_uuid])
            break

    if not master_template:
        return "Could not find a base host profile to use as template.", 400

    # 2. PREPARE OUTPUT STRUCTURE
    # Remove host-override and prepare a fresh host-specific section
    new_json = {k: v for k, v in original.items() if k != 'host-override'}
    new_json['host-specific'] = {}

    # 3. IDENTIFY ALL HOSTS FROM FORM
    uuids = set()
    for key in form.keys():
        if key.startswith('host['):
            uuids.add(key.split('[')[1].split(']')[0])

    # 4. BUILD NEW ENTRIES BASED ON MASTER
    for uuid in uuids:
        # Start with a 100% identical copy of the master profile (DNS, NTP, etc. preserved)
        new_host_entry = copy.deepcopy(master_template)

        # Access the network part safely
        net = new_host_entry.get('esx', {}).get('network', {})

        # Update Hostname
        new_hostname = form.get(f'host[{uuid}][hostname]')
        if 'net_stacks' in net and len(net['net_stacks']) > 0:
            net['net_stacks'][0]['host_name'] = new_hostname

        # Update existing VMKNICs or add new ones if they don't exist in template
        existing_vmks = net.get('vmknics', [])

        for i in range(10):  # Check vmk0-vmk9
            dev = f"vmk{i}"
            ip = form.get(f'host[{uuid}][{dev}][ip]')
            mask = form.get(f'host[{uuid}][{dev}][mask]')

            if ip or mask:
                # Look for this device in the template's vmknics
                target_vmk = next((v for v in existing_vmks if v['device'] == dev), None)

                if target_vmk:
                    # Update existing vmk from template
                    target_vmk['ip']['ipv4_address'] = ip or ""
                    target_vmk['ip']['ipv4_subnet_mask'] = mask or ""
                else:
                    # Add new vmk if it wasn't in the template
                    existing_vmks.append({
                        "device": dev,
                        "ip": {"ipv4_address": ip or "", "ipv4_subnet_mask": mask or ""},
                        # Default keys for new interfaces
                        "enabled_services": {"management": False},
                        "key": f"key-vim.host.VirtualNic-{dev}"
                    })

        new_json['host-specific'][uuid] = new_host_entry

    output = io.BytesIO()
    output.write(json.dumps(new_json, indent=2).encode('utf-8'))
    output.seek(0)
    return send_file(output, mimetype='application/json', as_attachment=True, download_name='final_host_profile.json')


if __name__ == '__main__':
    app.run(debug=True)