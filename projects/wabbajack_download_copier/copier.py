"""
Core copying logic for the Wabbajack Download Copier plugin
"""

import os
import shutil
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal


class CopyWorker(QThread):
    """Worker thread for copying download files"""
    progress_updated = pyqtSignal(int, str)
    copy_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, mod_downloads, destination_path):
        super().__init__()
        self.mod_downloads = mod_downloads
        self.destination_path = Path(destination_path)
        self.results = {
            'copied': [],
            'skipped': [],
            'failed': [],
            'meta_copied': [],
            'meta_missing': []
        }

    def run(self):
        try:
            self.destination_path.mkdir(parents=True, exist_ok=True)
            total_files = len(self.mod_downloads)
            
            for i, (mod_name, source_path) in enumerate(self.mod_downloads.items()):
                self.progress_updated.emit(
                    int((i / total_files) * 100),
                    f"Processing {mod_name}..."
                )
                
                source = Path(source_path)
                destination = self.destination_path / source.name
                
                try:
                    # Copy main download file
                    if destination.exists():
                        if destination.stat().st_size == source.stat().st_size:
                            self.results['skipped'].append(f"{mod_name} -> {source.name} (already exists)")
                        else:
                            shutil.copy2(source_path, destination)
                            self.results['copied'].append(f"{mod_name} -> {source.name}")
                    else:
                        shutil.copy2(source_path, destination)
                        self.results['copied'].append(f"{mod_name} -> {source.name}")
                    
                    # Copy corresponding .meta file if it exists
                    meta_source = Path(source_path + ".meta")
                    meta_destination = Path(str(destination) + ".meta")
                    
                    if meta_source.exists():
                        if meta_destination.exists():
                            if meta_destination.stat().st_size == meta_source.stat().st_size:
                                self.results['skipped'].append(f"{mod_name} -> {source.name}.meta (already exists)")
                            else:
                                shutil.copy2(meta_source, meta_destination)
                                self.results['meta_copied'].append(f"{mod_name} -> {source.name}.meta (updated)")
                        else:
                            shutil.copy2(meta_source, meta_destination)
                            self.results['meta_copied'].append(f"{mod_name} -> {source.name}.meta")
                    else:
                        self.results['meta_missing'].append(f"{mod_name} -> {source.name}.meta (no meta file found)")
                    
                except Exception as e:
                    self.results['failed'].append(f"{mod_name} -> {source.name}: {str(e)}")
            
            self.progress_updated.emit(100, "Copy operation completed")
            self.copy_completed.emit(self.results)
            
        except Exception as e:
            self.error_occurred.emit(f"Copy operation failed: {str(e)}")