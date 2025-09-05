from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

class ResultsUI:
    """Handles the display and export of PBR coverage analysis results."""
    
    def __init__(self, parent_widget):
        self.parent_widget = parent_widget
    
    def show_results(self, covered_mods, uncovered_mods, coverage_providers, 
                    pbr_textures, regular_textures, enabled_mods, debug_info, coverage_analyzer):
        """
        Display the PBR coverage analysis results in a dialog.
        
        Args:
            covered_mods: Dict of mods with covered textures
            uncovered_mods: Dict of mods with uncovered textures  
            coverage_providers: Dict mapping mods to their PBR providers
            pbr_textures: Dict of PBR covered textures
            regular_textures: Dict of regular textures
            enabled_mods: List of enabled mods
            debug_info: List of debug information
            coverage_analyzer: CoverageAnalyzer instance for debug matches
        """
        dialog = QDialog(self.parent_widget)
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
        if coverage_analyzer.debug_matches:
            debug_display += "\n\nElven Armor Matching Debug:\n" + "\n".join(coverage_analyzer.debug_matches[:10])
        debug_text.setPlainText(debug_display)
        layout.addWidget(debug_text)
        
        # Results - show potentially redundant mods with their uncovered textures
        if covered_mods or uncovered_mods:
            layout.addWidget(QLabel("Potentially Redundant Mods (showing uncovered textures for PBR gaps):"))
            
            results_widget = QTextEdit()
            results_widget.setReadOnly(True)
            results_text = self._generate_results_text(covered_mods, uncovered_mods, coverage_providers, regular_textures)
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
    
    def _generate_results_text(self, covered_mods, uncovered_mods, coverage_providers, regular_textures):
        """Generate the results text for display."""
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
        
        return results_text

    def _export_results(self, covered_mods, uncovered_mods, coverage_providers, regular_textures):
        """Export the analysis results to a text file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self.parent_widget,
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
                
                QMessageBox.information(self.parent_widget, "Export Complete", f"Results exported to {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self.parent_widget, "Export Error", f"Failed to export results: {str(e)}")