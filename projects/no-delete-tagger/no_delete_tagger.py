import mobase
import re
from typing import List, Dict, Set, Tuple

## no_delete_tagger.py
# 
# A comprehensive MO2 plugin for managing `[NoDelete]` tags and numerical indexes by 
# separator sections. Designed for Wabbajack users who need to preserve custom mod 
# configurations during modlist updates.
# 
# **Features:**
# - **Section-based tagging**: Add/remove `[NoDelete]` tags by separator sections with
#   checkbox selection
# - **Automatic indexing**: Optional numerical indexes `[009.00001]` for precise order
#   preservation  
# - **Auto-cleanup**: Removing `[NoDelete]` tags automatically strips associated indexes
# - **Three-tool menu**: Tag management dialog + standalone index tools
# 
# **Architecture:**
# - Uses LazyModlist approach (tight loops, no UI interference) for bulletproof reliability
# - Processes mods in `allModsByProfilePriority()` order to prevent race conditions
# - Single `refresh()` at completion to maintain MO2 internal state consistency
# 
# **Use Cases:**
# - Protect custom mods from Wabbajack deletion
# - Preserve exact mod order for restoration after updates
# - Clean up mod names by removing tags/indexes when no longer needed

try:
    from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QCheckBox, 
                                QPushButton, QLabel, QScrollArea, QWidget, 
                                QMessageBox, QGroupBox, QTextEdit, QProgressDialog,
                                QApplication)
    from PyQt6.QtCore import Qt, QTimer
except ImportError:
    from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QCheckBox, 
                                QPushButton, QLabel, QScrollArea, QWidget, 
                                QMessageBox, QGroupBox, QTextEdit, QProgressDialog,
                                QApplication)
    from PyQt5.QtCore import Qt, QTimer


def strip_mod_tags(mod_name: str) -> str:
    """
    Remove all tags in square brackets from the beginning of a mod name.
    Examples:
    "[NoDelete] Awesome Mod" -> "Awesome Mod"
    "[NoDelete] [009.00001] Awesome Mod" -> "Awesome Mod"
    "[Tag1][Tag2] Mod Name" -> "Mod Name"
    """
    pattern = r'^(\[[^\]]+\]\s*)+\s*'
    return re.sub(pattern, '', mod_name).strip()

def strip_numerical_index(mod_name: str) -> str:
    """
    Remove numerical index [xxx.xxxxx] from mod name while preserving other tags.
    Only removes indexes in the specific format: [XXX.XXXXX] (3 digits, dot, 5 digits)
    Examples:
    "[NoDelete] [009.00001] Awesome Mod" -> "[NoDelete] Awesome Mod"
    "[SomeTag] [009.00001] Mod Name" -> "[SomeTag] Mod Name"
    "[v1.2] Mod Name" -> "[v1.2] Mod Name" (preserved - not our format)
    """
    # Match exactly 3 digits, dot, exactly 5 digits
    pattern = r'\s*\[[0-9]{3}\.[0-9]{5}\]\s*'
    return re.sub(pattern, ' ', mod_name).strip()


class ModSectionUtils:
    """Utility class for analyzing mod organization by separators."""
    
    @staticmethod
    def analyze_mod_organization(mod_list) -> Tuple[Dict[str, List[str]], List[str]]:
        """Analyze the current mod list and organize mods by separator sections."""
        sections = {}
        section_order = []
        mod_buffer = []
        current_section = "Unsectioned"
        
        # Get all mods in priority order and REVERSE it to read correctly
        all_mods = list(reversed(mod_list.allModsByProfilePriority()))
        
        for mod_name in all_mods:
            mod_obj = mod_list.getMod(mod_name)
            if not mod_obj:
                continue
                
            # Skip system mods
            mod_path = mod_obj.absolutePath().lower()
            if any(skip in mod_path for skip in ["game root/data", "stock game/data", "skyrim special edition/data"]):
                continue
            
            # Check if this is a separator
            if mod_obj.isSeparator() or mod_name.endswith('_separator'):
                # Get section name
                if mod_name.endswith('_separator'):
                    section_name = mod_name[:-10]  # Remove '_separator' suffix
                else:
                    section_name = strip_mod_tags(mod_name)
                
                # Assign all buffered mods to this section
                if mod_buffer:
                    sections[section_name] = mod_buffer.copy()
                    mod_buffer = []
                
                # Track section order
                if section_name not in section_order:
                    section_order.append(section_name)
                
                continue
            
            # Regular mod - add to buffer
            mod_buffer.append(mod_name)
        
        # Handle any remaining mods in buffer
        if mod_buffer:
            sections[current_section] = mod_buffer.copy()
            if current_section not in section_order:
                section_order.append(current_section)
        
        return sections, section_order


