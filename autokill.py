#!/usr/bin/env python3
#
# autokill.py
#
"""
A script for automatically killing jobs
"""

from argparse import ArgumentParser
import asyncio

import signal
import re
import sys


def sig_handle(signal, frame):
    print("SIGNAL", signal)
    sys.exit(0)

signal.signal(signal.SIGTSTP, sig_handle)

parser = ArgumentParser()
parser.add_argument('job_ids',
                    nargs='+',
                    help='A list of masterjobs to watch.')
parser.add_argument('-t', '--time',
                    default='30',
                    type=float,
                    help='Time (in minutes) to repeat the action',)
args = parser.parse_args()


@asyncio.coroutine
def process_info(out, err):
    res = dict()
#   for line in out.readline():
    while True:
        line = yield from out.readline()
        if not line:
            break
        matches = re.search("Subjobs in (\w+) *: (\d+)", line.decode())
        if matches:
            res[matches.group(1)] = matches.group(2)
    return res


@asyncio.coroutine
def kill_job(jid):
    from asyncio.subprocess import PIPE
    prefix = "[%s] " % (jid)
    info_cmd = 'aliensh -c masterjob %s' % (jid)
    kill_cmd = 'aliensh -c masterjob %s -status DONE kill' % (jid)
    i = 0
    running = {'WAITING', 'RUNNING', 'SAVING'}
    while True:
        info = yield from asyncio.create_subprocess_shell(info_cmd,
                                                          stdout=PIPE,
                                                          stderr=PIPE)
        stats = yield from process_info(info.stdout, info.stderr)
        print(prefix, i, stats)
        if 'DONE' not in stats:
            print("no done jobs")
            yield from asyncio.sleep(args.time * 60)
            continue

        elif stats["DONE"]:
            kill = yield from asyncio.create_subprocess_shell(kill_cmd,
                                                              stdout=PIPE,
                                                              stderr=PIPE)
            jobs_killed = []
            while True:
                line = yield from kill.stdout.readline()
                if not line:
                    break
                m = re.search('killing subjob (\d+)', line.decode())
                if m:
                    jobs_killed.append(m.group(1))
            print(prefix, 'killed {} subjobs'.format(len(jobs_killed)))
        else:
            if len(running.intersection(stats.keys())) == 0:
                break

#       kill_ret = yield from kill
#       data = yield from kill_ret
#       proc = asyncio.create_subprocess_exec(*aliargs,
#                                             stdout=asyncio.subprocess.PIPE)
#       proc = asynco.create_subprocess_shell(' '.join(aliargs),
#                                             stdout=asyncio.subprocess.PIPE)
#       res = yield from proc
#       data = yield from res.stdout.read()
#       print (prefix, "===DATA====\n", data.decode())
        yield from asyncio.sleep(args.time * 60)
        i += 1


@asyncio.coroutine
def main(ids):
    yield from asyncio.wait([asyncio.async(kill_job(jid)) for jid in ids])
#   killers = asyncio.JoinableQueue()
#   for jid in args.job_ids:
#       yield from killers.put(asyncio.async(kill_job(jid)))
#   yield from killers.join()

loop = asyncio.get_event_loop()
loop.run_until_complete(main(args.job_ids))

# try:
# loop.call_soon(kill_main())
#   loop.run_forever()
# finally:
#   loop.close()

print("Done!")
