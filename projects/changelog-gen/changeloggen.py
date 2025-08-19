import json
import os
import re
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
import mobase

def strip_mod_tags(mod_name):
    """
    Remove all tags in square brackets from the beginning of a mod name.
    Examples:
    "[NoDelete] Awesome Mod" -> "Awesome Mod"
    "[NoDelete] [SomeSection] Awesome Mod" -> "Awesome Mod"
    "[Tag1][Tag2] Mod Name" -> "Mod Name"
    """
    # Pattern to match one or more [tag] patterns at the beginning, with optional spaces
    pattern = r'^(\[[^\]]+\]\s*)+\s*'
    return re.sub(pattern, '', mod_name).strip()

def normalize_mod_name(mod_name):
    """Convert mod name to lowercase for case-insensitive comparisons."""
    return mod_name.lower()

def parse_modlist(file_path):
    mods = set()
    mod_to_section = {}
    section_order = []
    mod_buffer = []  # Buffer mods until we find their separator
    current_section = "Unsectioned"  # Default section for mods at the end without separator
    
    # Mappings for case-insensitive lookups
    normalized_to_original = {}  # normalized_name -> original_name
    normalized_to_section = {}   # normalized_name -> section
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('+') or line.startswith('-'):
                    mod_name = line[1:].strip()
                    
                    # Check if this is a separator
                    if mod_name.endswith('_separator'):
                        # Get section name and assign all buffered mods to this section
                        section_name = mod_name[:-10]  # Remove '_separator' suffix
                        
                        # Assign all buffered mods to this section
                        for buffered_mod, buffered_normalized in mod_buffer:
                            normalized_to_section[buffered_normalized] = section_name
                            mod_to_section[buffered_mod] = section_name
                        
                        # Track section order (sections are encountered in reverse order)
                        if section_name not in section_order:
                            section_order.insert(0, section_name)  # Insert at beginning to maintain proper order
                        
                        # Clear buffer
                        mod_buffer = []
                        continue
                    
                    # Strip tags from mod name before processing
                    clean_mod_name = strip_mod_tags(mod_name)
                    normalized_name = normalize_mod_name(clean_mod_name)
                    
                    # Regular mod - add to set and buffer for section assignment
                    mods.add(normalized_name)  # Use normalized name for set operations
                    normalized_to_original[normalized_name] = clean_mod_name
                    mod_buffer.append((clean_mod_name, normalized_name))
        
        # Handle any remaining mods in buffer (they belong to the default section)
        for buffered_mod, buffered_normalized in mod_buffer:
            normalized_to_section[buffered_normalized] = current_section
            mod_to_section[buffered_mod] = current_section
        if mod_buffer and current_section not in section_order:
            section_order.insert(0, current_section)  # Insert at beginning
                        
    except Exception as e:
        return None, None, None, None, None
    
    return mods, mod_to_section, section_order, normalized_to_original, normalized_to_section

def get_current_mod_versions(organizer):
    mod_versions = {}
    mod_to_section = {}
    section_order = []
    mod_buffer = []  # Buffer mods until we find their separator
    current_section = "Unsectioned"
    
    # Mappings for case-insensitive lookups
    normalized_to_original = {}  # normalized_name -> original_name
    normalized_to_section = {}   # normalized_name -> section
    normalized_versions = {}     # normalized_name -> version
    
    mod_list = organizer.modList()
    for mod_name in mod_list.allMods():
        # Check if this is a separator
        if mod_name.endswith('_separator'):
            # Get section name and assign all buffered mods to this section
            section_name = mod_name[:-10]  # Remove '_separator' suffix
            
            # Assign all buffered mods to this section
            for buffered_mod, buffered_normalized in mod_buffer:
                if buffered_normalized in normalized_versions:  # Only assign if mod was successfully processed
                    normalized_to_section[buffered_normalized] = section_name
                    mod_to_section[buffered_mod] = section_name
            
            # Track section order (sections are encountered in reverse order)
            if section_name not in section_order:
                section_order.insert(0, section_name)  # Insert at beginning to maintain proper order
            
            # Clear buffer
            mod_buffer = []
            continue
        
        # Strip tags from mod name before processing
        clean_mod_name = strip_mod_tags(mod_name)
        normalized_name = normalize_mod_name(clean_mod_name)
        
        # Regular mod - process version and buffer for section assignment
        mod = organizer.getMod(mod_name)  # Use original name for MO2 API calls
        if mod:
            version = mod.version().displayString() if mod.version() else "Unknown"
            mod_versions[clean_mod_name] = version  # Store with clean name for display
            normalized_versions[normalized_name] = version  # Store with normalized name for lookups
            normalized_to_original[normalized_name] = clean_mod_name
            mod_buffer.append((clean_mod_name, normalized_name))
    
    # Handle any remaining mods in buffer (they belong to the default section)
    for buffered_mod, buffered_normalized in mod_buffer:
        if buffered_normalized in normalized_versions:  # Only assign if mod was successfully processed
            normalized_to_section[buffered_normalized] = current_section
            mod_to_section[buffered_mod] = current_section
    if mod_buffer and current_section not in section_order:
        section_order.insert(0, current_section)  # Insert at beginning
    
    # Return normalized set for comparisons, but keep original mappings for display
    normalized_mods = set(normalized_versions.keys())
    return (mod_versions, mod_to_section, section_order, 
            normalized_to_original, normalized_to_section, 
            normalized_mods, normalized_versions)

