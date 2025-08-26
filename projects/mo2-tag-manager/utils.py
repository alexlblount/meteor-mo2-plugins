"""
Utility functions for MO2 Tag Manager.
Handles tag parsing, mod analysis, and string operations.
"""

import re
from typing import List, Dict, Set, Tuple


def strip_mod_tags(mod_name: str) -> str:
    """
    Remove all tags in square brackets from the beginning of a mod name.
    Examples:
    "[NoDelete] Awesome Mod" -> "Awesome Mod"
    "[NoDelete] [009.00001] [Custom] Awesome Mod" -> "Awesome Mod"
    "[Tag1][Tag2] Mod Name" -> "Mod Name"
    """
    pattern = r'^(\[[^\]]+\]\s*)+\s*'
    return re.sub(pattern, '', mod_name).strip()


def strip_numerical_index(mod_name: str) -> str:
    """
    Remove numerical index [xxx.xxxxx] from mod name while preserving other tags.
    Only removes indexes in the specific format: [XXX.XXXXX] (3 digits, dot, 5 digits)
    Examples:
    "[NoDelete] [009.00001] [Custom] Awesome Mod" -> "[NoDelete] [Custom] Awesome Mod"
    "[SomeTag] [009.00001] Mod Name" -> "[SomeTag] Mod Name"
    "[v1.2] Mod Name" -> "[v1.2] Mod Name" (preserved - not our format)
    """
    # Match exactly 3 digits, dot, exactly 5 digits
    pattern = r'\s*\[[0-9]{3}\.[0-9]{5}\]\s*'
    return re.sub(pattern, ' ', mod_name).strip()


def parse_mod_tags(mod_name: str) -> Dict[str, any]:
    """
    Parse all tags from a mod name and return structured information.
    
    Returns:
    {
        'nodelete': bool,
        'index': str or None,  # e.g., "009.00001"
        'custom_tags': List[str],
        'clean_name': str
    }
    """
    result = {
        'nodelete': False,
        'index': None,
        'custom_tags': [],
        'clean_name': mod_name
    }
    
    # Find all tags at the beginning
    tags_match = re.match(r'^(\[[^\]]+\]\s*)+', mod_name)
    if not tags_match:
        return result
    
    tags_section = tags_match.group(0)
    result['clean_name'] = mod_name[len(tags_section):].strip()
    
    # Extract individual tags
    tag_pattern = r'\[([^\]]+)\]'
    tags = re.findall(tag_pattern, tags_section)
    
    for tag in tags:
        if tag == "NoDelete":
            result['nodelete'] = True
        elif re.match(r'^[0-9]{3}\.[0-9]{5}$', tag):
            result['index'] = tag
        else:
            result['custom_tags'].append(tag)
    
    return result


def build_mod_name(clean_name: str, nodelete: bool = False, index: str = None, custom_tags: List[str] = None) -> str:
    """
    Build a mod name with tags in the correct order: [NoDelete] [index] [custom] name
    """
    if custom_tags is None:
        custom_tags = []
    
    parts = []
    
    # Add tags in order
    if nodelete:
        parts.append("[NoDelete]")
    
    if index:
        parts.append(f"[{index}]")
    
    for custom_tag in custom_tags:
        parts.append(f"[{custom_tag}]")
    
    # Combine with clean name
    if parts:
        return f"{' '.join(parts)} {clean_name}".strip()
    else:
        return clean_name


class ModSectionUtils:
    """Utility class for analyzing mod organization by separators."""
    
    @staticmethod
    def analyze_mod_organization(mod_list) -> Tuple[Dict[str, List[str]], List[str], Dict[str, str]]:
        """
        Analyze the current mod list and organize mods by separator sections.
        
        Returns:
        - sections: Dict[section_name, List[mod_names]]
        - section_order: List[section_names] in display order
        - separator_map: Dict[section_name, separator_mod_name]
        """
        sections = {}
        section_order = []
        separator_map = {}
        mod_buffer = []
        current_section = "Unsectioned"
        
        # Get all mods in priority order and REVERSE it to read correctly
        all_mods = list(reversed(mod_list.allModsByProfilePriority()))
        
        for mod_name in all_mods:
            mod_obj = mod_list.getMod(mod_name)
            if not mod_obj:
                continue
                
            # Skip system mods
            mod_path = mod_obj.absolutePath().lower()
            if any(skip in mod_path for skip in ["game root/data", "stock game/data", "skyrim special edition/data"]):
                continue
            
            # Check if this is a separator
            if mod_obj.isSeparator() or mod_name.endswith('_separator'):
                # Get section name
                if mod_name.endswith('_separator'):
                    section_name = mod_name[:-10]  # Remove '_separator' suffix
                else:
                    section_name = strip_mod_tags(mod_name)
                
                # Assign all buffered mods to this section
                if mod_buffer:
                    sections[section_name] = mod_buffer.copy()
                    mod_buffer = []
                
                # Track section order and separator mapping
                if section_name not in section_order:
                    section_order.append(section_name)
                    separator_map[section_name] = mod_name
                
                continue
            
            # Regular mod - add to buffer
            mod_buffer.append(mod_name)
        
        # Handle any remaining mods in buffer
        if mod_buffer:
            sections[current_section] = mod_buffer.copy()
            if current_section not in section_order:
                section_order.append(current_section)
        
        return sections, section_order, separator_map