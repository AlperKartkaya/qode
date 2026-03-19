You are continuing work in the repository at /Users/alperkartkaya/Documents/qode.

Your job is to fully adapt the current pre-dataset scaffold to the real dataset and available API details, without leaving placeholder logic behind where real integration is now possible.

Core objective:
Take the existing architecture from assumptions/contracts/mocks/placeholders to a dataset-backed, end-to-end working system that:
1. ingests the real dataset,
2. updates assumptions before changing code,
3. implements the real analysis/data path,
4. connects every currently exposed internal endpoint/flow to the real pipeline where possible,
5. preserves the existing architecture quality and deterministic verification discipline.

Important repository context:
- `assumptions.md` is the source of truth for provisional assumptions and MUST be updated first when reality differs.
- Current major modules:
  - `src/smart_road_safety/data/` dataset adapter slot and ingestion planning
  - `src/smart_road_safety/analysis/` placeholder analysis boundary
  - `src/smart_road_safety/orchestration/` telecom workflow orchestration
  - `src/smart_road_safety/integration/` Number Verification / QoD contracts and mocks
  - `src/smart_road_safety/evaluation/` deterministic scenario evaluation
  - `src/smart_road_safety/export/` markdown reporting
  - `src/smart_road_safety/local_api/` thin local HTTP API
  - `src/smart_road_safety/cli.py` command surface
- Current examples and test fixtures are placeholders and should be updated only when the real dataset/API reality is understood.
- Current assumptions include dataset, orchestration, evaluation, export, API, and analysis assumptions. Respect them, then revise them.

Inputs you should expect me to provide:
- Real dataset root: <DATASET_ROOT>
- Dataset docs / README / label description: <DATASET_DOCS_PATH_OR_URL>
- API docs or endpoint details for Number Verification / QoD if available: <API_DOCS_PATH_OR_URL>
- Credentials or env requirements if available: <ENV_DETAILS_OR_CREDENTIAL_SETUP>

Execution requirements:
- Start by reading `assumptions.md`, `README.md`, and the current modules under `src/smart_road_safety/`.
- Inspect the real dataset tree and documentation before implementing.
- Create or update a real manifest in the shape expected by the current manifest tooling.
- Run the current manifest checker and identify every broken assumption.
- Update `assumptions.md` first, assumption by assumption, before changing ingestion/training/evaluation logic.
- Replace placeholders only where reality is now known.
- Keep stable contracts where they still make sense; adapt them where the real dataset/API contradicts them.
- Do not keep silent placeholders in paths that should now be real.
- If a path still cannot be fully implemented because an external dependency is missing, make that explicit and isolate it behind the existing interfaces.

Implementation scope:
A. Dataset adaptation
- Implement the real dataset loader(s) using the current adapter-slot architecture.
- Support the actual dataset structure, sample unit, annotation format, target taxonomy, and split strategy.
- Replace assumed manifests/examples with real ones where appropriate.
- Preserve or improve validation of malformed or partial dataset inputs.

B. Analysis boundary
- Replace placeholder analysis input flow with real dataset-backed analysis flow.
- Map real dataset fields / inference outputs into the stable analysis result contract, or revise the contract if the dataset proves it wrong.
- Handle all required target families that are actually present: vehicle, plate, speed, in-cabin object/behavior, risk signals, etc.
- If some targets are absent from the dataset, update assumptions and make those capabilities explicitly optional.

C. Orchestration and telecom integration
- Connect the analysis output into orchestration with real data, not placeholder heuristic payloads.
- Keep Number Verification and QoD flows wired through existing contracts.
- If real telecom endpoints are available, implement real clients behind the current interfaces.
- If telecom endpoints are still unavailable, preserve the real analysis integration and keep mocks only for the truly unavailable external parts.
- Do not leave placeholder booleans or fake controls in places where real behavior can now be derived.

D. Evaluation and reporting
- Replace placeholder scoring with dataset-backed evaluation wherever ground truth allows.
- Extend scenario coverage using real or realistic cases derived from the dataset.
- Keep markdown export useful for judges/reporting and update it if the report schema changes.
- Ensure exported artifacts reflect real analysis/evaluation results, not synthetic-only outputs.

E. Local API and CLI
- Update CLI commands and local API endpoints so they operate on the real analysis/data flow.
- Keep existing endpoints working unless a contract change is required by reality.
- If contracts change, update tests, docs, examples, and exports consistently.
- Ensure the local API remains a practical demo/development surface.

Non-negotiable workflow:
1. Read repo and dataset.
2. Update `assumptions.md`.
3. Update/add real manifest.
4. Implement dataset adapter(s).
5. Replace placeholder analysis path.
6. Connect orchestration/evaluation/export/local API to the real path.
7. Update tests.
8. Run diagnostics.
9. Run tests.
10. Manually execute the real flow and show evidence.

Acceptance criteria:
- All contradicted assumptions are updated in `assumptions.md`.
- Real dataset ingestion works from `<DATASET_ROOT>`.
- Placeholder analysis flow is replaced or explicitly reduced only where reality demands.
- Current CLI/API surfaces are connected to the real path wherever possible.
- Evaluation uses real ground truth where available.
- Tests pass.
- Diagnostics are clean.
- Manual QA is shown with actual command/API output.
- README and relevant examples are updated to the new reality.
- Any remaining blocker is explicitly external and documented.

Verification checklist:
- Run Python diagnostics on changed files.
- Run the unit test suite.
- Run the dataset manifest check against the real manifest.
- Run the analysis session / orchestration flow on real dataset-backed input.
- Run scenario evaluation if still applicable.
- Generate markdown export from real outputs.
- Exercise the local API endpoints with real-backed flows.
- Show actual outputs, not guesses.

Constraints:
- Do not use `as any`, `@ts-ignore`, or similar suppression patterns in any language.
- Do not leave dead placeholder code where real code can now exist.
- Do not silently change contracts without updating tests/docs/examples.
- Do not skip updating `assumptions.md`.
- Do not introduce unnecessary frameworks.
- Prefer small, clear, testable changes over large rewrites unless the dataset reality forces a redesign.

Deliverables at the end:
- Updated `assumptions.md`
- Real dataset manifest and adapter implementation
- Real analysis/data path
- Updated orchestration/evaluation/export/local API integrations
- Passing tests and diagnostics
- Manual QA evidence
- A concise summary of:
  - what assumptions changed,
  - what was fully integrated,
  - what remains blocked externally, if anything,
  - and a suggested commit message

Proceed until you reach a clean commit point. Do not commit or push.
