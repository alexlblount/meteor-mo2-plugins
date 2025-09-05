from pathlib import Path
from collections import defaultdict

class CoverageAnalyzer:
    """Analyzes PBR coverage by matching PBR textures with regular texture mods."""
    
    def __init__(self, texture_utils):
        self.texture_utils = texture_utils
        self._debug_matches = []
    
    def find_coverage_analysis(self, pbr_covered_textures, regular_textures):
        """
        Analyze coverage by matching PBR textures with regular textures.
        
        Args:
            pbr_covered_textures: Dict of {texture_path: set of providing mods}
            regular_textures: Dict of {base_texture_path: set of mod names}
            
        Returns:
            tuple: (covered_mods, uncovered_mods, coverage_providers)
        """
        covered_mods = defaultdict(list)
        uncovered_mods = defaultdict(list)
        coverage_providers = defaultdict(set)  # {mod_name: {providing_pbr_mods}}
        debug_matches = []
        
        for base_texture_path, mod_names in regular_textures.items():
            # Check if this base texture is covered by PBR
            providing_pbr_mods = set()
            match_info = f"Checking: {base_texture_path}"
            
            # Direct match (base texture names are already normalized)
            if base_texture_path in pbr_covered_textures:
                providing_pbr_mods = pbr_covered_textures[base_texture_path]
                match_info += f" -> Direct match found by {list(providing_pbr_mods)}"
            else:
                # Also check for numbered variants (_01, _02, etc.) as fallback
                base_name = Path(base_texture_path).stem
                texture_dir = str(Path(base_texture_path).parent).replace('\\', '/')
                
                for suffix in ['_01', '_02', '_03', '_04', '_05']:
                    if base_name.endswith(suffix):
                        fallback_base = base_name[:-3]
                        if texture_dir == '.':
                            fallback_path = f"{fallback_base}.dds"
                        else:
                            fallback_path = f"{texture_dir}/{fallback_base}.dds"
                        
                        if fallback_path in pbr_covered_textures:
                            providing_pbr_mods = pbr_covered_textures[fallback_path]
                            match_info += f" -> Numbered variant match found by {list(providing_pbr_mods)}"
                            break
                
                if not providing_pbr_mods:
                    match_info += " -> NO MATCH"
            
            # Store debug info for elven armor specifically
            if 'elven' in base_texture_path.lower():
                debug_matches.append(match_info)
            
            # Sort into covered or uncovered and track providers
            # mod_names is now a set, so iterate accordingly
            for mod_name in mod_names:
                if providing_pbr_mods:
                    covered_mods[mod_name].append(base_texture_path)
                    coverage_providers[mod_name].update(providing_pbr_mods)
                else:
                    uncovered_mods[mod_name].append(base_texture_path)
        
        # Store debug info for display
        self._debug_matches = debug_matches
        
        return covered_mods, uncovered_mods, coverage_providers
    
    @property
    def debug_matches(self):
        """Get debug match information for display."""
        return self._debug_matches