import subprocess
import re
import logging
import shutil
from typing import Tuple

def is_rocm_smi_available() -> bool:
    """Check if rocm-smi is available."""
    try:
        paths = [
            shutil.which('rocm-smi'),
            '/opt/rocm/bin/rocm-smi',
            'C:\\Program Files\\AMD\\ROCm\\bin\\rocm-smi.exe'
        ]
        for path in paths:
            if path:
                subprocess.run([path, '--showmeminfo', 'vram'],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               timeout=2)
                return True
    except (subprocess.SubprocessError, subprocess.TimeoutExpired):
        pass
    return False

def get_gpu_type():
    """Detect whether system has NVIDIA or AMD GPU with monitoring tools."""
    if shutil.which('nvidia-smi'):
        try:
            subprocess.run(['nvidia-smi'], stdout=subprocess.PIPE, timeout=2)
            return "nvidia"
        except (subprocess.SubprocessError, subprocess.TimeoutExpired):
            pass

    # Check for ROCm SMI first (official AMD tool)
    if is_rocm_smi_available():
        return "amd_rocm"

    # Fallback to radeontop on Linux
    if shutil.which('radeontop'):
        try:
            subprocess.run(['radeontop', '-d', '-', '-l', '1'], stdout=subprocess.PIPE, timeout=2)
            return "amd_radeontop"
        except (subprocess.SubprocessError, subprocess.TimeoutExpired):
            pass

    return None

def get_nvidia_vram():
    """Get VRAM info using nvidia-smi."""
    try:
        cmd = ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            used, total = map(float, result.stdout.strip().split(','))
            return used, total
    except (subprocess.SubprocessError, ValueError) as e:
        logging.warning(f"Error getting NVIDIA VRAM info: {str(e)}")
    return 0.0, 0.0

def get_amd_rocm_vram() -> Tuple[float, float]:
    """Get VRAM info using rocm-smi."""
    try:
        cmd = shutil.which('rocm-smi') or '/opt/rocm/bin/rocm-smi'
        if not cmd:
            cmd = 'C:\\Program Files\\AMD\\ROCm\\bin\\rocm-smi.exe'

        result = subprocess.run(
            [cmd, '--showmeminfo', 'vram', '--json'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=2
        )

        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            for card in data.values():
                vram_info = card.get('VRAM Memory')
                if vram_info:
                    used_mb = float(vram_info['used']) / 1024 / 1024
                    total_mb = float(vram_info['total']) / 1024 / 1024
                    return used_mb, total_mb

    except Exception as e:
        logging.warning(f"Error getting VRAM info via ROCm SMI: {str(e)}")
    return 0.0, 0.0

def get_amd_radeontop_vram():
    """Get VRAM info using radeontop (Linux fallback)."""
    try:
        cmd = ["radeontop", "-d", "-", "-l", "1"]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)

        for line in process.stdout:
            data = line.strip().split()
            if data[0] == "Dumping":
                continue

            line_str = ' '.join(data)
            vram_match = re.search(r'vram \d+\.\d+% (\d+\.\d+)mb', line_str)
            if vram_match:
                current_mb = float(vram_match.group(1))
                vram_percent = float(re.search(r'vram (\d+\.\d+)%', line_str).group(1))
                max_mb = current_mb / (vram_percent / 100) if vram_percent > 0 else 0
                process.terminate()
                return current_mb, max_mb

        process.terminate()
    except (subprocess.SubprocessError, Exception) as e:
        logging.warning(f"Error getting AMD VRAM info via radeontop: {str(e)}")
    return 0.0, 0.0

def get_vram_info():
    """Get VRAM usage information. Returns (current_mb, max_mb)."""
    if not hasattr(get_vram_info, '_gpu_type'):
        get_vram_info._gpu_type = get_gpu_type()
        if get_vram_info._gpu_type:
            logging.info(f"Detected {get_vram_info._gpu_type.upper()} GPU")
        else:
            logging.warning("No supported GPU monitoring tools found")
            logging.info("Continuing without VRAM monitoring")

    if get_vram_info._gpu_type == "nvidia":
        return get_nvidia_vram()
    elif get_vram_info._gpu_type == "amd_rocm":
        return get_amd_rocm_vram()
    elif get_vram_info._gpu_type == "amd_radeontop":
        return get_amd_radeontop_vram()
    return 0.0, 0.0