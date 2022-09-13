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
import urllib.request
import re

netnexturl = 'http://vger.kernel.org/~davem/net-next.html'
status_regex = re.compile(r'alt="net-next is (\S+)"')

def get_netnext():
    # Get a http.client.HTTPResponse object
    resp = urllib.request.urlopen(netnexturl)
    body = resp.read().decode('utf-8')
    match = status_regex.search(body)
    if match:
        return str(match[1]).capitalize()
    return 'None'

def update_state(data):
    data[datetime.date.today()] = get_netnext()

def load_datastore(filename):
    return yaml.load(open(filename, 'rt'), Loader=yaml.FullLoader)

def save_datastore(filename, data):
    yaml.dump(data, open(filename, 'wt'))

def generate_testdata(generate=False):
    data = {}
    if generate:
        day = datetime.timedelta(days=1)
        current = datetime.date(2021, 1, 1)
        now = datetime.date.today()
        while current < now:
            data[current] = 'Open'
            current += day
    return data

def create_datastore(filename):
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    data = generate_testdata()
    save_datastore(filename, data)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('filename', help='Path to the datastore file', type=str, metavar='path', default='~/.local/share/netnextstatus/status.csv')
    args = parser.parse_args()
    if args.filename:
        absfilename = os.path.expanduser(args.filename)
        if not os.path.exists(absfilename):
            create_datastore(absfilename)
        data = load_datastore(absfilename)
        update_state(data)
        save_datastore(absfilename, data)
