'use strict';

const crypto = require('crypto');

const ZONE_START = /<!--\s*zone:(\d+):start\s*-->/;
const ZONE_END   = /<!--\s*zone:(\d+):end\s*-->/;

/**
 * Parse an AGENTS.md file into its zone segments.
 * Returns { zones: { 1: string, 2: string, 3: string }, raw: string }
 */
function parseZones(content) {
  const lines = content.split('\n');
  const zones = {};
  let currentZone = null;
  let buffer = [];
  const order = [];   // track order zones were opened

  for (const line of lines) {
    const startMatch = line.match(ZONE_START);
    const endMatch   = line.match(ZONE_END);

    if (startMatch) {
      currentZone = parseInt(startMatch[1], 10);
      order.push(currentZone);
      buffer = [];
      continue;
    }

    if (endMatch) {
      const z = parseInt(endMatch[1], 10);
      if (currentZone === z) {
        zones[z] = buffer.join('\n').trim();
        currentZone = null;
        buffer = [];
      }
      continue;
    }

    if (currentZone !== null) {
      buffer.push(line);
    }
  }

  return { zones, order, raw: content };
}

/**
 * Compute a stable SHA-256 hash of zone content (normalised whitespace).
 */
function hashZone(content) {
  const normalised = content.replace(/\s+/g, ' ').trim();
  return crypto.createHash('sha256').update(normalised).digest('hex').slice(0, 16);
}

/**
 * Extract all headings (## level) from a zone string.
 */
function headingsInZone(zoneContent) {
  return (zoneContent.match(/^##\s+.+/gm) || []).map(h => h.replace(/^##\s+/, '').trim());
}

/**
 * Detect whether a block of text contains at least one shell-executable command.
 * Heuristic: a line inside a fenced code block, or a line starting with common
 * shell tokens (make, npm, yarn, pnpm, go, cargo, pytest, mvn, gradle, ./...).
 */
function hasExecutableCommand(zoneContent) {
  const codeBlocks = [...zoneContent.matchAll(/```[\s\S]*?```/g)];
  if (codeBlocks.length > 0) {
    for (const block of codeBlocks) {
      const inner = block[0].replace(/^```[^\n]*\n/, '').replace(/```$/, '');
      if (/\S/.test(inner)) return true;
    }
  }
  // inline code that looks like a command
  const inlineCode = [...zoneContent.matchAll(/`([^`]+)`/g)].map(m => m[1]);
  const cmdPattern = /^(make|npm|yarn|pnpm|go\s|cargo|pytest|mvn|gradle|\.\/|python|node|bash|sh\s|docker|kubectl)/;
  return inlineCode.some(c => cmdPattern.test(c.trim()));
}

module.exports = { parseZones, hashZone, headingsInZone, hasExecutableCommand };
