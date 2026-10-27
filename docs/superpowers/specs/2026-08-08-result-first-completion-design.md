# PDFdir Result-First Completion Design

## Product Read

- **User:** local PDF users who need to create, correct, or preserve navigation bookmarks.
- **Core job:** select a PDF, edit or recognize its table of contents, verify hierarchy and page mapping, then safely generate and reach a separate bookmarked PDF.
- **Product ratings:** operation risk 7, task frequency 4, information density 6, visual expression 3, motion 1.
- **Avoid:** silent draft loss, ambiguous destructive actions, stale recognition results, invalid or lossy output, accidental duplicate generation, transient completion feedback, and irrelevant settings noise.

## Evidence-Based Findings

### P1: completion has no persistent result owner

On the current Cocoa runtime, a successful write reports the generated `_new.pdf` in green while the adjacent output field immediately changes to `_new_2.pdf`. Five seconds later the success message disappears, the surface says it is ready to generate again, and the unchanged primary button creates another numbered copy. The durable file exists, but the product no longer presents that file as the completed result or offers a direct next action.

### P2: recognition settings expose controls that do not apply

The default indentation mode shows the entire disabled numbering-regular-expression group. This occupies roughly half of a low-frequency modal with controls that cannot affect the selected mode. The governing mode selector should also govern the visibility and geometry of its mode-specific controls.

### Rejected candidates

- The three stacked surfaces do not displace the visual center: the editor and preview remain the dominant work area.
- The filename and full path are not duplicate decoration. They provide document identity and location respectively, particularly at narrow widths.
- The supported 780x560 and 900x700-at-24pt layouts retain the core editors and action.
- The working state already freezes mutable inputs, identifies source and target, and promotes cancellation as the current action.

## Goal-Preservation Chain

`Safely create and reach a bookmarked PDF` -> `never overwrite an existing output, so numbered targets are selected automatically` -> `immediately replacing the completed path with the next hypothetical target hides the durable result and makes a no-change duplicate look like the primary next step` -> `retain non-overwrite behavior, but keep the actual result authoritative until the draft changes; only then compute the next safe target`.

## Intent Chain

1. User verifies the editable bookmark preview.
2. User invokes **Generate bookmarked PDF**.
3. The app freezes the source, bookmark snapshot, options, and chosen non-existing target.
4. The worker writes atomically and verifies the persisted result.
5. The action surface becomes a persistent completion state showing the actual generated path.
6. The primary action becomes **Open generated PDF** and opens that durable result through the operating system.
7. A meaningful draft or source change returns the surface to the dirty/generate state and computes the next non-existing target.
8. Returning the effective output exactly to the generated signature restores the completion state while the result still exists.
9. A missing result produces recoverable local feedback and returns the surface to generation. An unopenable but existing result retains the result path and Open action so the user can retry. Neither path deletes or overwrites files.

## Chosen Approach

Use the existing bottom action surface as a small state machine. It continues to own local status, output path, cancellation, and the one primary action. No new result card, output history, explicit save-location workflow, or dependency is introduced.

Two alternatives were rejected:

- **Copy-only correction:** relabel the next path and retain a transient status. This still leaves no direct result action and keeps accidental duplicate generation as the primary command.
- **Output chooser and result history:** this adds ceremony and a new persistent object to a single-document utility without evidence that users need output management.

## Feature Admission Card

### Feature and core user outcome

After generation, the user can unambiguously identify and open the PDF that was actually persisted. A no-change second click never silently produces a duplicate file.

### Domain object, owner, scope, and source of truth

- **Object:** latest generated result for the current in-memory document/draft.
- **Owner:** `Main` action-state logic in `src/gui/main.py`.
- **Source of truth:** generated absolute path plus the deterministic effective-output signature captured by the successful write. Filesystem existence is checked before opening or restoring completion.
- **Lifetime:** current application session. The PDF file itself is durable; the UI result state is not restored across launches.
- **Scope:** the current main window only. Switching to another source clears the current result relationship.

### Non-goals

