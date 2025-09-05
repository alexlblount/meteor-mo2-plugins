from pathlib import Path
from collections import defaultdict

class TextureScanner:
    """Scans mod texture folders to identify regular texture files."""
    
    def __init__(self, texture_utils):
        self.texture_utils = texture_utils
        
        # Patterns that PG Patcher doesn't patch (exclude from analysis)
        # Based on PG Patcher hardcoded ignores from source code analysis
        self.excluded_patterns = [
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
    
    def scan_regular_textures(self, mod_name, mod_path, regular_textures, debug_info):
        """
        Scan a mod's textures folder for regular (non-PBR) texture files.
        
        Args:
            mod_name: Name of the mod
            mod_path: Absolute path to the mod folder
            regular_textures: Dict to populate with {base_texture_path: set of mod names}
            debug_info: List to append debug information to
        """
        textures_path = Path(mod_path) / "textures"
        if not textures_path.exists():
            return
        
        base_textures_found = set()  # Track unique base textures for this mod
        excluded_count = 0
        total_files_processed = 0
        
        for dds_file in textures_path.rglob("*.dds"):
            relative_path = dds_file.relative_to(textures_path)
            path_str = str(relative_path).replace('\\', '/')
            
            # Normalize the path for consistent matching
            path_str = self.texture_utils.normalize_path(path_str).lower()
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
            if any(pattern in path_str for pattern in self.excluded_patterns):
                excluded_count += 1
                continue
            
            # Get base texture name (group variants together)
            base_texture_path = self.texture_utils.get_base_texture_name(path_str).lower()
            regular_textures[base_texture_path].add(mod_name)
            base_textures_found.add(base_texture_path)
        
        if base_textures_found or total_files_processed > 0:
            debug_info.append(f"'{mod_name}': Found {len(base_textures_found)} unique base textures from {total_files_processed} files, excluded {excluded_count} technical paths")