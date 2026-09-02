## [2026.9.0] - 2026-09-02

### Changed
- Based on Home Assistant 2026.9.0

### Upstream changes included
- `const.py`: Replace `component.DOMAIN` references with dedicated `DOMAIN` constants per component
- `helpers.py`: Use `EntityStateAttribute` enum instead of `ATTR_DEVICE_CLASS` / `ATTR_SUPPORTED_FEATURES`; use `er.async_get_effective_area_id`; use `dr.AnyDeviceEntry`; skip `deviceInfo` for child devices
- `trait.py`: Pervasive use of `EntityStateAttribute`, `MediaPlayerEntityStateAttribute`, `MediaPlayerEntityCapabilityAttribute` and `*_DOMAIN` constants throughout

## [2026.8.0] - 2026-08-06

### Changed
- Based on Home Assistant 2026.8.0

### Upstream changes included
- `__init__.py`: Move `request_sync` service registration to new `services.py` module
- `services.py`: New file — dedicated service registration module

## [2026.7.0] - 2026-06-16

### Changed
- Based on Home Assistant 2026.7.0

### Upstream changes included
- All files: Add `@override` decorators throughout all subclasses (Python 3.12+ `typing.override`)
- `const.py`: Map projector media players to Google TV device type
- `trait.py`: `StartStopTrait` — support vacuum zone cleaning via area registry
- `trait.py`: `ChannelTrait` — support `MediaPlayerDeviceClass.PROJECTOR`

## [2026.6.0] - 2026-06-04

### Changed
- Based on Home Assistant 2026.6.0

### Upstream changes included
- `trait.py`: Add `activeThermostatMode` to `TemperatureSettingTrait` (#166448)
- `helpers.py`: Rename `async_at_start` to `async_at_started`
- `http.py`: Fix `except TimeoutError, ClientError:` syntax to `except (TimeoutError, ClientError):`
- All files: Remove `from __future__ import annotations`
- `__init__.py`, `button.py`: Update pylint directive (`hass-use-runtime-data` → `home-assistant-use-runtime-data`)
