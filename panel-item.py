#!/usr/bin/python3
"""Add or remove this applet without changing any other MATE panel items."""
import sys

from gi.repository import Gio

OBJECT_ID = "local-power-profiles"
FACTORY_IID = "LocalPowerProfilesAppletFactory::PowerProfilesApplet"
panel = Gio.Settings.new("org.mate.panel")
ids = panel.get_strv("object-id-list")
settings = Gio.Settings.new_with_path(
    "org.mate.panel.object", f"/org/mate/panel/objects/{OBJECT_ID}/")

if "--remove" in sys.argv:
    panel.set_strv("object-id-list", [item for item in ids if item != OBJECT_ID])
    for key in settings.list_keys():
        settings.reset(key)
    Gio.Settings.sync()
    print("Power Profiles removed from the panel.")
else:
    if OBJECT_ID in ids:
        print("Power Profiles is already on the panel.")
        raise SystemExit(0)
    toplevels = panel.get_strv("toplevel-id-list")
    if not toplevels:
        raise SystemExit("No MATE panel was found.")
    # Place beside the existing notification area when there is one.
    toplevel, position, right_stick = toplevels[0], 50, True
    for object_id in ids:
        existing = Gio.Settings.new_with_path(
            "org.mate.panel.object", f"/org/mate/panel/objects/{object_id}/")
        if existing.get_string("applet-iid") == "NotificationAreaAppletFactory::NotificationArea":
            toplevel = existing.get_string("toplevel-id")
            right_stick = existing.get_boolean("panel-right-stick")
            position = existing.get_int("position") + 10
            break
    settings.delay()
    settings.set_string("object-type", "applet")
    settings.set_string("toplevel-id", toplevel)
    settings.set_string("applet-iid", FACTORY_IID)
    settings.set_int("position", position)
    settings.set_boolean("panel-right-stick", right_stick)
    settings.set_boolean("locked", False)
    settings.apply()
    Gio.Settings.sync()
    panel.set_strv("object-id-list", ids + [OBJECT_ID])
    Gio.Settings.sync()
    print(f"Added Power Profiles to panel {toplevel} beside the notification area.")
