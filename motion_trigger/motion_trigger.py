'''
Hacked from https://github.com/eifinger/appdaemon-scripts/blob/master/motionTrigger/motionTrigger.py

'''
import appdaemon.plugins.hass.hassapi as hass  # pylint: disable=import-error
import globals

class MotionTrigger(hass.Hass):
    def initialize(self):

        self.timer_handle = None
        self.listen_state_handle_list = []
        self.timer_handle_list = []

        self.sensors = globals.get_arg_list(self.args, "sensors")
        self.entities_on = globals.get_arg_list(self.args, "entities_on")
        self.entites_to_turned_on_by_script = {}

        try:
            self.delay = globals.get_arg(self.args, "delay")
            try:
                if self.delay.startswith("input_number"):
                    self.delay_entity = self.delay
                    self.delay = int(self.get_state(self.delay_entity).split(".")[0])
                    self.listen_state_handle_list.append(
                        self.listen_state(self.delay_changed, self.delay_entity)
                    )
            except AttributeError:  # does not have attribute 'startswith' -> is not of type string
                pass
            self.log("Delay changed to : {}".format(self.delay))
        except KeyError:
            self.delay = None

        for sensor in self.sensors:
            self.listen_state_handle_list.append(
                self.listen_state(self.state_changed, sensor)
            )

    def delay_changed(self, entity, attribute, old, new, kwargs):
        self.delay = int(self.get_state(self.delay_entity).split(".")[0])
        self.log("Delay changed to : {}".format(self.delay))

    def state_changed(self, entity, attribute, old, new, kwargs):
        # if self.get_state(self.app_switch) == "open":
        if new == "on":
            self.log(
                "Motion detected on sensor: {}".format(self.friendly_name(entity)),
                level="DEBUG",
            )
            turn_on = True

            if turn_on:
                for entity_on in self.entities_on:
                    if self.get_state(entity_on) == "off":
                        self.log("Motion detected: turning {} on".format(entity_on))
                        self.turn_on(entity_on)
                        self.entites_to_turned_on_by_script[entity_on] = True

                any_on_by_me = False
                for entity_on in self.entities_on:
                    if entity_on in self.entites_to_turned_on_by_script and self.entites_to_turned_on_by_script[entity_on]:
                        any_on_by_me = True
                        break

                if any_on_by_me:
                    delay = self.delay if self.delay is not None else 70
                    if self.timer_handle is not None:
                        self.log("Resetting timer")
                        self.timer_handle_list.remove(self.timer_handle)
                        self.cancel_timer(self.timer_handle)
                    self.log("Will turn off in {}s".format(delay))
                    self.timer_handle = self.run_in(self.turn_off_our_on_callback, delay)
                    self.timer_handle_list.append(self.timer_handle)

    def turn_off_our_on_callback(self, kwargs):
        turn_off = True
        # if self.entity_off is not None:
        #     for entity in self.turn_off_constraint_entities_off:
        #         entity_state = self.get_state(entity)
        #         if entity_state != "off":
        #             turn_off = False
        #             self.log("{} is still {}".format(entity, entity_state))
        #             break
        #     for entity in self.turn_off_constraint_entities_on:
        #         entity_state = self.get_state(entity)
        #         if entity_state != "on":
        #             turn_off = False
        #             self.log("{} is still {}".format(entity, entity_state))
        #             break
        #     if turn_off:
        #         self.log("Turning {} off".format(self.entity_off))
        #         self.turn_off(self.entity_off)
        #         self.turned_on_by_me = False
        # else:
        #     self.log("No entity_off defined", level="DEBUG")

        if turn_off:
            for entity_on in self.entities_on:
                if entity_on in self.entites_to_turned_on_by_script and self.entites_to_turned_on_by_script[entity_on] and self.get_state(entity_on) == "on":
                    self.turn_off(entity_on)
                    self.entites_to_turned_on_by_script[entity_on] = False

    def terminate(self):
        for timer_handle in self.timer_handle_list:
            self.cancel_timer(timer_handle)

        # for listen_event_handle in self.listen_event_handle_list:
        #     self.cancel_listen_event(listen_event_handle)

        for listen_state_handle in self.listen_state_handle_list:
            self.cancel_listen_state(listen_state_handle)