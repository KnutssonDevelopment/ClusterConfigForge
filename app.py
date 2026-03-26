from flask import Flask, render_template, request, redirect, url_for
import json

app = Flask(__name__)


def extract_host_data(data):
    """
    Parses VMware Host Profile JSON structure to extract host details.
    Ensures that even missing fields are initialized for the UI.
    """
    hosts = dict()
    vmknic_list = set()

    target_sections = ['host-override', 'host-specific']

    for section in target_sections:
        section_data = data.get(section, {})
        for uuid, content in section_data.items():
            esx_net = content.get('esx', {}).get('network', {})
            net_stacks = esx_net.get('net_stacks', [])

            # Extract Hostname
            extracted_hostname = uuid
            if isinstance(net_stacks, list) and len(net_stacks) > 0:
                extracted_hostname = net_stacks[0].get('host_name', uuid)

            # Extract Management IP (vmk0 logic)
            vmknics = esx_net.get('vmknics', [])
            for vmk in vmknics:
                vmknic_list.add(vmk['device'])

            # Append as an object for easier iteration in Jinja2
            hosts[uuid] = {
                "hostname": extracted_hostname,
                "vmknics": dict()
            }

            device = dict()
            for vmk in vmknics:
                name = vmk['device']
                hosts[uuid]['vmknics'][name] = {
                    "ipv4_address": vmk['ip']['ipv4_address'],
                    "ipv4_subnet_mask": vmk['ip']['ipv4_subnet_mask']
                }

    return hosts


@app.route('/')
def index():
    return render_template('index.html', hosts=[])


@app.route('/load-json', methods=['POST'])
def load_json():
    if 'file' not in request.files:
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('index'))

    try:
        raw_data = json.load(file)
        with open ("Test-Files/input.json", 'r') as file:
            raw_data = json.load(file)
        extracted_hosts = extract_host_data(raw_data)
        return render_template('index.html', hosts=extracted_hosts)
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return "Internal Server Error", 500


if __name__ == '__main__':
    app.run(debug=True)