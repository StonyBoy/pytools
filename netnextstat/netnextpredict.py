#! /usr/bin/env python3
'''
Parse the Linux NetNext repo status and propose the next merge window

Installation:
    pip --user install PyYAML

'''
import os
import os.path
import argparse
import yaml
import sys
import datetime

def load_datastore(filename):
    return yaml.load(open(filename, 'rt'), Loader=yaml.FullLoader)


class MergePeriod:
    def __init__(self, begin, next_begin):
        self.begin = begin
        self.duration = next_begin - self.begin
        self.end = next_begin - datetime.timedelta(days=1)

    def __str__(self):
        return '{0}: {1} days, ending {2}'.format(self.begin, self.duration.days, self.end)

def parse_datastore(data):
    merge_periods = []
    current = 'Open'
    closed = None
    for date, state in data.items():
        if current == 'Open' and state == 'Closed':
            closed = date
        if current == 'Closed' and state == 'Open':
            merge_periods.append(MergePeriod(closed, date))
        current = state
    return merge_periods

def predict_next(merge_periods):
    duration_avg = []
    for mp in merge_periods:
        print(mp)
    begin = None
    for mp in merge_periods:
        if not begin == None:
            diff = mp.begin - begin
            duration_avg.append(diff.days)
        begin = mp.begin
    avg = sum(duration_avg) // len(duration_avg)
    print('Days between Merge Windows:', duration_avg, 'Average days:', avg)
    print('Next Merge Window Starts: ', merge_periods[-1].begin + datetime.timedelta(days=avg))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-f', '--filename', help='Path to the datastore file', type=str, metavar='path',
        default='~/.local/share/netnextstatus/status.csv')
    args = parser.parse_args()
    if args.filename:
        absfilename = os.path.expanduser(args.filename)
        if not os.path.exists(absfilename):
            print('Could not find the datatore at: ', absfilename)
            sys.exit(1)
        data = load_datastore(absfilename)
        merge_periods = parse_datastore(data)
        predict_next(merge_periods)

