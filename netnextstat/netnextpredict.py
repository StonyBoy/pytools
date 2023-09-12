#! /usr/bin/env python3
'''
Read the lore.kernel.org netdev email list using a query to get the emails that announce that net-next opens or closes.
Use that to show the historic net-next cycles and predict the next three.

Installation:
    pip install beautifulsoup4
    pip install PyYAML
    pip install Jinja2
    pip install pytz

'''
import sys
import urllib.request
import bs4
import re
import datetime
import os
import os.path
import argparse
import yaml
import pytz
import jinja2
import subprocess

re_state = re.compile(r'net-next is (OPEN|CLOSED)', re.IGNORECASE)
re_pull_rc1 = re.compile(r'\[GIT PULL\] Networking for ([0-9.]+-rc[1-2])', re.IGNORECASE)
re_author = re.compile(r'-\sby\s([^@]+)\s@\s(\S+)\s+(\S+)\s+(\S+)\s+\[\d+%\]')

history_limit = datetime.datetime.strptime('2018-08-28 15:43', '%Y-%m-%d %H:%M').date()


class NetNextNotification:
    def __init__(self, subject, author):
        self._state = subject
        self._author = author
        self._datetime = datetime.datetime.now()

    def parse(self, regex, subject, author):
        self._state = regex.findall(subject)[0]
        mt = re_author.findall(author)
        if mt:
            self._author = mt[0][0]
            self._datetime = datetime.datetime.strptime(f'{mt[0][1]} {mt[0][2]} {mt[0][3]}', '%Y-%m-%d %H:%M %Z')
        else:
            self._author = ''
            self._datetime = datetime.datetime.strptime(author, '%Y-%m-%d')

    @property
    def state(self):
        return self._state.capitalize()

    @property
    def date(self):
        return self._datetime.date()

    @property
    def yaml(self):
        return [str(self.date), {'state': self.state, 'author': self._author}]

    def __eq__(self, other):
        return self._datetime == other._datetime

    def __lt__(self, other):
        return self._datetime < other._datetime

    def __str__(self):
        return f'{self._state:<10} {self._author:<20} {self._datetime}'


class NetNextStateChange(NetNextNotification):
    def __init__(self, subject, author):
        self.parse(re_state, subject, author)


class NetNextPullRequest(NetNextNotification):
    def __init__(self, subject, author):
        self.parse(re_pull_rc1, subject, author)


class NetNextCycle:
    def __init__(self, day1, day2, day3):
        self.day1 = day1
        self.day2 = day2
        self.day3 = day3
        self.open = self.day2 - self.day1
        self.closed = self.day3 - self.day2
        self.predicted = False
        self.version = None

    def set_version(self, version):
        self.version = version

    def has_no_version(self):
        return self.version is None

    def __str__(self):
        return self.dump()

    def dump(self, txt=''):
        if len(txt):
            txt = self.__class__.__name__
        close = self.day2 - datetime.timedelta(days=1)
        last = self.day3 - datetime.timedelta(days=1)
        return (f'{txt} Open: {self.day1.strftime("%d-%b-%Y")} to {close.strftime("%d-%b-%Y")}, {self.open.days} days, '
                f'Closed: {self.day2.strftime("%d-%b-%Y")} to {last.strftime("%d-%b-%Y")}, {self.closed.days} days, '
                f'{self.version}')


class PredictedNetNextCycle(NetNextCycle):
    def __init__(self, day1, open_days, closed_days):
        self.day1 = day1
        self.open = datetime.timedelta(days=open_days)
        self.closed = datetime.timedelta(days=closed_days)
        self.day2 = self.day1 + self.open
        self.day3 = self.day2 + self.closed
        self.predicted = True
        self.version = None

    def open_update(self, day2, today):
        # print(f'open_update: {day2} {today}')
        # Add one more day if net-next is still open today
        while self.day2 <= today:
            self.open += datetime.timedelta(days=1)
            self.day2 = self.day1 + self.open
            self.day3 = self.day2 + self.closed

    def close_update(self, day2, today):
        # print(f'close_update: {day2} {today}')
        self.day2 = day2
        self.open = day2 - self.day1
        self.day3 = self.day2 + self.closed
        # Add one more day if net-next is still closed today
        while self.day3 <= today:
            self.closed += datetime.timedelta(days=1)
            self.day3 = self.day2 + self.closed


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


def load_datastore(filename):
    return yaml.load(open(filename, 'rt'), Loader=yaml.FullLoader)


missing_data = [
    NetNextStateChange('net-next is Open', '2019-05-20'),
    NetNextStateChange('net-next is Closed', '2021-02-13'),
    NetNextStateChange('net-next is Closed', '2021-04-24'),
    NetNextStateChange('net-next is Open', '2021-05-12'),
    NetNextStateChange('net-next is Closed', '2021-06-26'),
    NetNextStateChange('net-next is Open', '2021-07-10'),
    NetNextStateChange('net-next is Closed', '2021-08-28'),
    NetNextStateChange('net-next is Closed', '2021-10-30'),
    NetNextStateChange('net-next is Closed', '2022-01-11'),
]


def get_updated_history():
    history = get_netnext_history() + missing_data
    return sorted(history)


def save_datastore(filename, data):
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    history = dict([item.yaml for item in data])
    yaml.dump(history, open(filename, 'wt'))
    print(f"... wrote {filename}")


