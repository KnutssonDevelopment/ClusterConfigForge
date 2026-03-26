from flask import Flask, render_template, request, send_file, session
import json
import io
import copy

app = Flask(__name__)
app.secret_key = 'vmware_secret_key'


def extract_host_data(data):
    hosts_dict = {}
    vmknic_set = set()
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

    master_template = {}
    for section in ['host-specific', 'host-override']:
        if section in original and original[section]:
            first_uuid = next(iter(original[section]))
            master_template = copy.deepcopy(original[section][first_uuid])
            break

    new_json = {k: v for k, v in original.items() if k != 'host-override'}
    new_json['host-specific'] = {}

    uuids = set()
    for key in form.keys():
        if key.startswith('host['):
            uuids.add(key.split('[')[1].split(']')[0])

    for uuid in uuids:
        new_host_entry = copy.deepcopy(master_template)
        net = new_host_entry.get('esx', {}).get('network', {})

        new_hostname = form.get(f'host[{uuid}][hostname]')
        if 'net_stacks' in net and len(net['net_stacks']) > 0:
            net['net_stacks'][0]['host_name'] = new_hostname

        existing_vmks = net.get('vmknics', [])
        for i in range(10):
            dev = f"vmk{i}"
            ip = form.get(f'host[{uuid}][{dev}][ip]')
            mask = form.get(f'host[{uuid}][{dev}][mask]')

            if ip is not None or mask is not None or i < 5:
                target_vmk = next((v for v in existing_vmks if v['device'] == dev), None)
                final_ip = ip if (ip and ip.strip()) else "0.0.0.0"
                final_mask = mask if (mask and mask.strip()) else "0.0.0.0"

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
        new_json['host-specific'][uuid] = new_host_entry

    output = io.BytesIO()
    output.write(json.dumps(new_json, indent=2).encode('utf-8'))
    output.seek(0)
    return send_file(output, mimetype='application/json', as_attachment=True, download_name='final_host_profile.json')


if __name__ == '__main__':
    app.run(debug=True)