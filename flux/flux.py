'''
Hacked from: https://github.com/fronzbot/githass/blob/master/apps/flux.py

Homemade Flux uses AppDaemon to dynamically set light color temperatures to
follow circadian rythym... or just warm-sided color temperatures.
'''

import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime, timezone, timedelta
import pytz
import globals
import re
import pytz

def utc_to_local(datetime_obj):
    millis = 1288483950000
    ts = millis * 1e-3
    # local time == (utc time + utc offset)
    utc_offset = datetime.fromtimestamp(ts) - datetime.utcfromtimestamp(ts)
    return datetime_obj + utc_offset

class Flux(hass.Hass):

    def initialize(self):
        self.entities = globals.get_arg_list(self.args, "entities")
        self.app_switch = globals.get_arg(self.args, "app_switch")

        self.steps = {
            # offset from sunrise
            'latelate': {'temp': 1600, 'sunrise_offset': -60, 'brightness': 75},
            'sunrise': {'temp': 2500, 'sunrise_offset': -45, 'brightness': 175},
            'morning': {'temp': 2850, 'sunrise_offset': 120, 'brightness': 240},
            'day': {'temp': 3100, 'sunrise_offset': 180, 'brightness': 255},
            # offset from sunset
            'evening': {'temp': 2850, 'sunset_offset': -165, 'brightness': 235},
            'sunset': {'temp': 2500, 'sunset_offset': -45, 'brightness': 220},
            # night_early is to get an aggressive temp/brightness change
            'night_early': {'temp': 2450, 'time': '20:03', 'brightness': 200},
            'night': {'temp': 2200, 'time': '21:15', 'brightness': 150},
            'late': {'temp': 1900, 'time': '23:00', 'brightness': 75},
        }
        self.steps_list = []
        for key, value in self.steps.items():
            value['key'] = key
            self.steps_list.append(value)

        self.run_every_handle = self.run_every(self.update_color, datetime.now(), 5*60)
        self.app_switch_state_handle = self.listen_state(self.on_app_switch_change, self.app_switch)

        self.on_entity_state_change_handle_list = []
        for entity in self.entities:
            self.on_entity_state_change_handle_list.append(
                self.listen_state(self.on_entity_state_change, entity)
            )

        self.update_color()

    def sunrise_tz(self):
        next_rising = re.sub(r'(\d\d):(\d\d)$', r'\1\2', self.get_state('sun.sun', attribute="next_rising"))
        return utc_to_local(datetime.strptime(next_rising, "%Y-%m-%dT%H:%M:%S%z"))

    def sunset_tz(self):
        next_setting = re.sub(r'(\d\d):(\d\d)$', r'\1\2', self.get_state('sun.sun', attribute="next_setting"))
        return utc_to_local(datetime.strptime(next_setting, "%Y-%m-%dT%H:%M:%S%z"))


    def on_entity_state_change(self, entity, attribute, old, new, kwargs):
        if self.get_state(entity) == "on" and old == "off":
            self.update_color([entity])


    def on_app_switch_change(self, entity, attribute, old, new, kwargs):
        if self.get_state(entity) == "on" and old == "off":
            self.update_color()

    def determine_state(self, now):
        sunrise = self.sunrise_tz() - timedelta(days=1)
        sunset = self.sunset_tz() - timedelta(days=1)
        now_time = now.time()
        found_state = None
        for index, value in enumerate(self.steps_list):
            value['time_start'] = sunrise
            if 'sunrise_offset' in value:
                value['time_start'] = sunrise + timedelta(minutes=value['sunrise_offset'])
            elif 'sunset_offset' in value:
                value['time_start'] = sunset + timedelta(minutes=value['sunset_offset'])
            elif 'time' in value:
                midnight = now.replace(hour=0, minute=0, second=0)
                times = value['time'].split(":")
                time_hours = int(times[0])
                time_mins = int(times[1])
                value['time_start'] = midnight + timedelta(hours=time_hours,minutes=time_mins)
            if found_state is None and now_time < value['time_start'].time():
                found_state = self.steps_list[index - 1]
        self.log("====")
        self.log(value['time_start'])
        return found_state if found_state is not None else self.steps_list[-1]

    def get_next_state(self, state, wrap_around = True):
        next_state = self.steps_list[(self.steps_list.index(state) + 1) % len(self.steps_list)]
        if not wrap_around and self.steps_list.index(next_state) == 0 :
            return None
        return next_state

    def calculate_progress(self, now, state):
        next_state = self.get_next_state(state, wrap_around = False)
        if next_state is None:
            return 0
        start = state['time_start']
        end = next_state['time_start']
        progress = round((now - start) / (end - start), 2)
        return progress

    def calculate_temp(self, state, progress):
        # home-assistant.io/components/light/
        # https://community-home-assistant-assets.s3.amazonaws.com/original/2X/b/b50f729dd0e6f71a1ba93a8e818464837b9116a1.jpg
        # Soft White (2700K – 3000K), Bright White/Cool White (3500K – 4100K), and Daylight (5000K – 6500K).
        # 2778K == 360 MIRED, 3846 == 260 MIRED, 5000k = 200 MIRED
        start = state['temp']
        next_state = self.get_next_state(state, wrap_around = False)
        if next_state is None:
            return start
        end = next_state['temp']
        return round(start + ((end - start) * progress))

    def calculate_brightness(self, state, progress):
        start = state['brightness']
        next_state = self.get_next_state(state, wrap_around = False)
        if next_state is None:
            return start
        end = next_state['brightness']
        return round(start + ((end - start) * progress))

    def update_color(self, entities = None, kwargs = None):
        if self.get_state(self.app_switch) != "on":
            self.log("Switch is not on, skipping update_color.")
            return

        now = utc_to_local(datetime.now(timezone.utc))
        state = self.determine_state(now)
        progress = self.calculate_progress(now, state)
        temp = self.calculate_temp(state, progress)
        mired = int(1e6 / temp)
        brightness = self.calculate_brightness(state, progress)

        self.log("Now={}: Sunrise={}, Sunset={}, Progress={}, Temp={}, State={}".format(now.time(), self.sunrise_tz().time(), self.sunset_tz().time(), progress, temp, state))
        self.log("Setting color_temp(mired)={}, brightness={}".format(mired, brightness))

        if not entities:
            entities = self.entities
        for light in entities:
            self.log("is {} on? {}".format(light, self.get_state(light)))
            if self.get_state(light) == 'on':
                self.turn_on(light, color_temp=mired, brightness=brightness)

    def terminate(self):
        if self.run_every_handle is not None:
            self.cancel_timer(self.run_every_handle)
        if self.app_switch_state_handle is not None:
            self.cancel_timer(self.app_switch_state_handle)
        for listen_state_handle in self.on_entity_state_change_handle_list:
            self.cancel_listen_state(listen_state_handle)

