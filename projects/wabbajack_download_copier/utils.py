"""
Utility functions for the Wabbajack Download Copier plugin
"""

import os
import ctypes
from pathlib import Path


def format_file_size(size_bytes):
    """Format file size in human-readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    if i == 0:
        return f"{int(size_bytes)} {size_names[i]}"
    else:
        return f"{size_bytes:.2f} {size_names[i]}"


def get_disk_usage(path):
    """Get disk usage statistics for the given path"""
    try:
        path = Path(path)
        
        if os.name == 'nt':  # Windows
            # For Windows, we need to get the root drive path
            # Convert D:\Modlists\NS3 PBR\downloads to D:\
            drive_path = str(path.anchor)  # Gets "D:\" from the path
            
            free_bytes = ctypes.c_ulonglong(0)
            total_bytes = ctypes.c_ulonglong(0)
            result = ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(drive_path),
                ctypes.pointer(free_bytes),
                ctypes.pointer(total_bytes),
                None
            )
            
            if result:
                return free_bytes.value, total_bytes.value
            else:
                # Fallback: try with the full path
                result = ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(str(path)),
                    ctypes.pointer(free_bytes),
                    ctypes.pointer(total_bytes),
                    None
                )
                if result:
                    return free_bytes.value, total_bytes.value
                else:
                    return None, None
        else:  # Unix-like
            statvfs = os.statvfs(str(path))
            free_bytes = statvfs.f_frsize * statvfs.f_bavail
            total_bytes = statvfs.f_frsize * statvfs.f_blocks
            return free_bytes, total_bytes
    except Exception:
        return None, None