import os
import shutil
from pathlib import Path
from datetime import datetime
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
import mobase


class WabbajackDownloadCopier(mobase.IPluginTool):
    def __init__(self):
        super().__init__()
        self._organizer = None
        self._parent_widget = None

    def init(self, organizer):
        self._organizer = organizer
        return True

    def name(self):
        return "Wabbajack Download Copier"

    def localizedName(self):
        return "Wabbajack Download Copier"

    def author(self):
        return "MO2 Plugin Developer"

    def description(self):
        return "Copies download files for all mods (active and inactive) to create a pristine Wabbajack downloads folder"

    def version(self):
        return mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.FINAL)

    def requirements(self):
        return []

    def settings(self):
        return []

    def displayName(self):
        return "Copy Downloads for Wabbajack"

    def tooltip(self):
        return "Identify and copy download files for all mods (active and inactive) to create a pristine downloads folder"

    def icon(self):
        return QIcon()

    def setParentWidget(self, widget):
        self._parent_widget = widget

    def display(self):
        dialog = WabbajackCopyDialog(self._organizer, self._parent_widget)
        dialog.exec()

    def get_default_downloads_path(self):
        """Get the expected downloads folder path for this MO2 instance"""
        base_path = Path(self._organizer.basePath())
        return base_path / "downloads"

    def get_mod_downloads(self):
        """Identify download files for all installed mods"""
        mod_downloads = {}
        missing_downloads = []
        
        mod_list = self._organizer.modList()
        current_downloads_path = Path(self._organizer.downloadsPath())
        
        # Debug info - let's show this in the UI instead since console isn't working
        all_mods = mod_list.allMods()
        total_mods = len(all_mods)
        separators = [mod for mod in all_mods if mod.endswith('_separator')]
        actual_mods = total_mods - len(separators)
        
        debug_info = []
        debug_info.append(f"Current downloads path: {current_downloads_path}")
        debug_info.append(f"Total entries: {total_mods}")
        debug_info.append(f"Separators (skipped): {len(separators)}")
        debug_info.append(f"Actual mods to scan: {actual_mods}")
        
        sample_count = 0
        for i, mod_name in enumerate(mod_list.allMods()):
            # Skip separators - they don't have downloads
            if mod_name.endswith('_separator'):
                continue
                
            if sample_count < 5:  # Only log first 5 non-separators for debugging
                mod = mod_list.getMod(mod_name)
                if mod:
                    installation_file = mod.installationFile()
                    if installation_file and not os.path.isabs(installation_file):
                        full_path = current_downloads_path / installation_file
                        exists = full_path.exists()
                        debug_info.append(f"Sample mod '{mod_name}':")
                        debug_info.append(f"  installationFile = '{installation_file}'")
                        debug_info.append(f"  full_path = '{full_path}'")
                        debug_info.append(f"  exists = {exists}")
                    else:
                        debug_info.append(f"Sample mod '{mod_name}': installationFile = '{installation_file}'")
                    sample_count += 1
            
            # Skip separators in main scanning loop too
            if mod_name.endswith('_separator'):
                continue
                
            mod = mod_list.getMod(mod_name)  # Use mod_list.getMod instead of organizer.getMod
            if mod:  # Include both active and inactive mods for Wabbajack
                installation_file = mod.installationFile()
                
                if installation_file:
                    # If installationFile returns just a filename, combine it with downloads path
                    if not os.path.isabs(installation_file):
                        full_path = current_downloads_path / installation_file
                    else:
                        full_path = Path(installation_file)
                    
                    if full_path.exists():
                        # Check if it's in the downloads folder
                        if current_downloads_path in full_path.parents or current_downloads_path == full_path.parent:
                            mod_downloads[mod_name] = str(full_path)
                        else:
                            # File exists but not in downloads folder - might be manually installed
                            missing_downloads.append({
                                'mod_name': mod_name,
                                'reason': 'File exists outside downloads folder',
                                'file_path': str(full_path)
                            })
                    else:
                        missing_downloads.append({
                            'mod_name': mod_name,
                            'reason': 'Installation file does not exist',
                            'file_path': str(full_path)
                        })
                else:
                    missing_downloads.append({
                        'mod_name': mod_name,
                        'reason': 'No installation file found',
                        'file_path': 'N/A'
                    })
        
        # Store debug info for display in UI
        self._debug_info = debug_info
        return mod_downloads, missing_downloads

    def generate_missing_downloads_report(self, missing_downloads, report_path):
        """Generate a detailed report of missing downloads"""
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("WABBAJACK MISSING DOWNLOADS REPORT\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"MO2 Instance: {self._organizer.basePath()}\n")
                f.write(f"Current Downloads Folder: {self._organizer.downloadsPath()}\n\n")
                f.write(f"Total Missing Downloads: {len(missing_downloads)}\n\n")
                
                if not missing_downloads:
                    f.write("✓ All mods have their download files available!\n")
                    return True
                
                f.write("MISSING DOWNLOADS:\n")
                f.write("-" * 30 + "\n\n")
                
                for i, missing in enumerate(missing_downloads, 1):
                    f.write(f"{i}. {missing['mod_name']}\n")
                    f.write(f"   Reason: {missing['reason']}\n")
                    f.write(f"   File Path: {missing['file_path']}\n\n")
                
                f.write("\nNOTES:\n")
                f.write("- Mods with 'No installation file found' may have been installed manually\n")
                f.write("- Mods with files 'outside downloads folder' may need their downloads re-downloaded\n")
                f.write("- Check these mods manually and re-download if needed for Wabbajack compatibility\n")
                f.write("- When re-downloading, ensure both the archive file AND its .meta file are present\n")
                f.write("- .meta files contain important metadata (Nexus IDs, versions) required by Wabbajack\n")
                
            return True
        except Exception as e:
            return False


class CopyWorker(QThread):
    progress_updated = pyqtSignal(int, str)
    copy_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, mod_downloads, destination_path):
        super().__init__()
        self.mod_downloads = mod_downloads
        self.destination_path = Path(destination_path)
        self.results = {
            'copied': [],
            'skipped': [],
            'failed': [],
            'meta_copied': [],
            'meta_missing': []
        }

    def run(self):
        try:
            self.destination_path.mkdir(parents=True, exist_ok=True)
            total_files = len(self.mod_downloads)
            
            for i, (mod_name, source_path) in enumerate(self.mod_downloads.items()):
                self.progress_updated.emit(
                    int((i / total_files) * 100),
                    f"Processing {mod_name}..."
                )
                
                source = Path(source_path)
                destination = self.destination_path / source.name
                
                try:
                    # Copy main download file
                    if destination.exists():
                        if destination.stat().st_size == source.stat().st_size:
                            self.results['skipped'].append(f"{mod_name} -> {source.name} (already exists)")
                        else:
                            shutil.copy2(source_path, destination)
                            self.results['copied'].append(f"{mod_name} -> {source.name}")
                    else:
                        shutil.copy2(source_path, destination)
                        self.results['copied'].append(f"{mod_name} -> {source.name}")
                    
                    # Copy corresponding .meta file if it exists
                    meta_source = Path(source_path + ".meta")
                    meta_destination = Path(str(destination) + ".meta")
                    
                    if meta_source.exists():
                        if meta_destination.exists():
                            if meta_destination.stat().st_size != meta_source.stat().st_size:
                                shutil.copy2(meta_source, meta_destination)
                                self.results['meta_copied'].append(f"{mod_name} -> {source.name}.meta (updated)")
                        else:
                            shutil.copy2(meta_source, meta_destination)
                            self.results['meta_copied'].append(f"{mod_name} -> {source.name}.meta")
                    else:
                        self.results['meta_missing'].append(f"{mod_name} -> {source.name}.meta (no meta file found)")
                    
                except Exception as e:
                    self.results['failed'].append(f"{mod_name} -> {source.name}: {str(e)}")
            
            self.progress_updated.emit(100, "Copy operation completed")
            self.copy_completed.emit(self.results)
            
        except Exception as e:
            self.error_occurred.emit(f"Copy operation failed: {str(e)}")


