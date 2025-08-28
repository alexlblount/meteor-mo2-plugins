# MO2 Plugin Development: API Patterns and BSA/VFS Access

Summary of Discussion - Ready for Local IDE Implementation

---

## Core MO2 API Patterns

### Reliable Mod Renaming Pattern

```python
# ✅ LazyModlist Approach (Bulletproof)
def rename_mods_safely(self):
    modList = self._organizer.modList()
    
    # Get mods in MO2's preferred order
    all_mods = modList.allModsByProfilePriority()
    
    # Process without UI interference
    for mod_name in all_mods:
        if self._should_process_mod(mod_name):
            modObj = modList.getMod(mod_name)
            new_name = self._calculate_new_name(mod_obj.name())
            modList.renameMod(modObj, new_name)
    
    # Single completion and refresh
    QMessageBox.information(self, "Complete", "Processing finished!")
    self._organizer.refresh(saveChanges=True)  # Explicit save to disk
```

### Critical Anti-Patterns (Avoid These)

```python
# ❌ NEVER DO THIS - Causes race conditions
progress = QProgressDialog(...)
for mod in custom_order:
    progress.setValue(...)        # UI updates
    QApplication.processEvents()  # UI interference 
    modList.renameMod(...)
    QTimer.singleShot(...)       # Artificial delays
```

**Key Insights:**

- Use `allModsByProfilePriority()` for processing order
- NO `processEvents()` calls during rename loops
- NO artificial delays between `renameMod()` calls
- Single `refresh(saveChanges=True)` at completion
- Always warn users about UI locking before processing

---

## Plugin State Management Discovery

### Pattern from Discord Dev Channel

```python
# Plugin state changes don't auto-persist
pluginList.setState(plugin_name, mobase.PluginState.INACTIVE)

# Must explicitly save and refresh
organizer.refresh(saveChanges=True)  # Force disk write
```

**Implications for Mod Renaming:**

- API calls modify internal state but don't auto-persist
- `refresh()` defaults to `saveChanges=True` but explicit is better
- UI interference can disrupt the save process
- LazyModlist approach works because it doesn't interrupt state management

---

## BSA and VFS Access Capabilities

### Virtual File System Access

```python
# Get complete virtual file tree
vfs_tree = organizer.virtualFileTree()  # Returns IFileTree

# Find files in virtual data directory  
files = organizer.findFiles("textures/", "*.dds")
file_infos = organizer.findFileInfos("meshes/", lambda info: info.archive)

# Get file origins (which mod/BSA provides a file)
origins = organizer.getFileOrigins("meshes/actors/character/animations/defaultfemale.hkx")
# Returns list of mod names in priority order

# Resolve virtual path to real disk location
real_path = organizer.resolvePath("textures/landscape/grass01.dds")
```

### FileInfo Class Structure

```python
class FileInfo:
    archive: str      # Which archive (BSA) contains this file
    filePath: str     # Virtual path
    origins: list[str] # All sources providing this file (priority order)
```

### Archive Extraction (During Installation)

```python
# In installer plugins
temp_file = installation_manager.extractFile(file_entry)
temp_files = installation_manager.extractFiles([entry1, entry2])
```

---

## PBR Coverage Analysis Architecture

### VFS-Based Complete Analysis Approach

**Target Set (All Game Textures):**

```python
def get_all_game_textures(self):
    """Get complete texture set from VFS - includes BSAs + loose files"""
    all_textures = self._organizer.findFiles("textures/", ["*.dds", "*.png", "*.tga"])
    
    # Get detailed info including BSA sources
    texture_infos = self._organizer.findFileInfos("textures/", lambda info: True)
    
    return {
        'paths': set(all_textures),
        'detailed': {info.filePath: info for info in texture_infos}
    }
```

**PBR Coverage Detection:**

```python
def analyze_pbr_coverage(self):
    # Get complete texture universe (base game + DLC + mods)
    all_textures = self.get_all_game_textures()
    
    # Find PBR-related files from ALL sources (loose + BSA)
    pbr_jsons = self._organizer.findFiles("", "*.json")  # Patcher instructions
    pbr_meshes = self._organizer.findFiles("meshes/", "*.nif")
    pbr_materials = self._organizer.findFiles("materials/", "*.bgsm")
    
    # Parse coverage from all sources
    coverage = self.calculate_coverage_from_all_sources(
        all_textures['paths'], pbr_jsons, pbr_meshes, pbr_materials
    )
    
    return coverage
```

**BSA Content Analysis:**

```python
def find_pbr_instructions_in_bsas(self):
    """Find JSON patcher files that might be packed in BSAs"""
    json_files = self._organizer.findFileInfos("", 
        lambda info: info.filePath.endswith('.json') and info.archive
    )
    
    pbr_instructions = {}
    for info in json_files:
        if any(pbr_keyword in info.filePath.lower() 
               for pbr_keyword in ['pbr', 'parallax', 'enb']):
            pbr_instructions[info.filePath] = {
                'source_bsa': info.archive,
                'providing_mods': info.origins
            }
    
    return pbr_instructions
```

**Conflict Resolution Analysis:**

```python
def analyze_texture_conflicts_for_pbr(self):
    """Find where PBR textures override base textures"""
    texture_infos = self._organizer.findFileInfos("textures/", 
        lambda info: len(info.origins) > 1
    )
    
    pbr_overrides = {}
    for info in texture_infos:
        # Check if any providing mod is PBR-related
        pbr_mods = [mod for mod in info.origins if self.is_pbr_mod(mod)]
        if pbr_mods:
            pbr_overrides[info.filePath] = {
                'base_sources': [mod for mod in info.origins if not self.is_pbr_mod(mod)],
                'pbr_sources': pbr_mods,
                'winning_source': info.origins[0]  # First in list wins
            }
    
    return pbr_overrides
```

---

## Implementation Benefits

### VFS Approach Captures

- ✅ Base game textures (from Skyrim BSAs)
- ✅ DLC textures (from DLC BSAs)  
- ✅ Mod textures (loose files)
- ✅ Mod textures (from mod BSAs)
- ✅ PBR instructions (loose JSON files)
- ✅ PBR instructions (JSON files in BSAs)
- ✅ Material definitions (BGSM files anywhere)
- ✅ True conflict resolution (what actually wins)

### Result: **True Coverage Analysis**

Instead of "what PBR mods did I install", you get "what percentage of textures that actually exist in my game have PBR variants available."

---

## Key Takeaways for Development

1. **Use LazyModlist pattern for any bulk mod operations**
2. **Leverage VFS for complete file analysis (don't just scan mod folders)**
3. **Always use explicit `refresh(saveChanges=True)`**
4. **BSA content analysis opens up powerful plugin possibilities**
5. **FileInfo.origins gives you the complete mod priority chain**
