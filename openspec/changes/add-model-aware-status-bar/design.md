# Design

## Data Boundary

Create a small UI model summary derived from `inspect_model_status(root)`.
The dashboard renderer consumes this summary instead of reading model config
directly.

## Rendering

The bottom bar has two zones:

- Left: keybindings.
- Right: model/runtime usage.

Compact mode renders the shorter model runtime string for narrow terminals.

## Fallbacks

When model config is missing, `inspect_model_status` creates or returns the
default local-stub configuration. Unknown context windows render `ctx: n/a`.
Unknown cost renders `cost: n/a`.
