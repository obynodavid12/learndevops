#!/bin/bash

[ -n "$1" ] && time="-d @$(date -d "$1" +%s)" || time=
printf '%-15s' 'US West';     TZ='America/Los_Angeles' date '+%H:%M %z %Z' $time
printf '%-15s' 'US East';     TZ='America/New_York'    date '+%H:%M %z %Z' $time
printf '%-15s' 'UTC';         TZ='UTC'                 date '+%H:%M %z %Z' $time
printf '%-15s' 'Ireland/UK';  TZ='Europe/Dublin'       date '+%H:%M %z %Z' $time
printf '%-15s' 'West Europe'; TZ='Europe/Amsterdam'    date '+%H:%M %z %Z' $time
printf '%-15s' 'New Zealand'; TZ='NZ'                  date '+%H:%M %z %Z' $time
printf '\n\x1b[1m%-15s' 'Current'; date '+%H:%M %z %Z' $time; printf '\x1b[0m'


# this is a nice date-related script
# Just tz will print the times in all the timezones, and tz 1900 (or tz 19:00, tz 7pm) will print the times corresponding to 19:00 in all the timezones.
