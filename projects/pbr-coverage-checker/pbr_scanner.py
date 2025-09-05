import json
from pathlib import Path
from collections import defaultdict

class PBRScanner:
    """Scans PBRNifPatcher folders to identify PBR coverage."""
    
    def __init__(self, texture_utils):
        self.texture_utils = texture_utils
        
        # Patterns that PG Patcher doesn't patch (exclude from coverage analysis)
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
    
    def scan_pbr_coverage(self, mod_name, mod_path, pbr_covered_textures, debug_info):
        """
        Scan a mod's PBRNifPatcher folder for PBR coverage information.
        
        Args:
            mod_name: Name of the mod
            mod_path: Absolute path to the mod folder
            pbr_covered_textures: Dict to populate with {texture_path: set of providing mods}
            debug_info: List to append debug information to
        """
        pbr_patcher_path = Path(mod_path) / "PBRNifPatcher"
        if not pbr_patcher_path.exists():
            return
            
        debug_info.append(f"Found PBRNifPatcher folder in '{mod_name}'")
        
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
                is_excluded = any(pattern in texture_dir.lower() for pattern in self.excluded_patterns)
                
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
                        texture_name = self.texture_utils.normalize_path(texture_name)
                        
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
                        texture_path = self.texture_utils.normalize_path(texture_path)
                        
                        # Check for non-ASCII characters (PG Patcher skips these)
                        try:
                            texture_path.encode('ascii')
                        except UnicodeEncodeError:
                            excluded_count += 1
                            if excluded_count <= 3:
                                debug_info.append(f"Excluded (non-ASCII chars): {texture_path}")
                            continue
                        
                        # Get base texture name (strip PBR suffixes for grouping)
                        base_texture_path = self.texture_utils.get_base_texture_name(texture_path).lower()
                        
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
                                
                                slot_texture_path = self.texture_utils.normalize_path(slot_texture_path)
                                
                                # Get base texture name (strip PBR suffixes)
                                base_slot_path = self.texture_utils.get_base_texture_name(slot_texture_path).lower()
                                
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