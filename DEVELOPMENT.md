# Development & Maintenance Guide

Complete guide for developing and maintaining Google Assistant Unleashed.

## Table of Contents

- [Repository Structure](#repository-structure)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Regular Maintenance](#regular-maintenance)
- [Merging Feature Branches](#merging-feature-branches)
- [Creating Releases](#creating-releases)
- [Troubleshooting](#troubleshooting)
- [Quick Reference Commands](#quick-reference-commands)
- [Pro Tips](#pro-tips)

---

## Repository Structure

You have two repositories:

1. **`homeassistant_core`** (fork) - Development and testing environment
   - Where features are developed with full HA test framework
   - Multiple feature branches + integration branch
   - All tests run here

2. **`google-assistant-unleashed`** (standalone) - Distribution repository
   - What users install via HACS or manually
   - Clean, minimal repository with only the integration code
   - No test infrastructure (tests are in the fork)

**Workflow:** Fork → Feature Development → Integration Branch → Sync to Unleashed → Release

---

## Development Workflow

### Initial Setup

Your fork has these branches:
- `feature/require-acknowledgment` - Voice confirmation feature
- `feature/location-restriction` - Presence-based restrictions
- `integration/google-assistant-unleashed` - Combined features for release

### Making Changes

All development happens in the **fork repository**:

```bash
cd /path/to/homeassistant_core

# Create/checkout feature branch
git checkout feature/require-acknowledgment

# Make your changes
# Edit files in homeassistant/components/google_assistant/

# Run tests (see Testing section)
docker exec CONTAINER_NAME bash -c "cd /workspaces/homeassistant_core && pytest tests/components/google_assistant/test_require_acknowledgment.py -v"

# Commit changes
git add homeassistant/components/google_assistant/
git commit -m "feat: Add new functionality"
```

### Key Files with Custom Changes

When working on features, these files contain your modifications:

- **`const.py`**
  - Line 47: `CONF_REQUIRE_ACK`
  - Lines 210-212: Challenge constants

- **`error.py`**
  - Lines 28-39: Modified `ChallengeNeeded` class

- **`trait.py`**
  - Lines 294-299: `check_ack()` method
  - Lines 303-311: `check_presence()` method
  - Multiple `execute()` methods call both checks

- **`__init__.py`**
  - Line 53: `CONF_REQUIRE_ACK` in schema
  - Entity schema includes both options

---

## Testing

### Why Tests Aren't in This Repository

Home Assistant integration tests require:
- The complete Home Assistant test framework and pytest plugins
- HA's test fixtures and mock helpers
- The entire HA codebase for imports and dependencies

**All tests are maintained in the fork repository** where the proper test environment exists.

### Test Coverage

**All 15 feature tests pass** ✅

**`require_acknowledgment` (7 tests):**
- Basic acknowledgment requirement enforcement
- PIN + acknowledgment interaction
- Bypass attempt prevention (false ack, empty challenge)
- Normal operation when disabled
- Invalid PIN after acknowledgment

**`require_presence` (8 tests):**
- Home/away blocking with input_boolean
- Binary sensor support (on/off states)
- Per-entity presence override
- Fail-open behavior (missing entity, no configuration)

**Base tests (~144 tests):** All original Home Assistant google_assistant tests pass, ensuring full compatibility and no regressions.

### Running Tests

```bash
# Navigate to the fork repository
cd /path/to/homeassistant_core

# Start dev container if needed
docker start YOUR_CONTAINER_NAME

# Checkout the integration branch
git checkout integration/google-assistant-unleashed

# Run feature tests
docker exec CONTAINER_NAME bash -c "cd /workspaces/homeassistant_core && pytest tests/components/google_assistant/test_require_acknowledgment.py tests/components/google_assistant/test_location_restriction.py -v"

# Expected output: 15 passed
```

### Quality Checks

All code passes Home Assistant's quality checks:
- ✅ **ruff check** - Code formatting and linting
- ✅ **ruff format** - Code style
- ✅ **mypy** - Type checking
- ✅ **pylint** - Code analysis
- ✅ **pytest** - All 15 feature tests passing

### Test Locations in Fork

- `homeassistant_core/tests/components/google_assistant/test_require_acknowledgment.py` (7 tests)
- `homeassistant_core/tests/components/google_assistant/test_location_restriction.py` (8 tests)
- `homeassistant_core/tests/components/google_assistant/` (~144 base tests)

---

## Regular Maintenance

### Monthly Maintenance Schedule

Your integration needs updates when Home Assistant releases new versions (typically first Wednesday of each month).

### Step 1: Update Your Fork (5 minutes)

```bash
cd /path/to/homeassistant_core
git checkout google_assistant_require_acknowledgment
git fetch origin
git merge origin/dev
```

### Step 2: Test Your Changes (2 minutes)

```bash
# Start container if needed
docker start YOUR_CONTAINER_NAME

# Run tests
docker exec YOUR_CONTAINER_NAME bash -c "cd /workspaces/homeassistant_core && pytest tests/components/google_assistant/test_require_acknowledgment.py -v"
```

### Step 3: Sync to Custom Component (30 seconds)

```bash
bash sync-to-unleashed.sh
```

The script does everything:
- ✅ Copies all files
- ✅ Updates versions
- ✅ Preserves your customizations
- ✅ Prompts for commit & push

### Step 4: Create Release (2 minutes)

See [Creating Releases](#creating-releases) section below.

### Total Time: ~10 minutes per HA release

### When to Update

| Trigger | Action | Priority |
|---------|--------|----------|
| New HA monthly release | Full sync + release | Required |
| HA changes Google Assistant | Immediate sync + release | Required |
| Bug in your feature | Fix in fork → sync | High |
| User requests | Evaluate → implement in fork → sync | Medium |
| Upstream fixes bugs | Monthly sync catches it | Low |

### Handling Upstream Conflicts

If Home Assistant makes changes to files you modified, you'll need to resolve conflicts.

#### 1. Identify Conflicts

```bash
cd /path/to/homeassistant_core
git checkout feature/require-acknowledgment  # Update each feature branch separately
git merge origin/dev

# If conflicts occur:
git status
```

#### 2. Resolve Conflicts

**Key principle:** Keep your changes, merge their changes around yours.

The main files with your changes:
- `const.py` - Added CONF_REQUIRE_ACK, CONF_REQUIRE_PRESENCE, etc.
- `error.py` - Modified `ChallengeNeeded` class
- `trait.py` - Added `check_ack()` and `check_presence()` methods
- `__init__.py` - Added both options to entity schema

#### 3. Re-run Tests

```bash
docker exec YOUR_CONTAINER_NAME bash -c "cd /workspaces/homeassistant_core && pytest tests/components/google_assistant/test_require_acknowledgment.py -v"
```

#### 4. Merge Features into Integration Branch

After updating feature branches with upstream changes, follow the [Merging Feature Branches](#merging-feature-branches) section to rebuild the integration branch.

#### 5. Sync to Unleashed

Once conflicts are resolved and tests pass, run the sync script.

---

## Merging Feature Branches

**⚠️ CRITICAL:** This is the most error-prone step. Follow this process exactly.

### Understanding Feature Interaction

**The two features interact with each other and MUST be executed in the correct order:**

1. **`require_presence` (location-restriction)** - First check: Is the user at home?
   - If user is away → **BLOCK command immediately**
   - If user is home → Continue to next check

2. **`require_acknowledgment`** - Second check: Does user confirm the action?
   - If acknowledgment required and not provided → **Request confirmation**
   - If acknowledgment provided or not required → Continue to next check

3. **`secure_devices_pin`** (built-in feature) - Third check: PIN verification
   - If PIN required and not provided → **Request PIN**
   - If PIN provided or not required → **Execute command**

**Execution Order in Code (MANDATORY):**

```python
async def execute(self, command, data, params, challenge):
    """Execute a command."""
    # FIRST: Check location restriction
    self.check_presence(data)

    # SECOND: Check acknowledgment requirement
    self.check_ack(challenge)

    # THIRD: PIN check happens automatically in Google Assistant's built-in flow

    # FINALLY: Execute the actual command
    # ... rest of method
```

**Why This Order Matters:**

- **Location first:** No point asking for confirmation if user isn't even home
- **Acknowledgment second:** User confirms they want to proceed
- **PIN last:** Final security check before execution

This creates a security funnel: `Location → Voice Confirmation → PIN → Execution`

### Real-World Example

User says: *"Hey Google, unlock the front door"*

**Configuration:**
```yaml
google_assistant:
  presence_entity: input_boolean.home
  secure_devices_pin: "1234"
  entity_config:
    lock.front_door:
      require_presence: true
      require_acknowledgment: true
```

**Execution Flow:**

1. **Check #1 - Location (`check_presence`):**
   - Is `input_boolean.home` = ON?
   - **If OFF:** ❌ Block immediately → "This device can only be controlled when you are present at home"
   - **If ON:** ✅ Continue to next check

2. **Check #2 - Acknowledgment (`check_ack`):**
   - Is `require_acknowledgment: true`?
   - **If YES and not acknowledged:** ❌ Request confirmation → "Are you sure?"
   - User: "Yes" → ✅ Continue to next check

3. **Check #3 - PIN (built-in):**
   - Is `secure_devices_pin` configured?
   - **If YES:** ❌ Request PIN → "What's your PIN?"
   - User: "1234" → ✅ Continue to execution

4. **Execute:** 🔓 Door unlocks

**Why wrong order would fail:**

If you put `check_ack` before `check_presence`:
- User away from home says "Unlock door"
- System asks "Are you sure?" (wrong - shouldn't even get here!)
- User says "Yes"
- System blocks due to presence check
- Result: Confusing UX, asked unnecessary question

**Correct order prevents this by blocking early.**

### The Problem

When merging multiple feature branches that modify the same files, you'll get conflicts. **DO NOT use `git checkout --theirs` or `git checkout --ours`** - this will DELETE code from one feature!

### Step-by-Step Merge Process

#### Step 1: Reset Integration Branch to Base Version

```bash
cd /path/to/homeassistant_core

# Reset integration branch to clean base (e.g., tag 2026.3.0)
git checkout integration/google-assistant-unleashed
git reset --hard 2026.3.0
```

#### Step 2: Merge First Feature (require-acknowledgment)

```bash
# Merge require-acknowledgment feature
git merge feature/require-acknowledgment

# Should merge cleanly with no conflicts
# Verify the merge:
git log --oneline -5
```

#### Step 3: Merge Second Feature (location-restriction)

```bash
# Start merge (this WILL have conflicts)
git merge feature/location-restriction

# Git will stop with conflicts. DO NOT panic, DO NOT use --theirs/--ours
```

#### Step 4: Manually Resolve Conflicts

**Files that will conflict:**
- `homeassistant/components/google_assistant/__init__.py`
- `homeassistant/components/google_assistant/trait.py`

**For `__init__.py` - Merge BOTH imports:**

Look for conflict markers like:
```python
<<<<<<< HEAD
from .const import (
    CONF_REQUIRE_ACK,
    ...
)
=======
from .const import (
    CONF_REQUIRE_PRESENCE,
    CONF_PRESENCE_ENTITY,
    ...
)
>>>>>>> feature/location-restriction
```

**Fix it to include BOTH:**
```python
from .const import (
    CONF_REQUIRE_ACK,
    CONF_REQUIRE_PRESENCE,
    CONF_PRESENCE_ENTITY,
    ...
)
```

**For `__init__.py` - ENTITY_SCHEMA must have BOTH options:**
```python
ENTITY_SCHEMA = vol.Schema({
    vol.Optional(CONF_NAME): cv.string,
    vol.Optional(CONF_EXPOSE, default=True): cv.boolean,
    vol.Optional(CONF_ALIASES): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_ROOM_HINT): cv.string,
    vol.Optional(CONF_REQUIRE_ACK, default=False): cv.boolean,        # From feature 1
    vol.Optional(CONF_REQUIRE_PRESENCE, default=False): cv.boolean,   # From feature 2
    vol.Optional(CONF_PRESENCE_ENTITY): cv.entity_id,                 # From feature 2
})
```

**For `trait.py` - Keep BOTH check methods:**

Look for conflict in method definitions:
```python
<<<<<<< HEAD
    def check_ack(self, challenge):
        """Verify if acknowledgment is required and present."""
        entity_config = self.config.entity_config.get(self.state.entity_id, {})
        if entity_config.get(CONF_REQUIRE_ACK):
            ack_ok = isinstance(challenge, dict) and challenge.get("ack") is True
            if not ack_ok:
                raise ChallengeNeeded(ack_needed=True)
=======
    def check_presence(self, data: RequestData) -> None:
        """Verify if presence is required and user is present."""
        entity_config = self.config.entity_config.get(self.state.entity_id, {})
        if not entity_config.get(CONF_REQUIRE_PRESENCE):
            return
        # ... rest of check_presence
>>>>>>> feature/location-restriction
```

**Fix it to have BOTH methods:**
```python
    def check_ack(self, challenge):
        """Verify if acknowledgment is required and present."""
        entity_config = self.config.entity_config.get(self.state.entity_id, {})
        if entity_config.get(CONF_REQUIRE_ACK):
            ack_ok = isinstance(challenge, dict) and challenge.get("ack") is True
            if not ack_ok:
                raise ChallengeNeeded(ack_needed=True)

    def check_presence(self, data: RequestData) -> None:
        """Verify if presence is required and user is present."""
        entity_config = self.config.entity_config.get(self.state.entity_id, {})
        if not entity_config.get(CONF_REQUIRE_PRESENCE):
            return
        # ... rest of check_presence
```

**For `trait.py` - All execute() methods must call BOTH checks in CORRECT ORDER:**

Look for conflicts in execute methods:
```python
<<<<<<< HEAD
    async def execute(self, command, data, params, challenge):
        """Execute a brightness command."""
        self.check_ack(challenge)
=======
    async def execute(self, command, data, params, challenge):
        """Execute a brightness command."""
        self.check_presence(data)
>>>>>>> feature/location-restriction
```

**⚠️ CRITICAL - Fix it to call BOTH in the CORRECT ORDER:**

```python
    async def execute(self, command, data, params, challenge):
        """Execute a brightness command."""
        # Order is MANDATORY: Presence → Acknowledgment → PIN → Execute
        self.check_presence(data)      # FIRST: Location check
        self.check_ack(challenge)       # SECOND: Voice confirmation
        # ... rest of method (PIN check is built-in, then execution)
```

**Why this order:**
1. **`check_presence(data)` FIRST** - Block command if user is away (no point continuing)
2. **`check_ack(challenge)` SECOND** - Request confirmation if required
3. PIN check happens automatically in Google Assistant's flow
4. Command executes only if all checks pass

#### Step 5: Remove Conflict Markers

```bash
# Check for any remaining conflict markers
grep -r "<<<<<<< HEAD" homeassistant/components/google_assistant/
grep -r "=======" homeassistant/components/google_assistant/
grep -r ">>>>>>>" homeassistant/components/google_assistant/

# If found, remove them manually with sed:
find homeassistant/components/google_assistant/ -type f -name "*.py" -exec sed -i '/^<<<<<<< HEAD$/d; /^=======$/d; /^>>>>>>> /d' {} \;
```

#### Step 6: Verify the Merge

**CRITICAL: Verify both features are present AND in correct order:**

```bash
# Should find 18 calls to check_ack
grep -c "self.check_ack(challenge)" homeassistant/components/google_assistant/trait.py

# Should find 23 calls to check_presence
grep -c "self.check_presence(data)" homeassistant/components/google_assistant/trait.py

# Verify both imports in __init__.py
grep "CONF_REQUIRE_ACK\|CONF_REQUIRE_PRESENCE" homeassistant/components/google_assistant/__init__.py

# Should show BOTH in ENTITY_SCHEMA
grep -A 10 "ENTITY_SCHEMA = vol.Schema" homeassistant/components/google_assistant/__init__.py

# CRITICAL: Verify execution order in ALL execute() methods
# check_presence MUST come BEFORE check_ack
grep -B2 "self.check_ack(challenge)" homeassistant/components/google_assistant/trait.py | grep "self.check_presence(data)"
```

**Expected output:**
- 18 check_ack calls ✅
- 23 check_presence calls ✅
- Both CONF_REQUIRE_ACK and CONF_REQUIRE_PRESENCE imported ✅
- Both options in ENTITY_SCHEMA ✅
- **Every check_ack call should be preceded by check_presence** ✅

**Manual verification of execution order:**

Open `trait.py` and verify that in ALL execute() methods, the order is:
```python
self.check_presence(data)      # FIRST
self.check_ack(challenge)       # SECOND
```

If you find ANY execute() method with the reversed order, **fix it immediately**.

#### Step 7: Complete the Merge

```bash
# Stage all resolved files
git add homeassistant/components/google_assistant/

# Commit the merge
git commit -m "Merge feature/location-restriction into integration branch

Both features now active:
- require_acknowledgment: Voice confirmation
- require_presence: Location-based restrictions"

# Verify clean merge
git log --oneline --graph -10
```

#### Step 8: Run Tests

```bash
# Test BOTH features
docker exec CONTAINER_NAME bash -c "cd /workspaces/homeassistant_core && pytest tests/components/google_assistant/test_require_acknowledgment.py tests/components/google_assistant/test_location_restriction.py -v"

# Should see: 15 passed (7 for acknowledgment, 8 for presence)
```

### Common Mistakes to AVOID

- ❌ **Using `git checkout --theirs`** → Deletes check_ack() completely
- ❌ **Using `git checkout --ours`** → Deletes check_presence() completely
- ❌ **Forgetting imports** → CONF_REQUIRE_PRESENCE not imported causes "Invalid config"
- ❌ **Not calling both checks** → One feature won't work
- ❌ **Wrong execution order** → `check_ack` before `check_presence` breaks security logic
- ❌ **Leaving conflict markers** → Code won't compile

### Quick Verification Checklist

Before syncing to custom component:

- [ ] Both `check_ack()` and `check_presence()` methods exist in trait.py
- [ ] **All execute() methods call checks in CORRECT ORDER:**
  - [ ] `self.check_presence(data)` **FIRST**
  - [ ] `self.check_ack(challenge)` **SECOND**
- [ ] Both CONF_REQUIRE_ACK and CONF_REQUIRE_PRESENCE imported in __init__.py
- [ ] Both options in ENTITY_SCHEMA in __init__.py
- [ ] No conflict markers remain (<<<<<<, =======, >>>>>>>)
- [ ] All tests pass (15 feature tests total)
- [ ] Grep verification shows 18 check_ack and 23 check_presence calls
- [ ] **Manual verification: Open trait.py and confirm order in at least 3 execute() methods**

---

## Creating Releases

### Regular Release (After Maintenance)

After syncing with a new Home Assistant version:

```bash
cd /path/to/google-assistant-unleashed

# Tag the version
git tag v2026.X.0
git push origin v2026.X.0
```

Then create GitHub Release:
1. Go to https://github.com/GuiPoM/google-assistant-unleashed/releases
2. Click "Draft a new release"
3. Select the tag you just created
4. Title: `v2026.X.0 - Updated for Home Assistant 2026.X`
5. Description:
   ```markdown
   ## Updates
   - Updated to Home Assistant 2026.X.0
   - All upstream changes included
   - require_acknowledgment feature maintained
   - require_presence feature maintained

   ## Installation
   - Via HACS: Update the integration
   - Manual: Download and extract to custom_components/
   ```
6. Publish release

### Emergency Hotfix

If an urgent bug is found:

```bash
# 1. Fix in fork
cd homeassistant_core
# make fix
git commit -m "fix: [issue]"

# 2. Quick sync
bash sync-to-unleashed.sh

# 3. Hotfix release
cd ../google-assistant-unleashed
git tag v2026.X.1  # Increment patch version
git push origin v2026.X.1
# Create GitHub release
```

### Clean History Release

To create a clean single-commit history (useful for initial release or major cleanup):

```bash
cd /path/to/google-assistant-unleashed

# Create orphan branch for clean history
git checkout --orphan new-main
git add -A
git commit -m "Initial release: Google Assistant Unleashed v2026.2.0

Features:
- require_acknowledgment: Voice confirmation for sensitive commands
- require_presence: Location-based restrictions (input_boolean/binary_sensor)

Based on Home Assistant 2026.2.3"

# Replace main branch
git branch -D main
git branch -m main
git push -f origin main

# Create tag
git tag -d v2026.2.0  # Delete old tag if exists
git tag -a v2026.2.0 -m "Release v2026.2.0

Features:
- require_acknowledgment: Voice confirmation for sensitive commands
- require_presence: Location-based restrictions (input_boolean/binary_sensor)

Based on Home Assistant 2026.2.3"

git push origin v2026.2.0 --force
```

**⚠️ Warning:** This rewrites history. Anyone who cloned the repo will need to re-clone.

---

## Troubleshooting

### Tests Failing After Upstream Merge

**Symptoms:** Tests that previously passed now fail after merging upstream changes.

**Solution:**
1. Check if upstream modified test expectations
2. Review changes to Google Assistant integration
3. Update your feature code to match new patterns
4. Re-run quality checks (ruff, mypy, pylint)

### Merge Conflicts Every Month

**Symptoms:** Constant conflicts when merging upstream.

**Solution:**
1. Check if your changes are in frequently-modified files
2. Consider refactoring to minimize footprint
3. Keep feature branches minimal and focused
4. Document conflict resolution patterns

### Sync Script Issues

**Symptoms:** sync-to-unleashed.sh fails or produces incorrect results.

**Solution:**
1. Verify both repositories are in correct state
2. Check file paths in the script
3. Manually verify copied files match source
4. Test manifest.json and hacs.json versions

### HACS Installation Issues

**Symptoms:** Users can't install via HACS.

**Solution:**
1. Verify hacs.json is present and valid
2. Check manifest.json has correct version
3. Ensure tag exists and is pushed
4. Validate GitHub release is published

---

---

## Quick Reference Commands

| Task | Command |
|------|---------|
| Update fork | `cd homeassistant_core && git fetch origin && git merge origin/dev` |
| Merge features to integration | See [Merging Feature Branches](#merging-feature-branches) - **DO NOT use --theirs/--ours** |
| Verify merge | `grep -c "self.check_ack" trait.py` (18) and `grep -c "self.check_presence" trait.py` (23) |
| Run tests | `docker exec CONTAINER_NAME bash -c "cd /workspaces/homeassistant_core && pytest tests/components/google_assistant/test_require_acknowledgment.py tests/components/google_assistant/test_location_restriction.py -v"` |
| Sync to unleashed | `bash sync-to-unleashed.sh` |
| Create release | Tag + push + GitHub release |

---

## Pro Tips

1. **Bookmark the sync script:** Keep `sync-to-unleashed.sh` handy
2. **Subscribe to HA releases:** Watch the main repo for new versions
3. **Join Discord/Forums:** Hear about breaking changes early
4. **Keep fork clean:** Only your feature branches, makes syncing easier
5. **Document conflicts:** If you hit a tricky merge, document it
6. **Calendar reminder:** Check for updates after monthly HA releases
7. **Test in fork first:** Always verify in development environment before syncing

---

## Support

If you encounter maintenance issues:
1. Check if it's your feature or upstream bug
2. Test with original HA to isolate
3. Fix in fork first, then sync
4. Update users via GitHub release notes

---

**Your component is production-ready and maintainable!** 🚀
