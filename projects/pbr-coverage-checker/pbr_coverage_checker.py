import mobase
import os
import json
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
        return "Uses PBRNifPatcher folders to identify texture mods covered by PBR replacers"

    def version(self):
        return mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.FINAL)

    def requirements(self):
        return []

    def settings(self):
        return []

    def displayName(self):
        return "PBR Coverage Checker"

    def tooltip(self):
        return "Scan PBRNifPatcher folders to find texture mods covered by PBR replacers"

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

            # Scan for PBR coverage using PBRNifPatcher folders
            pbr_covered_textures = defaultdict(set)  # {texture_path: {providing_mod1, providing_mod2}}
            regular_textures = defaultdict(list)
            debug_info = []
            
            for mod_name, mod_path in enabled_mods:
                self._scan_pbr_coverage(mod_name, mod_path, pbr_covered_textures, debug_info)
                self._scan_regular_textures(mod_name, mod_path, regular_textures, debug_info)

            # Find coverage
            covered_mods, uncovered_mods, coverage_providers = self._find_coverage_analysis(pbr_covered_textures, regular_textures)
            
            # Display results (with debug info)
            self._show_results(covered_mods, uncovered_mods, coverage_providers, pbr_covered_textures, regular_textures, enabled_mods, debug_info)

        except Exception as e:
            QMessageBox.critical(self.__parentWidget, "Error", f"Failed to analyze PBR coverage: {str(e)}")

    def _scan_pbr_coverage(self, mod_name, mod_path, pbr_covered_textures, debug_info):
        # pbr_covered_textures is now a dict: {texture_path: set of providing mods}
        pbr_patcher_path = Path(mod_path) / "PBRNifPatcher"
        if not pbr_patcher_path.exists():
            return
            
        debug_info.append(f"Found PBRNifPatcher folder in '{mod_name}'")
        
        # Patterns that PG Patcher doesn't patch (exclude from coverage analysis)
        excluded_patterns = ['cameras', 'dyndolod', 'lod', 'markers']
        
        json_count = 0
        excluded_count = 0
        for json_file in pbr_patcher_path.rglob("*.json"):
            try:
                # Try utf-8-sig first to handle BOM, fallback to utf-8
                try:
                    with open(json_file, 'r', encoding='utf-8-sig') as f:
                        data = json.load(f)
                except UnicodeDecodeError:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                
                # Get the relative path from PBRNifPatcher folder
                relative_path = json_file.relative_to(pbr_patcher_path)
                texture_dir = str(relative_path.parent).replace('\\', '/')
                
                # Check if path matches excluded patterns
                is_excluded = any(pattern in texture_dir.lower() for pattern in excluded_patterns)
                
                # Handle both JSON formats
                entries = []
                if isinstance(data, list):
                    # Simple array format (like Amidianborn)
                    entries = data
                elif isinstance(data, dict) and 'entries' in data:
                    # Object with entries array (like Faultier's)
                    entries = data['entries']
                
                # Extract texture names from entries
                for entry in entries:
                    if 'texture' in entry:
                        texture_name = entry['texture'].replace('\\', '/')
                        
                        # Build the full texture path
                        if texture_dir == '.':
                            texture_path = f"{texture_name}.dds"
                        else:
                            texture_path = f"{texture_dir}/{texture_name}.dds"
                        
                        if is_excluded:
                            excluded_count += 1
                            if excluded_count <= 3:
                                debug_info.append(f"Excluded (PG Patcher skip): {texture_path}")
                        else:
                            pbr_covered_textures[texture_path.lower()].add(mod_name)
                            json_count += 1
                            
                            if json_count <= 5:
                                debug_info.append(f"PBR Coverage: {json_file.name} covers {texture_path}")
                            
            except Exception as e:
                debug_info.append(f"Error reading {json_file}: {str(e)}")
        
        if json_count > 0 or excluded_count > 0:
            debug_info.append(f"'{mod_name}': Found {json_count} PBR coverage entries, excluded {excluded_count} technical paths")

    def _scan_regular_textures(self, mod_name, mod_path, regular_textures, debug_info):
        textures_path = Path(mod_path) / "textures"
        if not textures_path.exists():
            return
        
        # Patterns that PG Patcher doesn't patch (exclude from analysis)
        excluded_patterns = ['cameras', 'dyndolod', 'lod', 'markers']
        
        regular_count = 0
        excluded_count = 0
        for dds_file in textures_path.rglob("*.dds"):
            relative_path = dds_file.relative_to(textures_path)
            path_str = str(relative_path).lower().replace('\\', '/')
            
            # Skip PBR textures and variant maps
            if path_str.startswith('pbr/') or '/pbr/' in path_str:
                continue
            if any(dds_file.stem.endswith(suffix) for suffix in ['_n', '_m', '_s', '_g', '_p', '_e']):
                continue
            
            # Skip paths that PG Patcher doesn't handle
            if any(pattern in path_str for pattern in excluded_patterns):
                excluded_count += 1
                continue
                
            regular_textures[path_str].append(mod_name)
            regular_count += 1
        
        if regular_count > 0:
            debug_info.append(f"'{mod_name}': Found {regular_count} regular textures, excluded {excluded_count} technical paths")

    def _find_coverage_analysis(self, pbr_covered_textures, regular_textures):
        covered_mods = defaultdict(list)
        uncovered_mods = defaultdict(list)
        coverage_providers = defaultdict(set)  # {mod_name: {providing_pbr_mods}}
        debug_matches = []
        
        for texture_path, mod_names in regular_textures.items():
            # Check if this texture or its base name is covered by PBR
            providing_pbr_mods = set()
            match_info = f"Checking: {texture_path}"
            
            # Direct match
            if texture_path in pbr_covered_textures:
                providing_pbr_mods = pbr_covered_textures[texture_path]
                match_info += f" -> Direct match found by {list(providing_pbr_mods)}"
            else:
                # Check base name match (for texture variants)
                base_name = Path(texture_path).stem
                texture_dir = str(Path(texture_path).parent)
                original_base = base_name
                
                # Remove variant suffixes from base name (both numbered and text suffixes)
                # First try numbered suffixes
                for suffix in ['_01', '_02', '_03', '_04', '_05']:
                    if base_name.endswith(suffix):
                        base_name = base_name[:-3]
                        break
                
                # Then try any underscore suffix (like _em, _d, etc.)
                if '_' in base_name:
                    underscore_pos = base_name.rfind('_')
                    potential_base = base_name[:underscore_pos]
                    
                    # Only strip if the suffix looks like a texture variant
                    # (not too long, contains only letters/numbers)
                    suffix_part = base_name[underscore_pos+1:]
                    if len(suffix_part) <= 3 and suffix_part.isalnum():
                        base_name = potential_base
                
                # Reconstruct potential covered path (normalize path separators to forward slashes)
                texture_dir_normalized = texture_dir.replace('\\', '/')
                if texture_dir_normalized == '.':
                    potential_covered = f"{base_name}.dds"
                else:
                    potential_covered = f"{texture_dir_normalized}/{base_name}.dds"
                
                match_info += f" -> Base: {original_base} -> {base_name} -> Looking for: {potential_covered}"
                
                if potential_covered in pbr_covered_textures:
                    providing_pbr_mods = pbr_covered_textures[potential_covered]
                    match_info += f" -> MATCH FOUND by {list(providing_pbr_mods)}"
                else:
                    match_info += " -> NO MATCH"
            
            # Store debug info for elven armor specifically
            if 'elven' in texture_path.lower():
                debug_matches.append(match_info)
            
            # Sort into covered or uncovered and track providers
            for mod_name in mod_names:
                if providing_pbr_mods:
                    covered_mods[mod_name].append(texture_path)
                    coverage_providers[mod_name].update(providing_pbr_mods)
                else:
                    uncovered_mods[mod_name].append(texture_path)
        
        # Store debug info for display
        self._debug_matches = debug_matches
        
        return covered_mods, uncovered_mods, coverage_providers

    def _show_results(self, covered_mods, uncovered_mods, coverage_providers, pbr_textures, regular_textures, enabled_mods, debug_info):
        dialog = QDialog(self.__parentWidget)
        dialog.setWindowTitle("PBR Coverage Analysis")
        dialog.resize(800, 600)
        
        layout = QVBoxLayout(dialog)
        
        # Summary
        total_regular_textures = sum(len(mods) for mods in regular_textures.values())
        summary_text = f"Scanned {len(enabled_mods)} enabled mods.\nFound {len(pbr_textures)} PBR covered textures and {total_regular_textures} regular texture files across {len(regular_textures)} unique paths."
        layout.addWidget(QLabel(summary_text))
        
        # Debug info
        debug_text = QTextEdit()
        debug_text.setReadOnly(True)
        debug_text.setMaximumHeight(200)
        debug_display = "DEBUG INFO (PBRNifPatcher Method):\n"
        debug_display += f"Sample PBR covered textures: {list(pbr_textures)[:5]}\n"
        debug_display += f"Sample regular textures: {list(regular_textures.keys())[:5]}\n\n"
        debug_display += "Scan Details:\n" + "\n".join(debug_info[:25])
        
        # Add elven armor debug matches if available
        if hasattr(self, '_debug_matches') and self._debug_matches:
            debug_display += "\n\nElven Armor Matching Debug:\n" + "\n".join(self._debug_matches[:10])
        debug_text.setPlainText(debug_display)
        layout.addWidget(debug_text)
        
        # Results - show potentially redundant mods with their uncovered textures
        if covered_mods or uncovered_mods:
            layout.addWidget(QLabel("Potentially Redundant Mods (showing uncovered textures for PBR gaps):"))
            
            results_widget = QTextEdit()
            results_widget.setReadOnly(True)
            results_text = ""
            
            # Show mods that have some coverage, sorted by coverage percentage
            mods_with_coverage = {}
            for mod_name in covered_mods.keys():
                total_textures = len([p for p, mods in regular_textures.items() if mod_name in mods])
                covered_count = len(covered_mods[mod_name])
                uncovered_count = len(uncovered_mods.get(mod_name, []))
                coverage_percent = covered_count / total_textures * 100
                
                mods_with_coverage[mod_name] = {
                    'covered_count': covered_count,
                    'uncovered_count': uncovered_count,
                    'total_textures': total_textures,
                    'coverage_percent': coverage_percent,
                    'uncovered_textures': uncovered_mods.get(mod_name, [])
                }
            
            # Sort by coverage percentage (most covered first)
            for mod_name in sorted(mods_with_coverage.keys(), key=lambda x: mods_with_coverage[x]['coverage_percent'], reverse=True):
                mod_data = mods_with_coverage[mod_name]
                results_text += f"\n{mod_name}\n"
                results_text += f"  Coverage: {mod_data['covered_count']}/{mod_data['total_textures']} textures ({mod_data['coverage_percent']:.1f}%)\n"
                
                # Show which mods are providing PBR coverage
                if mod_name in coverage_providers and coverage_providers[mod_name]:
                    pbr_mods = sorted(list(coverage_providers[mod_name]))
                    results_text += f"  PBR provided by: {', '.join(pbr_mods)}\n"
                
                if mod_data['uncovered_textures']:
                    results_text += "  Missing PBR coverage for:\n"
                    for texture in sorted(mod_data['uncovered_textures'])[:8]:
                        results_text += f"    - {texture}\n"
                    if len(mod_data['uncovered_textures']) > 8:
                        results_text += f"    ... and {len(mod_data['uncovered_textures']) - 8} more\n"
                else:
                    results_text += "  ✓ Fully covered by PBR\n"
            
            results_widget.setPlainText(results_text)
            layout.addWidget(results_widget)
        else:
            layout.addWidget(QLabel("No texture mods found with PBR coverage."))
        
        # Buttons
        button_layout = QHBoxLayout()
        
        export_btn = QPushButton("Export Results")
        export_btn.clicked.connect(lambda: self._export_results(covered_mods, uncovered_mods, coverage_providers, regular_textures))
        button_layout.addWidget(export_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec()

    def _export_results(self, covered_mods, uncovered_mods, coverage_providers, regular_textures):
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
                        f.write("Potentially Redundant Mods (with PBR coverage gaps):\n\n")
                        
                        # Create coverage data like in the UI
                        mods_with_coverage = {}
                        for mod_name in covered_mods.keys():
                            total_textures = len([p for p, mods in regular_textures.items() if mod_name in mods])
                            covered_count = len(covered_mods[mod_name])
                            uncovered_count = len(uncovered_mods.get(mod_name, []))
                            coverage_percent = covered_count / total_textures * 100
                            
                            mods_with_coverage[mod_name] = {
                                'covered_count': covered_count,
                                'uncovered_count': uncovered_count,
                                'total_textures': total_textures,
                                'coverage_percent': coverage_percent,
                                'uncovered_textures': uncovered_mods.get(mod_name, [])
                            }
                        
                        # Sort by coverage percentage (most covered first)
                        for mod_name in sorted(mods_with_coverage.keys(), key=lambda x: mods_with_coverage[x]['coverage_percent'], reverse=True):
                            mod_data = mods_with_coverage[mod_name]
                            f.write(f"{mod_name}\n")
                            f.write(f"  Coverage: {mod_data['covered_count']}/{mod_data['total_textures']} textures ({mod_data['coverage_percent']:.1f}%)\n")
                            
                            # Show which mods are providing PBR coverage
                            if mod_name in coverage_providers and coverage_providers[mod_name]:
                                pbr_mods = sorted(list(coverage_providers[mod_name]))
                                f.write(f"  PBR provided by: {', '.join(pbr_mods)}\n")
                            
                            if mod_data['uncovered_textures']:
                                f.write("  Missing PBR coverage for:\n")
                                for texture in sorted(mod_data['uncovered_textures']):
                                    f.write(f"    - {texture}\n")
                            else:
                                f.write("  ✓ Fully covered by PBR\n")
                            f.write("\n")
                    else:
                        f.write("No mods found with PBR coverage.\n")
                
                QMessageBox.information(self.__parentWidget, "Export Complete", f"Results exported to {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self.__parentWidget, "Export Error", f"Failed to export results: {str(e)}")

def createPlugin():
    return PBRCoverageChecker()