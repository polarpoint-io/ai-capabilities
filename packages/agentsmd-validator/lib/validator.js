'use strict';

const { parseZones, hashZone, headingsInZone, hasExecutableCommand } = require('./parser');

const REQUIRED_ZONE1_SECTIONS = [
  'Sync model',
  'Forbidden paths',
  'Naming conventions',
  'Running tests',
];

/**
 * Run all checks against the parsed content.
 * Returns { errors: string[], warnings: string[], zone1Hash: string }
 */
function validate(content, schemaData) {
  const errors   = [];
  const warnings = [];

  const { zones, order } = parseZones(content);

  // ── 1. Zone markers present ───────────────────────────────────────────────
  if (!zones[1]) {
    errors.push('Zone 1 is missing. Add <!-- zone:1:start --> and <!-- zone:1:end --> markers.');
  }
  if (!zones[2]) {
    warnings.push('Zone 2 markers not found. Guarded section is optional but recommended.');
  }
  if (!zones[3]) {
    warnings.push('Zone 3 markers not found. Free section is optional but recommended.');
  }

  // ── 2. Zone order ─────────────────────────────────────────────────────────
  if (order.length > 1) {
    for (let i = 1; i < order.length; i++) {
      if (order[i] < order[i - 1]) {
        errors.push(`Zone markers are out of order: zone ${order[i]} appears after zone ${order[i - 1]}.`);
      }
    }
  }

  // ── 3. Required sections inside Zone 1 ───────────────────────────────────
  if (zones[1]) {
    const headings = headingsInZone(zones[1]);
    for (const section of REQUIRED_ZONE1_SECTIONS) {
      if (!headings.some(h => h.toLowerCase().includes(section.toLowerCase()))) {
        errors.push(`Required section "## ${section}" is missing from Zone 1.`);
      }
    }

    // ── 4. Running tests must contain an executable command ────────────────
    const testsIdx = headings.findIndex(h => h.toLowerCase().includes('running tests'));
    if (testsIdx !== -1) {
      // extract just the Running tests sub-section
      const z1Lines   = zones[1].split('\n');
      let inTests     = false;
      let testsBuffer = [];
      for (const line of z1Lines) {
        if (/^##\s+Running tests/i.test(line)) { inTests = true; continue; }
        if (inTests && /^##\s+/.test(line)) break;
        if (inTests) testsBuffer.push(line);
      }
      const testsContent = testsBuffer.join('\n');
      if (!hasExecutableCommand(testsContent)) {
        errors.push('"## Running tests" in Zone 1 must contain at least one executable command (code block or inline command).');
      }
    }

    // ── 5. Zone 1 hash drift check ────────────────────────────────────────
    const zone1Hash = hashZone(zones[1]);
    if (schemaData && schemaData.zone1Hash) {
      if (zone1Hash !== schemaData.zone1Hash) {
        warnings.push(
          `Zone 1 content hash (${zone1Hash}) does not match template version ` +
          `${schemaData.templateVersion || 'unknown'} (${schemaData.zone1Hash}). ` +
          `Run the sync engine or update Zone 1 from platform-standards.`
        );
      }
    }

    return { errors, warnings, zone1Hash };
  }

  return { errors, warnings, zone1Hash: null };
}

module.exports = { validate };
