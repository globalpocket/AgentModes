# Visible TODO V1 Contract

`VISIBLE_TODO_V1` defines the data shape that controllers must use when projecting Zoo/Roo visible TODO handoffs. It exists to prevent TODO text from being flattened into one escaped string that renders backslash+n instead of real line breaks.

## Required shape

```yaml
visible_todo:
  title: string
  items:
    - text: string
      status: pending | in_progress | completed
```

- `title` is a single-line heading and must not contain newline escapes.
- `items` is the source of truth for checklist rows; do not pre-join items into one text field.
- `status` controls checklist rendering: `pending` and `in_progress` render as unchecked rows, with `in_progress` marked in text; `completed` renders as a checked row.
- Render the visible TODO by joining `title` and rendered checklist rows with actual newline characters at the final UI/tool boundary.
- If a target tool only accepts one string, construct it from the structured fields at the last possible boundary and pass a raw multi-line string, not an escaped representation.
- Serialized artifacts may use YAML block scalars for review, but the runtime TODO payload must not contain backslash+n escape text as content.

## Rendering example

Required structured source:

```yaml
visible_todo:
  title: Current phase
  items:
    - text: Identify invariant
      status: in_progress
    - text: Run exact checks
      status: pending
    - text: Rehydrate ledger
      status: completed
```

Rendered TODO body:

```text
Current phase
- [ ] Identify invariant (in progress)
- [ ] Run exact checks
- [x] Rehydrate ledger
```

Do not store or hand off a single pre-escaped string whose visible content contains backslash+n separators.