- Choosing arbitrary output locations.
- Maintaining output history or reopening the last session.
- Revealing a file in a platform-specific file manager.
- Changing PDF write, verification, cancellation, or overwrite-safety semantics.
- Redesigning the shell, editor, preview, or menu structure.

### Capability/support matrix

| Dimension | Status | Contract |
| --- | --- | --- |
| macOS source runtime | Supported | Open the generated file with Qt desktop services; Cocoa pixel and desktop-process evidence required. |
| Windows source/runtime | Supported | Same Qt desktop-services path; semantic tests and existing CI cover behavior, package validation remains in release CI. |
| Linux source/runtime | Supported | Same Qt desktop-services path; semantic tests and existing CI cover behavior, package validation remains in release CI. |
| Chinese locale | Supported | Completion, open action, missing/unopenable recovery, and settings states are translated. |
| English locale | Supported | Same state and action coverage as Chinese. |
| 1040x720 default | Supported | Result path, status, and primary action remain visible. |
| 780x560 minimum | Supported | Result action remains contained and readable with path elision/tooltips. |
| 900x700 at 24pt | Supported | Compact action layout and mode-specific dialog geometry remain contained. |
| Packaged OCR capability | Not applicable | This change neither adds nor removes OCR support. |

### State/effect matrix

| State | User sees and can do | Persisted/external effect |
| --- | --- | --- |
| Idle, no source | Select-PDF guidance; generation disabled | None |
| Idle, source without TOC | Enter/recognize guidance; generation disabled | None |
| Dirty/ready | Ungenerated-change or ready guidance, predicted safe output, Generate primary action | None |
| Pressed | Native pressed/focus feedback on Generate | None before worker accepts the snapshot |
| Working | Frozen inputs, source-to-target status, Cancel task primary action | Temporary file may exist under existing atomic-write rules |
| Success | Persistent generated status, actual generated path, Open generated PDF primary action | Verified output PDF exists |
| Warning/error during generation | Existing local failure feedback; Generate can retry against a newly resolved safe target | Partial temporary output is rolled back by existing writer semantics |
| Cancellation | Existing cancelled feedback; Generate can retry | Temporary output is removed; no completed result is registered |
| Semantic no-op | Clicking the primary action after success opens the existing PDF; it does not generate another copy | No new PDF is written |
| Stale draft | Any current effective-output signature different from the generated signature shows dirty state and next safe target | Previous result remains on disk but is no longer presented as current |
| Return | Reverting to an effective output identical to the generated signature restores success/open while the result exists | No write |
| Missing result | Open detects absence, reports that the file moved or was removed, clears current-result ownership, and offers Generate | Existing unrelated files are untouched |
| Unopenable result | Qt reports open failure; result remains visible with an error so the user can retry or edit/regenerate | No write |
| Partial completion | Worker success is not registered until the existing persisted-output verification completes | Existing atomic rollback boundary remains authoritative |
| Rollback | Existing worker failure/cancel behavior removes temporary state and retains the prior valid result relationship, if any | No overwrite or deletion of prior output |
| Return from modal/settings | Close or Escape preserves settings and main-window action state | Existing configuration persistence semantics remain unchanged |

Action presentation follows one precedence order: active write task; active transient feedback; invalid preview; current generated result; dirty/ready/idle. A synchronizer may recompute lower states but must not overwrite a higher-priority working or feedback state. Generation failure and cancellation use the existing timed feedback override and never register a result. Missing-result feedback clears result ownership before presenting the timed error; after timeout it resolves to dirty/ready. Open-failure feedback retains result ownership; after timeout it resolves back to success/open. Locale and viewport changes re-render the current priority state and never clear its timer, ownership, or task context.

### Shared primitives and rule owners

