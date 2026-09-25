# PDFdir semantic-choice product review

## Product Read

- User: local PDF users who need to create, correct, or preserve navigation bookmarks.
- Core job: select a PDF, edit or recognize its TOC, verify hierarchy and page mapping, then generate a separate PDF safely.
- Product ratings: operation risk 7, task frequency 4, information density 6, visual expression 3, motion 1.
- Avoid: silent draft loss, ambiguous destructive actions, stale recognition results, invalid generation, lossy PDF output, and incomplete release evidence.

## Change Evidence Card

- Core outcome: switching PDFs, importing existing bookmarks, and closing the app must never make the user guess whether a draft will be kept or discarded.
- Governing layer: the main-window semantic choice-dialog primitive owns labels, default actions, Escape behavior, and the mapping from a clicked action to its data effect.
- Goal-preservation chain: keep every existing branch -> literal Yes/No labels hide the branch effect -> users must reread prose before a risky action -> name each effect while preserving the current data semantics and safe defaults.
- Intent chain:
  - Switch PDF -> keep draft / clear draft / cancel.
  - Import existing bookmarks over a draft -> import and replace / keep current draft.
  - Close with ungenerated changes -> discard and close / keep editing.
- No-op and recovery: closing a dialog, pressing Escape, or choosing the safe default leaves the current draft and document unchanged.
- Persistence effect: only the explicit destructive action may clear or discard draft state; generated PDFs and output-path behavior are unchanged.

## Product and visual contract

- Shell invariant: document identity, TOC editor, bookmark preview, local task status, cancellation, output, and generation remain visible at every supported size and applicable state.
- Emphasis budget: one recommended safe action may receive the native default focus; a destructive action is explicit but never presented as the recommended primary action.
- Primary anchor: AgentEnv Manager's system typography, neutral canvas, white work surfaces, hairline boundaries, compact controls, and one blue primary command.
- Rejected borrowing: sidebar navigation, dashboard cards, gradients, hover lift, and multi-destination structure do not support this single-task utility.
- Motion record: all additional animation candidates were rejected; native modal presentation and immediate focus feedback are sufficient for a motion rating of 1.

## Supported state matrix

| Surface | Idle | Working | Error | Destructive decision | Languages | Viewports |
| --- | --- | --- | --- | --- | --- | --- |
| Main shell | populated and dirty | generation with cancel | invalid recognition rule | n/a | Chinese and English | 1040x720, 780x560, 900x700 at 24pt |
| Switch PDF | n/a | n/a | n/a | keep / clear / cancel | Chinese and English | native dialog size |
| Import bookmarks | n/a | n/a | n/a | import and replace / keep current | Chinese and English strings covered | native dialog size |
| Close dirty draft | n/a | n/a | n/a | discard and close / keep editing | Chinese and English strings covered | native dialog size |

## Finding and correction

| Severity | Contract + runtime + correction evidence | Resolution |
| --- | --- | --- |
| P1 | The draft-safety contract requires explicit data effects; Cocoa showed switch, replace, and close dialogs with generic Yes/No buttons; replacing those labels with semantic verbs and retaining safe defaults removes the ambiguity without deleting any workflow branch. | Added a shared semantic choice-box builder, explicit Chinese/English verbs, safe default and Escape actions, and result-mapping tests across all three sibling flows. |

The initially suspicious 24pt working-state capture was rejected as a finding after clean-process and live-font reproductions both preserved the title, action area, and main-shell geometry. No code was changed for an unreproducible capture artifact.

## Visual evidence

Before/after decision pairs:

- [Switch PDF before](01-switch-before.png) / [after](04-switch-after.png)
- [Replace draft before](02-import-before.png) / [after](05-import-after.png)
- [Close dirty draft before](03-close-before.png) / [after](06-close-after.png)
- [English switch dialog](07-switch-english-after.png)

Current-code shell and state captures:

- [Default 1040x720](08-shell-default.png)
- [Minimum 780x560](09-shell-minimum.png)
- [Generation working 1040x720](10-shell-working.png)
- [Inline regular-expression error](11-regex-error.png)
- [English 24pt 900x700](12-shell-english-large-font.png)

Manual pixel cold-read: the final dialog set uses native macOS role ordering, keeps the safe action focused, does not promote destructive actions, and contains all Chinese and English labels. The unchanged shell preserves its hierarchy, containment, and action visibility in every captured state.

## Change-to-evidence map

| Change | Semantic evidence | Desktop evidence | Pixel evidence | Persistence/package evidence |
| --- | --- | --- | --- | --- |
| Shared semantic choice dialog | unit tests inspect labels, defaults, Escape, and clicked results | Cocoa prompt interaction tests | three paired dialogs plus English capture | existing document-switch, import, and dirty-close integration tests |
| Bilingual action labels | translation assertions | Cocoa Chinese and English dialogs | `04` through `07` | no persistence format change |
| Safe destructive defaults | explicit default and Escape assertions | native focus and button roles | blue focus remains on keep/cancel actions | generated-PDF behavior is unchanged and revalidated by E2E/smoke gates |

## Completion Evidence Receipt

- Functional: Python 3.9.6 and Python 3.12.11 each passed all 158 tests. The semantic-dialog tests cover labels, default and Escape actions, clicked-result mapping, document switching, bookmark import, and dirty-close behavior.
- Persistence: the desktop E2E and both packaged smoke runs generated a separate PDF and verified the persisted bookmark title and target page; existing output-path and non-overwrite tests remained green.
- Visual: 12 current review images include three before/after dialog pairs, bilingual choice surfaces, default and minimum shells, generation, inline error, and English 24pt states. Manual cold-read found no clipping, containment, hierarchy, or destructive-emphasis regression.
- Desktop process: 54 GUI and E2E tests passed with the native Cocoa Qt platform, including modal interaction, focus, cancellation, background workers, large text, and the full generate journey.
- Packaged artifact: a fresh arm64 `.app` was built from code commit `d7c04ef`; 17/17 tracked package inputs matched that commit and all 109 Mach-O files contained arm64. Isolated offscreen and Cocoa `--smoke-test` runs both returned 0. Bundle metadata was normalized to `com.chroming.pdfdir`, version `0.3.0`, build `1`; strict ad-hoc signature verification passed.
- Archive: `/tmp/pdfdir-review-package-phAyPX/pdfdir_mac_silicon-d7c04ef.zip`, SHA-256 `cc919158189255e2b69e9c19ed4b63d26115b773e3d4ddeea19978843f94ae27`.
- Release boundary: this local package is ad-hoc signed. Developer ID signing, notarization, staple, and Gatekeeper remain mandatory in the credentialed tag workflow and were not claimed locally.
