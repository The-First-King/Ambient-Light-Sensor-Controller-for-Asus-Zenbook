import time
import math
import os
import subprocess

# Path to read the Ambient Light Sensor (ALS) value (lux)
ALS_PATH = "/sys/devices/LNXSYSTM:00/LNXSYBUS:00/ACPI0008:00/ali"
# Path to write the backlight brightness value
BRIGHTNESS_PATH = "/sys/class/backlight/intel_backlight/brightness"
# Path for Keyboard Backlight Control
KB_BACKLIGHT_PATH = "/sys/class/leds/asus::kbd_backlight/brightness"
# Path to check the current power supply status (AC present/online status)
POWER_SUPPLY_STATUS_PATH = "/sys/class/power_supply/AC0/online"

# Software Toggle Flag File
ALS_SOFTWARE_FLAG_PATH = os.path.expanduser("~/.als_controller_state")

# Inactivity Dimming Configuration (120 seconds in milliseconds)
INACTIVITY_DIM_TIMEOUT_MS = 120000
# Target low brightness level as a percentage (1% of BRIGHTNESS_MAX)
INACTIVITY_DIM_BRIGHTNESS_PERCENT = 1

# Keyboard Backlight Inactivity Configuration (5 minutes in milliseconds)
KB_INACTIVITY_TIMEOUT_MS = 300000

# System Constraints
LUX_MAX = 6159.0
BRIGHTNESS_MAX = 820.0
BRIGHTNESS_MIN = 82.0
STEP_SIZE = 82.0

# Algorithm Parameter (Power Law Exponent)
POWER_EXPONENT = 0.3

# Keyboard Backlight Trigger
KB_LUX_THRESHOLD = 1.0

# Smooth Transition Parameters
FADE_DURATION = 2.0
FADE_STEPS = 50

# How often to check the sensor (seconds)
CHECK_INTERVAL = 5

ALS_READ_COUNT = 3
ALS_READ_DELAY = 0.5
HYSTERESIS_THRESHOLD = STEP_SIZE * 1.5 

def _write_brightness(level):
    """Helper to safely write the brightness level to the file."""
    try:
        with open(BRIGHTNESS_PATH, 'w') as f:
            f.write(str(int(level)))
    except PermissionError:
        print(f"\n*** FATAL ERROR: Permission denied during fade. Run script with 'sudo python3 als-controller.py' ***")
        exit(1)
    except Exception:
        # Suppress writing errors during fast fade to prevent console spam
        pass

def fade_brightness(start_level, end_level):
    """Linearly fades the brightness from start_level to end_level over FADE_DURATION."""
    if start_level == end_level:
        return

    brightness_diff = end_level - start_level
    
    num_steps = FADE_STEPS
    
    if abs(brightness_diff) < FADE_STEPS:
        num_steps = abs(brightness_diff)
        if num_steps == 0:
            num_steps = 1

    brightness_increment = brightness_diff / num_steps
    step_delay = FADE_DURATION / num_steps

    for i in range(1, num_steps + 1):
        intermediate_level = start_level + (i * brightness_increment)
        
        if i == num_steps:
            _write_brightness(end_level)
        else:
            _write_brightness(round(intermediate_level))
        
        time.sleep(step_delay)

def is_on_battery():
    """Reads the AC online status to check if the laptop is running on battery."""
    try:
        if os.path.exists(POWER_SUPPLY_STATUS_PATH):
            with open(POWER_SUPPLY_STATUS_PATH, 'r') as f:
                # '1' = AC connected; '0' = On Battery
                status = f.read().strip()
                return status == '0' # True if on battery
        
        return False
    except FileNotFoundError:
        print(f"Warning: Power supply status file not found at {POWER_SUPPLY_STATUS_PATH}. Assuming AC connected.")
        return False
    except Exception as e:
        print(f"Error reading power supply status: {e}. Assuming AC connected.")
        return False

