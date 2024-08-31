#!/usr/bin/env python3

import argparse
import cantools
import csv as csv_lib
import sys

from pprint import pprint
from pathlib import Path

def convert_candump_to_csv(dbc, candump, csv):
    try:
        print(f"Loading DBC file: {dbc}")
        db = cantools.database.load_file(dbc)
        pprint(vars(db))
        print(f"Successfully loaded DBC file.")
    except Exception as e:
        print(f"Error loading DBC file: {e}")
        return False

    try:
        print(f"Opening CAN dump log file: {candump}")
        with open(candump, 'r') as can_file:
            can_lines = can_file.readlines()
        print(f"Successfully read CAN dump file.")
    except Exception as e:
        print(f"Error opening CAN dump file: {e}")
        return False

    # Dictionary to keep track of column headers and data
    headers = set()
    data_rows = []

    for line in can_lines:
        line = line.strip()
        if not line:
            continue

        try:
            parts = line.split()
            if len(parts) < 1:
                print(f"Line format is incorrect: {line}")
                continue

            timestamp = parts[0].strip('()')
            interface = parts[1]
            message_part = parts[2]

            # Separate data between '#'
            if '#' not in message_part:
                print(f"Message part does not contain '#': {message_part}")
                continue

            can_id_str, can_payload_str = message_part.split('#', 1)
            can_id = int(can_id_str, 16)
            can_payload_bytes = bytes.fromhex(can_payload_str)

            try:
                message = db.get_message_by_frame_id(can_id)
                if not message:
                    print(f"Message with ID {can_id} not found in DBC file.")
                    continue
            except Exception as e:
                print(f"Error getting message by frame ID {can_id}: {e}. It doesn't exist.")
                continue

            try:
                decoded_signals = message.decode(can_payload_bytes)
            except Exception as e:
                print(f"Error decoding message with ID {can_id}: {e}")
                continue

            headers.update(decoded_signals.keys())

            # Signal dictionary
            signal_data = {signal_name: '' for signal_name in headers}
            # Create a row of data with placeholders for signals
            row_data = {
                'Timestamp': timestamp,
                'Interface': interface,
                'Message Name': message.name,
                **signal_data
            }

            # Update row data with actual signal values
            row_data.update(decoded_signals)

            data_rows.append(row_data)

        except Exception as e:
            print(f"Error processing line '{line}': {e}")

    # Convert headers to a sorted list and add 'Value'
    headers = sorted(headers)
    headers = ['Timestamp', 'Interface', 'Message Name'] + headers

    # Write data to the CSV file
    try:
        print(f"Opening CSV file: {csv}")
        with open(csv, 'w', newline='') as csv_file:
            csv_writer = csv_lib.writer(csv_file)

            # Write header
            csv_writer.writerow(headers)

            # Write data rows
            for row_data in data_rows:
                row = [row_data.get(header, '') for header in headers]
                csv_writer.writerow(row)

        return True

    except Exception as e:
        print(f"Error opening CSV file for writing: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert CAN log to human-readable CSV.")
    parser.add_argument("-c", "--candump", type=Path, required=True, help="Path to the CAN dump file.")
    parser.add_argument("-d", "--dbc", type=Path, required=True, help="Path to the DBC file.")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Path of the output file.")
    args = parser.parse_args()

    if not args.candump.is_file():
        print(f"The CAN dump file '{args.candump}' is missing.", file=sys.stderr)
        sys.exit(1)

    if not args.dbc.is_file():
        print(f"The DBC file '{args.dbc}' is missing.", file=sys.stderr)
        sys.exit(1)

    if args.output.is_file():
        print(f"The output file '{args.output}' already exists. Please specify a unique name.", file=sys.stderr)
        sys.exit(1)


    if convert_candump_to_csv(args.dbc, args.candump, args.output):
        print(f"Conversion completed successfully! Data has been saved to '{args.output}'.")
    else:
        print(f"Conversion failed. Please check the provided files and try again.")