- Main shell and surface composition: `Main._build_product_shell`.
- Local feedback: `action_status_label`, `_set_action_status`, `_refresh_action_status`.
- Output identity: existing read-only `output_path_edit` and `output_label`.
- Primary and cancellation actions: existing `export_button` and `cancel_button`.
- Draft ownership: existing draft-signature and clean/dirty methods.
- Background persistence: existing `PdfWriteWorker` and atomic PDF writer.
- Recognition settings: existing `advanced_dialog`, `advanced_mode_box`, and `sub_dir_group`.
- New shared components: none.
- Native exceptions: opening the result delegates to `QDesktopServices.openUrl(QUrl.fromLocalFile(...))`; no platform-specific process invocation is added.

### Executable component map

| Product role | Importable owner and supported variant |
| --- | --- |
| Page shell | `src.gui.main.Main`, default/compact/large-text variants |
| Primary and secondary actions | `Main.export_button` dispatches generate or open; `Main.cancel_button` owns working cancellation |
| Fields and option controls | Existing source/output line edits, hierarchy combo, offset field, and checkboxes |
| Selectable and data rows | Existing editable `QTreeWidget` bookmark rows |
| Inspector/editor header | Existing document identity and editor/preview labels |
| Resource groups and empty states | Existing document/workspace/action frames and preview empty label |
| Dialog frame, body, footer | Existing `advanced_dialog`; `sub_dir_group` is visible only for numbering mode |
| Preview, feedback, progress | Existing tree preview and local action status; no new global toast |
| New shared components required | None |
| Documented native exceptions | Qt desktop service opens the generated local file |

### Evidence registration

- **Domain/renderer:** GUI tests cover completion ownership, no-change open dispatch, dirty and exact-return transitions, source switching, missing/unopenable recovery, bilingual text, and mode-specific settings visibility.
- **Desktop process:** Cocoa E2E performs a real PDF generation and verifies that success keeps the generated target and changes the primary action without writing a second file. A separate packaged Cocoa smoke invokes the real, unstubbed Qt desktop-service dispatch for the temporary generated PDF and verifies that the operating system accepts the local-file URL; the opened temporary document is then closed during smoke cleanup.
- **Persistence:** `pypdf` reads the generated file and verifies bookmark title/page; the next numbered file remains absent after the completion action is invoked with desktop opening stubbed.
- **Geometry:** minimum and 24pt tests assert result/action containment and settings-dialog controls.
- **Pixels:** fresh independent Cocoa captures cover dirty, working, success, minimum success, indentation settings, numbering settings, and English 24pt success.
- **Package:** because `src/gui/main.py` changes, rebuild the current application before packaged smoke. Verify the fresh bundle launches and its smoke journey persists the expected bookmark. Platform release packaging outside the local host remains owned by CI.

### Completion boundary

Completion requires fresh source-suite, Cocoa GUI/E2E, pixel cold-read, persisted-PDF inspection, rebuilt-app smoke, and package-structure/signature evidence. A renderer assertion alone cannot close the result-workflow defect.

## Architecture and Data Flow

`Main` will store `last_generated_path` and `last_generated_signature`. A single action-state synchronizer derives the presentation from source validity, task state, active feedback override, current effective-output signature, result signature, and result-file existence. It owns the status text, output path, primary button text/description, and dispatch mode, while respecting the explicit precedence defined in the state matrix.

Result ownership uses a dedicated `_current_generation_signature`, not the broader close-prompt dirty signature. It contains only output-affecting data, in order: canonical source identity; keep-source-bookmarks flag; and the validated bookmark records in stable key order as `(title, real PDF page, parent key or None)`. Source identity is `expanduser` + absolute path + `normcase`. The worker captures this tuple from the same validated `index_dict` snapshot passed to `PdfWriteWorker`, before the task starts. Completion registers that frozen tuple. Current-state comparison reconstructs the same representation from the preview tree. Editing hidden numbering expressions, unmatched-line settings, source TOC text, printed-page labels, or offsets without changing the effective bookmark title/page/parent output therefore cannot make the result stale or enable duplicate generation. The existing `_current_draft_signature` may remain broader for draft-loss prompts; when indentation mode is active, it excludes the hidden numbering expressions and unmatched-line setting because they cannot affect that mode.

