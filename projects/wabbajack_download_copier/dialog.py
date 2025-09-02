"""
UI Dialog for the Wabbajack Download Copier plugin
"""

import os
from pathlib import Path
from datetime import datetime
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import *
import mobase
from .scanner import DownloadScanner
from .copier import CopyWorker
from .utils import format_file_size, get_disk_usage


class WabbajackCopyDialog(QDialog):
    """Main dialog for the Wabbajack Download Copier"""
    
    def __init__(self, organizer, parent=None):
        super().__init__(parent)
        self.organizer = organizer
        self.mod_downloads = {}
        self.missing_downloads = []
        self.copy_worker = None
        self.total_copy_size = 0
        self.total_file_count = 0
        
        self.setWindowTitle("Download Copier for Shared Download Folder Enjoyers")
        self.setModal(True)
        self.resize(700, 500)
        
        self.init_ui()
        self.scan_downloads()
        
        # Connect destination path changes to disk space updates
        self.dest_path_edit.textChanged.connect(self.update_disk_space_display)
        self.update_disk_space_display()  # Initial update

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("Copy Downloads for Wabbajack List Creation")
        header_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(header_label)
        
        # Description
        desc_label = QLabel(
            "This tool identifies download files for ALL mods (active and inactive) and copies them to a pristine folder "
            "suitable for Wabbajack list creation. Only files in your current downloads folder will be copied.\n\n"
            "Note: For merged mods, only the last merged mod's download is detected. Wabbajack needs all original individual downloads."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("margin-bottom: 15px;")
        layout.addWidget(desc_label)
        
        # Destination folder selection
        dest_group = QGroupBox("Destination Folder")
        dest_layout = QVBoxLayout(dest_group)
        
        # Auto-detected path info
        scanner = DownloadScanner(self.organizer)
        default_path = str(scanner.get_default_downloads_path())
        
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
        
        # Disk space info
        self.disk_space_label = QLabel("")
        self.disk_space_label.setStyleSheet("color: #666; font-size: 11px; margin-top: 5px;")
        dest_layout.addWidget(self.disk_space_label)
        
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
        
        # Size and disk space info
        self.size_info_label = QLabel("")
        self.size_info_label.setStyleSheet("font-weight: bold; color: #0066cc; margin: 10px 0;")
        self.size_info_label.setVisible(False)
        layout.addWidget(self.size_info_label)
        
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

    def update_disk_space_display(self):
        """Update the disk space display when destination path changes"""
        destination = self.dest_path_edit.text().strip()
        
        if not destination:
            self.disk_space_label.setText("")
            return
        
        try:
            # Check if the path exists or try to get its parent that exists
            path_to_check = Path(destination)
            while not path_to_check.exists() and path_to_check.parent != path_to_check:
                path_to_check = path_to_check.parent
            
            if path_to_check.exists():
                free_space, total_space = get_disk_usage(path_to_check)
                
                if free_space is not None and total_space is not None:
                    used_space = total_space - free_space
                    usage_percent = (used_space / total_space) * 100 if total_space > 0 else 0
                    
                    # Color coding based on available space
                    if free_space < 1024 * 1024 * 1024:  # Less than 1GB
                        color = "red"
                    elif free_space < 10 * 1024 * 1024 * 1024:  # Less than 10GB
                        color = "orange"
                    else:
                        color = "#666"
                    
                    space_text = (f"Drive space: {format_file_size(free_space)} free of "
                                f"{format_file_size(total_space)} ({usage_percent:.1f}% used)")
                    
                    self.disk_space_label.setText(space_text)
                    self.disk_space_label.setStyleSheet(f"color: {color}; font-size: 11px; margin-top: 5px;")
                else:
                    self.disk_space_label.setText("Could not detect drive space")
                    self.disk_space_label.setStyleSheet("color: #999; font-size: 11px; margin-top: 5px;")
            else:
                self.disk_space_label.setText("")
        except Exception:
            self.disk_space_label.setText("Could not detect drive space")
            self.disk_space_label.setStyleSheet("color: #999; font-size: 11px; margin-top: 5px;")

    def scan_downloads(self):
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("Scanning...")
        
        # Use the scanner to get download info
        scanner = DownloadScanner(self.organizer)
        
        self.mod_downloads, self.missing_downloads = scanner.get_mod_downloads()
        
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
        
        # Calculate total size of files to copy
        self.total_copy_size, self.total_file_count = scanner.calculate_copy_size(self.mod_downloads)
        
        # Update debug tab with summary
        debug_text = f"Scan Results:\n"
        debug_text += f"- Downloads folder: {self.organizer.downloadsPath()}\n"
        debug_text += f"- Found downloads: {len(self.mod_downloads)}\n"
        debug_text += f"- Missing downloads: {len(self.missing_downloads)}\n"
        debug_text += f"- Total copy size: {format_file_size(self.total_copy_size)}\n"
        debug_text += f"- Total files to copy: {self.total_file_count}\n"
        self.debug_widget.setPlainText(debug_text)
        
        # Update size info display
        if self.mod_downloads:
            size_text = f"Total size to copy: {format_file_size(self.total_copy_size)} ({self.total_file_count} files)"
            self.size_info_label.setText(size_text)
            self.size_info_label.setVisible(True)
        else:
            self.size_info_label.setVisible(False)
        
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
            scanner = DownloadScanner(self.organizer)
            
            success = scanner.generate_missing_downloads_report(self.missing_downloads, filename)
            
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
        
        # Check disk space
        free_space, total_space = get_disk_usage(destination)
        
        if free_space is not None:
            if self.total_copy_size > free_space:
                # Not enough space - show error
                QMessageBox.critical(
                    self,
                    "Insufficient Disk Space",
                    f"Not enough disk space!\n\n"
                    f"Required: {format_file_size(self.total_copy_size)}\n"
                    f"Available: {format_file_size(free_space)}\n"
                    f"Shortfall: {format_file_size(self.total_copy_size - free_space)}\n\n"
                    f"Please free up disk space or choose a different destination."
                )
                return
            elif self.total_copy_size > free_space * 0.9:  # Less than 10% free space remaining
                # Warn about low disk space but allow to continue
                reply = QMessageBox.question(
                    self,
                    "Low Disk Space Warning",
                    f"Warning: This operation will use most of your available disk space!\n\n"
                    f"Required: {format_file_size(self.total_copy_size)}\n"
                    f"Available: {format_file_size(free_space)}\n"
                    f"Remaining after copy: {format_file_size(free_space - self.total_copy_size)}\n\n"
                    f"Continue anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
        
        # Confirm operation
        size_info = f"Total size: {format_file_size(self.total_copy_size)} ({self.total_file_count} files)"
        if free_space is not None:
            size_info += f"\nFree space after copy: {format_file_size(free_space - self.total_copy_size)}"
        
        reply = QMessageBox.question(
            self, 
            "Confirm Copy Operation",
            f"Copy {len(self.mod_downloads)} download files to:\n{destination}\n\n"
            f"{size_info}\n\nThis operation may take some time.",
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