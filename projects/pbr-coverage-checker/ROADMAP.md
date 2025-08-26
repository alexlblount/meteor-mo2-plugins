# PBR Coverage Checker - Development Roadmap

## Current Status

- ✅ Basic PBR coverage analysis using PBRNifPatcher folders
- ✅ Fixed path separator issues for Windows compatibility
- ✅ Added support for underscored texture variants (`_em, _d, etc.`)
- ✅ Export functionality for analysis results
- ✅ **Phase 1.1 Complete**: Enhanced reporting with PBR provider information

## Phase 1: Enhanced Reporting (Next Priority)

### 1.1 Show Covering Mods ✅ COMPLETE

- ✅ Add which PBR mod(s) are providing coverage for each texture
- ✅ Display as a list in the output (don't need exact texture-to-mod mapping)
- ✅ Update both UI display and export functionality
- ✅ BONUS: Implemented accurate base texture counting using PG Patcher's official suffix definitions
- ✅ BONUS: Added condensed format for 100% covered mods

### 1.2 VFS-Based Analysis

- Use MO2's VFS to get complete texture inventory from all sources
- Compare VFS textures against PBR coverage
- API Implementation:

  ```python
  # Get complete texture universe (base game + DLC + mods + BSAs)
  all_textures = organizer.findFiles("textures/", ["*.dds", "*.png", "*.tga"])
  texture_infos = organizer.findFileInfos("textures/", lambda info: True)
  
  # Get file origins to show which mods provide each texture
  for texture in problem_textures:
      origins = organizer.getFileOrigins(texture)  # Returns mod priority list
  ```

- This will show coverage for:
  - ✅ Base game textures (from Skyrim BSAs)
  - ✅ DLC textures (from DLC BSAs)
  - ✅ Creation Club content
  - ✅ All mod-added textures (loose + BSA)
  - ✅ True conflict resolution (what actually wins)

### 1.3 PG Patcher Logic Integration

- Download/reference PG Patcher repository
- Study their texture/mesh detection logic
- Integrate improved detection patterns into our tool
- Ensure we match PG Patcher's patching behavior exactly

## Phase 2: Advanced Features (Future)

### 2.1 BSA Support

- Scan PBRNifPatcher folders inside BSA files
- Handle packed JSON files from PBR mods
- API Implementation:

  ```python
  # Find JSON patcher files in BSAs
  json_files = organizer.findFileInfos("", 
      lambda info: info.filePath.endswith('.json') and info.archive)
  
  # Filter for PBR-related files
  pbr_jsons = [info for info in json_files 
               if any(keyword in info.filePath.lower() 
                     for keyword in ['pbr', 'parallax', 'patcher'])]
  ```

- Note: Rarely used but would provide complete coverage

### 2.2 Performance Optimizations

- Caching mechanisms for large mod lists
- Incremental analysis (only scan changed mods)
- Background processing for large installations

## Progress Log

### Phase 1.1 Completion (Dec 2024)

**Deliverables:**

- Enhanced output format showing which mods provide PBR coverage
- Condensed display for 100% covered mods: `✓ Mod Name [PBR Providers]`
- Detailed display for partial coverage with provider info
- Both UI and export functionality updated

**Technical Improvements:**

- Integrated PG Patcher's official texture suffix definitions from source code
- Fixed texture variant grouping (e.g., `armor_d.dds`, `armor_n.dds`, `armor_em.dds` → `armor` base texture)
- Accurate coverage percentages based on base textures instead of individual files
- Path separator normalization for cross-platform compatibility

**Output Enhancement:**

```
✓ Fully covered by PBR
------------------------------------
  Ancient Falmer Armors SE [Amidianborn PBR]
  Blades Armor SE [Amidianborn PBR, Alternative Armors PBR]

Partial PBR coverage:
------------------------------------

Elven Armors SE  
  Coverage: 8/10 base textures (80%)
  PBR provided by: Alternative Armors PBR
  Missing PBR coverage for base textures:
    - creationclub/bgssse043/weapons/elven/elvencrossbow01.dds
    - creationclub/bgssse064/armor/elvenmail/f/elvenarmor_variant.dds
```

## Implementation Notes

### VFS Integration Approach

```python
# Complete texture universe analysis
def analyze_complete_pbr_coverage(self):
    # Get all textures from all sources (base game + mods + BSAs)
    all_textures = self._organizer.findFiles("textures/", ["*.dds"])
    texture_infos = self._organizer.findFileInfos("textures/", lambda info: True)
    
    # Get detailed origins for conflict analysis
    detailed_textures = {info.filePath: info for info in texture_infos}
    
    # Find all PBR instructions (loose + BSA)
    pbr_jsons = self._organizer.findFiles("", "*.json")
    pbr_in_bsa = self._organizer.findFileInfos("", 
        lambda info: info.filePath.endswith('.json') and info.archive)
    
    return self.calculate_true_coverage(all_textures, detailed_textures, 
                                       pbr_jsons, pbr_in_bsa)
```

### PG Patcher Integration

- Repository: <https://github.com/kapil-dev-code/PBR-Graphics-Patcher>
- Key files to study:
  - Texture detection patterns
  - Exclusion rules
  - Mesh patching logic

### Data Structure Improvements

```python
# Track which mods provide coverage
pbr_coverage = {
    'texture_path': {
        'covered_by': ['mod1', 'mod2'],
        'json_files': ['file1.json', 'file2.json']
    }
}
```

## Testing Strategy

- Test with various PBR mod combinations
- Verify against known PBR coverage (Amidianborn, Alternative Armors, etc.)
- Performance testing with large mod lists (500+ mods)
- Validation against PG Patcher results

## Long-term Vision

- Complete PBR coverage analysis for entire Skyrim installation
- Integration with mod management workflows
- Automated recommendations for PBR gaps
- Support for other games using similar PBR patching systems
