#!/usr/bin/env python

# Copyright 2012 James E. Blair <corvus@gnu.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import subprocess
import signal
import threading

import gobject
import dbus.mainloop.glib
import dbus


class OIRunner(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.wake_event = threading.Event()
        self.should_run = False
        self.popen = None

    def run(self):
        while True:
            self.wake_event.wait()
            self.wake_event.clear()
            if self.should_run:
                self.is_running = True
                print "Offlineimap is starting"
                self._run_oi()
                print "Offlineimap is stopped"
                # In case offlineimap crashed, set the wake event so we
                # go through this loop one more time.
                self.wake_event.set()

    def _run_oi(self):
        self.popen = subprocess.Popen('offlineimap', shell=True)
        self.popen.wait()
        self.popen = None

    def startOI(self):
        print "Starting offlineimap"
        self.should_run = True
        self.wake_event.set()

    def stopOI(self):
        print "Stopping offlineimap"
        self.should_run = False
        if self.popen:
            try:
                self.popen.send_signal(signal.SIGUSR2)
            except:
                print "Exception sending signal to offlineimap"

    def onBatteryChanged(self, on_battery):
        on_battery = bool(on_battery)
        if on_battery:
            print "Switched to battery"
            self.stopOI()
        else:
            print "Switched to AC"
            self.startOI()


def main():
    gobject.threads_init()
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SessionBus()
    should_start = False
    try:
        power = bus.get_object('org.freedesktop.PowerManagement',
                               '/org/freedesktop/PowerManagement')
        on_battery = bool(power.GetOnBattery())
        if not on_battery:
            should_start = True
    except:
        print "Unable to query current power state"
        # Power manager may not have started yet

    runner = OIRunner()
    runner.start()

    if should_start:
        runner.onBatteryChanged(False)

    bus.add_signal_receiver(runner.onBatteryChanged,
                            signal_name='OnBatteryChanged')

    loop = gobject.MainLoop()
    loop.run()


if __name__ == '__main__':
    main()
