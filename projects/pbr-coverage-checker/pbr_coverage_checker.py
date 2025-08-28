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
        
        # Known texture suffixes from PG Patcher wiki and source code (order matters - check longer ones first)
        # From: https://github.com/hakasapl/PGPatcher/wiki/Mod-Authors
        # Combined with PGPatcher\PGLib\src\util\NIFUtil.cpp texture suffix map
        self.pbr_suffixes = [
            '_envmask',  # Environment mask (full name)
            '_rmaos',    # Combined roughness/metallicness/AO/subsurface
            '_flow',     # Hair flow map
            '_cnr',      # Coat normal roughness
            '_msn',      # Model space normal
            '_em',       # Environment mask (short form)
            '_bl',       # Backlight (alternative to _b)
            '_sk',       # Skin tint
            '_b',        # Backlight
            '_d',        # Diffuse (standard or without suffix)
            '_e',        # Environment/Cubemap
            '_f',        # Fuzz
            '_g',        # Glow/Emissive
            '_i',        # Inner layer
            '_m',        # Environment mask (can be parallax in ENB)
            '_n',        # Normal
            '_p',        # Height/Parallax
            '_s',        # Subsurface tint
            'mask',      # Diffuse mask (no underscore!)
        ]
    
    def _normalize_path(self, path_str):
        """
        Normalize path by removing empty parts and using consistent separators.
        Handles leading slashes, double slashes, mixed separators.
        E.g. '\\armor//steel\\cuirass' -> 'armor/steel/cuirass'
        """
        if not path_str:
            return ""
        
        # Split on both types of slashes, filter empty parts, rejoin with forward slash
        parts = [part for part in path_str.replace('\\', '/').split('/') if part]
        return '/'.join(parts)

    def _get_base_texture_name(self, texture_path):
        """
        Convert texture path to base texture name by stripping PBR suffixes.
        E.g. 'armor/steel/cuirass_m.dds' -> 'armor/steel/cuirass.dds'
        """
        # First normalize the path
        normalized_path = self._normalize_path(texture_path)
        
        path_obj = Path(normalized_path)
        stem = path_obj.stem
        directory = str(path_obj.parent).replace('\\', '/')
        
        # Check for known PBR suffixes (longer ones first)
        for suffix in self.pbr_suffixes:
            if stem.endswith(suffix):
                base_stem = stem[:-len(suffix)]
                break
        else:
            # No known suffix found, use original stem
            base_stem = stem
        
        # Reconstruct path
        if directory == '.':
            return f"{base_stem}.dds"
        else:
            return f"{directory}/{base_stem}.dds"

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
            pbr_covered_textures = defaultdict(set)  # {base_texture_path: {providing_mod1, providing_mod2}}
            regular_textures = defaultdict(set)      # {base_texture_path: {mod1, mod2}} - using set to avoid duplicates from variants
            debug_info = []
            debug_info.append("=== Enhanced PBR Coverage Analysis (v1.3) ===")
            debug_info.append("Features: match_diffuse support, default merging, path normalization")
            debug_info.append("Enhanced exclusions: facetint, skintint, landscape, grass, cc, _resourcepack, non-ASCII")
            debug_info.append(f"Processing {len(enabled_mods)} enabled mods:")
            for mod_name, _ in enabled_mods[:10]:  # Show first 10 mod names
                debug_info.append(f"  - {mod_name}")
            if len(enabled_mods) > 10:
                debug_info.append(f"  ... and {len(enabled_mods) - 10} more")
            
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
        # Based on PG Patcher hardcoded ignores from source code analysis
        excluded_patterns = [
            # Original patterns
            'cameras', 'dyndolod', 'lod', 'markers',
            
            # Additional PG Patcher exclusions found in source code:
            # Non-patchable texture types from PG Patcher
            'facetint', 'skintint',  # PBR ignores Skin Tint and Face Tint types
            'landscape', 'grass',    # Landscape and grass textures can't be PBR'ed
            
            # File patterns that PG Patcher skips
            'meta.ini',  # Special MO2 metadata file
            
            # Creation Club content patterns
            'cc',  # Creation Club BSAs start with "cc"
            
            # Resource pack patterns  
            '_resourcepack',  # Resource pack BSAs end with "_resourcepack.bsa"
        ]
        
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
                
                # Handle both JSON formats with default merging
                entries = []
                defaults = {}
                
                if isinstance(data, list):
                    # Simple array format (like Amidianborn)
                    entries = data
                elif isinstance(data, dict):
                    # Object format - extract defaults and entries
                    if 'default' in data:
                        defaults = data['default']
                    if 'entries' in data:
                        entries = data['entries']
                    else:
                        # Treat the whole object as a single entry
                        entries = [data]
                
                # Process entries with default merging
                for entry in entries:
                    # Merge defaults into entry (entry values override defaults)
                    merged_entry = {**defaults, **entry}
                    
                    # Extract texture name - support both 'texture' and 'match_diffuse' fields
                    texture_name = None
                    base_texture_path = None
                    if 'match_diffuse' in merged_entry:
                        texture_name = merged_entry['match_diffuse']
                    elif 'texture' in merged_entry:
                        texture_name = merged_entry['texture']
                    
                    if texture_name:
                        # Normalize the texture path
                        texture_name = self._normalize_path(texture_name)
                        
                        # Build the full texture path
                        if texture_dir == '.':
                            texture_path = f"{texture_name}.dds"
                        else:
                            texture_path = f"{texture_dir}/{texture_name}.dds"
                        
                        # Handle path-less texture names 
                        if '/' not in texture_name and '\\' not in texture_name:
                            # This is a simple filename - use the JSON's directory structure to build the path
                            # The JSON file location indicates where the texture should be found
                            if texture_dir != '.':
                                # Use the JSON's directory path as the texture path
                                texture_path = f"{texture_dir}/{texture_name}.dds"
                            else:
                                # Fallback: try to find it in the mod's PBR structure
                                pbr_mod_path = Path(mod_path) / "textures" / "PBR"
                                if pbr_mod_path.exists():
                                    for found_file in pbr_mod_path.rglob(f"{texture_name}.dds"):
                                        # Found the file, use its actual path relative to textures/
                                        relative_path = found_file.relative_to(Path(mod_path) / "textures")
                                        texture_path = str(relative_path).replace('\\', '/')
                                        break
                        
                        # Normalize the full path too
                        texture_path = self._normalize_path(texture_path)
                        
                        # Check for non-ASCII characters (PG Patcher skips these)
                        try:
                            texture_path.encode('ascii')
                        except UnicodeEncodeError:
                            excluded_count += 1
                            if excluded_count <= 3:
                                debug_info.append(f"Excluded (non-ASCII chars): {texture_path}")
                            continue
                        
                        # Get base texture name (strip PBR suffixes for grouping)
                        base_texture_path = self._get_base_texture_name(texture_path).lower()
                        
                        if is_excluded:
                            excluded_count += 1
                            if excluded_count <= 3:
                                debug_info.append(f"Excluded (PG Patcher skip): {texture_path}")
                        else:
                            pbr_covered_textures[base_texture_path].add(mod_name)
                            json_count += 1
                            
                            if json_count <= 5:
                                debug_info.append(f"PBR Coverage: {json_file.name} covers {texture_path} (base: {base_texture_path})")
                    
                    # Also check for slot commands (slot2, slot3, etc.) - these indicate PBR coverage
                    for key in merged_entry:
                        if key.startswith('slot') and key[4:].isdigit():
                            slot_texture_path = merged_entry[key]
                            if slot_texture_path:
                                # Remove "textures/" prefix if present and normalize
                                if slot_texture_path.lower().startswith('textures/'):
                                    slot_texture_path = slot_texture_path[9:]
                                elif slot_texture_path.lower().startswith('textures\\'):
                                    slot_texture_path = slot_texture_path[9:]
                                
                                slot_texture_path = self._normalize_path(slot_texture_path)
                                
                                # Get base texture name (strip PBR suffixes)
                                base_slot_path = self._get_base_texture_name(slot_texture_path).lower()
                                
                                # Don't double-count if we already added this texture from the main texture field
                                if base_texture_path is None or base_slot_path != base_texture_path:
                                    pbr_covered_textures[base_slot_path].add(mod_name)
                                    json_count += 1
                                    
                                    if json_count <= 5:
                                        debug_info.append(f"PBR Coverage ({key}): {json_file.name} covers {slot_texture_path} (base: {base_slot_path})")
                            
            except Exception as e:
                debug_info.append(f"Error reading {json_file}: {str(e)}")
        
        if json_count > 0 or excluded_count > 0:
            debug_info.append(f"'{mod_name}': Found {json_count} PBR coverage entries, excluded {excluded_count} technical paths")

    def _scan_regular_textures(self, mod_name, mod_path, regular_textures, debug_info):
        textures_path = Path(mod_path) / "textures"
        if not textures_path.exists():
            return
        
        # Patterns that PG Patcher doesn't patch (exclude from analysis)
        # Based on PG Patcher hardcoded ignores from source code analysis
        excluded_patterns = [
            # Original patterns
            'cameras', 'dyndolod', 'lod', 'markers',
            
            # Additional PG Patcher exclusions found in source code:
            # Non-patchable texture types from PG Patcher
            'facetint', 'skintint',  # PBR ignores Skin Tint and Face Tint types
            'landscape', 'grass',    # Landscape and grass textures can't be PBR'ed
            
            # File patterns that PG Patcher skips
            'meta.ini',  # Special MO2 metadata file
            
            # Creation Club content patterns
            'cc',  # Creation Club BSAs start with "cc"
            
            # Resource pack patterns  
            '_resourcepack',  # Resource pack BSAs end with "_resourcepack.bsa"
        ]
        
        base_textures_found = set()  # Track unique base textures for this mod
        excluded_count = 0
        total_files_processed = 0
        
        for dds_file in textures_path.rglob("*.dds"):
            relative_path = dds_file.relative_to(textures_path)
            path_str = str(relative_path).replace('\\', '/')
            
            # Normalize the path for consistent matching
            path_str = self._normalize_path(path_str).lower()
            total_files_processed += 1
            
            # Check for non-ASCII characters (PG Patcher skips these)
            try:
                path_str.encode('ascii')
            except UnicodeEncodeError:
                excluded_count += 1
                continue
            
            # Skip PBR textures and variant maps
            if path_str.startswith('pbr/') or '/pbr/' in path_str:
                continue
            if any(dds_file.stem.endswith(suffix) for suffix in ['_n', '_m', '_s', '_g', '_p', '_e']):
                continue
            
            # Skip paths that PG Patcher doesn't handle
            if any(pattern in path_str for pattern in excluded_patterns):
                excluded_count += 1
                continue
            
            # Get base texture name (group variants together)
            base_texture_path = self._get_base_texture_name(path_str).lower()
            regular_textures[base_texture_path].add(mod_name)
            base_textures_found.add(base_texture_path)
        
        if base_textures_found or total_files_processed > 0:
            debug_info.append(f"'{mod_name}': Found {len(base_textures_found)} unique base textures from {total_files_processed} files, excluded {excluded_count} technical paths")

    def _find_coverage_analysis(self, pbr_covered_textures, regular_textures):
        covered_mods = defaultdict(list)
        uncovered_mods = defaultdict(list)
        coverage_providers = defaultdict(set)  # {mod_name: {providing_pbr_mods}}
        debug_matches = []
        
        for base_texture_path, mod_names in regular_textures.items():
            # Check if this base texture is covered by PBR
            providing_pbr_mods = set()
            match_info = f"Checking: {base_texture_path}"
            
            # Direct match (base texture names are already normalized)
            if base_texture_path in pbr_covered_textures:
                providing_pbr_mods = pbr_covered_textures[base_texture_path]
                match_info += f" -> Direct match found by {list(providing_pbr_mods)}"
            else:
                # Also check for numbered variants (_01, _02, etc.) as fallback
                base_name = Path(base_texture_path).stem
                texture_dir = str(Path(base_texture_path).parent).replace('\\', '/')
                
                for suffix in ['_01', '_02', '_03', '_04', '_05']:
                    if base_name.endswith(suffix):
                        fallback_base = base_name[:-3]
                        if texture_dir == '.':
                            fallback_path = f"{fallback_base}.dds"
                        else:
                            fallback_path = f"{texture_dir}/{fallback_base}.dds"
                        
                        if fallback_path in pbr_covered_textures:
                            providing_pbr_mods = pbr_covered_textures[fallback_path]
                            match_info += f" -> Numbered variant match found by {list(providing_pbr_mods)}"
                            break
                
                if not providing_pbr_mods:
                    match_info += " -> NO MATCH"
            
            # Store debug info for elven armor specifically
            if 'elven' in base_texture_path.lower():
                debug_matches.append(match_info)
            
            # Sort into covered or uncovered and track providers
            # mod_names is now a set, so iterate accordingly
            for mod_name in mod_names:
                if providing_pbr_mods:
                    covered_mods[mod_name].append(base_texture_path)
                    coverage_providers[mod_name].update(providing_pbr_mods)
                else:
                    uncovered_mods[mod_name].append(base_texture_path)
        
        # Store debug info for display
        self._debug_matches = debug_matches
        
        return covered_mods, uncovered_mods, coverage_providers

    def _show_results(self, covered_mods, uncovered_mods, coverage_providers, pbr_textures, regular_textures, enabled_mods, debug_info):
        dialog = QDialog(self.__parentWidget)
        dialog.setWindowTitle("PBR Coverage Analysis")
        dialog.resize(800, 600)
        
        layout = QVBoxLayout(dialog)
        
        # Summary  
        total_mod_instances = sum(len(mods) for mods in regular_textures.values())
        summary_text = f"Scanned {len(enabled_mods)} enabled mods.\nFound {len(pbr_textures)} PBR covered base textures and {total_mod_instances} mod-texture combinations across {len(regular_textures)} unique base textures."
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
            
            # Show all mods that have textures, including zero coverage ones
            mods_with_coverage = {}
            all_texture_mods = set(covered_mods.keys()) | set(uncovered_mods.keys())
            for mod_name in all_texture_mods:
                # Count base textures, not texture variants
                total_textures = len([p for p, mods in regular_textures.items() if mod_name in mods])
                covered_count = len(covered_mods[mod_name])
                uncovered_count = len(uncovered_mods.get(mod_name, []))
                coverage_percent = covered_count / total_textures * 100 if total_textures > 0 else 0
                
                mods_with_coverage[mod_name] = {
                    'covered_count': covered_count,
                    'uncovered_count': uncovered_count,
                    'total_textures': total_textures,
                    'coverage_percent': coverage_percent,
                    'uncovered_textures': uncovered_mods.get(mod_name, [])
                }
            
            # Separate mods into fully covered and partially covered
            fully_covered = []
            partially_covered = []
            
            for mod_name in mods_with_coverage.keys():
                mod_data = mods_with_coverage[mod_name]
                if mod_data['coverage_percent'] >= 100.0:
                    fully_covered.append(mod_name)
                else:
                    partially_covered.append(mod_name)
            
            # Sort partially covered by coverage percentage for further subdivision
            partially_covered.sort(key=lambda x: mods_with_coverage[x]['coverage_percent'], reverse=True)
            
            # Split partially covered into detailed view and bottom 20% simple view
            if len(partially_covered) > 0:
                bottom_20_percent_count = max(1, len(partially_covered) // 5)  # At least 1 mod
                detailed_partial = partially_covered[:-bottom_20_percent_count]
                bottom_20_partial = partially_covered[-bottom_20_percent_count:]
            else:
                detailed_partial = []
                bottom_20_partial = []
            
            # Show fully covered mods in condensed format
            if fully_covered:
                results_text += "\n✓ Fully covered by PBR\n"
                results_text += "------------------------------------\n"
                for mod_name in sorted(fully_covered):
                    mod_data = mods_with_coverage[mod_name]
                    pbr_mods = sorted(list(coverage_providers.get(mod_name, [])))
                    pbr_list = f"[{', '.join(pbr_mods)}]" if pbr_mods else ""
                    results_text += f"  {mod_name} {pbr_list}\n"
            
            # Show partially covered mods with reasonable coverage in detailed format
            if detailed_partial:
                if fully_covered:  # Add separator if we showed fully covered mods
                    results_text += "\nPartial PBR coverage:\n"
                    results_text += "------------------------------------\n"
                
                # Already sorted by coverage percentage (most covered first) 
                for mod_name in detailed_partial:
                    mod_data = mods_with_coverage[mod_name]
                    results_text += f"\n{mod_name}\n"
                    results_text += f"  PBR Coverage: {mod_data['coverage_percent']:.1f}% ({mod_data['covered_count']}/{mod_data['total_textures']} base textures)\n"
                    
                    # Show which mods are providing PBR coverage
                    if mod_name in coverage_providers and coverage_providers[mod_name]:
                        pbr_mods = sorted(list(coverage_providers[mod_name]))
                        results_text += f"  PBR provided by: {', '.join(pbr_mods)}\n"
                    
                    results_text += "  Missing PBR coverage for base textures:\n"
                    for texture in sorted(mod_data['uncovered_textures'])[:8]:
                        results_text += f"    - {texture}\n"
                    if len(mod_data['uncovered_textures']) > 8:
                        results_text += f"    ... and {len(mod_data['uncovered_textures']) - 8} more\n"
            
            # Show bottom 20% of partially covered mods in condensed format
            if bottom_20_partial:
                if fully_covered or detailed_partial:
                    results_text += "\n❌ Minimal PBR coverage (bottom 20%):\n"
                    results_text += "------------------------------------\n"
                
                for mod_name in bottom_20_partial:
                    mod_data = mods_with_coverage[mod_name]
                    pbr_mods = sorted(list(coverage_providers.get(mod_name, [])))
                    pbr_list = f" [{', '.join(pbr_mods)}]" if pbr_mods else ""
                    results_text += f"  {mod_name} ({mod_data['coverage_percent']:.1f}%){pbr_list}\n"
            
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
                        
                        # Create coverage data like in the UI - include all mods with textures
                        mods_with_coverage = {}
                        all_texture_mods = set(covered_mods.keys()) | set(uncovered_mods.keys())
                        for mod_name in all_texture_mods:
                            # Count base textures, not texture variants
                            total_textures = len([p for p, mods in regular_textures.items() if mod_name in mods])
                            covered_count = len(covered_mods[mod_name])
                            uncovered_count = len(uncovered_mods.get(mod_name, []))
                            coverage_percent = covered_count / total_textures * 100 if total_textures > 0 else 0
                            
                            mods_with_coverage[mod_name] = {
                                'covered_count': covered_count,
                                'uncovered_count': uncovered_count,
                                'total_textures': total_textures,
                                'coverage_percent': coverage_percent,
                                'uncovered_textures': uncovered_mods.get(mod_name, [])
                            }
                        
                        # Separate mods into fully covered and partially covered
                        fully_covered = []
                        partially_covered = []
                        
                        for mod_name in mods_with_coverage.keys():
                            mod_data = mods_with_coverage[mod_name]
                            if mod_data['coverage_percent'] >= 100.0:
                                fully_covered.append(mod_name)
                            else:
                                partially_covered.append(mod_name)
                        
                        # Sort partially covered by coverage percentage for further subdivision
                        partially_covered.sort(key=lambda x: mods_with_coverage[x]['coverage_percent'], reverse=True)
                        
                        # Split partially covered into detailed view and bottom 20% simple view
                        if len(partially_covered) > 0:
                            bottom_20_percent_count = max(1, len(partially_covered) // 5)  # At least 1 mod
                            detailed_partial = partially_covered[:-bottom_20_percent_count]
                            bottom_20_partial = partially_covered[-bottom_20_percent_count:]
                        else:
                            detailed_partial = []
                            bottom_20_partial = []
                        
                        # Export fully covered mods in condensed format
                        if fully_covered:
                            f.write("\n✓ Fully covered by PBR\n")
                            f.write("------------------------------------\n")
                            for mod_name in sorted(fully_covered):
                                mod_data = mods_with_coverage[mod_name]
                                pbr_mods = sorted(list(coverage_providers.get(mod_name, [])))
                                pbr_list = f"[{', '.join(pbr_mods)}]" if pbr_mods else ""
                                f.write(f"  {mod_name} {pbr_list}\n")
                        
                        # Export partially covered mods with reasonable coverage in detailed format
                        if detailed_partial:
                            if fully_covered:  # Add separator if we showed fully covered mods
                                f.write("\nPartial PBR coverage:\n")
                                f.write("------------------------------------\n")
                            
                            # Already sorted by coverage percentage (most covered first)
                            for mod_name in detailed_partial:
                                mod_data = mods_with_coverage[mod_name]
                                f.write(f"\n{mod_name}\n")
                                f.write(f"  PBR Coverage: {mod_data['coverage_percent']:.1f}% ({mod_data['covered_count']}/{mod_data['total_textures']} base textures)\n")
                                
                                # Show which mods are providing PBR coverage
                                if mod_name in coverage_providers and coverage_providers[mod_name]:
                                    pbr_mods = sorted(list(coverage_providers[mod_name]))
                                    f.write(f"  PBR provided by: {', '.join(pbr_mods)}\n")
                                
                                f.write("  Missing PBR coverage for base textures:\n")
                                for texture in sorted(mod_data['uncovered_textures']):
                                    f.write(f"    - {texture}\n")
                                f.write("\n")
                        
                        # Export bottom 20% of partially covered mods in condensed format
                        if bottom_20_partial:
                            if fully_covered or detailed_partial:
                                f.write("\n❌ Minimal PBR coverage (bottom 20%):\n")
                                f.write("------------------------------------\n")
                            
                            for mod_name in bottom_20_partial:
                                mod_data = mods_with_coverage[mod_name]
                                pbr_mods = sorted(list(coverage_providers.get(mod_name, [])))
                                pbr_list = f" [{', '.join(pbr_mods)}]" if pbr_mods else ""
                                f.write(f"  {mod_name} ({mod_data['coverage_percent']:.1f}%){pbr_list}\n")
                            f.write("\n")
                    else:
                        f.write("No mods found with PBR coverage.\n")
                
                QMessageBox.information(self.__parentWidget, "Export Complete", f"Results exported to {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self.__parentWidget, "Export Error", f"Failed to export results: {str(e)}")

def createPlugin():
    return PBRCoverageChecker()