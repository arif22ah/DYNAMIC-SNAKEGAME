import platform
import psutil

print("="*40)
print("💻 SYSTEM INFORMATION")
print("="*40)

print("OS      :", platform.system())
print("Release :", platform.release())
print("CPU     :", platform.processor())
print("Cores   :", psutil.cpu_count())
print("RAM     :", round(psutil.virtual_memory().total/1024**3, 2), "GB")
print("Disk    :", round(psutil.disk_usage('/').total/1024**3, 2), "GB")
