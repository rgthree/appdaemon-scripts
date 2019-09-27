import appdaemon.plugins.hass.hassapi as hass  # pylint: disable=import-error
import globals


class BinarySensor(hass.Hass):
    def initialize(self):

        self.isInitialized = "trigger" in self.args
        if not self.isInitialized:
          self.log("Skipping setup, no trigger.")
          return

        self.timer_handle = None
        self.listen_state_handle_list = []
        self.timer_handle_list = []

        self.app_switch = globals.get_arg(self.args, "app_switch", allow_empty = True)

        self.sensors = globals.get_arg_list(self.args, "sensors")
        self.entities_on = globals.get_arg_list(self.args, "entities_on", allow_empty = True)
        self.entities_off = globals.get_arg_list(self.args, "entities_off", allow_empty = True)
        self.services = globals.get_arg_list(self.args, "services", allow_empty = True)
        self.trigger = globals.get_arg(self.args, "trigger")

        for sensor in self.sensors:
            self.listen_state_handle_list.append(
                self.listen_state(self.state_changed, sensor)
            )


    def state_changed(self, entity, attribute, old, new, kwargs):
        if self.app_switch is not None and self.get_state(self.app_switch) != "on":
            self.log("Switch is not on, skipping update_color.")
            return

        if self.trigger == new:
            do_work = True # TODO: Check if a switch is off to disable
            if do_work:
                for entity_on in self.entities_on:
                    if self.get_state(entity_on) == "off":
                        self.turn_on(entity_on)
                for entity_off in self.entities_off:
                    if self.get_state(entity_off) == "on":
                        self.turn_off(entity_off)
                for service in self.services:
                    self.call_service(globals.get_arg(service, "service"),
                        title = globals.get_arg(service, "title", allow_empty = True, default_value = ""),
                        message = globals.get_arg(service, "message", allow_empty = True, default_value = "")
                    )

    def terminate(self):
        if not self.isInitialized:
          return

        for listen_state_handle in self.listen_state_handle_list:
            self.cancel_listen_state(listen_state_handle)