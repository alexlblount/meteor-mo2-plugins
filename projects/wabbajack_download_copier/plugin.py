"""
Main plugin class for the Wabbajack Download Copier
"""

from PyQt6.QtGui import QIcon
import mobase


class WabbajackDownloadCopier(mobase.IPluginTool):
    """Main plugin class implementing the MO2 IPluginTool interface"""
    
    def __init__(self):
        super().__init__()
        self._organizer = None
        self._parent_widget = None

    def init(self, organizer):
        self._organizer = organizer
        return True

    def name(self):
        return "Download Copier for Shared Download Folder Enjoyers"

    def localizedName(self):
        return "Download Copier for Shared Download Folder Enjoyers"

    def author(self):
        return "MO2 Plugin Developer"

    def description(self):
        return "Copies mod downloads from shared download folders into the pristine download folder structure required by Wabbajack"

    def version(self):
        return mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.FINAL)

    def requirements(self):
        return []

    def settings(self):
        return []

    def displayName(self):
        return "Copy Downloads from Shared Folder"

    def tooltip(self):
        return "Copy mod downloads from shared folders to create pristine Wabbajack-compatible download structure"

    def icon(self):
        return QIcon()

    def setParentWidget(self, widget):
        self._parent_widget = widget

    def display(self):
        from .dialog import WabbajackCopyDialog
        dialog = WabbajackCopyDialog(self._organizer, self._parent_widget)
        dialog.exec()

