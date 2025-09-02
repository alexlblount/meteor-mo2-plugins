"""
Download scanning logic for the Wabbajack Download Copier plugin
"""

import os
from pathlib import Path
from datetime import datetime


class DownloadScanner:
    """Handles scanning and analyzing mod downloads"""
    
    def __init__(self, organizer):
        self.organizer = organizer

    def get_default_downloads_path(self):
        """Get the expected downloads folder path for this MO2 instance"""
        base_path = Path(self.organizer.basePath())
        return base_path / "downloads"

    def get_mod_downloads(self):
        """Identify download files for all installed mods"""
        mod_downloads = {}
        missing_downloads = []
        
        mod_list = self.organizer.modList()
        current_downloads_path = Path(self.organizer.downloadsPath())
        all_mods = mod_list.allMods()
        
        for mod_name in all_mods:
            # Skip separators - they don't have downloads
            if mod_name.endswith('_separator'):
                continue
                
            mod = mod_list.getMod(mod_name)  # Use mod_list.getMod instead of organizer.getMod
            if mod:  # Include both active and inactive mods for Wabbajack
                installation_file = mod.installationFile()
                
                if installation_file:
                    # If installationFile returns just a filename, combine it with downloads path
                    if not os.path.isabs(installation_file):
                        full_path = current_downloads_path / installation_file
                    else:
                        full_path = Path(installation_file)
                    
                    if full_path.exists():
                        # Check if it's in the downloads folder
                        if current_downloads_path in full_path.parents or current_downloads_path == full_path.parent:
                            mod_downloads[mod_name] = str(full_path)
                        else:
                            # File exists but not in downloads folder - might be manually installed
                            missing_downloads.append({
                                'mod_name': mod_name,
                                'reason': 'File exists outside downloads folder',
                                'file_path': str(full_path)
                            })
                    else:
                        missing_downloads.append({
                            'mod_name': mod_name,
                            'reason': 'Installation file does not exist',
                            'file_path': str(full_path)
                        })
                else:
                    missing_downloads.append({
                        'mod_name': mod_name,
                        'reason': 'No installation file found',
                        'file_path': 'N/A'
                    })
        
        return mod_downloads, missing_downloads

    def calculate_copy_size(self, mod_downloads):
        """Calculate total size of files to be copied (including meta files)"""
        total_size = 0
        file_count = 0
        
        for mod_name, download_path in mod_downloads.items():
            try:
                # Main download file
                if os.path.exists(download_path):
                    total_size += os.path.getsize(download_path)
                    file_count += 1
                
                # Meta file
                meta_path = download_path + ".meta"
                if os.path.exists(meta_path):
                    total_size += os.path.getsize(meta_path)
                    file_count += 1
                    
            except OSError:
                # Skip files we can't access
                continue
        
        return total_size, file_count

    def generate_missing_downloads_report(self, missing_downloads, report_path):
        """Generate a detailed report of missing downloads"""
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("WABBAJACK MISSING DOWNLOADS REPORT\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"MO2 Instance: {self.organizer.basePath()}\n")
                f.write(f"Current Downloads Folder: {self.organizer.downloadsPath()}\n\n")
                f.write(f"Total Missing Downloads: {len(missing_downloads)}\n\n")
                
                if not missing_downloads:
                    f.write("✓ All mods have their download files available!\n")
                    return True
                
                f.write("MISSING DOWNLOADS:\n")
                f.write("-" * 30 + "\n\n")
                
                for i, missing in enumerate(missing_downloads, 1):
                    f.write(f"{i}. {missing['mod_name']}\n")
                    f.write(f"   Reason: {missing['reason']}\n")
                    f.write(f"   File Path: {missing['file_path']}\n\n")
                
                f.write("\nNOTES:\n")
                f.write("- Mods with 'No installation file found' may have been installed manually\n")
                f.write("- Mods with files 'outside downloads folder' may need their downloads re-downloaded\n")
                f.write("- Check these mods manually and re-download if needed for Wabbajack compatibility\n")
                f.write("- When re-downloading, ensure both the archive file AND its .meta file are present\n")
                f.write("- .meta files contain important metadata (Nexus IDs, versions) required by Wabbajack\n")
                
            return True
        except Exception:
            return False