# PBR Coverage Checker - Post Mortem

## Project Summary

An attempt to create an MO2 plugin that identifies which texture mods are made redundant by PBR texture replacers, specifically targeting Amidianborn PBR vs various Xavbio texture packs.

## Final Status: Deferred to PG Patcher Author

The project successfully demonstrated the concept but revealed fundamental technical limitations that led us to pursue a better solution through the PG Patcher author.

- PG Patcher on github: <https://github.com/hakasapl/PGPatcher>

## What We Built

1. **pbr_coverage_checker.py** - Working MO2 plugin using mod folder scanning approach
2. **pbr_coverage_checker_v2.py** - Attempted virtual file system approach (abandoned)

### Working Results from V1

The folder-scanning approach successfully identified:

- **Blades Armors and Weapons Retexture SE** - 100% coverage (7/7 textures)
- **Steel Armors and Weapons Retexture SE** - 52.5% coverage (21/40 textures)
- **Ebony Armors and Weapons Retexture SE** - 48.8% coverage (20/41 textures)
- And 10+ other mods with varying coverage percentages

## Key Technical Insights Discovered

### 1. PBR Workflow Understanding

- **PBR mods** contain textures in `/pbr/` folders + JSON configuration files
- **PG Patcher** reads JSONs and patches meshes/textures according to configuration
- **Post-patch**, only normal texture paths exist in the virtual file system
- **PBR information** is stored as flags in NIF mesh files, not as separate texture paths

### 2. Why Our Approaches Had Limitations

#### Mod Folder Scanning (V1)

**Pros:**

- Successfully detected many coverage cases
- Useful for path-similar texture replacements
- Good proof of concept

**Cons:**

- Inaccurate due to JSON-driven mapping logic
- JSON files can specify different paths than folder structure suggests
- Misses complex PBR patching rules
- Path normalization is guesswork

#### Virtual File System (V2)

**Why it failed:**

- VFS only shows post-patch results (normal texture paths)
- PBR information exists in NIFs, not texture paths
- Can't distinguish PBR-enabled from non-PBR textures at VFS level

### 3. The Correct Solution

**PG Patcher coverage report** would be the ideal approach because:

- Has access to JSON configuration files
- Understands the actual patching logic
- Can provide definitive coverage information
- Would be more accurate than any reverse-engineering attempt

## Technical Achievements

1. **Working MO2 plugin architecture** - proper IPluginTool implementation
2. **Texture file discovery** - successful scanning of mod folders
3. **Path normalization logic** - handling PBR suffixes like `_rmaos`
4. **Conflict detection** - identifying overlapping texture coverage
5. **Results export** - structured output for analysis

## Code Highlights

- Two-pass texture scanning (PBR first, then regular)
- Proper handling of PBR-specific suffixes (`_rmaos`, `_m`, `_s`, etc.)
- Exclusion of normal maps (`_n.dds`) and blocked paths (cameras, dyndolod, lod, markers)
- Percentage-based coverage analysis with detailed texture lists

## Lessons Learned

1. **Domain expertise is crucial** - Understanding the actual workflow prevented wasted effort
2. **Upstream solutions are often better** - Getting the authoritative tool to add features beats reverse-engineering
3. **Proof of concepts have value** - Our working example helped communicate the need effectively
4. **Path-based heuristics have limits** - JSON configuration files contain the real truth

## Future Possibilities

If PG Patcher author doesn't implement coverage reporting:

1. **Parse PG Patcher JSON files** - Read the actual configuration to understand mappings
2. **NIF file analysis** - Learn to read PBR flags from mesh files
3. **Integration with PG Patcher** - Hook into its processing pipeline
4. **Hybrid approach** - Combine JSON parsing with mod folder scanning for missing cases

## Files for Reference

- `pbr_coverage_checker.py` - Working folder-scanning implementation
- `pbr_coverage_checker_v2.py` - VFS attempt (educational)
- `__init__.py` - Plugin initialization
- Sample output showing 100% coverage detection for Blades textures

## Outcome

Successfully demonstrated the value proposition to PG Patcher author, who expressed openness to implementing proper coverage reporting. This represents the best possible outcome - getting the authoritative tool to provide the feature rather than attempting to reverse-engineer it.

## Note

PG Patcher doesn't patch the following paths by default:

- `*\cameras\*`
- `*\dyndolod\*`
- `*\lod\*`
- `*\markers\*`

**Date:** August 2025  
**Status:** Deferred to upstream solution (PG Patcher coverage report)  
**Value:** Proof of concept successful, led to better solution path
