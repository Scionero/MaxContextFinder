import subprocess
import re

def get_vram_info():
    cmd = ["radeontop", "-d", "-", "-l", "1"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)

    for line in process.stdout:
        data = line.strip().split()

        # Skip the "Dumping to" message
        if data[0] == "Dumping":
            continue

        line_str = ' '.join(data)

        # Modified regex to capture both current and max VRAM
        vram_match = re.search(r'vram \d+\.\d+% (\d+\.\d+)mb', line_str)
        if vram_match:
            current_mb = float(vram_match.group(1))
            # Calculate max VRAM from percentage
            vram_percent = float(re.search(r'vram (\d+\.\d+)%', line_str).group(1))
            max_mb = current_mb / (vram_percent / 100) if vram_percent > 0 else 0
            process.terminate()
            return current_mb, max_mb

    process.terminate()
    return None, None
