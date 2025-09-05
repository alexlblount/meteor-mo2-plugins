from pathlib import Path

class TextureUtils:
    """Utilities for texture path normalization and analysis."""
    
    def __init__(self):
        # Known texture suffixes from PG Patcher wiki and source code (order matters - check longer ones first)
        # From: https://github.com/hakasapl/PGPatcher/wiki/Mod-Authors
        # Combined with PGPatcher\PGLib\src\util\NIFUtil.cpp texture suffix map
        self.pbr_suffixes = [
            # PG Patcher PBR suffixes (from wiki and source)
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
            
            # Custom suffixes found in mods
            '_normalmap', # Normal map (full name)
            '_envmap',    # Environment map
            '_spec',      # Specular
            '_emit',      # Emissive
            '_nm',        # Normal map (short)
        ]
    
    def normalize_path(self, path_str):
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

    def get_base_texture_name(self, texture_path):
        """
        Convert texture path to base texture name by stripping PBR suffixes.
        E.g. 'armor/steel/cuirass_m.dds' -> 'armor/steel/cuirass.dds'
        """
        # First normalize the path
        normalized_path = self.normalize_path(texture_path)
        
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
