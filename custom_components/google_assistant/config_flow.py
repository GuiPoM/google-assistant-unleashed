"""Config flow for google assistant component."""

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
    OptionsFlowWithConfigEntry,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ENTITY_CONFIG,
    CONF_EXPOSE,
    CONF_EXPOSE_BY_DEFAULT,
    CONF_EXPOSED_DOMAINS,
    CONF_PRESENCE_ENTITY,
    CONF_PROJECT_ID,
    CONF_REQUIRE_ACK,
    CONF_REQUIRE_PRESENCE,
    DATA_CONFIG,
    DOMAIN,
    DOMAIN_TO_GOOGLE_TYPES,
)

CONF_EXPOSED_ENTITIES = "exposed_entities"

# Domains supported by Google Assistant
GA_SUPPORTED_DOMAINS = sorted(DOMAIN_TO_GOOGLE_TYPES.keys())


class GoogleAssistantHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Import a config entry."""
        await self.async_set_unique_id(unique_id=import_data[CONF_PROJECT_ID])
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=import_data[CONF_PROJECT_ID], data=import_data
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Get the options flow for this handler."""
        return GoogleAssistantOptionsFlow(config_entry)


def _defaults_from_yaml(hass) -> dict[str, Any]:
    """Extract unleashed defaults from the YAML config.

    Reads the YAML entity_config and builds the list format used by the
    options flow so the UI pre-populates with what's already in YAML.
    """
    yaml_config = hass.data.get(DOMAIN, {}).get(DATA_CONFIG, {})

    presence_entity = yaml_config.get(CONF_PRESENCE_ENTITY, "")
    entity_config: dict[str, dict] = yaml_config.get(CONF_ENTITY_CONFIG, {})

    ack_entities: list[str] = []
    presence_entities: list[str] = []

    for entity_id, cfg in entity_config.items():
        if cfg.get(CONF_REQUIRE_ACK):
            ack_entities.append(entity_id)
        if cfg.get(CONF_REQUIRE_PRESENCE):
            presence_entities.append(entity_id)

    return {
        CONF_PRESENCE_ENTITY: presence_entity,
        CONF_REQUIRE_ACK: ack_entities,
        CONF_REQUIRE_PRESENCE: presence_entities,
    }


def _get_exposed_entity_ids(hass, config_entry: ConfigEntry) -> list[str]:
    """Get the list of entity IDs currently exposed to Google Assistant.

    Uses the GoogleConfig instance (stored as runtime_data) to check
    which entities pass the should_expose filter.
    """
    google_config = config_entry.runtime_data
    exposed: list[str] = []
    for state in hass.states.async_all():
        if google_config.should_expose(state):
            exposed.append(state.entity_id)
    exposed.sort()
    return exposed


class GoogleAssistantOptionsFlow(OptionsFlowWithConfigEntry):
    """Handle Google Assistant Unleashed options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__(config_entry)
        self._exposed_entities: list[str] = []
        self._presence_entity: str = ""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: Global settings and entity exposure."""
        if user_input is not None:
            # Store step 1 data and move to step 2
            self._exposed_entities = user_input.get(CONF_EXPOSED_ENTITIES, [])
            self._presence_entity = user_input.get(CONF_PRESENCE_ENTITY, "")
            return await self.async_step_security()

        # Load defaults
        if self.options:
            defaults = dict(self.options)
        else:
            defaults = _defaults_from_yaml(self.hass)

        current_presence = defaults.get(CONF_PRESENCE_ENTITY, "")

        # Get currently exposed entities
        current_exposed = defaults.get(
            CONF_EXPOSED_ENTITIES,
            _get_exposed_entity_ids(self.hass, self.config_entry),
        )

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_PRESENCE_ENTITY,
                    default=current_presence,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["input_boolean", "binary_sensor"],
                        multiple=False,
                    ),
                ),
                vol.Optional(
                    CONF_EXPOSED_ENTITIES,
                    default=current_exposed,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=GA_SUPPORTED_DOMAINS,
                        multiple=True,
                    ),
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={},
            last_step=False,
        )

    async def async_step_security(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: Security settings for exposed entities."""
        if user_input is not None:
            # Combine step 1 + step 2 data and save
            return self.async_create_entry(
                title="",
                data={
                    CONF_PRESENCE_ENTITY: self._presence_entity,
                    CONF_EXPOSED_ENTITIES: self._exposed_entities,
                    CONF_REQUIRE_ACK: user_input.get(CONF_REQUIRE_ACK, []),
                    CONF_REQUIRE_PRESENCE: user_input.get(CONF_REQUIRE_PRESENCE, []),
                },
            )

        # Load defaults for step 2
        if self.options:
            defaults = dict(self.options)
        else:
            defaults = _defaults_from_yaml(self.hass)

        current_ack = defaults.get(CONF_REQUIRE_ACK, [])
        current_presence = defaults.get(CONF_REQUIRE_PRESENCE, [])

        exposed = self._exposed_entities
        exposed_set = set(exposed)

        # Filter defaults to only include entities that are in the exposed list.
        # Stale entries (e.g. from YAML referencing entities that don't exist
        # or aren't exposed) would cause validation errors.
        current_ack = [e for e in current_ack if e in exposed_set]
        current_presence = [e for e in current_presence if e in exposed_set]

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_REQUIRE_ACK,
                    default=current_ack,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        include_entities=exposed,
                        multiple=True,
                    ),
                ),
                vol.Optional(
                    CONF_REQUIRE_PRESENCE,
                    default=current_presence,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        include_entities=exposed,
                        multiple=True,
                    ),
                ),
            }
        )

        return self.async_show_form(
            step_id="security",
            data_schema=schema,
            description_placeholders={
                "exposed_count": str(len(exposed)),
            },
            last_step=True,
        )