def calculate_brightness(current_lux):
    """
    Calculates the target discrete brightness level using a power law mapping.
    """
    lux = max(0.0, min(current_lux, LUX_MAX))

    if lux <= 1:
        b_target = BRIGHTNESS_MIN
    else:
        normalized_lux_power = math.pow(lux / LUX_MAX, POWER_EXPONENT)
        b_target = BRIGHTNESS_MIN + (BRIGHTNESS_MAX - BRIGHTNESS_MIN) * normalized_lux_power

    num_steps = round(b_target / STEP_SIZE)
    num_steps = max(1, min(10, num_steps))
    
    discrete_brightness = int(num_steps * STEP_SIZE)

    return discrete_brightness

def read_als_value():
    """Reads the current ambient light value from the system file."""
    try:
        with open(ALS_PATH, 'r') as f:
            return float(f.read().strip())
    except Exception:
        return 0.0

def read_stabilized_lux():
    """Reads the ALS value multiple times with a short delay and returns the average."""
    readings = []
    for _ in range(ALS_READ_COUNT):
        readings.append(read_als_value())
        time.sleep(ALS_READ_DELAY)
    
    # Calculate and return the average lux value
    return sum(readings) / len(readings)

def read_als_enable_state():
    """Reads the current enable state (1 or 0) from the software flag file."""
    try:
        if os.path.exists(ALS_SOFTWARE_FLAG_PATH):
            with open(ALS_SOFTWARE_FLAG_PATH, 'r') as f:
                content = f.read().strip()
                return 1 if content == '1' else 0
        return 1
    except Exception as e:
        print(f"Error reading ALS software flag: {e}. Assuming enabled (1).")
        return 1

def read_current_brightness():
    """Reads the current brightness value from the system file."""
    try:
        with open(BRIGHTNESS_PATH, 'r') as f:
            return int(f.read().strip())
    except Exception:
        return -1

def read_idle_time_ms():
    """Reads the time since the last user activity in milliseconds."""
    try:
        result = subprocess.run(
            ["xprintidle"],
            capture_output=True,
            text=True,
            check=True,
            timeout=1
        )
        return int(result.stdout.strip())
    except FileNotFoundError:
        print("Error: 'xprintidle' command not found. Cannot check for user inactivity.")
        return 0
    except subprocess.CalledProcessError:
        print("Warning: 'xprintidle' failed (X server issue?). Assuming active.")
        return 0
    except Exception as e:
        print(f"Error checking idle time: {e}")
        return 0

def send_notification(brightness_level, lux):
    """Sends a desktop notification using 'notify-send'."""
    percent_value = max(10, min(100, int((brightness_level / BRIGHTNESS_MAX) * 100)))

    try:
        subprocess.run([
            "notify-send", 
            "Brightness Updated", 
            f"Set to {brightness_level} (Lux: {lux:.0f})",
            f"--hint=int:value:{percent_value}",
            "--hint=string:x-canonical-private-icon:display-brightness",
            "--expire-time=1500"
        ], check=True)
    except FileNotFoundError:
        print("\nWarning: 'notify-send' command not found.")
    except Exception as e:
        print(f"Error sending notification: {e}")

def set_keyboard_backlight(current_lux, forced_state=None):
    """Controls the keyboard backlight (ON if lux is low, OFF otherwise, or forced)."""
    
    if forced_state is not None:
        target_state = forced_state
        reason = "Forced"
    else:
        target_state = 0
        reason = "ALS"
        if current_lux <= KB_LUX_THRESHOLD: 
            target_state = 1
    
    try:
        current_state = 0
        if os.path.exists(KB_BACKLIGHT_PATH):
            with open(KB_BACKLIGHT_PATH, 'r') as f:
                current_state = int(f.read().strip())
        
        if current_state != target_state:
            with open(KB_BACKLIGHT_PATH, 'w') as f:
                f.write(str(target_state))
            print(f"Keyboard Backlight ({reason}) set to: {'ON' if target_state == 1 else 'OFF'}")

    except FileNotFoundError:
        pass 
    except PermissionError:
        print(f"Warning: Permission denied when setting keyboard backlight. (Path: {KB_BACKLIGHT_PATH})")
    except Exception as e:
        print(f"Error controlling keyboard backlight: {e}")
            
