import mobase
import os
from pathlib import Path
from collections import defaultdict
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

class PBRCoverageChecker(mobase.IPluginTool):
    def __init__(self):
        super().__init__()
        self.__organizer = None
        self.__parentWidget = None
    

    def init(self, organizer):
        self.__organizer = organizer
        return True

    def name(self):
        return "PBR Coverage Checker"

    def localizedName(self):
        return "PBR Coverage Checker"

    def author(self):
        return "Claude"

    def description(self):
        return "Identifies texture mods that may be redundant due to PBR texture coverage"

    def version(self):
        return mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.FINAL)

    def requirements(self):
        return []

    def settings(self):
        return []

    def displayName(self):
        return "PBR Coverage Checker"

    def tooltip(self):
        return "Check which texture mods are covered by PBR replacers"

    def icon(self):
        return QIcon()

    def setParentWidget(self, widget):
        self.__parentWidget = widget

    def display(self):
        try:
            # Get all enabled mods
            mod_list = self.__organizer.modList()
            enabled_mods = []
            
            for mod_name in mod_list.allMods():
                if mod_list.state(mod_name) & mobase.ModState.ACTIVE:
                    mod = self.__organizer.getMod(mod_name)
                    if mod:
                        enabled_mods.append((mod_name, mod.absolutePath()))

            # Scan for texture files
            pbr_textures = set()
            regular_textures = defaultdict(list)
            debug_info = []
            
            for mod_name, mod_path in enabled_mods:
                self._scan_mod_textures(mod_name, mod_path, pbr_textures, regular_textures, debug_info)

            # Find coverage
            covered_mods = self._find_covered_mods(pbr_textures, regular_textures)
            
            # Display results (with debug info)
            self._show_results(covered_mods, pbr_textures, regular_textures, enabled_mods, debug_info)

        except Exception as e:
            QMessageBox.critical(self.__parentWidget, "Error", f"Failed to analyze PBR coverage: {str(e)}")

    def _scan_mod_textures(self, mod_name, mod_path, pbr_textures, regular_textures, debug_info):
        textures_path = Path(mod_path) / "textures"
        if not textures_path.exists():
            return

        # Debug: Check if this might be a PBR mod
        pbr_path = textures_path / "pbr"
        if pbr_path.exists():
            debug_info.append(f"Found PBR folder in '{mod_name}' at {pbr_path}")

        # PASS 1: Find all PBR textures first
        pbr_count = 0
        pbr_files_checked = 0
        for dds_file in textures_path.rglob("*.dds"):
            relative_path = dds_file.relative_to(textures_path)
            path_str = str(relative_path).lower().replace('\\', '/')
            
            # Debug: show first few paths from Amidianborn PBR to see what we're getting
            if mod_name == "Amidianborn PBR" and pbr_files_checked < 10:
                debug_info.append(f"Sample path in {mod_name}: '{path_str}'")
                pbr_files_checked += 1
            
            if path_str.startswith('pbr/') or '/pbr/' in path_str:
                # Skip only normal maps for PBR textures
                if dds_file.stem.endswith('_n'):
                    continue
                
                # Create base texture name by removing PBR-specific suffixes
                base_name = dds_file.stem
                # Remove PBR-specific suffixes like _rmaos, _m, _s, etc. but keep the core name
                for suffix in ['_rmaos', '_m', '_s', '_g', '_p', '_e']:
                    if base_name.endswith(suffix):
                        base_name = base_name[:-len(suffix)]
                        break
                
                # Normalize path: remove /pbr/ and use base name
                path_parts = path_str.split('/')
                normalized_parts = [part for part in path_parts if part != 'pbr']
                normalized_parts[-1] = base_name + '.dds'  # Replace filename with base name
                normalized_path = '/'.join(normalized_parts)
                
                pbr_textures.add(normalized_path)
                pbr_count += 1
                
                # Debug first few PBR textures
                if pbr_count <= 5:
                    debug_info.append(f"PBR: {path_str} -> {normalized_path}")
        
        # PASS 2: Find regular textures
        regular_count = 0
        for dds_file in textures_path.rglob("*.dds"):
            relative_path = dds_file.relative_to(textures_path)
            path_str = str(relative_path).lower().replace('\\', '/')
            
            # Skip PBR textures (already processed)
            if path_str.startswith('pbr/') or '/pbr/' in path_str:
                continue
                
            # Skip variant maps for regular textures
            if any(dds_file.stem.endswith(suffix) for suffix in ['_n', '_m', '_s', '_g', '_p', '_e']):
                continue
                
            regular_textures[path_str].append(mod_name)
            regular_count += 1
        
        # Debug output
        total_textures = sum(1 for _ in textures_path.rglob("*.dds"))
        if total_textures > 0:
            debug_info.append(f"'{mod_name}': {total_textures} total, {pbr_count} PBR, {regular_count} regular textures")

    def _find_covered_mods(self, pbr_textures, regular_textures):
        covered_mods = defaultdict(list)
        
        for texture_path, mod_names in regular_textures.items():
            if texture_path in pbr_textures:
                for mod_name in mod_names:
                    covered_mods[mod_name].append(texture_path)
        
        return covered_mods

    def _show_results(self, covered_mods, pbr_textures, regular_textures, enabled_mods, debug_info):
        dialog = QDialog(self.__parentWidget)
        dialog.setWindowTitle("PBR Coverage Analysis")
        dialog.resize(800, 600)
        
        layout = QVBoxLayout(dialog)
        
        # Summary
        total_regular_textures = sum(len(mods) for mods in regular_textures.values())
        summary_text = f"Scanned {len(enabled_mods)} enabled mods.\nFound {len(pbr_textures)} PBR textures and {total_regular_textures} regular texture files across {len(regular_textures)} unique paths."
        layout.addWidget(QLabel(summary_text))
        
        # Debug info
        debug_text = QTextEdit()
        debug_text.setReadOnly(True)
        debug_text.setMaximumHeight(200)
        debug_display = "DEBUG INFO:\n"
        debug_display += f"Sample PBR textures: {list(pbr_textures)[:5]}\n"
        debug_display += f"Sample regular textures: {list(regular_textures.keys())[:5]}\n\n"
        debug_display += "Scan Details:\n" + "\n".join(debug_info[:20])
        debug_text.setPlainText(debug_display)
        layout.addWidget(debug_text)
        
        # Results
        if covered_mods:
            layout.addWidget(QLabel("Potentially Redundant Mods:"))
            
            results_widget = QTextEdit()
            results_widget.setReadOnly(True)
            results_text = ""
            
            for mod_name, covered_textures in covered_mods.items():
                coverage_percent = len(covered_textures) / len([p for p, mods in regular_textures.items() if mod_name in mods]) * 100
                results_text += f"\n{mod_name} - {len(covered_textures)} textures covered ({coverage_percent:.1f}%)\n"
                
                # Show some example covered textures
                for texture in sorted(covered_textures)[:5]:
                    results_text += f"  • {texture}\n"
                if len(covered_textures) > 5:
                    results_text += f"  ... and {len(covered_textures) - 5} more\n"
            
            results_widget.setPlainText(results_text)
            layout.addWidget(results_widget)
        else:
            layout.addWidget(QLabel("No redundant mods found - no regular texture mods are covered by PBR textures."))
        
        # Buttons
        button_layout = QHBoxLayout()
        
        export_btn = QPushButton("Export Results")
        export_btn.clicked.connect(lambda: self._export_results(covered_mods, regular_textures))
        button_layout.addWidget(export_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec()

    def _export_results(self, covered_mods, regular_textures):
        file_path, _ = QFileDialog.getSaveFileName(
            self.__parentWidget,
            "Export PBR Coverage Results",
            "pbr_coverage_analysis.txt",
            "Text Files (*.txt)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("PBR Coverage Analysis Results\n")
                    f.write("=" * 40 + "\n\n")
                    
                    if covered_mods:
                        f.write("Potentially Redundant Mods:\n\n")
                        for mod_name, covered_textures in covered_mods.items():
                            total_textures = len([p for p, mods in regular_textures.items() if mod_name in mods])
                            coverage_percent = len(covered_textures) / total_textures * 100
                            
                            f.write(f"{mod_name}\n")
                            f.write(f"  Coverage: {len(covered_textures)}/{total_textures} textures ({coverage_percent:.1f}%)\n")
                            f.write("  Covered textures:\n")
                            for texture in sorted(covered_textures):
                                f.write(f"    - {texture}\n")
                            f.write("\n")
                    else:
                        f.write("No redundant mods found.\n")
                
                QMessageBox.information(self.__parentWidget, "Export Complete", f"Results exported to {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self.__parentWidget, "Export Error", f"Failed to export results: {str(e)}")

def createPlugin():
    return PBRCoverageChecker()