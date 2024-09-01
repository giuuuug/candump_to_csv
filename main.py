#!/usr/bin/env python3

import can
import argparse
import cantools
import csv as csv_lib
import sys

from pathlib import Path

def convert_candump_to_csv(dbc, candump, csv):
    print(f"Opening CAN dump log file: {candump}")
    try:
        can_reader = can.LogReader(candump)
    except ValueError as e:
        print(f"Failed to read log file '{candump}'. Error: {e}", file=sys.stderr)
        return False

    try:
        print(f"Loading DBC file: {dbc}")
        db = cantools.database.load_file(dbc)
        print(f"Successfully loaded DBC file.")
    except Exception as e:
        print(f"Error loading DBC file: {e}", file=sys.stderr)
        return False

    # Dictionary to keep track of column headers and data
    headers = set()
    data_rows = []

    for can_msg in can_reader:
        try:
            dbc_msg = db.get_message_by_frame_id(can_msg.arbitration_id)
            if not dbc_msg:
                print(f"Message with ID {can_msg.arbitration_id} not found in DBC file.", file=sys.stderr)
                continue
        except KeyError as e:
            print(f"Error getting message by frame ID {can_msg.arbitration_id}: {e}. It doesn't exist in the DBC.", file=sys.stderr)
            continue

        decoded_signals = dbc_msg.decode(can_msg.data)

        headers.update(decoded_signals.keys())

        # Signal dictionary
        signal_data = {signal_name: "" for signal_name in headers}
        # Create a row of data with placeholders for signals
        row_data = {
            "Timestamp": can_msg.timestamp,
            "Interface": can_msg.channel,
            "Message Name": dbc_msg.name,
            **signal_data,
        }

        # Update row data with actual signal values
        row_data.update(decoded_signals)

        data_rows.append(row_data)

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
        print(f"Error opening CSV file for writing: {e}", file=sys.stderr)
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
        print(f"Conversion failed. Please check the provided files and try again.", file=sys.stderr)
