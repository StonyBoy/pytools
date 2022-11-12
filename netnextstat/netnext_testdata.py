#! /usr/bin/env python3
'''
Pull the Linux NetNext repo status and save it in a file

Installation:
    pip --user install PyYAML

Service Installation:
    - Copy the netnextstatus.service and netnextstatus.timer to ~/.config/systemd/user
    - Reload: systemctl --user daemon-reload
    - Enable and start the timer: systemctl --user enable --now netnextstatus.timer
    - Check timer status: systemctl --user list-timers
    - Check log: journalctl -xe --user -u netnextstatus.service
    - Check output update: ls -l  ~/.local/share/netnextstatus/status.csv
    - Check output content: less  ~/.local/share/netnextstatus/status.csv
    - Run the service now: systemctl restart --user netnextstatus.service
'''
import os
import os.path
import argparse
import datetime
import yaml

def load_datastore(filename):
    return yaml.load(open(filename, 'rt'), Loader=yaml.FullLoader)

def save_datastore(filename, data):
    yaml.dump(data, open(filename, 'wt'))

def generate_testdata(data):
    day = datetime.timedelta(days=1)
    current = datetime.date(2010, 1, 1)
    first = list(data.keys())[0]
    opendays = range(0, 51)
    closeddays = range(51, 65)
    index = 0
    while current < first:
        if index in opendays:
            data[current] = 'Open'
        if index in closeddays:
            data[current] = 'Closed'
        current += day
        index += 1
        index %= 65
    return data

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('filename', help='Path to the datastore file', type=str, metavar='path', default='~/.local/share/netnextstatus/status.csv')
    args = parser.parse_args()
    if args.filename:
        absfilename = os.path.expanduser(args.filename)
        data = load_datastore(absfilename)
        generate_testdata(data)
        save_datastore(absfilename, data)
