# Short Description

The three files together implement an automatic brightness controller for Asus Zenbook laptops. The Python script (als-controller.py) continuously reads the ambient light sensor and adjusts screen brightness accordingly. The shell script (als_toggle.sh) provides a simple on/off toggle for enabling or disabling the controller. The systemd service file (als-controller.service) ensures the Python controller runs automatically in the background at startup.

# ALS Controller Functionality Breakdown

1. als-controller.py

    Purpose: Core controller that manages brightness based on ambient light.

    How it works:

    * Reads values from the laptop’s ambient light sensor.

    * Maps sensor readings to appropriate screen brightness levels.

	* In the dark environment, the keyboard backlight is turning on automatically and turning off when not needed.

	* Continuously monitors changes in light and updates brightness dynamically.

	* Includes smoothing logic (to avoid flickering) and clamps brightness within safe min/max ranges.

	* Automatically reduces screen brightness to a lower value on inactivity after 2 minutes when the laptop is running on battery. If the keyboard backlight is on, then it is going to be turned off automatically in 5 minutes of inactivity.

    Effect: Your screen brightness automatically adapts to the environment — dimmer in dark rooms, brighter in sunlight.
	
2. als_toggle.sh

    Purpose: Quick toggle utility for the controller.

    How it works:

    * It is using a software toggle flag file logic for the als-controller.py main script to have ability to quickly enable/disable ALS controller.

    Effect: Acts like a manual switch so the user can override automatic brightness control easily.
	
3. als-controller.service

    Purpose: systemd unit file to manage the controller as a background service.

    How it works:

    * Defines the service name (als-controller).

    * Specifies that it should run als-controller.py at startup.

    * Keeps the process alive and restarts it if it crashes.

    * Allows integration with systemctl commands (start, stop, enable, disable).

    Effect: Ensures the ambient light controller runs automatically and reliably in the background, without requiring manual execution.
	
All together, they provide a complete auto-brightness solution. The Python script does the actual work. The service ensures it runs continuously. The shell script gives you manual control.

# Tested Platforms

* Xubuntu 20.04 (Linux 5.15.0) running on Asus UX32.
* Xubuntu 24.04 (Linux 6.14.0) running on Asus UX32.

In theory, it should work on other Ultrabooks in this series where the same ALS driver is used.

# Recommended XFCE Power Manager Display Settings

The script has been designed to be applied to the following settings when running on battery:

<div align="center">
<img src="https://github.com/The-First-King/Ambient-Light-Sensor-Controller-for-Asus-Zenbook/blob/main/XFCE%20Power%20Manager%20Display%20settings.png?raw=true" alt="XFCE Power Manager Display settings" />
</div>

# Installation Steps

By default, Ubuntu releases do not include the ALS driver to support the ALS sensor on Asus Zenbooks. The first step can be skipped if the driver is already installed.

1. Installation of the ALS Driver provided by [danieleds](https://github.com/danieleds).

   The best way is to use installation with DKMS. This allows to keep the driver across multiple kernel upgrades in the future.

   <pre>
   sudo -i
   cd /usr/src && wget https://github.com/danieleds/als/archive/master.tar.gz && tar xvf master.tar.gz && rm master.tar.gz
   dkms add -m als -v master
   dkms install -m als -v master
   echo als >>/etc/modules
   exit
   </pre>
   
    Note: After the kernel upgrade, the driver reverts to a disabled state. To re-enable it, use the following command.
	
	<pre>
	echo 1 | sudo tee /sys/bus/acpi/devices/ACPI0008:00/enable > /dev/null
    </pre>
	
2. Downloading als-controller.py and als_toggle.sh scripts to home directory.

   <pre>
   wget https://raw.githubusercontent.com/The-First-King/Ambient-Light-Sensor-Controller-for-Asus-Zenbook/main/als-controller.py && wget https://raw.githubusercontent.com/The-First-King/Ambient-Light-Sensor-Controller-for-Asus-Zenbook/main/als_toggle.sh
   </pre>

3. Create a systemd service.

   <pre>
   sudo -i
   cd /etc/systemd/system && wget https://raw.githubusercontent.com/The-First-King/Ambient-Light-Sensor-Controller-for-Asus-Zenbook/refs/heads/main/als-controller.service
   </pre>

   Change the username in lines 9 and 12, and save the changes before closing the file:

   <pre>
   nano als-controller.service
   </pre>

   To start a service:

   <pre>
   systemctl daemon-reload
   systemctl start als-controller.service
   systemctl enable als-controller.service
   exit
   </pre>

4. The Fn+A hotkey does not work because Asus only provides support for it on Windows through proprietary drivers and ACPI event handling. Linux does not include a native handler for that key combination, so pressing Fn+A generates no recognized event. To enable or disable the ALS under Xubuntu, you need to map a different key sequence, for example Super+A.

   Go to **Settings Manager** → **Keyboard** → **Application Shortcuts** → **Add**, and in the command field select the path to als_toggle.sh.

# Uninstallation Steps

1. Stop and remove the service.

   <pre>
   sudo systemctl stop als-controller.service
   sudo rm /etc/systemd/system/als-controller.service
   </pre>

2. Removing als-controller.py and als_toggle.sh scripts from home directory.

   <pre>
   rm als-controller.py
   rm als_toggle.sh
   </pre>
   
3. Removing ALS Driver.

   <pre>
   sudo dkms remove -m als -v master --all
   sudo rm -r /usr/src/als-master
   </pre>
