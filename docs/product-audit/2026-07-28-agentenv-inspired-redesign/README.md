# AgentEnv-inspired desktop redesign evidence

## Product contract

- Core job: select a PDF, edit or recognize its table of contents, verify bookmark hierarchy and page mapping, then generate a separate PDF safely.
- Shell: page identity and current document stay above one editor/preview work surface; parsing tools stay inside that surface; output, cancellation, status, and the primary generation command stay fixed below it.
- Primary visibility invariant: the current document, editor, preview, local status, cancellation, and generation command remain available at every supported size and applicable state.
- Visual calibration: system typography, neutral canvas, white work surfaces, hairline boundaries, compact controls, one blue primary command, and restrained selection treatment. The AgentEnv Manager sidebar and multi-destination structure were intentionally not copied into this single-task utility.

## Capture matrix

All captures use the same working-tree artifact, Python 3.12.11, PyQt5 5.15.11, the macOS Cocoa Qt platform, 100% scale, and the same realistic PDF/TOC fixture unless noted.

| Capture | Viewport or surface | State |
|---|---:|---|
| `01-default-1040x720.png` | 1040x720 | Chinese, populated, idle |
| `02-minimum-780x560.png` | 780x560 | Chinese, populated, compact |
| `03-recognition-settings.png` | settings dialog | numbering rules enabled |
| `04-working-1040x720.png` | 1040x720 | generation working, cancellation visible |
| `05-english-minimum-780x560.png` | 780x560 | English chrome, long mixed-language data |

`QMainWindow.grab()` captures the application surface but excludes native title-bar chrome. Packaged launch is verified separately by the release smoke test.

## Visual approval

- Default/minimum and idle/working state pairs preserve the primary command and local status.
- The recognition settings dialog no longer changes main-window geometry and supports Escape with focus restoration.
- The minimum-height rule removes secondary pane hints before compressing the editing regions.
- English control labels remain contained at the minimum supported window.
