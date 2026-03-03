# Google Assistant Unleashed 🚀

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/GuiPoM/google-assistant-unleashed.svg)](https://github.com/GuiPoM/google-assistant-unleashed/releases)

**A fork of the [official Home Assistant Google Assistant integration](https://www.home-assistant.io/integrations/google_assistant) with enhanced security features.**

This is a complete replacement for the built-in integration, adding voice confirmation and presence-based access control — features that were rejected from the official integration. [Why?](#why-this-fork-exists)

**📖 [View Full Documentation](DEVELOPMENT.md)** - Complete guide for development and maintenance.

## Features

This fork adds two powerful security features to the official Google Assistant integration:

### 1️⃣ Voice Acknowledgment (`require_acknowledgment`)

**Require voice confirmation before executing sensitive commands.**

#### How It Works

**Without `require_acknowledgment`:**
- You: *"Hey Google, unlock the front door"*
- ✓ Door unlocks immediately

**With `require_acknowledgment`:**
- You: *"Hey Google, unlock the front door"*
- Google Assistant: *"Are you sure?"*
- You: *"Yes"*
- ✓ Door unlocks

Adds an extra confirmation step before executing commands, without requiring a PIN.

#### Configuration

```yaml
google_assistant:
  project_id: YOUR_PROJECT_ID
  service_account: !include SERVICE_ACCOUNT.json
  entity_config:
    lock.front_door:
      expose: true
      require_acknowledgment: true

    switch.garage_door:
      expose: true
      require_acknowledgment: true
```

#### Works with PIN Protection

Acknowledgment and PIN checks work together in sequence:

```yaml
google_assistant:
  secure_devices_pin: "1234"
  entity_config:
    lock.front_door:
      require_acknowledgment: true  # Step 1: Voice confirmation
                                     # Step 2: PIN (built-in feature)
```

**Flow:**
1. Voice acknowledgment: *"Are you sure?"* → *"Yes"*
2. PIN verification: *"What's your PIN?"* → *"1234"*
3. ✓ Command executes

---

### 2️⃣ Presence-Based Access Control (`require_presence`)

**Block commands when you're away from home (geofencing).**

#### How It Works

**When you're home (`input_boolean.home` is `ON`):**
- You: *"Hey Google, unlock the front door"*
- ✓ Command executes normally

**When you're away (`input_boolean.home` is `OFF`):**
- You: *"Hey Google, unlock the front door"*
- Google Assistant: *"This device can only be controlled when you are present at home"*
- ❌ Command blocked for safety

Prevents command execution based on your location. Commands are blocked when your presence entity indicates you're away.

#### Configuration

**Global presence entity (applies to all entities that enable it):**

```yaml
google_assistant:
  presence_entity: input_boolean.home  # Global presence sensor
  entity_config:
    lock.front_door:
      expose: true
      require_presence: true

    cover.garage_door:
      expose: true
      require_presence: true
```

**Per-entity presence override:**

```yaml
google_assistant:
  presence_entity: input_boolean.home  # Default for all
  entity_config:
    lock.front_door:
      require_presence: true
      presence_entity: input_boolean.custom_presence  # Override for this entity
```

#### Supported Presence Entities

- `input_boolean.*` - ON = home, OFF = away
- `binary_sensor.*` - ON = home, OFF = away

#### Fail-Safe Design

**Important:** If the presence entity is missing or not configured, commands are **allowed** (fail-open). This prevents lockout scenarios where you can't control devices due to misconfiguration.

---

### 3️⃣ Combining All Security Features

**Maximum security: Location + Voice Confirmation + PIN**

#### How It Works - Real-World Example

You: *"Hey Google, unlock the front door"*

1. ✅ **Presence:** System checks `input_boolean.home` = ON → Pass
2. ✅ **Acknowledgment:** *"Are you sure?"* → You: *"Yes"* → Pass
3. ✅ **PIN:** *"What's your PIN?"* → You: *"1234"* → Pass
4. 🔓 **Door unlocks**

If you were away (step 1 fails), the command stops immediately without asking for confirmation or PIN.

#### Configuration

```yaml
google_assistant:
  presence_entity: input_boolean.home
  secure_devices_pin: "1234"
  entity_config:
    lock.front_door:
      expose: true
      require_presence: true         # Check 1: Must be home
      require_acknowledgment: true   # Check 2: Voice confirmation
                                     # Check 3: PIN (built-in)
```

#### Security Execution Flow

**Checks run in this mandatory order:**

1. **Presence Check** → ❌ Blocked if away from home
2. **Voice Acknowledgment** → *"Are you sure?"* → You: *"Yes"*
3. **PIN Verification** (if configured) → *"What's your PIN?"* → You: *"1234"*
4. ✓ **Command executes**

**Why this order matters:** No point asking for confirmation if the user isn't even home. Each check acts as a security gate that must pass before proceeding to the next.

## Installation

### ⚠️ Important: How This Works

**This custom component replaces the built-in Google Assistant integration.**

When installed in `custom_components/google_assistant/`:
- ✅ Home Assistant will load this version instead of the built-in one
- ✅ All your existing Google Assistant configuration continues to work
- ✅ No migration needed - just adds new optional features (`require_acknowledgment`, `require_presence`)
- ✅ You can revert anytime by removing the custom component folder and restarting

**Can I start fresh with this integration (without setting up the official one first)?**
- ✅ **Yes!** This is a complete, standalone integration
- You can install it directly and configure Google Assistant from scratch
- Follow the [official Google Assistant setup guide](https://www.home-assistant.io/integrations/google_assistant) - all steps work the same

**Do I need to keep the official integration's configuration?**
- ✅ **Yes, keep your configuration!** This custom component uses the **exact same** YAML configuration
- Don't change anything in your `configuration.yaml` - it just works
- The built-in integration files can stay (Home Assistant ignores them when custom component is present)

**Note:** You cannot have both the official and custom version active simultaneously. Home Assistant only loads one integration per domain, and custom components take priority.

### Via HACS (Recommended)

1. Open HACS in your Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/GuiPoM/google-assistant-unleashed`
6. Select category: "Integration"
7. Click "Add"
8. Search for "Google Assistant Unleashed"
9. Click "Download"
10. Restart Home Assistant

### Manual Installation

1. Download the latest release from [Releases](https://github.com/GuiPoM/google-assistant-unleashed/releases)
2. Extract the `google_assistant` folder from the zip
3. Copy it to your `<config>/custom_components/` directory
4. Restart Home Assistant

## Configuration

This integration uses the exact same configuration as the official Google Assistant integration, with the addition of `require_acknowledgment` and `require_presence` options.

See the [official documentation](https://www.home-assistant.io/integrations/google_assistant) for general setup, then add the new security features as needed.

### Example Configuration

```yaml
google_assistant:
  project_id: my-project-id
  service_account: !include SERVICE_ACCOUNT.json
  report_state: true
  presence_entity: input_boolean.home  # Global presence sensor (optional)
  exposed_domains:
    - switch
    - light
    - lock
    - cover
  entity_config:
    # Maximum security: presence + acknowledgment
    lock.front_door:
      name: Front Door Lock
      expose: true
      require_presence: true
      require_acknowledgment: true
      room: Entrance

    # Only presence check
    cover.garage_door:
      name: Garage Door
      expose: true
      require_presence: true

    # Only acknowledgment
    switch.security_system:
      name: Security System
      expose: true
      require_acknowledgment: true

    # Regular entities (no extra security)
    light.living_room:
      name: Living Room Light
      expose: true
      room: Living Room
```

## Compatibility

- **Home Assistant**: 2026.2.0 or later
- **Python**: 3.13 or later
- Based on Home Assistant 2026.2.3 core integration
- Compatible with all Google Assistant features
- Works alongside Home Assistant Cloud or manual Google Cloud setup

## Supported Entities

The `require_acknowledgment` option works with any entity that supports the following traits:
- Brightness (lights)
- OnOff (switches, lights, etc.)
- ColorSetting (lights)
- Scene activation
- Dock (vacuums)
- Locator
- StartStop (vacuums, lawn mowers)
- TemperatureControl
- TemperatureSetting (thermostats)
- HumiditySetting (humidifiers)
- LockUnlock (locks)
- ArmDisarm (alarm panels)
- FanSpeed
- Modes
- InputSelector
- OpenClose (covers, valves)
- Volume
- TransportControl (media players)

## Testing

This custom component is **fully tested** with comprehensive test coverage:

- **15 feature tests** for the new functionality (7 for require_acknowledgment + 8 for require_presence)
- **~144 base tests** from the official Home Assistant integration

**All tests pass** ✅ and are maintained in the [fork repository](https://github.com/GuiPoM/homeassistant_core) where the full Home Assistant test framework is available.

**📖 See [DEVELOPMENT.md](DEVELOPMENT.md#testing)** for details on running tests and test coverage.

## Why "Unleashed"?

Because good features shouldn't be held back by arbitrary bureaucracy. This feature was:
- ✅ Fully implemented
- ✅ Comprehensively tested
- ✅ Following Google's Smart Home API standards
- ✅ Solving a real security/UX need
- ❌ Rejected for inconsistent reasons

So here it is, **unleashed** from the constraints of the official repository.

## Why This Fork Exists

The `require_acknowledgment` feature was fully implemented and tested but **rejected from the official integration** (PR [#162982](https://github.com/home-assistant/core/pull/162982)).

### The Real Reason for Rejection

**Home Assistant maintainers stated:** *"We do not wish to add this feature at this point. The reason is that it is added here as a YAML only feature and doesn't include an option for users to set this using the UI."*

**The underlying issue:**

The Google Assistant integration is part of **Home Assistant Cloud** (Nabu Casa), which is their **paid cloud offering**. They want all features to have a UI component in their cloud interface, not just YAML configuration.

**The problem:**
- ✅ The feature is fully implemented and tested
- ✅ Works perfectly as YAML configuration (like many existing options in the same integration)
- ❌ **But adding UI requires changes to the Home Assistant Cloud paid service**
- ❌ **As a user, I have no control over their cloud UI**

**The contradiction:**
- They could have accepted the PR and simply not used the feature in their Cloud UI
- The YAML configuration would work for advanced users and manual Google Cloud setups
- Instead, they blocked the entire feature for everyone

The maintainers suggested creating a custom component instead. So here it is, **unleashed** for everyone to use, without waiting for UI implementation in a paid service.

**This fork also adds:**
- `require_presence` - An additional location-based security feature built on the same foundation

## Support

- **Issues**: [GitHub Issues](https://github.com/GuiPoM/google-assistant-unleashed/issues)
- **Original PR Discussion**: [home-assistant/core#162982](https://github.com/home-assistant/core/pull/162982)

## Contributing

This is a fork of the official Home Assistant Google Assistant integration. Contributions are welcome, but please read the scope below before opening an issue or PR.

### Scope

This fork only maintains the two added features (`require_acknowledgment` and `require_presence`) on top of the official integration. Everything else is out of scope:

- **Bug not related to the added features?** Please first reproduce it against the [official integration](https://www.home-assistant.io/integrations/google_assistant). If it exists there too, report it upstream. I will not work on it.
- **Feature request for your specific use case?** I will not implement it. I don't have the time and this fork is not meant to become a general-purpose alternative. That said, if your idea makes broader sense and could benefit others, open an issue and we can discuss it.
- **Bug in `require_acknowledgment` or `require_presence`?** Open an issue, I'll look at it.
- **Improvement to the added features?** PRs are welcome.

### How to Contribute

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

**📖 For Maintainers and Contributors:**

See [DEVELOPMENT.md](DEVELOPMENT.md) for complete documentation on:
- Repository structure and development workflow
- Running tests in the fork repository
- Merging feature branches (with correct execution order)
- Regular maintenance and keeping up-to-date with Home Assistant
- Creating releases

## Troubleshooting

### How do I revert to the official integration?

Remove the custom component, clean up custom configuration, and restart:

```bash
# 1. Remove the custom component folder
rm -rf <config>/custom_components/google_assistant/

# 2. Remove custom settings from configuration.yaml
# Edit your configuration.yaml and remove:
#   - require_acknowledgment: true (from all entities)
#   - require_presence: true (from all entities)
#   - presence_entity: ... (from google_assistant config)

# 3. Restart Home Assistant
```

Home Assistant will automatically load the built-in version again. Removing the custom settings prevents any warnings about unknown configuration options.

### Will this break my existing setup?

No! This is the official integration with added features. Your existing configuration works exactly the same. The new features (`require_acknowledgment`, `require_presence`) are **optional** and disabled by default.

### Can I use this with Home Assistant Cloud?

This is a **complete replacement** of the built-in Google Assistant integration. It works with any setup method:
- Home Assistant Cloud (Nabu Casa)
- Manual Google Cloud setup

All official features remain fully functional.

### What happens if I don't configure the new features?

Nothing changes! If you don't add `require_acknowledgment` or `require_presence` to your entities, everything works exactly like the official integration. The new features are opt-in only.

## License

This integration is based on the Home Assistant Google Assistant integration, which is licensed under Apache License 2.0.

## Acknowledgments

Thanks to the Home Assistant community for the excellent platform, even when the maintainers make questionable decisions. 😉