def set_brightness(target_brightness, current_brightness, lux):
    """Fades brightness, sends notification, and updates KB backlight."""
    try:
        # 1. Fade LCD Brightness
        fade_brightness(current_brightness, target_brightness)
        
        # 2. Send the desktop notification
        if lux is not None:
            send_notification(target_brightness, lux)
        
        # 3. Control Keyboard Backlight 
        if lux is not None:
            set_keyboard_backlight(lux)

    except PermissionError:
        print(f"\n*** FATAL ERROR: Permission denied. Run script with 'sudo python3 als-controller.py' ***")
        exit(1)
    except Exception as e:
        print(f"Error writing brightness value: {e}")

def main():
    """Main loop for the auto-brightness controller."""
    print(f"Starting auto-brightness controller. Checking every {CHECK_INTERVAL} seconds.")
    print(f"ALS Path: {ALS_PATH}")
    print(f"Power Status Path: {POWER_SUPPLY_STATUS_PATH}")
    print(f"Brightness Path: {BRIGHTNESS_PATH}")
    print(f"Fade Duration: {FADE_DURATION} seconds.")
    print(f"Inactivity Dim Threshold (LCD): {INACTIVITY_DIM_TIMEOUT_MS/1000} seconds.")
    print(f"KB Inactivity Timeout (KB): {KB_INACTIVITY_TIMEOUT_MS/1000} seconds.") 
    print(f"KB Backlight Lux Threshold: {KB_LUX_THRESHOLD} lux.") 
    print(f"Hysteresis Threshold: {HYSTERESIS_THRESHOLD:.2f} brightness units.") # New output
    
    if os.geteuid() != 0:
        print("\n*** WARNING: This script should be run with root privileges (sudo). ***")
        
    while True:
        is_enabled = read_als_enable_state()
        
        if is_enabled == 1:
            # Read stabilized lux value
            lux = read_stabilized_lux() 
            current_brightness = read_current_brightness()
            idle_time_ms = read_idle_time_ms()
            
            # Check 1: Inactivity Control (ON BATTERY ONLY)
            
            if is_on_battery(): 
                
                if idle_time_ms > INACTIVITY_DIM_TIMEOUT_MS:
                    dim_target = int(BRIGHTNESS_MAX * (INACTIVITY_DIM_BRIGHTNESS_PERCENT / 100.0))
                    target_brightness = max(dim_target, int(BRIGHTNESS_MIN))

                    if target_brightness != current_brightness:
                        print(f"*** ON BATTERY: Inactive for {idle_time_ms//1000}s. Dimming LCD to {target_brightness}. ***")
                        set_brightness(target_brightness, current_brightness, lux=None)
                    else:
                        print(f"ON BATTERY: Inactive for {idle_time_ms//1000}s. LCD already dimmed to {current_brightness}.")
                    
                    if idle_time_ms > KB_INACTIVITY_TIMEOUT_MS:
                        print(f"*** ON BATTERY: Idle > 5min. Turning KB Backlight OFF. ***")
                        set_keyboard_backlight(current_lux=lux, forced_state=0)
                    
                    time.sleep(CHECK_INTERVAL)
                    continue 
                else:
                    print(f"ON BATTERY: Active (Idle: {idle_time_ms//1000}s). Checking ALS...")
            else:
                print("ON AC: Inactivity dimming/KB-off bypassed. Checking ALS...")
                
            # Check 2: ALS Calculation (Runs if active OR on AC)
            target_brightness = calculate_brightness(lux)
            
            # Hysteresis Check
            brightness_difference = abs(target_brightness - current_brightness)

            if brightness_difference >= HYSTERESIS_THRESHOLD:
                print(f"ALS: {lux:.2f} lux. Target: {target_brightness}. Current: {current_brightness}. Diff ({brightness_difference:.2f}) > Threshold ({HYSTERESIS_THRESHOLD:.2f}). Updating...")
                set_brightness(target_brightness, current_brightness, lux=lux)
            else:
                print(f"ALS: {lux:.2f} lux. Target: {target_brightness}. Current: {current_brightness}. Change too small ({brightness_difference:.2f}). No update.")
                set_keyboard_backlight(lux)
                
        else:
            print("Auto-brightness control is currently DISABLED by user hotkey.")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAuto-brightness controller stopped by user.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