def get_netnext_history():
    res = []
    uri = 'https://lore.kernel.org/netdev/?q=s%3A%22net-next+is+%22'
    with urllib.request.urlopen(uri) as response:
        html = response.read()
        parsed_html = bs4.BeautifulSoup(html, 'html.parser')
        for item in parsed_html.find_all('a'):
            if re_state.search(item.text) and 'Re:' not in item.text:
                state = NetNextStateChange(item.text, item.parent.next_sibling)
                if state.date >= history_limit:
                    res.append(state)
    return res


def get_netnext_prs():
    res = []
    uri = 'https://lore.kernel.org/netdev/?q=s%3B%22%5BGIT+PULL%5D+Networking+for+*%22'
    with urllib.request.urlopen(uri) as response:
        html = response.read()
        parsed_html = bs4.BeautifulSoup(html, 'html.parser')
        for item in parsed_html.find_all('a'):
            if re_pull_rc1.search(item.text) and 'Re:' not in item.text:
                res.append(NetNextPullRequest(item.text, item.parent.next_sibling))
    return res


def generate_netnext_cycles(history):
    cycles = []
    size = len(history)
    for idx, item in enumerate(history):
        if item.state == 'Open':
            if idx < size - 2:
                cycles.append(NetNextCycle(item.date, history[idx + 1].date, history[idx + 2].date))
    for idx, cycle in enumerate(cycles):
        if cycle.open.days < 20:
            del cycles[idx]
    return cycles


def predict(cycles, history, today):
    open_days = []
    closed_days = []
    for cycle in cycles[-3:]:
        open_days.append(cycle.open.days)
        closed_days.append(cycle.closed.days)
    next_open = int(sum(open_days) / len(open_days))
    next_closed = int(sum(closed_days) / len(closed_days))
    size = len(history)
    for idx, item in enumerate(history):
        if item.state == 'Open':
            if idx >= size - 2:
                cycle = PredictedNetNextCycle(item.date, next_open, next_closed)
                if idx == size - 1:
                    cycle.open_update(history[-1].date, today)
                elif idx < size - 1:
                    cycle.close_update(history[-1].date, today)
                cycles.append(cycle)
    for idx in range(0, 2):
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
    last_tag = linux_versions[0]
    for cycle in cycles:
        for tag in linux_versions:
            diff = tag.date - cycle.day3
            near = diff.days > -14 and diff.days < 2
            if near:
                cycle.set_version(tag.version)
                last_tag = tag
                break
        if cycle.has_no_version():
            last_tag.increment()
            cycle.set_version(last_tag.version)


def generate_html(cycles, now, linux_versions, outputpath):
    html_filename = os.path.join(os.path.expanduser(outputpath), 'index.html')
    templatepath = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'templates')
    print('templates:', templatepath)
    environment = jinja2.Environment(loader=jinja2.FileSystemLoader(templatepath))
    html_template = environment.get_template('netnext.html.jinja')
    content = {
        'cycles': cycles,
        'linux_versions': linux_versions,
        'generated': now,
    }
    with open(html_filename, mode="w", encoding="utf-8") as results:
        results.write(html_template.render(content))
        print(f"... wrote {html_filename}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-p', '--pullreq', help='Get rc1 or rc2 pull requests', action='store_true')
    parser.add_argument('-z', '--timezone', help='Set timezone for current date', type=str, default='Europe/Copenhagen')
    parser.add_argument('-g', '--generate', help='Generate an HTML file with the prediction', action='store_true')
    parser.add_argument('-o', '--outdir', help='Output folder for generated files', type=str, default='.')
    parser.add_argument('-r', '--repo', help='Path to linux git repo with tag information', type=str, default=None)
    parser.add_argument('-s', '--statusonly', help='Just get the lore.kernel.org net-next status', action='store_true')
    parser.add_argument('-c', '--cyclesonly', help='Show the net next cycles', action='store_true')
    parser.add_argument('-a', '--savestatus', help='Save the lore.kernel.org net-next status', action='store_true')

    args = parser.parse_args()

    history = get_updated_history()

    if args.savestatus:
        filename = 'history.yaml'
        if args.outdir:
            datastorepath = os.path.join(os.path.expanduser(args.outdir), filename)
        else:
            datastorepath = filename
        save_datastore(datastorepath, history)
        sys.exit(0)

    if args.statusonly:
        if args.pullreq:
            print('Net Next Emails with RC1/RC2 pull requests')
            history += get_netnext_prs()
            history = sorted(history)
        else:
            print('Net Next Status Emails')

        last = history[0].date
        for item in history:
            diff = item.date - last
            print(f'    {item} {diff.days} {"***" if diff.days > 65 else ""}')
            last = item.date
        sys.exit(0)

    cycles = generate_netnext_cycles(history)[-17:]

    tz = pytz.timezone('Europe/Copenhagen')
    if args.timezone:
        tz = pytz.timezone(args.timezone)
    now = datetime.datetime.now(tz)

    cycles = predict(cycles, history, now.date())

    linux_versions = None
    if args.repo:
        linux_versions = get_git_linux_tags(os.path.expanduser(args.repo))
        if linux_versions:
            add_linux_versions(cycles, linux_versions)

    if args.cyclesonly:
        print('Net Next Cycles')
        for item in cycles:
            print(f'    {item.dump("-")}')
        sys.exit(0)

    if args.generate:
        generate_html(cycles, now, linux_versions, args.outdir)
    else:
        print('Net Next Cycles Prediction')
        for item in cycles:
            print(f'    {item}')