def load_versions(file_path):
    if not file_path:
        return None, None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            versions = json.load(f)
            # Create normalized version mapping
            normalized_versions = {}
            normalized_to_original = {}
            for mod_name, version in versions.items():
                normalized_name = normalize_mod_name(mod_name)
                normalized_versions[normalized_name] = version
                normalized_to_original[normalized_name] = mod_name
            return versions, normalized_versions, normalized_to_original
    except Exception as e:
        return None, None, None

def organize_mods_by_section(mods, mod_to_section, section_order, normalized_to_original):
    """Organize mods by their sections, preserving section order and alphabetizing within sections"""
    sectioned_mods = {}
    
    # Group mods by section
    for normalized_mod in mods:
        original_mod = normalized_to_original.get(normalized_mod, normalized_mod)
        section = mod_to_section.get(original_mod, "Unsectioned")
        if section not in sectioned_mods:
            sectioned_mods[section] = []
        sectioned_mods[section].append(original_mod)
    
    # Sort mods within each section (case-insensitive)
    for section in sectioned_mods:
        sectioned_mods[section].sort(key=str.lower)
    
    # Return sections in order
    ordered_sections = []
    for section in section_order:
        if section in sectioned_mods:
            ordered_sections.append((section, sectioned_mods[section]))
    
    # Add any sections not in the order (shouldn't happen, but just in case)
    for section, mods_list in sectioned_mods.items():
        if section not in section_order:
            ordered_sections.append((section, mods_list))
    
    return ordered_sections

def generate_changelog(old_mods, new_mods, old_mod_to_section=None, new_mod_to_section=None, 
                      old_section_order=None, new_section_order=None, 
                      old_versions=None, new_versions=None,
                      old_normalized_to_original=None, new_normalized_to_original=None,
                      old_normalized_to_section=None, new_normalized_to_section=None):
    if old_mods is None or new_mods is None:
        return None
    
    # Perform set operations on normalized names
    added = new_mods - old_mods
    removed = old_mods - new_mods
    common = old_mods & new_mods
    updated = []
    
    # For version comparisons, use normalized lookups
    if old_versions and new_versions:
        for normalized_mod in common:
            old_v = old_versions.get(normalized_mod, "Unknown")
            new_v = new_versions.get(normalized_mod, "Unknown")
            if old_v != new_v:
                # Get original name for display
                original_mod = new_normalized_to_original.get(normalized_mod, normalized_mod)
                updated.append((original_mod, old_v, new_v))
    
    markdown = "# Modlist Changelog\n\n"
    
    markdown += "### Summary\n"
    markdown += f"- **Added:** {len(added)} mods\n"
    markdown += f"- **Removed:** {len(removed)} mods\n"
    markdown += f"- **Updated:** {len(updated)} mods\n\n"
    
    # Added Mods - organized by new sections
    markdown += "## Added Mods\n\n"
    if added and new_mod_to_section and new_section_order and new_normalized_to_original:
        sectioned_added = organize_mods_by_section(added, new_mod_to_section, new_section_order, new_normalized_to_original)
        if sectioned_added:
            for section, mods_list in sectioned_added:
                markdown += f"### {section}\n"
                markdown += "\n".join(f"- {mod}" for mod in mods_list) + "\n\n"
        else:
            markdown += "No mods added.\n\n"
    elif added:
        # Fallback to flat list if no section data
        # Convert normalized names back to original names for display
        added_originals = []
        for normalized_mod in added:
            original_mod = new_normalized_to_original.get(normalized_mod, normalized_mod) if new_normalized_to_original else normalized_mod
            added_originals.append(original_mod)
        sorted_added = sorted(added_originals, key=str.lower)
        markdown += "\n".join(f"- {mod}" for mod in sorted_added) + "\n\n"
    else:
        markdown += "No mods added.\n\n"
    
    # Removed Mods - organized by old sections
    markdown += "## Removed Mods\n\n"
    if removed and old_mod_to_section and old_section_order and old_normalized_to_original:
        sectioned_removed = organize_mods_by_section(removed, old_mod_to_section, old_section_order, old_normalized_to_original)
        if sectioned_removed:
            for section, mods_list in sectioned_removed:
                markdown += f"### {section}\n"
                markdown += "\n".join(f"- {mod}" for mod in mods_list) + "\n\n"
        else:
            markdown += "No mods removed.\n\n"
    elif removed:
        # Fallback to flat list if no section data
        # Convert normalized names back to original names for display
        removed_originals = []
        for normalized_mod in removed:
            original_mod = old_normalized_to_original.get(normalized_mod, normalized_mod) if old_normalized_to_original else normalized_mod
            removed_originals.append(original_mod)
        sorted_removed = sorted(removed_originals, key=str.lower)
        markdown += "\n".join(f"- {mod}" for mod in sorted_removed) + "\n\n"
    else:
        markdown += "No mods removed.\n\n"
    
    # Updated Mods - flat list as requested
    markdown += "## Updated Mods\n\n"
    if updated:
        # Sort by mod name (case-insensitive)
        updated.sort(key=lambda x: x[0].lower())
        for mod, old_v, new_v in updated:
            markdown += f"- {mod}: {old_v} → {new_v}\n"
        markdown += "\n"
    else:
        markdown += "No mods updated.\n\n"
    
    return markdown

