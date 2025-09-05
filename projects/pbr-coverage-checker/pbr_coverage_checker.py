import mobase
from collections import defaultdict
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

from .texture_utils import TextureUtils
from .pbr_scanner import PBRScanner
from .texture_scanner import TextureScanner
from .coverage_analyzer import CoverageAnalyzer
from .results_ui import ResultsUI

class PBRCoverageChecker(mobase.IPluginTool):
    def __init__(self):
        super().__init__()
        self.__organizer = None
        self.__parentWidget = None
        
        # Initialize modular components
        self.texture_utils = TextureUtils()
        self.pbr_scanner = PBRScanner(self.texture_utils)
        self.texture_scanner = TextureScanner(self.texture_utils)
        self.coverage_analyzer = CoverageAnalyzer(self.texture_utils)
        self.results_ui = None  # Will be initialized when parent widget is set

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
        self.results_ui = ResultsUI(widget)

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
                self.pbr_scanner.scan_pbr_coverage(mod_name, mod_path, pbr_covered_textures, debug_info)
                self.texture_scanner.scan_regular_textures(mod_name, mod_path, regular_textures, debug_info)

            # Find coverage
            covered_mods, uncovered_mods, coverage_providers = self.coverage_analyzer.find_coverage_analysis(pbr_covered_textures, regular_textures)
            
            # Display results (with debug info)
            self.results_ui.show_results(covered_mods, uncovered_mods, coverage_providers, pbr_covered_textures, regular_textures, enabled_mods, debug_info, self.coverage_analyzer)

        except Exception as e:
            QMessageBox.critical(self.__parentWidget, "Error", f"Failed to analyze PBR coverage: {str(e)}")

def createPlugin():
    return PBRCoverageChecker()