The primary-button handler dispatches to the existing generation method unless the synchronizer identifies a current result. In the current-result state it validates the file and delegates opening to Qt desktop services. Generation completion registers the returned path and the worker's frozen effective-output signature, marks the draft clean, and synchronizes without calling the old unconditional next-target update.

Mutations that change the effective output do not delete or rewrite the prior result. They simply make it non-current and show a newly computed safe target. If later mutations restore the exact generated signature and the file still exists, synchronization restores the result state. Source switching clears the relationship so an old document can never be presented as the current result.

Every successful source-replacement entry point clears result ownership and any active timed feedback immediately before committing the new active document. Cancelling a switch or failing to load/validate a candidate preserves the active document, its result relationship, and the existing feedback state. Clearing the typed source path also clears result ownership. A failed or cancelled later generation retains the previous result relationship in memory; it can become current again only if the effective output returns to its exact signature and that file still exists.

Write completion, failure, and cancellation are mutually exclusive terminal events for one frozen task context. The first accepted terminal callback marks that context terminal; later callbacks for the same or an obsolete context are ignored. The existing writer validates and fsyncs the temporary candidate, performs one final cancellation check, then atomically creates the non-existing target with a hard link. Cancellation observed by that final check wins and registers no result. There is no cancellable verification phase after target creation: once the hard link succeeds, the already-verified durable result wins and the worker emits success even if a cancellation request arrives afterward.

The settings mode owner will set `sub_dir_group` visibility, not only enabled state. It recalculates geometry after initial construction, before every open, after switching modes in either direction, after locale changes, and after application-font changes. At normal text, indentation mode may shrink to its visible size while numbering mode has a 680x360 minimum. At 24pt, indentation mode has a 720x360 minimum and numbering mode retains the existing 720x600 minimum with single-column rules. Every target size is capped to the current screen's available geometry with 24px horizontal and 36px vertical margins; if content exceeds that bound, the existing layout remains navigable by keyboard and no visible option or footer may fall outside the dialog. Switching back to indentation must remove the numbering group from layout geometry rather than leaving reserved blank space.

## Visual and Interaction Contract

- Preserve the neutral canvas, white work surfaces, hairline boundaries, system typography, and one-blue-primary-action grammar.
- Keep the workspace as the visual center; the change remains within the existing action surface and settings modal.
- Success is persistent green local feedback, not a toast. The actual output path remains adjacent to it.
- The primary anchor changes with the user's next meaningful intent: Generate while dirty/ready, Cancel while working, Open generated PDF after success.
- Do not introduce success illustrations, badges, extra cards, gradients, motion, or platform-specific file-manager controls.
- Long paths are elided in the field and fully available through its existing tooltip/accessibility description.
- Disabled controls remain visible only when they communicate a relevant unavailable capability. Numbering rules are irrelevant in indentation mode, so they are hidden rather than greyed out.

## Error and Recovery Rules

- A missing generated file is a local recoverable error, not a modal warning. The UI clears current-result ownership, resolves the next safe output target, and returns to Generate.
- A desktop-service open failure keeps the valid result path and open action available, reports failure locally, and performs no write.
- Worker failure and cancellation never register a result.
- Active write and transient feedback states outrank ordinary synchronization. Timed feedback clears only through its timeout or a new explicit operation; source, language, font, and resize refreshes cannot erase it.
- Source or draft changes during work remain governed by the existing frozen-input contract.
- Language or viewport changes re-render the current state; they do not change ownership, create output, or clear the result.

## Implementation Scope

Expected files:

- `src/gui/main.py`: result ownership, action dispatch/synchronization, bilingual strings, and mode-specific settings geometry.
- `tests/test_gui_product_design.py` and/or `tests/test_gui_review_fixes.py`: state, translation, geometry, and settings regression tests.
- `tests/e2e/test_desktop_journey.py`: persisted completion and no-duplicate journey.
- `docs/product-audit/2026-08-08-result-first-completion/`: final evidence receipt and current pixel captures.

No dependency, PDF format, configuration schema, release workflow, or generated UI source change is planned.
