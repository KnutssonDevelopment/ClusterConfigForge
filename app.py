from flask import Flask, render_template, request, redirect, url_for
import json

app = Flask(__name__)


def extract_host_data(data):
    """
    Parses VMware Host Profile JSON structure to extract host details.
    Maps vmk devices dynamically to each host.
    """
    hosts = dict()
    vmknic_set = set()  # Track all unique vmk devices found across all hosts

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

            vmknics = esx_net.get('vmknics', [])

            # Initialize host entry
            hosts[uuid] = {
                "hostname": extracted_hostname,
                "vmknics": {}
            }

            for vmk in vmknics:
                name = vmk['device']
                vmknic_set.add(name)  # Add to global list for table columns

                hosts[uuid]['vmknics'][name] = {
                    "ipv4_address": vmk.get('ip', {}).get('ipv4_address', ""),
                    "ipv4_subnet_mask": vmk.get('ip', {}).get('ipv4_subnet_mask', "")
                }

    # Sort vmk list alphabetically (vmk0, vmk1...)
    sorted_vmknics = sorted(list(vmknic_set))

    return hosts, sorted_vmknics


@app.route('/')
def index():
    return render_template('index.html', hosts={}, vmk_columns=[])


@app.route('/load-json', methods=['POST'])
def load_json():
    if 'file' not in request.files:
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('index'))

    try:
        raw_data = json.load(file)
        hosts, vmk_columns = extract_host_data(raw_data)

        return render_template('index.html',
                               hosts=hosts,
                               vmk_columns=vmk_columns)
    except Exception as e:
        print(f"Error: {e}")
        return f"Error parsing JSON: {str(e)}", 500


if __name__ == '__main__':
    app.run(debug=True)