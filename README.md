# MATE Power Profile Switcher

A native MATE panel applet for switching between **Performance**, **Balanced**,
and **Power Saver**. With the included optional TuneD configuration, Performance
becomes **Max Power** on firmware that supports it.

The panel button shows the selected profile. Click it to open the menu;
right-click to move or remove it using MATE's normal panel controls.

![Applet with the optional Max Power configuration](docs/screenshot.png)

## Requirements

- MATE panel in an **X11** session. This out-of-process applet does not support
  Wayland.
- System Python 3 with PyGObject, GTK 3, and MatePanelApplet 4.0 introspection
  bindings. Scripts deliberately use `/usr/bin/python3` rather than a virtual
  environment or pyenv interpreter.
- A service providing `org.freedesktop.UPower.PowerProfiles` on the system D-Bus.
  Tested with **TuneD 2.28 + tuned-ppd**, MATE 1.28, and openSUSE Tumbleweed.

On the tested openSUSE system, relevant packages are `mate-panel`,
`python313-gobject`, `python313-gobject-Gdk`, `typelib-1_0-Gtk-3_0`,
`typelib-1_0-MatePanelApplet-4_0`, `tuned`, and `tuned-ppd`. Package names vary by
distribution and default Python version; install GI bindings through the system
package manager.

Other PowerProfiles providers exposing the same D-Bus interface should work, but
have not been tested. Unsupported profiles are disabled in the menu. The applet
only requests modes from the existing power service.

## Install

From a source checkout:

```sh
sudo bash ./install.sh
```

Then, as your normal desktop user:

```sh
/usr/bin/python3 /opt/mate-power-profile-switcher/panel-item.py
```

Alternatively, right-click the panel, choose **Add to Panel**, and add
**Power Profiles**. A panel restart or a new login may be needed for newly
registered applets to appear in that list.

The source and runtime are installed together in
`/opt/mate-power-profile-switcher`. Small registration files under
`/usr/share/mate-panel/applets` and `/usr/share/dbus-1/services` point there.
Installation does not change TuneD settings or the current power mode.

The applet runs as your desktop user. Your power service's authorization policy
determines whether profile changes require authentication. No new polkit rules
are installed.

## Optional: firmware Max Power with TuneD

This step is for machines whose firmware exposes `max-power`:

```sh
cat /sys/firmware/acpi/platform_profile_choices
```

The bundled example was tested on a Lenovo Legion R7000P ADR10. It uses a TuneD
profile named `legion-max-power`, based on `balanced`, with the CPU performance
preference, CPU boost enabled, and firmware `platform_profile=max-power`.

Review the example and setup script, then run:

```sh
sudo bash ./configure-tuned.sh
```

The script backs up existing TuneD configuration, maps Performance to
`legion-max-power`, enables TuneD at boot, and selects Max Power. Balanced and
Power Saver remain available. Max Power also applies on battery, increasing
power consumption and potentially fan noise. Firmware and thermal limits still
apply.

Reload the applet after changing the mapping: remove it from the panel and add
Power Profiles again. Its Performance label will become **Max Power**.
If `legion-max-power` is already configured, skip this setup.

To undo the optional setup, select a stock profile with
`sudo /usr/sbin/tuned-adm profile balanced`, stop `tuned-ppd`, restore the saved
`ppd.conf` and `ppd_base_profile` files from the backup directory printed by the
script, and start `tuned-ppd` again. Revert `tuned.service` enablement according
to the saved `tuned-enabled-state` if needed. The custom profile directory can
be removed after it is no longer active or referenced. Reload the applet again
to restore its standard Performance label.

## Update and uninstall

After changing the source checkout, run `sudo bash ./install.sh` again. Reload
the applet by removing it from the panel and adding Power Profiles again. MATE
saves the panel item; the power service manages the selected mode.

To uninstall, remove the panel item first, as your normal desktop user:

```sh
/usr/bin/python3 /opt/mate-power-profile-switcher/panel-item.py --remove
sudo bash /opt/mate-power-profile-switcher/uninstall.sh
```

Uninstallation removes the applet's known files. Additional files and TuneD
configuration are preserved.

## Diagnostics and development

```sh
# Read the selected mode without changing it.
/usr/bin/python3 ./power-profile-switcher.py --check

# Preview the same widget in a standalone GTK window.
/usr/bin/python3 ./power-profile-switcher.py --standalone

# Check syntax and exercise installation/uninstallation in temporary directories.
make check
```

`make check` does not require root or change panel or power settings. For package
staging, `DESTDIR=/absolute/staging/path bash ./install.sh` installs under that
directory while registration paths retain their final `/opt` locations.
`uninstall.sh` supports the same `DESTDIR`.

Develop in a writable Git checkout; `/opt` is the installed, root-owned copy.

## License

[MIT](LICENSE), copyright 2026 Alex01d.
