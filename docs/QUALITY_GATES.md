# Quality Gates (FAZ 1)

## Gate Layers

### 1) Intake Gate
- Is the request clear enough to execute?
- Are constraints and acceptance criteria present?

### 2) Planning Gate
- Is task graph complete and dependency-safe?
- Are risks and failure branches identified?

### 3) Execution Gate
- Do called skills match declared permissions?
- Do input/output schemas pass validation?
- Are state transitions legal?

### 4) Review Gate
- Any contradictions, missing edge cases, security issues?
- Is output aligned with acceptance criteria?

### 5) Memory Gate
- Is memory write reusable and strategic?
- Should it go to PM/KS or stay in WM?

## Minimum Gate Artifacts
- Decision (`allow` / `deny`)
- Reason code
- Trace reference
- Reviewer notes (if applicable)
