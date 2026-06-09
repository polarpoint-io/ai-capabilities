#!/usr/bin/env node
'use strict';

const fs      = require('fs');
const path    = require('path');
const https   = require('https');
const http    = require('http');
const { validate } = require('../lib/validator');

// ── CLI argument parsing ──────────────────────────────────────────────────────
const args = process.argv.slice(2);
let schemaArg = null;
let fileArg   = null;
let strict    = false;

for (let i = 0; i < args.length; i++) {
  if (args[i] === '--schema' && args[i + 1]) { schemaArg = args[++i]; continue; }
  if (args[i] === '--file'   && args[i + 1]) { fileArg   = args[++i]; continue; }
  if (args[i] === '--strict')                { strict = true;          continue; }
}

if (!fileArg) {
  console.error('Usage: agentsmd-validator --file <path> [--schema <url|path>] [--strict]');
  process.exit(1);
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function fetchUrl(url) {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;
    client.get(url, res => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        return fetchUrl(res.headers.location).then(resolve).catch(reject);
      }
      let data = '';
      res.on('data', chunk => { data += chunk; });
      res.on('end', () => resolve(data));
    }).on('error', reject);
  });
}

function loadSchema(schemaArg) {
  if (!schemaArg) return Promise.resolve(null);
  if (schemaArg.startsWith('http://') || schemaArg.startsWith('https://')) {
    return fetchUrl(schemaArg).then(JSON.parse).catch(err => {
      console.warn(`  ⚠  Could not fetch schema from ${schemaArg}: ${err.message}`);
      return null;
    });
  }
  try {
    return Promise.resolve(JSON.parse(fs.readFileSync(path.resolve(schemaArg), 'utf8')));
  } catch (err) {
    console.warn(`  ⚠  Could not read schema file ${schemaArg}: ${err.message}`);
    return Promise.resolve(null);
  }
}

// ── Main ──────────────────────────────────────────────────────────────────────
async function main() {
  const filePath = path.resolve(fileArg);
  if (!fs.existsSync(filePath)) {
    console.error(`  ✗  File not found: ${filePath}`);
    process.exit(1);
  }

  const content    = fs.readFileSync(filePath, 'utf8');
  const schemaData = await loadSchema(schemaArg);

  console.log(`\nValidating ${path.basename(filePath)}\n${'─'.repeat(50)}`);

  const { errors, warnings, zone1Hash } = validate(content, schemaData);

  if (zone1Hash) {
    console.log(`  Zone 1 hash : ${zone1Hash}`);
  }

  if (warnings.length) {
    console.log('');
    warnings.forEach(w => console.log(`  ⚠  ${w}`));
  }

  if (errors.length) {
    console.log('');
    errors.forEach(e => console.error(`  ✗  ${e}`));
    console.log(`\n${'─'.repeat(50)}`);
    console.log(`  FAILED  ${errors.length} error(s), ${warnings.length} warning(s)\n`);
    process.exit(1);
  }

  console.log(`\n${'─'.repeat(50)}`);
  if (warnings.length) {
    console.log(`  PASSED with ${warnings.length} warning(s)\n`);
    if (strict) {
      console.log('  (--strict mode: warnings treated as errors)');
      process.exit(1);
    }
  } else {
    console.log('  PASSED\n');
  }
}

main().catch(err => {
  console.error(`  ✗  Unexpected error: ${err.message}`);
  process.exit(1);
});
