## [2026.6.0] - 2026-06-04

### Changed
- Based on Home Assistant 2026.6.0

### Upstream changes included
- `trait.py`: Add `activeThermostatMode` to `TemperatureSettingTrait` (#166448)
- `helpers.py`: Rename `async_at_start` to `async_at_started`
- `http.py`: Fix `except TimeoutError, ClientError:` syntax to `except (TimeoutError, ClientError):`
- All files: Remove `from __future__ import annotations`
- `__init__.py`, `button.py`: Update pylint directive (`hass-use-runtime-data` → `home-assistant-use-runtime-data`)