class NoDeleteTagDialog(QDialog):
    def __init__(self, parent, organizer):
        super().__init__(parent)
        self.organizer = organizer
        self.modList = organizer.modList()
        self.noDeleteTag = "[NoDelete]"
        
        self.setWindowTitle("NoDelete Tag Manager")
        self.setMinimumSize(450, 400)
        self.resize(550, 500)
        
        # Analyze current mod organization
        self.sections, self.section_order = ModSectionUtils.analyze_mod_organization(self.modList)
        
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Title and description
        title_label = QLabel("Select sections to manage [NoDelete] tags:")
        title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(title_label)
        
        desc_label = QLabel("Add or remove [NoDelete] tags from mods by section.\n"
                           "[NoDelete] tags protect mods from deletion during Wabbajack updates.\n"
                           "Note: Removing [NoDelete] tags will also remove any numerical indexes.")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Scroll area for section checkboxes
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        self.section_checkboxes = {}
        
        if not self.section_order:
            no_sections_label = QLabel("No organized sections found in your mod list.")
            scroll_layout.addWidget(no_sections_label)
        else:
            # Display sections in reverse order (top to bottom in UI)
            display_order = list(reversed(self.section_order))
            for section in display_order:
                mods_in_section = self.sections.get(section, [])
                separator_has_tag = self._separator_has_no_delete_tag(section)
                
                if mods_in_section:
                    # Section with mods - always selectable
                    checkbox = QCheckBox(f"{section} ({len(mods_in_section)} mods)")
                    self.section_checkboxes[section] = checkbox
                    scroll_layout.addWidget(checkbox)
                elif separator_has_tag:
                    # Empty separator with [NoDelete] tag - make it selectable
                    checkbox = QCheckBox(section)
                    self.section_checkboxes[section] = checkbox
                    scroll_layout.addWidget(checkbox)
                else:
                    # Empty separator without tag - show as plain label
                    label = QLabel(section)
                    label.setStyleSheet("color: #666; font-style: italic; margin-left: 10px;")
                    scroll_layout.addWidget(label)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        # Selection buttons
        selection_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all)
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self._deselect_all)
        
        selection_layout.addWidget(select_all_btn)
        selection_layout.addWidget(deselect_all_btn)
        selection_layout.addStretch()
        layout.addLayout(selection_layout)
        
        # Option to automatically add indexes
        self.auto_index_checkbox = QCheckBox("Also add numerical indexes when adding [NoDelete] tags")
        self.auto_index_checkbox.setToolTip("Automatically add [xxx.xxxxx] indexes to preserve exact mod order")
        layout.addWidget(self.auto_index_checkbox)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        add_tags_btn = QPushButton("Add [NoDelete] Tags")
        add_tags_btn.clicked.connect(self._apply_tags)
        remove_tags_btn = QPushButton("Remove [NoDelete] Tags")
        remove_tags_btn.clicked.connect(self._remove_tags)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(add_tags_btn)
        button_layout.addWidget(remove_tags_btn)
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
    
    def _select_all(self):
        for checkbox in self.section_checkboxes.values():
            checkbox.setChecked(True)
    
    def _deselect_all(self):
        for checkbox in self.section_checkboxes.values():
            checkbox.setChecked(False)
    
    def _get_selected_sections(self) -> List[str]:
        selected = []
        for section, checkbox in self.section_checkboxes.items():
            if checkbox.isChecked():
                selected.append(section)
        return selected
    
    def _apply_tags(self):
        """Apply [NoDelete] tags to selected sections."""
        selected_sections = self._get_selected_sections()
        if not selected_sections:
            QMessageBox.information(self, "Add Tags", "No sections selected.")
            return
        
        also_index = self.auto_index_checkbox.isChecked()
        operation_name = "Adding Tags and Indexes" if also_index else "Adding Tags"
        
        # Show pre-processing message
        QMessageBox.information(
            self, 
            operation_name, 
            f"{operation_name} for selected sections...\n\n"
            "The interface will be unresponsive briefly while processing.\n"
            "Click OK to continue."
        )
        
        success = self._process_tags_lazymodlist_style(selected_sections, operation_name, True, also_index)
        if success:
            self.accept()  # Close dialog on success
    
    def _remove_tags(self):
        """Remove [NoDelete] tags from selected sections."""
        selected_sections = self._get_selected_sections()
        if not selected_sections:
            QMessageBox.information(self, "Remove Tags", "No sections selected.")
            return
        
        # Show pre-processing message
        QMessageBox.information(
            self, 
            "Removing Tags", 
            "Removing [NoDelete] tags and indexes from selected sections...\n\n"
            "The interface will be unresponsive briefly while processing.\n"
            "Click OK to continue."
        )
        
        success = self._process_tags_lazymodlist_style(selected_sections, "Removing Tags", False, False)
        if success:
            self.accept()  # Close dialog on success
    
    def _process_tags_lazymodlist_style(self, selected_sections, operation_name, add_tags, also_add_indexes):
        """Process tags using the LazyModlist approach - no UI interference during processing."""
        
        # Build mappings for selected sections
        mod_to_section = {}
        separator_to_section = {}
        section_to_index = {}
        
        # Create section index mapping if we're adding indexes
        if also_add_indexes:
            display_order = list(reversed(self.section_order))
            for i, section in enumerate(display_order, 1):
                section_to_index[section] = i
        
        # Build mod -> section mapping for selected sections only
        for section in selected_sections:
            mods_in_section = self.sections.get(section, [])
            for mod_name in mods_in_section:
                mod_to_section[mod_name] = section
        
        # Build separator -> section mapping for selected sections
        for mod_name in self.modList.allMods():
            mod_obj = self.modList.getMod(mod_name)
            if not mod_obj:
                continue
            
            for section in selected_sections:
                is_separator = False
                if mod_name.endswith('_separator') and mod_name[:-10] == section:
                    is_separator = True
                elif mod_obj.isSeparator() and strip_mod_tags(mod_name) == section:
                    is_separator = True
                
                if is_separator:
                    separator_to_section[mod_name] = section
                    break
        
        # Get all mods in MO2's internal priority order
        all_mods_in_order = self.modList.allModsByProfilePriority()
        
        # Filter to only mods/separators in selected sections
        mods_to_process = []
        for mod_name in all_mods_in_order:
            if mod_name in mod_to_section or mod_name in separator_to_section:
                mods_to_process.append(mod_name)
        
        if not mods_to_process:
            QMessageBox.information(self, operation_name, "No mods found in selected sections.")
            return False
        
        processed_count = 0
        skipped_count = 0
        errors = []
        
        try:
            # Process using LazyModlist approach - no UI interference!
            for mod_name in mods_to_process:
                mod_obj = self.modList.getMod(mod_name)
                if not mod_obj:
                    continue
                
                # Determine if this is a separator or regular mod, and which section
                is_separator = mod_name in separator_to_section
                section = separator_to_section.get(mod_name) or mod_to_section.get(mod_name)
                
                if not section:
                    continue  # Skip if not in selected sections
                
                try:
                    current_name = mod_obj.name()
                    new_name = current_name
                    
                    # Handle tag operations
                    if add_tags and not self._has_no_delete_tag(current_name):
                        new_name = self._add_no_delete_tag(new_name)
                    elif not add_tags and self._has_no_delete_tag(current_name):
                        new_name = self._remove_no_delete_tag(new_name)
                        # Also remove any numerical indexes when removing [NoDelete] tags
                        new_name = strip_numerical_index(new_name)
                    
                    # Handle index operations (only if adding tags and checkbox is checked)
                    if also_add_indexes and add_tags and self._has_no_delete_tag(new_name):
                        section_index = section_to_index.get(section, 0)
                        if is_separator:
                            position_index = 0
                        else:
                            # Calculate position within section - FIXED: reverse the indexing
                            mods_in_section = self.sections.get(section, [])
                            try:
                                position_index = len(mods_in_section) - mods_in_section.index(mod_name)
                            except ValueError:
                                position_index = 1  # Fallback
                        new_name = self._add_numerical_index(new_name, section_index, position_index)
                    
                    if new_name != current_name:
                        self.modList.renameMod(mod_obj, new_name)
                        processed_count += 1
                    else:
                        skipped_count += 1
                    
                    # NO delays, NO processEvents() - LazyModlist approach!
                    
                except Exception as e:
                    errors.append(f"Error processing '{mod_name}': {str(e)}")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
            return False
        
        # Show completion message (like LazyModlist does)
        if add_tags and also_add_indexes:
            message = f"Successfully added [NoDelete] tags and indexes to {processed_count} mods."
        elif add_tags:
            message = f"Successfully added [NoDelete] tags to {processed_count} mods."
        else:
            message = f"Successfully removed [NoDelete] tags and indexes from {processed_count} mods."
        
        if skipped_count > 0:
            skip_reason = "already had tags" if add_tags else "didn't have tags"
            message += f"\n{skipped_count} mods were skipped ({skip_reason})."
        if errors:
            message += f"\n{len(errors)} errors occurred."
        
        QMessageBox.information(self, "Complete", message)
        
        # Single refresh at the end - LazyModlist approach!
        self.organizer.refresh()
        return True
    
    def _process_separator(self, section, add_tags, also_add_indexes, section_index, processed_count, skipped_count, errors):
        """Process the separator for a section."""
        for mod_name in self.modList.allMods():
            mod_obj = self.modList.getMod(mod_name)
            if not mod_obj:
                continue
                
            # Check if this is the separator for this section
            is_separator = False
            if mod_name.endswith('_separator') and mod_name[:-10] == section:
                is_separator = True
            elif mod_obj.isSeparator() and strip_mod_tags(mod_name) == section:
                is_separator = True
            
            if is_separator:
                try:
                    current_name = mod_obj.name()
                    new_name = current_name
                    
                    # Handle tag operations
                    if add_tags and not self._has_no_delete_tag(current_name):
                        new_name = self._add_no_delete_tag(new_name)
                    elif not add_tags and self._has_no_delete_tag(current_name):
                        new_name = self._remove_no_delete_tag(new_name)
                        # Also remove any numerical indexes when removing [NoDelete] tags
                        new_name = strip_numerical_index(new_name)
                    
                    # Handle index operations (only if adding tags and also_add_indexes is True)
                    if also_add_indexes and add_tags and self._has_no_delete_tag(new_name):
                        new_name = self._add_numerical_index(new_name, section_index, 0)
                    
                    if new_name != current_name:
                        self.modList.renameMod(mod_obj, new_name)
                        processed_count += 1
                    else:
                        skipped_count += 1
                        
                except Exception as e:
                    errors.append(f"Error processing separator '{mod_name}': {str(e)}")
                
                # CRITICAL: Delay to prevent mod order corruption
                QTimer.singleShot(50, lambda: None)
                QApplication.processEvents()
                break
    
    def _has_no_delete_tag(self, mod_name: str) -> bool:
        """Check if mod already has the [NoDelete] tag."""
        return mod_name.startswith(self.noDeleteTag)
    
    def _separator_has_no_delete_tag(self, section: str) -> bool:
        """Check if the separator for this section has the [NoDelete] tag."""
        for mod_name in self.modList.allMods():
            mod_obj = self.modList.getMod(mod_name)
            if not mod_obj:
                continue
                
            # Check if this is the separator for this section
            is_separator = False
            if mod_name.endswith('_separator') and mod_name[:-10] == section:
                is_separator = True
            elif mod_obj.isSeparator() and strip_mod_tags(mod_name) == section:
                is_separator = True
            
            if is_separator:
                return self._has_no_delete_tag(mod_name)
        
        return False
    
    def _add_no_delete_tag(self, mod_name: str) -> str:
        """Add [NoDelete] tag to mod name if not already present."""
        if self._has_no_delete_tag(mod_name):
            return mod_name
        return f"{self.noDeleteTag} {mod_name}"
    
    def _remove_no_delete_tag(self, mod_name: str) -> str:
        """Remove [NoDelete] tag from mod name if present."""
        if not self._has_no_delete_tag(mod_name):
            return mod_name
        
        pattern = re.escape(self.noDeleteTag) + r'\s*'
        return re.sub(f'^{pattern}', '', mod_name)
    
    def _add_numerical_index(self, mod_name: str, section_index: int, position_index: int) -> str:
        """Add numerical index to mod name in format [xxx.xxxxx]."""
        # Remove any existing numerical index first
        clean_name = strip_numerical_index(mod_name)
        
        # Find where to insert the numerical index
        tags_match = re.match(r'^(\[[^\]]+\]\s*)+', clean_name)
        numerical_tag = f"[{section_index:03d}.{position_index:05d}]"
        
        if tags_match:
            # Insert after existing tags
            tags_part = tags_match.group(0).rstrip()
            remaining_part = clean_name[len(tags_match.group(0)):].strip()
            return f"{tags_part} {numerical_tag} {remaining_part}".strip()
        else:
            # No existing tags, add at the beginning
            return f"{numerical_tag} {clean_name}".strip()


