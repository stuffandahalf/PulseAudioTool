#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Source: PulseAudioTool.py
# By: Gregory Norton

# PulseAudio logo from http://blog.rabin.io/wp-content/uploads/2014/10/pulseaudio-logo.png

# main module imports
from __future__ import division
import time
import os
from subprocess import Popen, PIPE, check_output
import threading

# gtk module imports
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
gi.require_version('AppIndicator3', '0.1')
from gi.repository import AppIndicator3 as appindicator

device_id = 'alsa_input.usb-BLUE_MICROPHONE_Blue_Snowball_201607-00.analog-mono'    #default device id
volume = 100                                                            # default input volume level

pref_file = '.PulseAudioTool.pref'                                       # default preference file
lock_file = '.PulseAudioTool.lock'                                      # lock file

APPINDICATOR_ID = 'PulseAudioTool'                                      # app id

opened = False                                                          # status of the window
halted = False                                                          # halt status of program
broken = False                                                          # microphone level exceeding 100
WINDOW_HEIGHT = 200                                                     # default and minimum height of the window
WINDOW_WIDTH = 400                                                      # default and minimum width of the window

def read_preferences(pref_file):
    global device_id
    global volume
    f = open(pref_file, 'r')
    device_id = f.readline().rstrip('\r\n')
    volume = int(f.readline().rstrip('\r\n'))
    f.close()
    
def write_preferences(pref_file):
    global device_id
    global volume
    f = open(pref_file, 'w+')
    f.write(device_id + '\n')
    f.write(str(volume))
    f.close()

def call_pulseaudio_command(device, volume):
    bash_command = 'pacmd set-source-volume ' + device + ' ' + str(volume)
    process = Popen(bash_command.split(), stdout=PIPE)
    output, error = process.communicate()
    returnvals = [output, error]
    return returnvals

def get_devices():
    process1 = Popen('pacmd list-sources'.split(), stdout = PIPE)
    process2 = Popen('grep name:'.split(), stdin = process1.stdout, stdout = PIPE)
    output = check_output('grep input'.split(), stdin = process2.stdout)
    devices = output.split('\n')
    for i in range(0, len(devices)-1):
        devices[i] = devices[i].strip(' \t\n\r')[7:-1]
        #print devices[i]
    return devices

def convert_volume(in_volume):
    #max input volume 781.25
    #max converted volume 512000
    if in_volume > 781.25:
        in_volume = 781.25
    elif in_volume < 0:
        in_volume = 0
    out_volume = in_volume / 100 * 65536
    out_volume = int(out_volume)
    return out_volume

def set_volume():
    global halted, device_id, volume
    while not halted:
        time.sleep(0.1)
        #print volume
        outputs = call_pulseaudio_command(device_id, convert_volume(volume))
        
class Tray_Indicator(object):
    def __init__(self):
        self.indicator = appindicator.Indicator.new(APPINDICATOR_ID,
                                                    os.path.abspath('pulseaudio-logo.png'),             #icon
                                                    appindicator.IndicatorCategory.SYSTEM_SERVICES)
        self.indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
        self.indicator.set_menu(self.build_menu())

    def build_menu(self):
        menu = gtk.Menu()
        
        item_show = gtk.MenuItem('Show')
        item_show.connect('activate', self.show)
        menu.append(item_show)
        
        item_quit = gtk.MenuItem('Quit')
        item_quit.connect('activate', self.quit_app)
        menu.append(item_quit)
        
        menu.show_all()
        return menu
        
    def show(self, data):
        global opened
        if opened == False:
            window = PAT_Window()
            opened = True
            
    def quit_app(self, data):
        global halted
        halted = True
        os.remove(lock_file)
        write_preferences(pref_file)
        exit()

class PAT_Window(object):
    def __init__(self):
        self.window = gtk.Window()
        self.window.set_default_size(WINDOW_WIDTH, WINDOW_HEIGHT)       # set the default window size
        self.window.set_size_request(WINDOW_WIDTH, WINDOW_HEIGHT)       # set the minimum window size
        self.window.show()                                              # show the window
        self.window.set_title('PulseAudioTool')                         # set title of window
        
        self.layout = gtk.Layout()                                      # create a new gtk layout object
        self.window.add(self.layout)                                    # add the layout to the window
        self.layout.show()                                              # show the layout
        
        self.add_volume_slider()
        self.add_device_dropdown()
        self.add_refresh_button()
        self.add_break_button()
        
        self.window.show_all()
        self.window.connect('delete-event', self.close_window)

    def close_window(self, widget, e):
        global opened
        self.window.destroy
        opened = not opened
        
    def add_volume_slider(self):
        volume_label = gtk.Label('Volume:')
        self.layout.put(volume_label, 10, 33)
        
        self.slider = gtk.HScale()
        self.slider.set_size_request(300, 30)
        self.slider.set_range(0, 100)
        self.slider.set_increments(1, 10)
        self.slider.set_digits(0)
        self.slider.set_value(volume)
        
        def on_changed(widget):
            global volume
            volume = int(widget.get_value())
            write_preferences(pref_file)
        self.slider.connect('value-changed', on_changed)
        
        self.layout.put(self.slider, 75, 15)
        
    
    def add_device_dropdown(self):
        self.dropdown = gtk.ComboBoxText()
        self.dropdown.set_size_request(390, 50)
        self.devices = get_devices()
        #print device_id
        for i in range(0, len(self.devices)-1):
            device = self.devices[i].split('.')
            self.dropdown.append_text(self.devices[i].split('.')[1])
            if device_id == self.devices[i]:
                self.dropdown.set_active(i)
        
        def dropdown_changed(widget):
            global device_id
            index = widget.get_active()
            device_id = self.devices[index]
        self.dropdown.connect('changed', dropdown_changed)
        
        dropdown_label = gtk.Label('Devices:')
        self.layout.put(dropdown_label, 5, WINDOW_HEIGHT - 85)
        
        self.layout.put(self.dropdown, 5, WINDOW_HEIGHT - 55)
    
    def add_refresh_button(self):
        refresh_button = gtk.Button(label = 'Refresh')
        refresh_button.set_size_request(100, 50)
        
        def refresh_dropdown(widget):
            for i in range(0, len(self.devices)-1):
                self.dropdown.remove(0)
            self.devices = get_devices()
            self.dropdown.append_text(self.devices[i].split('.')[1])
            
        refresh_button.connect('clicked', refresh_dropdown)
        
        self.layout.put(refresh_button, WINDOW_WIDTH - 210, WINDOW_HEIGHT - 110)
        
    def add_break_button(self):
        break_button = gtk.Button(label = 'Break')
        break_button.set_size_request(100, 50)
        
        def break_volume(widget):
            global volume, broken
            if not broken:
                self.old_volume = volume
                volume = 781.25
                self.slider.set_sensitive(False)
                broken = True
            else:
                volume = self.old_volume
                self.slider.set_sensitive(True)
                broken = False
        
        break_button.connect('clicked', break_volume)
        
        self.layout.put(break_button, WINDOW_WIDTH - 105, WINDOW_HEIGHT - 110)

def main(args):
    if not os.path.exists(lock_file):
        open(lock_file, 'w+')
        if not os.path.exists(pref_file):
            write_preferences(pref_file)
        else:
            read_preferences(pref_file)
        t1 = threading.Thread(target = set_volume)
        t1.start()
        indicator = Tray_Indicator()
        gtk.main()
    else:
        print 'Script already launched'
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
