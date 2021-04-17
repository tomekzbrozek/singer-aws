import json
import argparse
import logging

def main():

    logging.basicConfig(level = logging.INFO)

    parser = argparse.ArgumentParser(description='Arguments for Singer Tap execution.')
    parser.add_argument('--tap', help='Name of Singer Tap to inspect,', required=True)
    args = parser.parse_args()
    tap = args.tap
    tap_config_path = f"taps/tap-{tap}/catalog.json"

    try:
        with open(tap_config_path) as tap_catalog:
            tap_catalog_json = json.load(tap_catalog)
    except:
        logging.error(f"ERROR: {tap_config_path} catalog path does not exist.")

    tap_catalog_json['streams']
    streams = tap_catalog_json['streams']

    for stream in streams:

        stream_id = stream['tap_stream_id']
        print(f"inspecting stream: {stream_id}...")

        for meta_item in stream['metadata']:
            if len(meta_item['breadcrumb']) == 0 and meta_item['metadata']['selected']:
                print(f"    \u2705 stream is SELECTED")
                continue
            elif len(meta_item['breadcrumb']) == 0 and not meta_item['metadata']['selected']:
                print(f"    \u274C stream is NOT SELECTED")
                continue
            else:
                continue

        count_properties = len(stream['schema']['properties'].keys())
        print(f"    \u2022 found {count_properties} available properties")

        selected_properties_list = []
        count_selected_properties = 0

        for meta_item in stream['metadata']:
            if len(meta_item['breadcrumb']) > 0:
                if meta_item['metadata'].get('selected'):
                    count_selected_properties += 1
                    selected_properties_list.append(meta_item['breadcrumb'][1])
            else:
                continue

        print(f"    \u2022 found {count_selected_properties} selected properties")
        print(f"    \u2022 selected properties: {selected_properties_list}")

if __name__ == '__main__':
    main()