class NoDeleteTagManager(mobase.IPluginTool):
    def __init__(self):
        super().__init__()
        self._organizer = None
        self._parent_widget = None

    def init(self, organizer: mobase.IOrganizer):
        self._organizer = organizer
        return True

    def name(self) -> str:
        return "NoDelete Tag Manager"

    def author(self) -> str:
        return "Alex"

    def description(self) -> str:
        return "Add or remove [NoDelete] tags by separator sections"

    def version(self) -> mobase.VersionInfo:
        return mobase.VersionInfo(1, 2, 0, mobase.ReleaseType.ALPHA)

    def settings(self) -> List[mobase.PluginSetting]:
        return []

    def displayName(self) -> str:
        return "[NoDelete] Tagger v1.2.0/1. Add or Remove [NoDelete] tags"

    def tooltip(self) -> str:
        return "Add or remove [NoDelete] tags by separator sections"

    def icon(self):
        try:
            from PyQt6.QtGui import QIcon
        except ImportError:
            from PyQt5.QtGui import QIcon
        return QIcon()

    def setParentWidget(self, widget):
        self._parent_widget = widget

    def display(self) -> bool:
        if not self._organizer:
            return False
            
        dialog = NoDeleteTagDialog(self._parent_widget, self._organizer)
        dialog.exec()
        return True


