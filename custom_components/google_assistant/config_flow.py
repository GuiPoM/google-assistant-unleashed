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
    CONF_PRESENCE_ENTITY,
    CONF_PROJECT_ID,
    CONF_REQUIRE_ACK,
    CONF_REQUIRE_PRESENCE,
    DATA_CONFIG,
    DOMAIN,
)


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

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the security options."""
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    CONF_PRESENCE_ENTITY: user_input.get(CONF_PRESENCE_ENTITY, ""),
                    CONF_REQUIRE_ACK: user_input.get(CONF_REQUIRE_ACK, []),
                    CONF_REQUIRE_PRESENCE: user_input.get(CONF_REQUIRE_PRESENCE, []),
                },
            )

        # If UI options exist, use them; otherwise seed from YAML config
        if self.options:
            defaults = dict(self.options)
        else:
            defaults = _defaults_from_yaml(self.hass)

        current_presence = defaults.get(CONF_PRESENCE_ENTITY, "")
        current_ack_entities = defaults.get(CONF_REQUIRE_ACK, [])
        current_presence_entities = defaults.get(CONF_REQUIRE_PRESENCE, [])

        # Get entities exposed to Google Assistant for the entity selectors
        exposed_entities = _get_exposed_entity_ids(self.hass, self.config_entry)

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
                    CONF_REQUIRE_ACK,
                    default=current_ack_entities,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        include_entities=exposed_entities,
                        multiple=True,
                    ),
                ),
                vol.Optional(
                    CONF_REQUIRE_PRESENCE,
                    default=current_presence_entities,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        include_entities=exposed_entities,
                        multiple=True,
                    ),
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={
                "exposed_count": str(len(exposed_entities)),
            },
        )
