from flask import Flask, render_template, request, send_file, session
import json
import io
import copy

app = Flask(__name__)
app.secret_key = 'vmware_secret_key'


def extract_host_data(data):
    hosts_dict = {}
    vmknic_set = set()
    # We look in both sections to find existing hosts to display
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

    # Ensure columns for vmk0-vmk4 are always present
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

    # 1. Find a template structure from existing data to preserve keys like 'defaultTcpipStack'
    template_structure = {}
    for section in ['host-specific', 'host-override']:
        if section in original and original[section]:
            first_uuid = next(iter(original[section]))
            template_structure = copy.deepcopy(original[section][first_uuid])
            break

    # 2. Prepare the new JSON structure
    # Remove host-override as requested
    new_json = {k: v for k, v in original.items() if k != 'host-override'}
    new_json['host-specific'] = {}

    # 3. Build host-specific entries from form data
    # We group form data by UUID first
    hosts_to_process = set()
    for key in form.keys():
        if key.startswith('host['):
            uuid = key.split('[')[1].split(']')[0]
            hosts_to_process.add(uuid)

    for uuid in hosts_to_process:
        # Create a new host entry based on the template
        host_entry = copy.deepcopy(template_structure)

        # Ensure path exists
        if 'esx' not in host_entry: host_entry['esx'] = {}
        if 'network' not in host_entry['esx']: host_entry['esx']['network'] = {}
        net = host_entry['esx']['network']

        # Update Hostname
        new_hostname = form.get(f'host[{uuid}][hostname]')
        if 'net_stacks' not in net: net['net_stacks'] = [{"key": "defaultTcpipStack"}]
        net['net_stacks'][0]['host_name'] = new_hostname

        # Update/Rebuild VMKNICs
        net['vmknics'] = []
        for i in range(10):  # Check vmk0-vmk9
            dev = f"vmk{i}"
            ip = form.get(f'host[{uuid}][{dev}][ip]')
            mask = form.get(f'host[{uuid}][{dev}][mask]')

            if ip or mask:
                net['vmknics'].append({
                    "device": dev,
                    "ip": {
                        "ipv4_address": ip or "",
                        "ipv4_subnet_mask": mask or ""
                    }
                })

        new_json['host-specific'][uuid] = host_entry

    # Generate file
    output = io.BytesIO()
    output.write(json.dumps(new_json, indent=2).encode('utf-8'))
    output.seek(0)
    return send_file(output, mimetype='application/json', as_attachment=True,
                     download_name='host_specific_profile.json')


if __name__ == '__main__':
    app.run(debug=True)