class AddIndexesTool(mobase.IPluginTool):
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
        return mobase.VersionInfo(1, 2, 0, mobase.ReleaseType.ALPHA)

    def settings(self) -> List[mobase.PluginSetting]:
        return []

    def displayName(self) -> str:
        return "[NoDelete] Tagger v1.2.0/2. Add Indexes to [NoDelete] tags"

    def tooltip(self) -> str:
        return "Add numerical indexes [xxx.xxxxx] to all mods with [NoDelete] tags"

    def icon(self):
        try:
            from PyQt6.QtGui import QIcon
        except ImportError:
            from PyQt5.QtGui import QIcon
        return QIcon()

    def display(self) -> bool:
        if not self._organizer:
            return False
        
        # Confirm with user and show pre-processing message
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
        
        # Process all mods
        self._add_indexes_to_all_nodelete_mods()
        return True
    
    def _add_indexes_to_all_nodelete_mods(self):
        """Add indexes to all mods with [NoDelete] tags using LazyModlist approach."""
        modList = self._organizer.modList()
        sections, section_order = ModSectionUtils.analyze_mod_organization(modList)
        
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
                if mod_obj and "[NoDelete]" in mod_obj.name():
                    mod_to_section[mod_name] = section
        
        # Map all separators to their sections (if they have [NoDelete] tags)
        for mod_name in modList.allMods():
            mod_obj = modList.getMod(mod_name)
            if not mod_obj or "[NoDelete]" not in mod_obj.name():
                continue
            
            for section in sections:
                is_separator = False
                if mod_name.endswith('_separator') and mod_name[:-10] == section:
                    is_separator = True
                elif mod_obj.isSeparator() and strip_mod_tags(mod_name) == section:
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
                    if "[NoDelete]" in current_name:
                        section_index = section_to_index.get(section, 0)
                        if is_separator:
                            position_index = 0
                        else:
                            # Calculate position within section - FIXED: reverse the indexing
                            mods_in_section = sections.get(section, [])
                            try:
                                position_index = len(mods_in_section) - mods_in_section.index(mod_name)
                            except ValueError:
                                position_index = 1  # Fallback
                        
                        new_name = self._add_numerical_index(current_name, section_index, position_index)
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
    
    def _add_numerical_index(self, mod_name: str, section_index: int, position_index: int) -> str:
        """Add numerical index to mod name in format [xxx.xxxxx]."""
        # Remove any existing numerical index first
        clean_name = strip_numerical_index(mod_name)
        
        # Find where to insert the numerical index
        tags_match = re.match(r'^(\[[^\]]+\]\s*)+', clean_name)
        numerical_tag = f"[{section_index:03d}.{position_index:05d}]"
        
        if tags_match:
            # Insert after existing tags
            tags_part = tags_match.group(0).rstrip()
            remaining_part = clean_name[len(tags_match.group(0)):].strip()
            return f"{tags_part} {numerical_tag} {remaining_part}".strip()
        else:
            # No existing tags, add at the beginning
            return f"{numerical_tag} {clean_name}".strip()


