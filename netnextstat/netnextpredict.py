#! /usr/bin/env python3
'''
Read the netnetstatus file and calculate statistics and predict the next cycle
If a git repo is provided the Linux version will be added to the cycles

Installation:
    pip --user install PyYAML
    pip --user install Jinja2
    pip --user install pytz

'''
import os
import os.path
import argparse
import datetime
import sys
import subprocess
import re

import yaml
import jinja2
import pytz

statuspath = os.path.expanduser('~/.local/share/netnextstat/status.csv')

def load_datastore(filename):
    return yaml.load(open(filename, 'rt'), Loader=yaml.FullLoader)

class NetNextCycle:
    def __init__(self, day1, day2, day3):
        self.day1 = day1
        self.day2 = day2
        self.day3 = day3
        self.open = self.day2 - self.day1
        self.close = self.day3 - self.day2
        self.current = False
        self.predicted = False
        self.update()
        self.version = None

    def update(self):
        today = datetime.date.today()
        if self.day1 <= today and today <= self.day3:
            self.current = True

    def set_version(self, version):
        self.version = version

    def no_version(self):
        return self.version == None

    def __str__(self):
        close = self.day2 - datetime.timedelta(days=1)
        last = self.day3 - datetime.timedelta(days=1)
        return (f'Open: {self.day1.strftime("%d-%b-%Y")} to {close.strftime("%d-%b-%Y")}, {self.open.days} days, '
                f'Closed: {self.day2.strftime("%d-%b-%Y")} to {last.strftime("%d-%b-%Y")}, {self.close.days} days, '
                f'{self.version}')

class PredictedNetNextCycle(NetNextCycle):
    def __init__(self, day1, open_days, closed_days):
        self.day1 = day1
        self.open = datetime.timedelta(days=open_days)
        self.close = datetime.timedelta(days=closed_days)
        self.day2 = self.day1 + self.open
        self.day3 = self.day2 + self.close
        self.predicted = False
        self.update()
        self.predicted = True
        self.version = None

class LinuxTag:
    regex = re.compile(r'Linux (\d+)\.(\d+)')
    def __init__(self, date, tag, version):
        self.date = datetime.date(date.year, date.month, date.day)
        self.tag = tag
        self.version = version

    def increment(self):
        mt = LinuxTag.regex.findall(self.version)
        if mt:
            major = int(mt[0][0])
            minor = int(mt[0][1])
            if minor >= 19:
                major += 1
                minor = 0
            else:
                minor += 1
            self.version = f'Linux {major}.{minor}'

    def __str__(self):
        return f'{self.date}: {self.version}'

def generate_netnext_cycles(data):
    laststate = None
    events = []
    cycles = []
    for day, state in data.items():
        if state != laststate:
            events.append((day, state))
            if len(events) >= 2:
                if events[-1][1] == 'Open' and len(events) >= 3:
                    cycles.append(NetNextCycle(events[-3][0], events[-2][0], events[-1][0]))
            laststate = state
    # Filter out truncated cycles
    for idx, cycle in enumerate(cycles):
        if cycle.open.days < 20:
            del cycles[idx]
    return cycles

def predict(cycles):
    open_days = []
    closed_days = []
    for cycle in cycles[-3:]:
        open_days.append(cycle.open.days)
        closed_days.append(cycle.close.days)
    next_open = int(sum(open_days) / len(open_days))
    next_closed = int(sum(closed_days) / len(closed_days))
    for _unused in range(0, 3):
        open_date = cycles[-1].day3
        cycles.append(PredictedNetNextCycle(open_date, next_open, next_closed))
    return cycles

def get_git_linux_tags(repo):
    cp = subprocess.run(['git', '-C', repo, 'tag', '-l',
                         '--format=%(refname:short);%(taggerdate:iso-strict);%(contents:subject)',
                         '--sort=taggerdate'],
                        capture_output=True)
    if cp.returncode == 0:
        lines = cp.stdout.decode().split('\n')
        history = []
        # Look for the RC1 tags as they start a new Linux Version
        regex = re.compile(r'([^;]+)-rc1;([^;]+);([^;]+)-rc1')
        for line in lines:
            mt = regex.findall(line)
            if mt:
                tagstr, datestr, versionstr = mt[0][0:3]
                history.append(LinuxTag(datetime.datetime.fromisoformat(datestr), tagstr, versionstr))
        return history
    return None

def add_linux_versions(cycles, linux_versions):
    for cycle in cycles:
        for tag in linux_versions:
            diff = tag.date - cycle.day3
            if diff.days <= 2:
                cycle.set_version(tag.version)

    # add future versions
    last_tag = linux_versions[-1]
    for cycle in cycles:
        if cycle.predicted:
            last_tag.increment()
            cycle.set_version(last_tag.version)

def generate_html(cycles, linux_versions, outputpath):
    html_filename = os.path.join(os.path.expanduser(outputpath), 'netnext.html')
    templatepath = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'templates')
    print('templates:', templatepath)
    environment = jinja2.Environment(loader=jinja2.FileSystemLoader(templatepath))
    html_template = environment.get_template('netnext.html.jinja')
    tz = pytz.timezone('Europe/Copenhagen')
    content = {
            'cycles': cycles,
            'linux_versions': linux_versions,
            'generated': datetime.datetime.now(tz)
    }
    with open(html_filename, mode="w", encoding="utf-8") as results:
        results.write(html_template.render(content))
        print(f"... wrote {html_filename}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-g', '--generate', help='Generate an HTML file with the prediction', action='store_true')
    parser.add_argument('-o', '--outdir', help='Output folder for generated files', type=str, default='.')
    parser.add_argument('-r', '--repo', help='path to linux git repo with tag information', type=str, default=None)
    parser.add_argument('filename', help='Path to the netnext datastore file', type=str, metavar='path',
                        default=statuspath)
    args = parser.parse_args()
    if args.filename:
        absfilename = os.path.expanduser(args.filename)
        if not os.path.exists(absfilename):
            print(f'No netnext status file found at {absfilename}')
            sys.exit(1)

        linux_versions = None
        if args.repo:
            linux_versions = get_git_linux_tags(os.path.expanduser(args.repo))

        data = load_datastore(absfilename)
        cycles = generate_netnext_cycles(data)
        cycles = predict(cycles)
        add_linux_versions(cycles, linux_versions)
        if args.generate:
            generate_html(cycles, linux_versions, args.outdir)
        else:
            for cycle in cycles:
                print(cycle)
