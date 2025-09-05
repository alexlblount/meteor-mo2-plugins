import mobase
import csv
import os
from datetime import datetime
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *


class ModUpdateChecker(mobase.IPluginTool):
    """Plugin to check for mod updates and export them to CSV"""
    
    def __init__(self):
        super().__init__()
        self._organizer = None
        self._parent_widget = None
    
    def init(self, organizer: mobase.IOrganizer) -> bool:
        self._organizer = organizer
        return True
    
    def name(self) -> str:
        return "Mod Update Checker"
    
    def localizedName(self) -> str:
        return "Mod Update Checker"
    
    def author(self) -> str:
        return "Claude"
    
    def description(self) -> str:
        return "Exports a list of mods that need updates to CSV format"
    
    def version(self) -> mobase.VersionInfo:
        return mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.FINAL)
    
    def requirements(self) -> list[mobase.IPluginRequirement]:
        return []
    
    def isActive(self) -> bool:
        return True
    
    def settings(self) -> list[mobase.PluginSetting]:
        return []
    
    def displayName(self) -> str:
        return "Mod Update Checker"
    
    def tooltip(self) -> str:
        return "Check for mod updates and export to CSV"
    
    def icon(self) -> QIcon:
        return QIcon()
    
    def setParentWidget(self, parent: QWidget) -> None:
        self._parent_widget = parent
    
    def display(self) -> None:
        """Main plugin execution"""
        try:
            # Get all mods that need updates
            outdated_mods = self._find_outdated_mods()
            
            if not outdated_mods:
                QMessageBox.information(
                    self._parent_widget,
                    "No Updates",
                    "All mods are up to date!"
                )
                return
            
            # Ask user where to save the file
            file_path, _ = QFileDialog.getSaveFileName(
                self._parent_widget,
                "Save Update Report",
                f"mod_updates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "CSV Files (*.csv)"
            )
            
            if file_path:
                self._export_to_csv(outdated_mods, file_path)
                QMessageBox.information(
                    self._parent_widget,
                    "Export Complete",
                    f"Update report saved to:\n{file_path}\n\n"
                    f"Found {len(outdated_mods)} mods with available updates."
                )
        
        except Exception as e:
            QMessageBox.critical(
                self._parent_widget,
                "Error",
                f"An error occurred: {str(e)}"
            )
    
    def _find_outdated_mods(self) -> list[dict]:
        """Find all mods that have available updates"""
        outdated_mods = []
        mod_list = self._organizer.modList()
        
        for mod_name in mod_list.allMods():
            mod = mod_list.getMod(mod_name)
            if not mod:
                continue
            
            # Skip separators and special mods
            if mod.isSeparator() or mod.isOverwrite() or mod.isForeign():
                continue
            
            current_version = mod.version()
            newest_version = mod.newestVersion()
            
            # Check if mod has update available
            if (newest_version.isValid() and 
                current_version.isValid() and 
                newest_version != current_version):
                
                nexus_id = mod.nexusId()
                nexus_url = ""
                
                # Prioritize Nexus URL if we have a Nexus ID, otherwise use custom URL
                if nexus_id > 0:
                    game_name = self._organizer.managedGame().gameShortName().lower()
                    # Map game names to correct Nexus URLs
                    if game_name == "skyrimse":
                        game_name = "skyrimspecialedition"
                    final_url = f"https://www.nexusmods.com/{game_name}/mods/{nexus_id}"
                else:
                    final_url = mod.url() if mod.url() else ""
                
                mod_info = {
                    'name': mod.name(),
                    'current_version': current_version.displayString(),
                    'latest_version': newest_version.displayString(),
                    'nexus_id': nexus_id if nexus_id > 0 else '',
                    'mod_url': final_url
                }
                
                outdated_mods.append(mod_info)
        
        return outdated_mods
    
    def _export_to_csv(self, mods: list[dict], file_path: str) -> None:
        """Export mod update information to CSV"""
        fieldnames = [
            'Mod Name',
            'Current Version', 
            'Latest Version',
            'Nexus ID',
            'Mod URL'
        ]
        
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for mod in mods:
                writer.writerow({
                    'Mod Name': mod['name'],
                    'Current Version': mod['current_version'],
                    'Latest Version': mod['latest_version'],
                    'Nexus ID': mod['nexus_id'],
                    'Mod URL': mod['mod_url']
                })


def createPlugin() -> ModUpdateChecker:
    return ModUpdateChecker()