class RemoveIndexesTool(mobase.IPluginTool):
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
        return mobase.VersionInfo(1, 1, 0, mobase.ReleaseType.ALPHA)

    def settings(self) -> List[mobase.PluginSetting]:
        return []

    def displayName(self) -> str:
        return "[NoDelete] Tagger v1.2.0/3. Remove Indexes from [NoDelete] tags"

    def tooltip(self) -> str:
        return "Remove numerical indexes [xxx.xxxxx] from all mods"

    def icon(self):
        try:
            from PyQt6.QtGui import QIcon
        except ImportError:
            from PyQt5.QtGui import QIcon
        return QIcon()

    def display(self) -> bool:
        if not self._organizer:
            return False
        
        # Confirm with user and show pre-processing message
        reply = QMessageBox.question(
            None, 
            "Remove Indexes", 
            "This will remove ALL numerical indexes [xxx.xxxxx] from mod names.\n\n"
            "[NoDelete] tags will be preserved.\n\n"
            "The interface will be unresponsive briefly while processing.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return True
        
        # Process all mods
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
                        new_name = strip_numerical_index(current_name)
                        
                        if new_name != current_name:
                            modList.renameMod(mod_obj, new_name)
                            processed_count += 1
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


def createPlugins():
    return [NoDeleteTagManager(), AddIndexesTool(), RemoveIndexesTool()]
