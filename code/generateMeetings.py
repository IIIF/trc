#!/usr/bin/python

import sys
from ics import Calendar, Event
from datetime import datetime,timedelta
from dateutil import tz

def timezone(timeInstance, timezone):
    return timeInstance.astimezone(tz.gettz(timezone)).time()

if __name__ == "__main__":
    if len(sys.argv) != 3 and len(sys.argv) != 4:
        print ('Usage:\n\t./code/calendar.py [start_date YYYY-MM-DD] [Occurrence count] [Japan time frequency]')
        sys.exit(0)

    if len(sys.argv) == 3:
        frequency = 4
    else:
        frequency = int(sys.argv[3])

    cal = Calendar()

    first_meeting = datetime(int(sys.argv[1][0:4]), int(sys.argv[1][5:7]), int(sys.argv[1][8:10]), 12, 0, 0, 0, tz.gettz('America/New_York'))
    occurences = sys.argv[2]
    next_meeting = first_meeting
    for i in range(int(occurences)):
        issues_shared = next_meeting - timedelta(days=7)
        voting_closes = next_meeting + timedelta(days=7*2)
        if i % frequency == 0 and i != 0:
            meeting_time = next_meeting.replace(hour=19)
        else:
            meeting_time = next_meeting
        timestr = '{} Europe / {} UK / {} US Eastern / {} US Pacific / {} Japan'.format(timezone(meeting_time, 'Europe/Paris'), timezone(meeting_time, 'Europe/London'), timezone(meeting_time, 'America/New_York'), timezone(meeting_time, 'America/Los_Angeles'), timezone(meeting_time, 'Asia/Tokyo'))
        print ('TRC meeting: {} ({}), \nSend out issues: {}, \nVoting closes: {}\n'.format(meeting_time.date(), timestr, issues_shared.date(), voting_closes.date()))

        e = Event()
        e.name = 'IIIF Technical Review Committee'
        e.begin = next_meeting
        cal.events.add(e)
        next_meeting += timedelta(days=4*7)

    with open('/tmp/trc.ics', 'w') as ics_file:
        ics_file.writelines(cal) 


    
