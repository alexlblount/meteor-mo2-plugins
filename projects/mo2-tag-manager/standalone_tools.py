"""
Standalone tools for MO2 Tag Manager.
Quick tools for bulk operations on all mods.
"""

import mobase
from typing import List

try:
    from PyQt6.QtWidgets import QMessageBox
    from PyQt6.QtGui import QIcon
except ImportError:
    from PyQt5.QtWidgets import QMessageBox
    from PyQt5.QtGui import QIcon

from .utils import ModSectionUtils, parse_mod_tags, build_mod_name, strip_numerical_index


class TagMgrAddIndexesTool(mobase.IPluginTool):
    """Standalone tool to add indexes to all mods with [NoDelete] tags."""
    
    def __init__(self):
        super().__init__()
        self._organizer = None

    def init(self, organizer: mobase.IOrganizer):
        self._organizer = organizer
        return True

    def name(self) -> str:
        return "Add Indexes Tool"

    def author(self) -> str:
        return "Alex"

    def description(self) -> str:
        return "Add numerical indexes to all mods with [NoDelete] tags"

    def version(self) -> mobase.VersionInfo:
        return mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.ALPHA)

    def settings(self) -> List[mobase.PluginSetting]:
        return []

    def displayName(self) -> str:
        return "Tag Manager v1.0.0/2. Add Indexes to [NoDelete] mods"

    def tooltip(self) -> str:
        return "Add numerical indexes [xxx.xxxxx] to all mods with [NoDelete] tags"

    def icon(self):
        return QIcon()

    def display(self) -> bool:
        if not self._organizer:
            return False
        
        # Confirm with user
        reply = QMessageBox.question(
            None, 
            "Add Indexes", 
            "This will add numerical indexes [xxx.xxxxx] to ALL mods with [NoDelete] tags.\n\n"
            "This helps preserve exact mod order for restoration after updates.\n\n"
            "The interface will be unresponsive briefly while processing.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return True
        
        self._add_indexes_to_all_nodelete_mods()
        return True
    
    def _add_indexes_to_all_nodelete_mods(self):
        """Add indexes to all mods with [NoDelete] tags using LazyModlist approach."""
        modList = self._organizer.modList()
        sections, section_order, separator_map = ModSectionUtils.analyze_mod_organization(modList)
        
        # Create section index mapping
        section_to_index = {}
        display_order = list(reversed(section_order))
        for i, section in enumerate(display_order, 1):
            section_to_index[section] = i
        
        # Build mappings for ALL mods with [NoDelete] tags
        mod_to_section = {}
        separator_to_section = {}
        
        # Map all mods to their sections
        for section in sections:
            mods_in_section = sections.get(section, [])
            for mod_name in mods_in_section:
                mod_obj = modList.getMod(mod_name)
                if mod_obj:
                    tags_info = parse_mod_tags(mod_obj.name())
                    if tags_info['nodelete']:
                        mod_to_section[mod_name] = section
        
        # Map all separators to their sections (if they have [NoDelete] tags)
        for mod_name in modList.allMods():
            mod_obj = modList.getMod(mod_name)
            if not mod_obj:
                continue
            
            tags_info = parse_mod_tags(mod_obj.name())
            if not tags_info['nodelete']:
                continue
            
            for section in sections:
                is_separator = False
                if mod_name.endswith('_separator') and mod_name[:-10] == section:
                    is_separator = True
                elif mod_obj.isSeparator() and tags_info['clean_name'] == section:
                    is_separator = True
                
                if is_separator:
                    separator_to_section[mod_name] = section
                    break
        
        # Get all mods in MO2's internal priority order
        all_mods_in_order = modList.allModsByProfilePriority()
        
        # Filter to only mods/separators with [NoDelete] tags
        mods_to_process = []
        for mod_name in all_mods_in_order:
            if mod_name in mod_to_section or mod_name in separator_to_section:
                mods_to_process.append(mod_name)
        
        processed_count = 0
        skipped_count = 0
        errors = []
        
        try:
            # Process using LazyModlist approach - no UI interference!
            for mod_name in mods_to_process:
                mod_obj = modList.getMod(mod_name)
                if not mod_obj:
                    continue
                
                # Determine if this is a separator or regular mod, and which section
                is_separator = mod_name in separator_to_section
                section = separator_to_section.get(mod_name) or mod_to_section.get(mod_name)
                
                if not section:
                    continue
                
                try:
                    current_name = mod_obj.name()
                    tags_info = parse_mod_tags(current_name)
                    
                    if tags_info['nodelete']:
                        section_index = section_to_index.get(section, 0)
                        if is_separator:
                            position_index = 0
                        else:
                            # Calculate position within section
                            mods_in_section = sections.get(section, [])
                            try:
                                position_index = len(mods_in_section) - mods_in_section.index(mod_name)
                            except ValueError:
                                position_index = 1  # Fallback
                        
                        tags_info['index'] = f"{section_index:03d}.{position_index:05d}"
                        
                        new_name = build_mod_name(
                            tags_info['clean_name'],
                            tags_info['nodelete'],
                            tags_info['index'],
                            tags_info['custom_tags']
                        )
                        
                        if new_name != current_name:
                            modList.renameMod(mod_obj, new_name)
                            processed_count += 1
                        else:
                            skipped_count += 1
                    else:
                        skipped_count += 1
                        
                except Exception as e:
                    errors.append(f"Error processing '{mod_name}': {str(e)}")
        
        except Exception as e:
            QMessageBox.critical(None, "Error", f"An error occurred: {str(e)}")
            return
        
        # Show completion message
        message = f"Successfully added indexes to {processed_count} mods with [NoDelete] tags."
        if skipped_count > 0:
            message += f"\n{skipped_count} mods were skipped (no [NoDelete] tag or no changes needed)."
        if errors:
            message += f"\n{len(errors)} errors occurred."
        
        QMessageBox.information(None, "Complete", message)
        self._organizer.refresh()


class TagMgrRemoveIndexesTool(mobase.IPluginTool):
    """Standalone tool to remove all numerical indexes."""
    
    def __init__(self):
        super().__init__()
        self._organizer = None

    def init(self, organizer: mobase.IOrganizer):
        self._organizer = organizer
        return True

    def name(self) -> str:
        return "Remove Indexes Tool"

    def author(self) -> str:
        return "Alex"

    def description(self) -> str:
        return "Remove numerical indexes from all mods"

    def version(self) -> mobase.VersionInfo:
        return mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.ALPHA)

    def settings(self) -> List[mobase.PluginSetting]:
        return []

    def displayName(self) -> str:
        return "Tag Manager v1.0.0/3. Remove all indexes"

    def tooltip(self) -> str:
        return "Remove numerical indexes [xxx.xxxxx] from all mods"

    def icon(self):
        return QIcon()

    def display(self) -> bool:
        if not self._organizer:
            return False
        
        # Confirm with user
        reply = QMessageBox.question(
            None, 
            "Remove Indexes", 
            "This will remove ALL numerical indexes [xxx.xxxxx] from mod names.\n\n"
            "[NoDelete] and custom tags will be preserved.\n\n"
            "The interface will be unresponsive briefly while processing.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return True
        
        self._remove_indexes_from_all_mods()
        return True
    
    def _remove_indexes_from_all_mods(self):
        """Remove indexes from all mods using LazyModlist approach."""
        modList = self._organizer.modList()
        processed_count = 0
        skipped_count = 0
        errors = []
        
        try:
            for mod_name in modList.allMods():
                try:
                    mod_obj = modList.getMod(mod_name)
                    if mod_obj:
                        current_name = mod_obj.name()
                        tags_info = parse_mod_tags(current_name)
                        
                        if tags_info['index']:
                            tags_info['index'] = None
                            new_name = build_mod_name(
                                tags_info['clean_name'],
                                tags_info['nodelete'],
                                tags_info['index'],
                                tags_info['custom_tags']
                            )
                            
                            if new_name != current_name:
                                modList.renameMod(mod_obj, new_name)
                                processed_count += 1
                            else:
                                skipped_count += 1
                        else:
                            skipped_count += 1
                except Exception as e:
                    errors.append(f"Error processing '{mod_name}': {str(e)}")
        
        except Exception as e:
            QMessageBox.critical(None, "Error", f"An error occurred: {str(e)}")
            return
        
        # Show completion message
        message = f"Successfully removed indexes from {processed_count} mods."
        if skipped_count > 0:
            message += f"\n{skipped_count} mods were skipped (no changes needed)."
        if errors:
            message += f"\n{len(errors)} errors occurred."
        
        QMessageBox.information(None, "Complete", message)
        self._organizer.refresh()