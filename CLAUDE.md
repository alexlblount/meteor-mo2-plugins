# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a fresh repository for meteor-mo2-plugins, currently containing only a LICENSE file. The repository appears to be intended for Mod Organizer 2 (MO2) plugins related to the Meteor project.

## Current State

The repository is in its initial state with:

- MIT License (Copyright 2025 Alex Blount)
- Empty codebase ready for development

## Development Notes

Since this is a new repository with no existing code structure, future development should establish:

- Project structure and architecture
- Build system and dependencies
- Testing framework
- Development workflow

## Purpose

You, the AI Agent, are helping the user to create Mod Organizer 2 (MO2) plugins in python. The user primarily plays modded Skyrim.

## Mod Organizer 2 api

Reference these api when writing code for MO2 plugins:

- **mo2-python-api.txt** - python api definition for MO2
- **mo2-widget-api.text** - python api definitions for UI in MO2

## Sample Files

- **changeloggen4.py** - a plugin that compares two modlists to create a changelog. organizes the output by separator.
- **LazyModlistRenamer.py and LazyModlistUnRenamer.py** - a plugin which iterates through your MO2 modlist and add's canonical naming (kind of) to the mods and separators. This serves 2 purposes: 1) Good for organization. 2) It makes your mod folders sort and import in the exact order in a new instance of MO2.
- **[NoDelete] Indexer.py** - A plugin for Mod Organizer 2 that will automatically index all mods and separators with the NoDelete tag. Also includes a backup system. Useful to keep your custom mod order when updating the modlist via Wabbajack.

## MO2 Known Issues

- Changing mod names too fast will cause `modlist.txt` to not get properly updated. This will result in breaking the mod list. The approach in `[NoDelete] Indexer.py` is prone to this side effect.
- `LazyModlistRenamer.py` and `LazyModlistUnRenamer.py` also rename multiple mods, but does not seem to trigger the issue where the modlist fails to update, likely due to a delay in updating each mod name.
- modlist.txt is in reverse order, so ordering with it must be reversed to display mods in proper order to a user in UI elements. `changeloggen4.py` has examples of reading the mod list order and displaying it to the user in sections properly.

## Successes

- 16-AUG-2025 - Released `no_delete_tagger.py` as "NoDelete Tagger and Indexer" to Nexus at <https://www.nexusmods.com/skyrimspecialedition/mods/157026>
