#!/usr/bin/python3
"""A MATE panel menu backed by the existing TuneD PowerProfiles interface."""

import configparser
import json
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("MatePanelApplet", "4.0")
from gi.repository import Gio, GLib, Gtk, MatePanelApplet


FACTORY = "LocalPowerProfilesAppletFactory"
APPLET = "PowerProfilesApplet"
BUS_NAME = "org.freedesktop.UPower.PowerProfiles"
OBJECT_PATH = "/org/freedesktop/UPower/PowerProfiles"
INTERFACE = BUS_NAME
def max_power_configured():
    """Recognize the optional TuneD mapping shipped with this project."""
    config = configparser.ConfigParser()
    try:
        config.read("/etc/tuned/ppd.conf")
        return config.get("profiles", "performance", fallback="") == "legion-max-power"
    except (configparser.Error, OSError):
        return False


MAX_POWER = max_power_configured()
MODES = {
    "performance": ("Max Power" if MAX_POWER else "Performance",
                    "power-profile-performance-symbolic",
                    "Favor performance over energy savings."),
    "balanced": ("Balanced", "power-profile-balanced-symbolic",
                 "Balance performance and energy use."),
    "power-saver": ("Power Saver", "power-profile-power-saver-symbolic",
                    "Reduce power use and extend battery life."),
}


def connect_service():
    return Gio.DBusProxy.new_for_bus_sync(
        Gio.BusType.SYSTEM, Gio.DBusProxyFlags.NONE, None,
        BUS_NAME, OBJECT_PATH, INTERFACE, None,
    )


def firmware_profile():
    try:
        return Path("/sys/firmware/acpi/platform_profile").read_text().strip()
    except OSError:
        return "unavailable"


