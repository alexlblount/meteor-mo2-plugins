"""
Wabbajack Download Copier Plugin

This plugin identifies download files for all mods (active and inactive) and copies them 
to a pristine folder suitable for Wabbajack list creation.
"""

from .plugin import WabbajackDownloadCopier

def createPlugin():
    return WabbajackDownloadCopier()