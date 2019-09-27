import appdaemon.plugins.hass.hassapi as hass  # pylint: disable=import-error
import globals

class LightifySwitch(hass.Hass):
    def initialize(self):

        self.switch_ieee = globals.get_arg(self.args, "switch_ieee")

        self.turn_on_top_left_presses_lists = {}
        self.turn_on_bottom_left_presses_lists = {}
        for i in [1,2,3]:
            self.turn_on_top_left_presses_lists[i] = globals.get_arg_list(self.args, "turn_on_top_left_presses_{}".format(i), allow_empty=True)
            self.turn_on_bottom_left_presses_lists[i] = globals.get_arg_list(self.args, "turn_on_bottom_left_presses_{}".format(i), allow_empty=True)

        self.turn_on_top_left_hold_list = globals.get_arg_list(self.args, "turn_on_top_left_hold")
        self.turn_on_bottom_left_hold_list = globals.get_arg_list(self.args, "turn_on_bottom_left_hold")

        self.multi_click_delay = 2 # 1 second seems to get stuck in multithreads
        self.multi_press_timer_handle = None
        self.multi_press_timer_handle_list = []
        self.top_presses = 0
        self.bottom_presses = 0

        self.listen_event_handle_list = []
        self.listen_event_handle_list.append(self.listen_event_switch(self.on_top_left_press, "on"))
        self.listen_event_handle_list.append(self.listen_event_switch(self.on_bottom_left_press, "off"))
        self.listen_event_handle_list.append(self.listen_event_switch(self.on_top_left_hold, "move_with_on_off"))
        self.listen_event_handle_list.append(self.listen_event_switch(self.on_bottom_left_hold, "move"))

    def listen_event_switch(self, callback, command):
        return self.listen_event(callback, "zha_event", command=command, device_ieee=self.switch_ieee)

    def on_top_left_press(self, event_name, data, kwargs):
        if self.multi_press_timer_handle is not None:
            self.multi_press_timer_handle_list.remove(self.multi_press_timer_handle)
            self.cancel_timer(self.multi_press_timer_handle)
        self.top_presses += 1

        self.log(self.top_presses)
        self.multi_press_timer_handle = self.run_in(self.turn_on_top_left_press_entities, self.multi_click_delay)
        self.multi_press_timer_handle_list.append(self.multi_press_timer_handle)
        
    def turn_on_top_left_press_entities(self, kwargs):
        self.log("turn_on_top_left_press_entities : {}".format(self.top_presses))
        entities = self.turn_on_top_left_presses_lists[self.top_presses]
        if entities is not None:
            for entity in entities:
                self.turn_on(entity)
        self.top_presses = 0

    def on_bottom_left_press(self, event_name, data, kwargs):
        if self.multi_press_timer_handle is not None:
            self.multi_press_timer_handle_list.remove(self.multi_press_timer_handle)
            self.cancel_timer(self.multi_press_timer_handle)
        self.bottom_presses += 1

        self.log(self.bottom_presses)
        self.multi_press_timer_handle = self.run_in(self.turn_on_bottom_left_press_entities, self.multi_click_delay)
        self.multi_press_timer_handle_list.append(self.multi_press_timer_handle)
        
    def turn_on_bottom_left_press_entities(self, kwargs):
        self.log("turn_on_bottom_left_press_entities : {}".format(self.bottom_presses))
        entities = self.turn_on_bottom_left_presses_lists[self.bottom_presses]
        if entities is not None:
            for entity in entities:
                self.turn_on(entity)
        self.bottom_presses = 0

    def on_top_left_hold(self, event_name, data, kwargs):
        for entity in self.turn_on_top_left_hold_list:
            self.turn_on(entity)

    def on_bottom_left_hold(self, event_name, data, kwargs):
        for entity in self.turn_on_bottom_left_hold_list:
            self.turn_on(entity)

    def terminate(self):
        for listen_event_handle in self.listen_event_handle_list:
            self.cancel_listen_event(listen_event_handle)

        for timer_handle in self.multi_press_timer_handle_list:
            self.cancel_timer(timer_handle)


        # {
        #     "event_type": "zha_event",
        #     "data": {
        #         "unique_id": "0xc907:1:0x0006",
        #         "device_ieee": "00:0d:6f:00:0e:c9:01:85",
        #         "command": "on",
        #         "args": []
        #     },
        #     "origin": "LOCAL",
        #     "time_fired": "2019-08-28T04:20:58.896630+00:00",
        #     "context": {
        #         "id": "1ec6ccec1651455eb0b98162c6a0298a",
        #         "parent_id": null,
        #         "user_id": null
        #     }
        # }

        # self.timer_handle = None
        # self.listen_state_handle_list = []
        # self.timer_handle_list = []

        # self.sensors = globals.get_arg_list(self.args, "sensors")
        # self.entities_on = globals.get_arg_list(self.args, "entities_on")
        # self.entites_to_turned_on_by_script = {}

        # try:
        #     self.delay = globals.get_arg(self.args, "delay")
        #     try:
        #         if self.delay.startswith("input_number"):
        #             self.delay_entity = self.delay
        #             self.delay = int(self.get_state(self.delay_entity).split(".")[0])
        #             self.listen_state_handle_list.append(
        #                 self.listen_state(self.delay_changed, self.delay_entity)
        #             )
        #     except AttributeError:  # does not have attribute 'startswith' -> is not of type string
        #         pass
        #     self.log("Delay changed to : {}".format(self.delay))
        # except KeyError:
        #     self.delay = None

        # for sensor in self.sensors:
        #     self.listen_state_handle_list.append(
        #         self.listen_state(self.state_changed, sensor)
        #     )

    # def delay_changed(self, entity, attribute, old, new, kwargs):
    #     self.delay = int(self.get_state(self.delay_entity).split(".")[0])
    #     self.log("Delay changed to : {}".format(self.delay))

    # def state_changed(self, entity, attribute, old, new, kwargs):
    #     # if self.get_state(self.app_switch) == "open":
    #     if new == "on":
    #         self.log(
    #             "Motion detected on sensor: {}".format(self.friendly_name(entity)),
    #             level="DEBUG",
    #         )
    #         turn_on = True

    #         if turn_on:
    #             for entity_on in self.entities_on:
    #                 if self.get_state(entity_on) == "off":
    #                     self.log("Motion detected: turning {} on".format(entity_on))
    #                     self.turn_on(entity_on)
    #                     self.entites_to_turned_on_by_script[entity_on] = True

    #             any_on_by_me = False
    #             for entity_on in self.entities_on:
    #                 if self.entites_to_turned_on_by_script[entity_on]:
    #                     any_on_by_me = True
    #                     break

    #             if any_on_by_me:
    #                 delay = self.delay if self.delay is not None else 70
    #                 if self.timer_handle is not None:
    #                     self.log("Resetting timer")
    #                     self.timer_handle_list.remove(self.timer_handle)
    #                     self.cancel_timer(self.timer_handle)
    #                 self.log("Will turn off in {}s".format(delay))
    #                 self.timer_handle = self.run_in(self.turn_off_our_on_callback, delay)
    #                 self.timer_handle_list.append(self.timer_handle)

    # def turn_off_our_on_callback(self, kwargs):
    #     turn_off = True
    #     # if self.entity_off is not None:
    #     #     for entity in self.turn_off_constraint_entities_off:
    #     #         entity_state = self.get_state(entity)
    #     #         if entity_state != "off":
    #     #             turn_off = False
    #     #             self.log("{} is still {}".format(entity, entity_state))
    #     #             break
    #     #     for entity in self.turn_off_constraint_entities_on:
    #     #         entity_state = self.get_state(entity)
    #     #         if entity_state != "on":
    #     #             turn_off = False
    #     #             self.log("{} is still {}".format(entity, entity_state))
    #     #             break
    #     #     if turn_off:
    #     #         self.log("Turning {} off".format(self.entity_off))
    #     #         self.turn_off(self.entity_off)
    #     #         self.turned_on_by_me = False
    #     # else:
    #     #     self.log("No entity_off defined", level="DEBUG")

    #     if turn_off:
    #         for entity_on in self.entities_on:
    #             if self.entites_to_turned_on_by_script[entity_on] and self.get_state(entity_on) == "on":
    #                 self.turn_off(entity_on)
    #                 self.entites_to_turned_on_by_script[entity_on] = False

    # def terminate(self):
    #     for timer_handle in self.timer_handle_list:
    #         self.cancel_timer(timer_handle)

    #     # for listen_event_handle in self.listen_event_handle_list:
    #     #     self.cancel_listen_event(listen_event_handle)

    #     for listen_state_handle in self.listen_state_handle_list:
    #         self.cancel_listen_state(listen_state_handle)