class WabbajackCopyDialog(QDialog):
    def __init__(self, organizer, parent=None):
        super().__init__(parent)
        self.organizer = organizer
        self.mod_downloads = {}
        self.missing_downloads = []
        self.copy_worker = None
        
        self.setWindowTitle("Wabbajack Download Copier")
        self.setModal(True)
        self.resize(700, 500)
        
        self.init_ui()
        self.scan_downloads()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("Copy Downloads for Wabbajack List Creation")
        header_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(header_label)
        
        # Description
        desc_label = QLabel(
            "This tool identifies download files for ALL mods (active and inactive) and copies them to a pristine folder "
            "suitable for Wabbajack list creation. Only files in your current downloads folder will be copied."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("margin-bottom: 15px;")
        layout.addWidget(desc_label)
        
        # Destination folder selection
        dest_group = QGroupBox("Destination Folder")
        dest_layout = QVBoxLayout(dest_group)
        
        # Auto-detected path info
        copier = WabbajackDownloadCopier()
        copier._organizer = self.organizer
        default_path = str(copier.get_default_downloads_path())
        
        info_label = QLabel(f"Suggested path (MO2 instance + /downloads): {default_path}")
        info_label.setStyleSheet("color: #666; font-size: 11px; margin-bottom: 5px;")
        dest_layout.addWidget(info_label)
        
        path_layout = QHBoxLayout()
        self.dest_path_edit = QLineEdit()
        self.dest_path_edit.setText(default_path)  # Pre-fill with suggested path
        self.dest_path_edit.setPlaceholderText("Select destination folder for pristine downloads...")
        path_layout.addWidget(self.dest_path_edit)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_destination)
        path_layout.addWidget(browse_btn)
        
        use_default_btn = QPushButton("Use Default")
        use_default_btn.clicked.connect(lambda: self.dest_path_edit.setText(default_path))
        path_layout.addWidget(use_default_btn)
        
        dest_layout.addLayout(path_layout)
        layout.addWidget(dest_group)
        
        # Results display
        self.results_tabs = QTabWidget()
        
        # Found downloads tab
        self.found_widget = QTextEdit()
        self.found_widget.setReadOnly(True)
        self.results_tabs.addTab(self.found_widget, "Found Downloads (0)")
        
        # Missing downloads tab
        self.missing_widget = QTextEdit()
        self.missing_widget.setReadOnly(True)
        self.results_tabs.addTab(self.missing_widget, "Missing Downloads (0)")
        
        # Debug tab
        self.debug_widget = QTextEdit()
        self.debug_widget.setReadOnly(True)
        self.debug_widget.setFont(QFont("Consolas", 9))
        self.results_tabs.addTab(self.debug_widget, "Debug Info")
        
        layout.addWidget(self.results_tabs)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Refresh Scan")
        self.refresh_btn.clicked.connect(self.scan_downloads)
        button_layout.addWidget(self.refresh_btn)
        
        self.report_btn = QPushButton("Save Missing Report")
        self.report_btn.clicked.connect(self.save_missing_report)
        self.report_btn.setEnabled(False)
        button_layout.addWidget(self.report_btn)
        
        button_layout.addStretch()
        
        self.copy_btn = QPushButton("Copy Downloads")
        self.copy_btn.clicked.connect(self.start_copy)
        self.copy_btn.setEnabled(False)
        button_layout.addWidget(self.copy_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)

    def browse_destination(self):
        folder = QFileDialog.getExistingDirectory(
            self, 
            "Select Destination Folder for Pristine Downloads",
            self.dest_path_edit.text()
        )
        if folder:
            self.dest_path_edit.setText(folder)
            self.update_buttons()

    def scan_downloads(self):
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("Scanning...")
        
        # Use the copier instance to get download info
        copier = WabbajackDownloadCopier()
        copier._organizer = self.organizer
        
        self.mod_downloads, self.missing_downloads = copier.get_mod_downloads()
        
        # Update found downloads tab
        found_text = []
        for mod_name, download_path in sorted(self.mod_downloads.items()):
            filename = os.path.basename(download_path)
            found_text.append(f"• {mod_name} → {filename}")
        
        self.found_widget.setPlainText("\n".join(found_text))
        self.results_tabs.setTabText(0, f"Found Downloads ({len(self.mod_downloads)})")
        
        # Update missing downloads tab
        missing_text = []
        for missing_info in sorted(self.missing_downloads, key=lambda x: x['mod_name']):
            missing_text.append(f"• {missing_info['mod_name']}")
            missing_text.append(f"  Reason: {missing_info['reason']}")
            if missing_info['file_path'] != 'N/A':
                missing_text.append(f"  File: {missing_info['file_path']}")
            missing_text.append("")  # Empty line for spacing
        
        self.missing_widget.setPlainText("\n".join(missing_text))
        self.results_tabs.setTabText(1, f"Missing Downloads ({len(self.missing_downloads)})")
        
        # Update debug tab
        if hasattr(copier, '_debug_info'):
            debug_text = "\n".join(copier._debug_info)
            debug_text += f"\n\nFinal Results:\n"
            debug_text += f"- Found downloads: {len(self.mod_downloads)}\n"
            debug_text += f"- Missing downloads: {len(self.missing_downloads)}\n"
            self.debug_widget.setPlainText(debug_text)
        
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("Refresh Scan")
        self.update_buttons()

    def update_buttons(self):
        has_downloads = len(self.mod_downloads) > 0
        has_destination = bool(self.dest_path_edit.text().strip())
        self.copy_btn.setEnabled(has_downloads and has_destination)
        self.report_btn.setEnabled(True)  # Always allow saving report

    def save_missing_report(self):
        """Save detailed missing downloads report to a text file"""
        default_filename = f"missing_downloads_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        default_path = str(Path(self.organizer.basePath()) / default_filename)
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Missing Downloads Report",
            default_path,
            "Text Files (*.txt);;All Files (*)"
        )
        
        if filename:
            copier = WabbajackDownloadCopier()
            copier._organizer = self.organizer
            
            success = copier.generate_missing_downloads_report(self.missing_downloads, filename)
            
            if success:
                QMessageBox.information(
                    self, 
                    "Report Saved",
                    f"Missing downloads report saved to:\n{filename}\n\n"
                    f"Found {len(self.missing_downloads)} missing downloads."
                )
            else:
                QMessageBox.critical(
                    self,
                    "Save Error", 
                    f"Failed to save report to:\n{filename}"
                )

    def start_copy(self):
        destination = self.dest_path_edit.text().strip()
        if not destination:
            QMessageBox.warning(self, "No Destination", "Please select a destination folder.")
            return
        
        if not self.mod_downloads:
            QMessageBox.warning(self, "No Downloads", "No download files found to copy.")
            return
        
        # Confirm operation
        reply = QMessageBox.question(
            self, 
            "Confirm Copy Operation",
            f"Copy {len(self.mod_downloads)} download files to:\n{destination}\n\nThis operation may take some time.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Start copy operation
        self.copy_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)
        
        self.copy_worker = CopyWorker(self.mod_downloads, destination)
        self.copy_worker.progress_updated.connect(self.update_progress)
        self.copy_worker.copy_completed.connect(self.copy_finished)
        self.copy_worker.error_occurred.connect(self.copy_error)
        self.copy_worker.start()

    def update_progress(self, value, message):
        self.progress_bar.setValue(value)
        self.status_label.setText(message)

    def copy_finished(self, results):
        self.progress_bar.setVisible(False)
        self.status_label.setVisible(False)
        self.copy_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        
        # Show results
        message = f"Copy operation completed!\n\n"
        message += f"Downloads copied: {len(results['copied'])} files\n"
        message += f"Downloads skipped: {len(results['skipped'])} files (already exist)\n"
        message += f"Meta files copied: {len(results['meta_copied'])} files\n"
        message += f"Meta files missing: {len(results['meta_missing'])} files\n"
        message += f"Failed: {len(results['failed'])} files\n"
        
        if results['meta_missing']:
            message += f"\nNote: {len(results['meta_missing'])} downloads had no .meta files - this may affect Wabbajack compatibility.\n"
        
        if results['failed']:
            message += f"\nFailed files:\n"
            for failed in results['failed'][:5]:  # Show first 5 failures
                message += f"• {failed}\n"
            if len(results['failed']) > 5:
                message += f"... and {len(results['failed']) - 5} more"
        
        QMessageBox.information(self, "Copy Complete", message)

    def copy_error(self, error_message):
        self.progress_bar.setVisible(False)
        self.status_label.setVisible(False)
        self.copy_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        
        QMessageBox.critical(self, "Copy Error", error_message)


def createPlugin():
    return WabbajackDownloadCopier()