"""
Tree view dialog for MO2 Tag Manager.
Provides expandable sections with individual mod selection.
"""

try:
    from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, 
                                QTreeWidgetItem, QPushButton, QLabel, QLineEdit,
                                QMessageBox, QGroupBox, QCheckBox, QComboBox,
                                QProgressDialog, QApplication, QSplitter)
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QFont
except ImportError:
    from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, 
                                QTreeWidgetItem, QPushButton, QLabel, QLineEdit,
                                QMessageBox, QGroupBox, QCheckBox, QComboBox,
                                QProgressDialog, QApplication, QSplitter)
    from PyQt5.QtCore import Qt, QTimer
    from PyQt5.QtGui import QFont

from .utils import ModSectionUtils, parse_mod_tags, build_mod_name, strip_numerical_index


class TagManagerTreeDialog(QDialog):
    def __init__(self, parent, organizer):
        super().__init__(parent)
        self.organizer = organizer
        self.modList = organizer.modList()
        
        self.setWindowTitle("MO2 Tag Manager")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        
        # Analyze current mod organization
        self.sections, self.section_order, self.separator_map = ModSectionUtils.analyze_mod_organization(self.modList)
        
        self._setup_ui()
        self._populate_tree()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Title and description
        title_label = QLabel("MO2 Tag Manager - Select mods and separators to manage tags")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)
        
        desc_label = QLabel("Select individual mods or entire sections. Separators can also be tagged.\n"
                           "Tag order: [NoDelete] [index] [custom tags] Mod Name")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Main splitter for tree and controls
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Item", "Current Tags"])
        self.tree.setColumnWidth(0, 400)
        splitter.addWidget(self.tree)
        
        # Controls panel
        controls_widget = self._create_controls_panel()
        splitter.addWidget(controls_widget)
        
        # Set splitter proportions
        splitter.setStretchFactor(0, 3)  # Tree gets more space
        splitter.setStretchFactor(1, 1)  # Controls get less space
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all)
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self._deselect_all)
        expand_all_btn = QPushButton("Expand All")
        expand_all_btn.clicked.connect(self.tree.expandAll)
        collapse_all_btn = QPushButton("Collapse All")
        collapse_all_btn.clicked.connect(self.tree.collapseAll)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(deselect_all_btn)
        button_layout.addWidget(expand_all_btn)
        button_layout.addWidget(collapse_all_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
    
    def _create_controls_panel(self):
        """Create the controls panel for tag operations."""
        controls_widget = QGroupBox("Tag Operations")
        layout = QVBoxLayout(controls_widget)
        
        # NoDelete tag controls
        nodelete_group = QGroupBox("[NoDelete] Tags")
        nodelete_layout = QVBoxLayout(nodelete_group)
        
        # Auto-index option
        self.auto_index_checkbox = QCheckBox("Also add numerical indexes")
        self.auto_index_checkbox.setToolTip("Automatically add [xxx.xxxxx] indexes when adding [NoDelete] tags")
        nodelete_layout.addWidget(self.auto_index_checkbox)
        
        add_nodelete_btn = QPushButton("Add [NoDelete] Tags")
        add_nodelete_btn.clicked.connect(lambda: self._apply_nodelete_tags(True))
        remove_nodelete_btn = QPushButton("Remove [NoDelete] Tags")
        remove_nodelete_btn.clicked.connect(lambda: self._apply_nodelete_tags(False))
        
        nodelete_layout.addWidget(add_nodelete_btn)
        nodelete_layout.addWidget(remove_nodelete_btn)
        layout.addWidget(nodelete_group)
        
        # Index controls
        index_group = QGroupBox("Numerical Indexes")
        index_layout = QVBoxLayout(index_group)
        
        add_indexes_btn = QPushButton("Add Indexes")
        add_indexes_btn.clicked.connect(self._add_indexes)
        remove_indexes_btn = QPushButton("Remove Indexes")
        remove_indexes_btn.clicked.connect(self._remove_indexes)
        
        index_layout.addWidget(add_indexes_btn)
        index_layout.addWidget(remove_indexes_btn)
        layout.addWidget(index_group)
        
        # Custom tag controls
        custom_group = QGroupBox("Custom Tags")
        custom_layout = QVBoxLayout(custom_group)
        
        # Tag input
        self.custom_tag_input = QLineEdit()
        self.custom_tag_input.setPlaceholderText("Enter custom tag name...")
        custom_layout.addWidget(QLabel("Custom Tag:"))
        custom_layout.addWidget(self.custom_tag_input)
        
        # Common presets
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["", "Favorites", "Essential", "Optional", "Testing", "WIP"])
        self.preset_combo.currentTextChanged.connect(lambda text: self.custom_tag_input.setText(text))
        custom_layout.addWidget(QLabel("Quick Presets:"))
        custom_layout.addWidget(self.preset_combo)
        
        add_custom_btn = QPushButton("Add Custom Tag")
        add_custom_btn.clicked.connect(self._add_custom_tag)
        remove_custom_btn = QPushButton("Remove Custom Tag")
        remove_custom_btn.clicked.connect(self._remove_custom_tag)
        
        custom_layout.addWidget(add_custom_btn)
        custom_layout.addWidget(remove_custom_btn)
        layout.addWidget(custom_group)
        
        # Strip all tags
        strip_group = QGroupBox("Cleanup")
        strip_layout = QVBoxLayout(strip_group)
        
        strip_all_btn = QPushButton("Remove All Tags")
        strip_all_btn.clicked.connect(self._strip_all_tags)
        strip_all_btn.setStyleSheet("QPushButton { color: red; }")
        
        strip_layout.addWidget(strip_all_btn)
        layout.addWidget(strip_group)
        
        return controls_widget
    
    def _populate_tree(self):
        """Populate the tree with sections and mods."""
        self.tree.clear()
        
        # Display sections in reverse order (top to bottom in UI)
        display_order = list(reversed(self.section_order))
        
        for section in display_order:
            # Create section item (separator)
            section_item = QTreeWidgetItem(self.tree)
            separator_name = self.separator_map.get(section, section)
            
            # Parse separator tags
            separator_obj = self.modList.getMod(separator_name) if separator_name in [m for m in self.modList.allMods()] else None
            if separator_obj:
                tags_info = parse_mod_tags(separator_obj.name())
                tags_display = self._format_tags_display(tags_info)
                section_item.setText(0, f"[Separator] {tags_info['clean_name']}")
                section_item.setText(1, tags_display)
            else:
                section_item.setText(0, f"[Separator] {section}")
                section_item.setText(1, "")
            
            section_item.setCheckState(0, Qt.CheckState.Unchecked)
            section_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'separator', 'name': separator_name, 'section': section})
            
            # Make separator bold
            font = section_item.font(0)
            font.setBold(True)
            section_item.setFont(0, font)
            
            # Add mods in this section
            mods_in_section = self.sections.get(section, [])
            for mod_name in mods_in_section:
                mod_obj = self.modList.getMod(mod_name)
                if mod_obj:
                    mod_item = QTreeWidgetItem(section_item)
                    tags_info = parse_mod_tags(mod_obj.name())
                    tags_display = self._format_tags_display(tags_info)
                    
                    mod_item.setText(0, tags_info['clean_name'])
                    mod_item.setText(1, tags_display)
                    mod_item.setCheckState(0, Qt.CheckState.Unchecked)
                    mod_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'mod', 'name': mod_name, 'section': section})
        
        # Expand all by default
        self.tree.expandAll()
    
    def _format_tags_display(self, tags_info):
        """Format tags for display in the tree."""
        tags = []
        if tags_info['nodelete']:
            tags.append("[NoDelete]")
        if tags_info['index']:
            tags.append(f"[{tags_info['index']}]")
        for custom in tags_info['custom_tags']:
            tags.append(f"[{custom}]")
        return " ".join(tags)
    
    def _get_selected_items(self):
        """Get all selected items from the tree."""
        selected = []
        
        def check_item(item):
            if item.checkState(0) == Qt.CheckState.Checked:
                selected.append(item.data(0, Qt.ItemDataRole.UserRole))
            
            for i in range(item.childCount()):
                check_item(item.child(i))
        
        for i in range(self.tree.topLevelItemCount()):
            check_item(self.tree.topLevelItem(i))
        
        return selected
    
    def _select_all(self):
        """Select all items."""
        def set_checked(item, checked):
            item.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            for i in range(item.childCount()):
                set_checked(item.child(i), checked)
        
        for i in range(self.tree.topLevelItemCount()):
            set_checked(self.tree.topLevelItem(i), True)
    
    def _deselect_all(self):
        """Deselect all items."""
        def set_checked(item, checked):
            item.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            for i in range(item.childCount()):
                set_checked(item.child(i), checked)
        
        for i in range(self.tree.topLevelItemCount()):
            set_checked(self.tree.topLevelItem(i), False)
    
    def _apply_nodelete_tags(self, add_tags):
        """Add or remove [NoDelete] tags from selected items."""
        selected = self._get_selected_items()
        if not selected:
            QMessageBox.information(self, "No Selection", "Please select items to modify.")
            return
        
        also_add_indexes = add_tags and self.auto_index_checkbox.isChecked()
        operation = "Adding [NoDelete] Tags" + (" and Indexes" if also_add_indexes else "")
        if not add_tags:
            operation = "Removing [NoDelete] Tags"
        
        self._process_tag_operation(selected, operation, lambda tags, item: self._modify_nodelete_tag(tags, add_tags, also_add_indexes))
    
    def _add_indexes(self):
        """Add numerical indexes to selected items."""
        selected = self._get_selected_items()
        if not selected:
            QMessageBox.information(self, "No Selection", "Please select items to add indexes to.")
            return
        
        self._process_tag_operation(selected, "Adding Indexes", self._modify_add_index)
    
    def _remove_indexes(self):
        """Remove numerical indexes from selected items."""
        selected = self._get_selected_items()
        if not selected:
            QMessageBox.information(self, "No Selection", "Please select items to remove indexes from.")
            return
        
        self._process_tag_operation(selected, "Removing Indexes", self._modify_remove_index)
    
    def _add_custom_tag(self):
        """Add custom tag to selected items."""
        custom_tag = self.custom_tag_input.text().strip()
        if not custom_tag:
            QMessageBox.information(self, "No Tag", "Please enter a custom tag name.")
            return
        
        selected = self._get_selected_items()
        if not selected:
            QMessageBox.information(self, "No Selection", "Please select items to add the custom tag to.")
            return
        
        self._process_tag_operation(selected, f"Adding [{custom_tag}]", lambda tags, item: self._modify_add_custom_tag(tags, custom_tag))
    
    def _remove_custom_tag(self):
        """Remove custom tag from selected items."""
        custom_tag = self.custom_tag_input.text().strip()
        if not custom_tag:
            QMessageBox.information(self, "No Tag", "Please enter the custom tag name to remove.")
            return
        
        selected = self._get_selected_items()
        if not selected:
            QMessageBox.information(self, "No Selection", "Please select items to remove the custom tag from.")
            return
        
        self._process_tag_operation(selected, f"Removing [{custom_tag}]", lambda tags, item: self._modify_remove_custom_tag(tags, custom_tag))
    
    def _strip_all_tags(self):
        """Remove all tags from selected items."""
        selected = self._get_selected_items()
        if not selected:
            QMessageBox.information(self, "No Selection", "Please select items to remove all tags from.")
            return
        
        reply = QMessageBox.question(
            self, "Confirm", 
            f"This will remove ALL tags from {len(selected)} selected items. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._process_tag_operation(selected, "Removing All Tags", self._modify_strip_all)
    
    def _process_tag_operation(self, selected_items, operation_name, modify_function):
        """Process tag operations using LazyModlist approach."""
        processed_count = 0
        skipped_count = 0
        errors = []
        
        # Show pre-processing message
        QMessageBox.information(
            self, 
            operation_name, 
            f"{operation_name} for {len(selected_items)} selected items...\n\n"
            "The interface will be unresponsive briefly while processing.\n"
            "Click OK to continue."
        )
        
        try:
            for item_data in selected_items:
                try:
                    mod_name = item_data['name']
                    mod_obj = self.modList.getMod(mod_name)
                    if not mod_obj:
                        continue
                    
                    current_name = mod_obj.name()
                    tags_info = parse_mod_tags(current_name)
                    
                    # Apply modification
                    new_tags_info = modify_function(tags_info, item_data)
                    
                    # Handle auto-indexing for NoDelete operations
                    if hasattr(self, 'auto_index_checkbox') and self.auto_index_checkbox.isChecked():
                        if 'Adding [NoDelete] Tags' in operation_name and new_tags_info['nodelete']:
                            new_tags_info = self._modify_add_index(new_tags_info, item_data)
                    
                    if new_tags_info:
                        new_name = build_mod_name(
                            new_tags_info['clean_name'],
                            new_tags_info['nodelete'],
                            new_tags_info['index'],
                            new_tags_info['custom_tags']
                        )
                        
                        if new_name != current_name:
                            self.modList.renameMod(mod_obj, new_name)
                            processed_count += 1
                        else:
                            skipped_count += 1
                    else:
                        skipped_count += 1
                        
                except Exception as e:
                    errors.append(f"Error processing '{mod_name}': {str(e)}")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
            return
        
        # Show completion message
        message = f"Successfully {operation_name.lower()} on {processed_count} items."
        if skipped_count > 0:
            message += f"\n{skipped_count} items were skipped (no changes needed)."
        if errors:
            message += f"\n{len(errors)} errors occurred."
        
        QMessageBox.information(self, "Complete", message)
        
        # Refresh and repopulate
        self.organizer.refresh()
        self._populate_tree()
    
    def _modify_nodelete_tag(self, tags_info, add_tag, also_add_indexes=False):
        """Modify NoDelete tag in tags_info."""
        if add_tag:
            tags_info['nodelete'] = True
            # Add index if requested
            if also_add_indexes:
                # This will be calculated in the calling context
                pass
        else:
            tags_info['nodelete'] = False
            # Also remove indexes when removing NoDelete
            tags_info['index'] = None
        return tags_info
    
    def _modify_add_index(self, tags_info, item_data):
        """Add numerical index to tags_info."""
        section = item_data['section']
        item_type = item_data['type']
        
        # Create section index mapping
        display_order = list(reversed(self.section_order))
        section_index = display_order.index(section) + 1 if section in display_order else 0
        
        if item_type == 'separator':
            position_index = 0
        else:
            # Calculate position within section
            mods_in_section = self.sections.get(section, [])
            try:
                position_index = len(mods_in_section) - mods_in_section.index(item_data['name'])
            except ValueError:
                position_index = 1
        
        tags_info['index'] = f"{section_index:03d}.{position_index:05d}"
        return tags_info
    
    def _modify_remove_index(self, tags_info, item_data):
        """Remove numerical index from tags_info."""
        tags_info['index'] = None
        return tags_info
    
    def _modify_add_custom_tag(self, tags_info, custom_tag):
        """Add custom tag to tags_info."""
        if custom_tag not in tags_info['custom_tags']:
            tags_info['custom_tags'].append(custom_tag)
        return tags_info
    
    def _modify_remove_custom_tag(self, tags_info, custom_tag):
        """Remove custom tag from tags_info."""
        if custom_tag in tags_info['custom_tags']:
            tags_info['custom_tags'].remove(custom_tag)
        return tags_info
    
    def _modify_strip_all(self, tags_info, item_data):
        """Remove all tags from tags_info."""
        tags_info['nodelete'] = False
        tags_info['index'] = None
        tags_info['custom_tags'] = []
        return tags_info