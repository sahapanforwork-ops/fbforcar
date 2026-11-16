import subprocess
import platform
import pyperclip

# ฟังก์ชันดึง Hardware ID
def get_hardware_id():
    system = platform.system().lower()
    if system == "windows":
        # Windows 11 รุ่นใหม่ไม่มี wmic แล้ว ใช้ PowerShell อ่าน Serial เมนบอร์ดค่าเดียวกันแทน
        command = ['powershell', '-NoProfile', '-Command', '(Get-CimInstance Win32_BaseBoard).SerialNumber']
        try:
            result = subprocess.check_output(
                command, timeout=30, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            ).decode(errors="ignore").strip()
            return result if result else "Not Available"
        except Exception:
            return "Not Available"
    elif system == "darwin":
        command = 'system_profiler SPHardwareDataType | grep "Hardware UUID"'
        try:
            result = subprocess.check_output(command, shell=True).decode().strip()
            return result.split(":")[1].strip() if result else "Not Available"
        except Exception:
            return "Not Available"
    return "Not Available"

# ฟังก์ชันคัดลอก Hardware ID
def copy_hardware_id():
    hardware_id = get_hardware_id()
    pyperclip.copy(hardware_id)
    return hardware_id