class ProfileSwitcher(Gtk.MenuButton):
    def __init__(self):
        super().__init__()
        self.proxy = None
        self.busy = False
        self.syncing = False
        self.closed = False
        self.timer = None
        self.signal_handlers = []
        self.last_error = None
        self.set_relief(Gtk.ReliefStyle.NONE)
        self.set_focus_on_click(False)
        self.get_accessible().set_name("Power profile switcher")

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.image = Gtk.Image.new_from_icon_name(
            "power-profile-balanced-symbolic", Gtk.IconSize.MENU)
        self.label = Gtk.Label(label="Power Profile")
        box.pack_start(self.image, False, False, 0)
        box.pack_start(self.label, False, False, 0)
        self.add(box)

        self.menu = Gtk.Menu()
        title = Gtk.MenuItem(label="Power Profile")
        title.set_sensitive(False)
        self.menu.append(title)
        self.menu.append(Gtk.SeparatorMenuItem())
        self.items = {}
        group = None
        for mode, (name, _icon, description) in MODES.items():
            item = Gtk.RadioMenuItem.new_with_label_from_widget(group, name)
            group = item
            item.set_tooltip_text(description)
            item.connect("activate", self._activate, mode)
            self.items[mode] = item
            self.menu.append(item)
        self.menu.show_all()
        self.set_popup(self.menu)
        self.menu.connect("show", lambda *_: self.refresh())
        self.connect("destroy", self._destroy)
        self.refresh()
        self.timer = GLib.timeout_add_seconds(5, self.refresh)
        self.show_all()

    def _destroy(self, *_args):
        self.closed = True
        if self.timer:
            GLib.source_remove(self.timer)
            self.timer = None
        if self.proxy:
            for handler in self.signal_handlers:
                self.proxy.disconnect(handler)
            self.signal_handlers.clear()

    def refresh(self):
        if self.closed:
            return GLib.SOURCE_REMOVE
        try:
            if self.proxy is None:
                self.proxy = connect_service()
                self.signal_handlers = [
                    self.proxy.connect("g-properties-changed", self._changed),
                    self.proxy.connect("notify::g-name-owner", self._changed),
                ]
            if not self.proxy.get_name_owner():
                raise RuntimeError("The power profile service is unavailable.")
            value = self.proxy.get_cached_property("ActiveProfile")
            active = value.unpack() if value else None
            profiles = self.proxy.get_cached_property("Profiles")
            available = {entry["Profile"] for entry in profiles.unpack()} if profiles else set()
            name, icon, description = MODES.get(
                active, ("Custom", "preferences-system-power-symbolic",
                         "A custom power profile is selected."))
            self.syncing = True
            try:
                for mode, item in self.items.items():
                    item.set_active(mode == active)
                    item.set_sensitive(not self.busy and mode in available)
            finally:
                self.syncing = False
            self.label.set_text("Switching…" if self.busy else name)
            self.image.set_from_icon_name(icon, Gtk.IconSize.MENU)
            self.set_tooltip_text(f"{name}: {description}\nClick to change power profile.")
            self.last_error = None
        except (GLib.Error, RuntimeError) as error:
            self.label.set_text("Power Unavailable")
            self.set_tooltip_text(str(error))
            for item in self.items.values():
                item.set_sensitive(False)
            self.last_error = str(error)
        return GLib.SOURCE_CONTINUE

    def _changed(self, *_args):
        self.refresh()

    def _activate(self, item, mode):
        if self.syncing or self.busy or not item.get_active():
            return
        self.select(mode)

    def select(self, mode, finished=None):
        """Change mode asynchronously; used by the menu and validation."""
        if mode not in MODES or self.proxy is None or self.busy:
            return
        self.busy = True
        self.refresh()

        def completed(connection, result, _data):
            error_message = None
            try:
                connection.call_finish(result)
            except GLib.Error as error:
                error_message = error.message
            self.busy = False
            if self.closed:
                return
            self.refresh()
            if error_message:
                self.last_error = error_message
                if finished is None:
                    dialog = Gtk.MessageDialog(
                        message_type=Gtk.MessageType.ERROR,
                        buttons=Gtk.ButtonsType.CLOSE,
                        text="Could not change power profile",
                    )
                    dialog.format_secondary_text(error_message)
                    dialog.connect("response", lambda dialog, _response: dialog.destroy())
                    dialog.show_all()
            if finished:
                finished(error_message)

        self.proxy.get_connection().call(
            BUS_NAME, OBJECT_PATH, "org.freedesktop.DBus.Properties", "Set",
            GLib.Variant("(ssv)", (INTERFACE, "ActiveProfile", GLib.Variant("s", mode))),
            None, Gio.DBusCallFlags.ALLOW_INTERACTIVE_AUTHORIZATION,
            30000, None, completed, None,
        )


def factory(applet, iid, _data):
    if iid != APPLET:
        return False
    switcher = ProfileSwitcher()
    applet.set_flags(MatePanelApplet.AppletFlags.EXPAND_MINOR)
    applet.set_background_widget(applet)
    applet.add(switcher)

    def orient_changed(_applet, orientation):
        switcher.label.set_visible(orientation in (
            MatePanelApplet.AppletOrient.UP, MatePanelApplet.AppletOrient.DOWN))

    applet.connect("change-orient", orient_changed)
    applet.show_all()
    orient_changed(applet, applet.get_orient())
    return True


if __name__ == "__main__":
    if "--check" in sys.argv:
        proxy = connect_service()
        print(json.dumps({
            "active": proxy.get_cached_property("ActiveProfile").unpack(),
            "firmware": firmware_profile(),
            "choices": [entry[0] for entry in MODES.values()],
        }, indent=2))
    elif "--standalone" in sys.argv:
        window = Gtk.Window(title="Power Profiles")
        window.add(ProfileSwitcher())
        window.connect("destroy", Gtk.main_quit)
        window.show_all()
        Gtk.main()
    else:
        Gtk.init(None)
        raise SystemExit(MatePanelApplet.Applet.factory_main(
            FACTORY, True, MatePanelApplet.Applet.__gtype__, factory, None))
