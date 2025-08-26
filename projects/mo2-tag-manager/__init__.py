"""
MO2 Tag Manager Plugin

A comprehensive Mod Organizer 2 plugin for managing tags and indexes on mods and separators.
Supports [NoDelete] tags, numerical indexes, and custom tags with granular selection.

Features:
- Tree view with expandable sections
- Individual mod and separator selection
- NoDelete tag management for Wabbajack protection
- Numerical indexing for order preservation
- Custom tag support with presets
- Tag ordering: [NoDelete] [index] [custom] Mod Name

Author: Alex
Version: 1.0.0
"""

import mobase
from typing import List

try:
    from PyQt6.QtGui import QIcon
except ImportError:
    from PyQt5.QtGui import QIcon

from .tree_dialog import TagManagerTreeDialog
from .standalone_tools import TagMgrAddIndexesTool, TagMgrRemoveIndexesTool


class MO2TagManager(mobase.IPluginTool):
    def __init__(self):
        super().__init__()
        self._organizer = None
        self._parent_widget = None

    def init(self, organizer: mobase.IOrganizer):
        self._organizer = organizer
        return True

    def name(self) -> str:
        return "MO2 Tag Manager"

    def author(self) -> str:
        return "Alex"

    def description(self) -> str:
        return "Comprehensive tag and index management for mods and separators"

    def version(self) -> mobase.VersionInfo:
        return mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.ALPHA)

    def settings(self) -> List[mobase.PluginSetting]:
        return []

    def displayName(self) -> str:
        return "Tag Manager v1.0.0/1. Advanced tag and index management"

    def tooltip(self) -> str:
        return "Manage [NoDelete], numerical indexes, and custom tags with granular selection"

    def icon(self):
        return QIcon()

    def setParentWidget(self, widget):
        self._parent_widget = widget

    def display(self) -> bool:
        if not self._organizer:
            return False
            
        dialog = TagManagerTreeDialog(self._parent_widget, self._organizer)
        dialog.exec()
        return True


def createPlugins():
    return [MO2TagManager(), TagMgrAddIndexesTool(), TagMgrRemoveIndexesTool()]