class ComparerDialog(QDialog):
    def __init__(self, parent, organizer):
        super().__init__(parent)
        self.organizer = organizer
        self.setWindowTitle("Changelog Helper")
        self.setMinimumWidth(600)  # Make the dialog wider by default
        
        layout = QVBoxLayout(self)
        
        # Modlists
        h1 = QHBoxLayout()
        lbl1 = QLabel("Old modlist:")
        self.old_modlist_edit = QLineEdit()
        btn1 = QPushButton("Browse")
        btn1.clicked.connect(self.select_old_modlist)
        h1.addWidget(lbl1)
        h1.addWidget(self.old_modlist_edit)
        h1.addWidget(btn1)
        layout.addLayout(h1)
        
        h2 = QHBoxLayout()
        lbl2 = QLabel("New modlist:")
        self.new_modlist_edit = QLineEdit()
        current_profile_path = self.organizer.profilePath()
        modlist_path = os.path.join(current_profile_path, "modlist.txt")
        if os.path.exists(modlist_path):
            self.new_modlist_edit.setText(modlist_path)
        btn2 = QPushButton("Browse")
        btn2.clicked.connect(self.select_new_modlist)
        h2.addWidget(lbl2)
        h2.addWidget(self.new_modlist_edit)
        h2.addWidget(btn2)
        layout.addLayout(h2)
        
        # Versions
        h3 = QHBoxLayout()
        lbl3 = QLabel("Old versions:")
        self.old_versions_edit = QLineEdit()
        btn3 = QPushButton("Browse")
        btn3.clicked.connect(self.select_old_versions)
        h3.addWidget(lbl3)
        h3.addWidget(self.old_versions_edit)
        h3.addWidget(btn3)
        layout.addLayout(h3)
        
        # Buttons
        btn_layout = QHBoxLayout()
        export_btn = QPushButton("Export Current Versions")
        export_btn.clicked.connect(self.export_current_versions)
        gen_btn = QPushButton("Generate Changelog")
        gen_btn.clicked.connect(self.generate)
        btn_layout.addWidget(export_btn)
        btn_layout.addWidget(gen_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def select_old_modlist(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Old modlist.txt", "", "Text files (*.txt)")
        if path:
            self.old_modlist_edit.setText(path)
    
    def select_new_modlist(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select New modlist.txt", "", "Text files (*.txt)")
        if path:
            self.new_modlist_edit.setText(path)
    
    def select_old_versions(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Old versions.json", "", "JSON files (*.json)")
        if path:
            self.old_versions_edit.setText(path)
    
    def export_current_versions(self):
        result = get_current_mod_versions(self.organizer)
        mod_versions = result[0]  # Original versions mapping for export
        
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Current Versions", "versions.json", "JSON files (*.json)")
        if save_path:
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(mod_versions, f, indent=4, sort_keys=True)
                QMessageBox.information(self, "Success", f"Versions exported to {save_path}")
            except Exception as e:
                QMessageBox.error(self, "Error", str(e))
    
    def generate(self):
        old_modlist_file = self.old_modlist_edit.text()
        new_modlist_file = self.new_modlist_edit.text()
        
        # Parse modlists with section data
        if old_modlist_file:
            old_result = parse_modlist(old_modlist_file)
            if old_result[0] is not None:
                (old_mods, old_mod_to_section, old_section_order, 
                 old_normalized_to_original, old_normalized_to_section) = old_result
            else:
                old_mods = old_mod_to_section = old_section_order = None
                old_normalized_to_original = old_normalized_to_section = None
        else:
            old_mods = old_mod_to_section = old_section_order = None
            old_normalized_to_original = old_normalized_to_section = None
            
        if new_modlist_file:
            new_result = parse_modlist(new_modlist_file)
            if new_result[0] is not None:
                (new_mods, new_mod_to_section, new_section_order,
                 new_normalized_to_original, new_normalized_to_section) = new_result
            else:
                new_mods = new_mod_to_section = new_section_order = None
                new_normalized_to_original = new_normalized_to_section = None
        else:
            new_mods = new_mod_to_section = new_section_order = None
            new_normalized_to_original = new_normalized_to_section = None
        
        # Load old versions
        old_versions_file = self.old_versions_edit.text()
        if old_versions_file:
            old_versions_result = load_versions(old_versions_file)
            if old_versions_result[0] is not None:
                _, old_normalized_versions, old_norm_to_orig_versions = old_versions_result
                # Update original mappings if we don't have them from modlist
                if old_normalized_to_original is None:
                    old_normalized_to_original = old_norm_to_orig_versions
            else:
                QMessageBox.error(self, "Error", "Failed to load old versions.")
                return
        else:
            old_normalized_versions = None
        
        # Get current versions with section data
        current_result = get_current_mod_versions(self.organizer)
        (new_versions_display, new_mod_to_section_from_mo2, new_section_order_from_mo2,
         new_normalized_to_original_from_mo2, new_normalized_to_section_from_mo2,
         new_mods_from_mo2, new_normalized_versions) = current_result
        
        # Use MO2 section data if we don't have new modlist file
        if new_mod_to_section is None:
            new_mod_to_section = new_mod_to_section_from_mo2
            new_section_order = new_section_order_from_mo2
            new_normalized_to_original = new_normalized_to_original_from_mo2
            new_normalized_to_section = new_normalized_to_section_from_mo2
        
        # Set up mod sets for comparison (use normalized versions)
        if old_mods is None and old_normalized_versions:
            old_mods = set(old_normalized_versions.keys())
        if new_mods is None:
            new_mods = new_mods_from_mo2
        
        if old_mods is None or new_mods is None:
            QMessageBox.warning(self, "Warning", "Insufficient data for comparison.")
            return
        
        # Generate changelog with section data
        markdown = generate_changelog(
            old_mods, new_mods, 
            old_mod_to_section, new_mod_to_section,
            old_section_order, new_section_order,
            old_normalized_versions, new_normalized_versions,
            old_normalized_to_original, new_normalized_to_original,
            old_normalized_to_section, new_normalized_to_section
        )
        
        if markdown is None:
            return
        
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Changelog", "changelog.md", "Markdown files (*.md)")
        if save_path:
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(markdown)
                QMessageBox.information(self, "Success", f"Saved to {save_path}")
            except Exception as e:
                QMessageBox.error(self, "Error", str(e))

class ChangelogTool(mobase.IPluginTool):
    def __init__(self):
        super().__init__()
        self.__organizer = None
        self.__parentWidget = None
    
    def init(self, organizer):
        self.__organizer = organizer
        return True
    
    def name(self):
        return "Changelog Helper"
    
    def author(self):
        return "Bottle"
    
    def description(self):
        return "A tool to compare modlists/versions and generate a changelog in Markdown format."
    
    def version(self):
        return mobase.VersionInfo(1, 4, 0)
    
    def settings(self):
        return []
    
    def displayName(self):
        return "Changelog Helper"
    
    def tooltip(self):
        return "Compare modlists and generate changelog"
    
    def icon(self):
        return QIcon()
    
    def setParentWidget(self, widget):
        self.__parentWidget = widget
    
    def display(self):
        dialog = ComparerDialog(self.__parentWidget, self.__organizer)
        dialog.exec()

def createPlugin():
    return ChangelogTool()
