"""Support for Actions on Google Assistant Smart Home Control."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

import voluptuous as vol
import yaml

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.components.persistent_notification import (
    async_create as pn_async_create,
)
from homeassistant.const import CONF_API_KEY, CONF_NAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .const import (  # noqa: F401
    CONF_ALIASES,
    CONF_CLIENT_EMAIL,
    CONF_ENTITY_CONFIG,
    CONF_EXPOSE,
    CONF_EXPOSE_BY_DEFAULT,
    CONF_EXPOSED_DOMAINS,
    CONF_PRESENCE_ENTITY,
    CONF_PRIVATE_KEY,
    CONF_PROJECT_ID,
    CONF_REPORT_STATE,
    CONF_REQUIRE_ACK,
    CONF_REQUIRE_PRESENCE,
    CONF_ROOM_HINT,
    CONF_SECURE_DEVICES_PIN,
    CONF_SERVICE_ACCOUNT,
    DATA_CONFIG,
    DEFAULT_EXPOSE_BY_DEFAULT,
    DEFAULT_EXPOSED_DOMAINS,
    DOMAIN,
    EVENT_QUERY_RECEIVED,
    SERVICE_REQUEST_SYNC,
    SOURCE_CLOUD,
)
from .http import GoogleAssistantView, GoogleConfig

from .const import EVENT_COMMAND_RECEIVED, EVENT_SYNC_RECEIVED  # noqa: F401, isort:skip

_LOGGER = logging.getLogger(__name__)

CONF_ALLOW_UNLOCK = "allow_unlock"

PLATFORMS = [Platform.BUTTON]

SERVICE_EXPORT_CONFIG = "export_unleashed_config"
CONF_FILENAME = "filename"
DEFAULT_EXPORT_FILENAME = "google_assistant_unleashed_export.yaml"

ENTITY_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_EXPOSE, default=True): cv.boolean,
        vol.Optional(CONF_ALIASES): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_ROOM_HINT): cv.string,
        vol.Optional(CONF_REQUIRE_ACK, default=False): cv.boolean,
        vol.Optional(CONF_REQUIRE_PRESENCE, default=False): cv.boolean,
        vol.Optional(CONF_PRESENCE_ENTITY): cv.entity_id,
    }
)

GOOGLE_SERVICE_ACCOUNT = vol.Schema(
    {
        vol.Required(CONF_PRIVATE_KEY): cv.string,
        vol.Required(CONF_CLIENT_EMAIL): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)


def _check_report_state(data):
    if data[CONF_REPORT_STATE] and CONF_SERVICE_ACCOUNT not in data:
        raise vol.Invalid("If report state is enabled, a service account must exist")
    return data


GOOGLE_ASSISTANT_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Required(CONF_PROJECT_ID): cv.string,
            vol.Optional(
                CONF_EXPOSE_BY_DEFAULT, default=DEFAULT_EXPOSE_BY_DEFAULT
            ): cv.boolean,
            vol.Optional(
                CONF_EXPOSED_DOMAINS, default=DEFAULT_EXPOSED_DOMAINS
            ): cv.ensure_list,
            vol.Optional(CONF_ENTITY_CONFIG): {cv.entity_id: ENTITY_SCHEMA},
            # str on purpose, makes sure it is configured correctly.
            vol.Optional(CONF_SECURE_DEVICES_PIN): str,
            vol.Optional(CONF_PRESENCE_ENTITY): cv.entity_id,
            vol.Optional(CONF_REPORT_STATE, default=False): cv.boolean,
            vol.Optional(CONF_SERVICE_ACCOUNT): GOOGLE_SERVICE_ACCOUNT,
            # deprecated configuration options
            vol.Remove(CONF_ALLOW_UNLOCK): cv.boolean,
            vol.Remove(CONF_API_KEY): cv.string,
        },
        extra=vol.PREVENT_EXTRA,
    ),
    _check_report_state,
)

CONFIG_SCHEMA = vol.Schema(
    {vol.Optional(DOMAIN): GOOGLE_ASSISTANT_SCHEMA}, extra=vol.ALLOW_EXTRA
)

type GoogleConfigEntry = ConfigEntry[GoogleConfig]


async def async_setup(hass: HomeAssistant, yaml_config: ConfigType) -> bool:
    """Activate Google Actions component."""
    if DOMAIN not in yaml_config:
        return True

    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][DATA_CONFIG] = yaml_config[DOMAIN]

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={CONF_PROJECT_ID: yaml_config[DOMAIN][CONF_PROJECT_ID]},
        )
    )

    return True


def _merge_options_into_config(config: ConfigType, options: Mapping[str, Any]) -> None:
    """Merge options flow data into the YAML config.

    Options flow stores unleashed settings as:
      {
        "presence_entity": "input_boolean.home",
        "require_acknowledgment": ["lock.front_door", ...],
        "require_presence": ["lock.front_door", ...],
      }

    Once the user has saved the options flow at least once, the UI becomes
    the source of truth for unleashed keys. This means:
    - Entities in the UI lists get the feature enabled
    - Entities NOT in the UI lists get the feature explicitly disabled
      (even if YAML had them enabled)
    """
    if not options:
        return

    # Merge global presence entity. Once the user has saved the options
    # flow, the UI value takes priority — including clearing it.
    if CONF_PRESENCE_ENTITY in options:
        ui_presence = options[CONF_PRESENCE_ENTITY]
        if ui_presence:
            config[CONF_PRESENCE_ENTITY] = ui_presence
        else:
            config.pop(CONF_PRESENCE_ENTITY, None)

    # Merge per-entity unleashed settings
    ack_entities: set[str] = set(options.get(CONF_REQUIRE_ACK, []))
    presence_entities: set[str] = set(options.get(CONF_REQUIRE_PRESENCE, []))

    entity_config = config.setdefault(CONF_ENTITY_CONFIG, {})

    # Apply UI state to all entities that appear in either the UI lists
    # or the existing YAML entity_config. This ensures that removing an
    # entity from the UI list actually disables the feature, even if YAML
    # still has it enabled.
    all_entities = ack_entities | presence_entities | set(entity_config.keys())

    for entity_id in all_entities:
        entity_cfg = entity_config.setdefault(entity_id, {})
        entity_cfg[CONF_REQUIRE_ACK] = entity_id in ack_entities
        entity_cfg[CONF_REQUIRE_PRESENCE] = entity_id in presence_entities


def _build_export_data(config: ConfigType) -> dict[str, Any]:
    """Build the unleashed-only config data for export.

    Extracts only the unleashed-specific keys from the effective config,
    producing a clean YAML snippet the user can merge into configuration.yaml.
    """
    export: dict[str, Any] = {}

    if presence := config.get(CONF_PRESENCE_ENTITY):
        export[CONF_PRESENCE_ENTITY] = presence

    entity_config: dict[str, dict] = config.get(CONF_ENTITY_CONFIG, {})
    entity_export: dict[str, dict] = {}

    for entity_id, cfg in entity_config.items():
        unleashed_cfg: dict[str, Any] = {}
        if cfg.get(CONF_REQUIRE_ACK):
            unleashed_cfg[CONF_REQUIRE_ACK] = True
        if cfg.get(CONF_REQUIRE_PRESENCE):
            unleashed_cfg[CONF_REQUIRE_PRESENCE] = True
        if per_entity_presence := cfg.get(CONF_PRESENCE_ENTITY):
            unleashed_cfg[CONF_PRESENCE_ENTITY] = per_entity_presence
        if unleashed_cfg:
            entity_export[entity_id] = unleashed_cfg

    if entity_export:
        export[CONF_ENTITY_CONFIG] = entity_export

    return export


async def async_setup_entry(hass: HomeAssistant, entry: GoogleConfigEntry) -> bool:
    """Set up from a config entry."""

    config: ConfigType = {**hass.data[DOMAIN][DATA_CONFIG]}

    if entry.source == SOURCE_IMPORT:
        # if project was changed, remove entry a new will be setup
        if config[CONF_PROJECT_ID] != entry.data[CONF_PROJECT_ID]:
            hass.async_create_task(hass.config_entries.async_remove(entry.entry_id))
            return False

    config.update(entry.data)

    # Merge UI options into config (UI takes priority over YAML for unleashed keys)
    _merge_options_into_config(config, entry.options)

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, config[CONF_PROJECT_ID])},
        manufacturer="Google",
        model="Google Assistant",
        name=config[CONF_PROJECT_ID],
        entry_type=dr.DeviceEntryType.SERVICE,
    )

    google_config = GoogleConfig(hass, config)
    await google_config.async_initialize()

    entry.runtime_data = google_config

    hass.http.register_view(GoogleAssistantView(google_config))

    if google_config.should_report_state:
        google_config.async_enable_report_state()

    async def request_sync_service_handler(call: ServiceCall) -> None:
        """Handle request sync service calls."""
        agent_user_id = call.data.get("agent_user_id") or call.context.user_id

        if agent_user_id is None:
            _LOGGER.warning(
                "No agent_user_id supplied for request_sync. Call as a user or pass in"
                " user id as agent_user_id"
            )
            return

        await google_config.async_sync_entities(agent_user_id)

    # Register service only if key is provided
    if CONF_SERVICE_ACCOUNT in config:
        hass.services.async_register(
            DOMAIN, SERVICE_REQUEST_SYNC, request_sync_service_handler
        )

    # Register export service (always available)
    async def export_config_handler(call: ServiceCall) -> None:
        """Export the current unleashed config to a YAML file."""
        filename = call.data.get(CONF_FILENAME, DEFAULT_EXPORT_FILENAME)
        export_path = Path(hass.config.config_dir) / filename

        export_data = _build_export_data(config)

        if not export_data:
            _LOGGER.warning("No unleashed settings to export")
            pn_async_create(
                hass,
                "No unleashed settings configured to export.",
                title="Google Assistant Unleashed",
                notification_id="ga_unleashed_export",
            )
            return

        header = (
            "# Google Assistant Unleashed - Exported Configuration\n"
            "# Merge these keys into your google_assistant: block\n"
            "# in configuration.yaml to use with YAML-only config.\n"
            "#\n"
            f"# Exported from UI options on {datetime.now().isoformat()}\n"
            "\n"
        )

        yaml_content = yaml.dump(
            export_data, default_flow_style=False, allow_unicode=True, sort_keys=False
        )

        await hass.async_add_executor_job(
            export_path.write_text, header + yaml_content, "utf-8"
        )

        _LOGGER.info("Unleashed config exported to %s", export_path)
        pn_async_create(
            hass,
            f"Unleashed configuration exported to `{filename}`.\n\n"
            "Merge the contents into your `google_assistant:` block "
            "in `configuration.yaml` to keep a portable YAML config.",
            title="Google Assistant Unleashed",
            notification_id="ga_unleashed_export",
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_EXPORT_CONFIG,
        export_config_handler,
        schema=vol.Schema(
            {
                vol.Optional(CONF_FILENAME, default=DEFAULT_EXPORT_FILENAME): cv.string,
            }
        ),
    )

    # Listen for options updates and reload when changed
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def _async_update_listener(hass: HomeAssistant, entry: GoogleConfigEntry) -> None:
    """Handle options update — reload the integration."""
    await hass.config_entries.async_reload(entry.entry_id)
