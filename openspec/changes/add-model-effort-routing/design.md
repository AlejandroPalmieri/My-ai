# Design

## Effort Profiles

`agentos.models.effort` defines `low`, `medium`, `high`, and `max` with
temperature defaults, max output token hints, reasoning budget hints, and
intended use.

## Routing

`agentos.models.routing` owns `.agentos/model-routing.yaml` and validates route
names, model profile names, and effort values.

Default routes:

- `default_chat`: `medium`
- `coding`: `high`
- `sdd_explore`: `medium`
- `sdd_design`: `high`
- `sdd_verify`: `max`
- `refiner_analyze`: `high`
- `safety_review`: `max`

## Integration

Explicit CLI `--effort` wins over route defaults. Agents without `--effort`
use the `coding` route. Dashboard model status shows the effective chat route
effort.
