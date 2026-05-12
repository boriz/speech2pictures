#!/usr/bin/env node

import { promises as fs } from "node:fs";
import path from "node:path";
import process from "node:process";
import { ESLint } from "eslint";

const argv = new Set(process.argv.slice(2));
const shouldFix = argv.has("--fix");
const keepTemp = argv.has("--keep-temp");

const repoRoot = process.cwd();
const templatesDir = path.join(repoRoot, "templates");
const tempDir = path.join(repoRoot, ".lint-tmp", "js");

function sanitizeJinja(scriptBody) {
  return scriptBody
    .replace(/\{#([\s\S]*?)#\}/g, "")
    .replace(/\{\{([\s\S]*?)\}\}/g, "0")
    .replace(/\{%-?([\s\S]*?)-?%\}/g, "");
}

async function listTemplateFiles(dir) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await listTemplateFiles(fullPath)));
      continue;
    }
    if (entry.isFile() && fullPath.endsWith(".html")) {
      files.push(fullPath);
    }
  }
  return files;
}

function extractScriptBlocks(html) {
  const matches = [];
  const scriptTagRegex = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
  let match = scriptTagRegex.exec(html);
  while (match) {
    const attrs = match[1] || "";
    const body = match[2] || "";
    const hasSrc = /\bsrc\s*=/.test(attrs);
    if (!hasSrc && body.trim()) {
      matches.push(body);
    }
    match = scriptTagRegex.exec(html);
  }
  return matches;
}

async function buildLintFiles() {
  await fs.rm(tempDir, { recursive: true, force: true });
  await fs.mkdir(tempDir, { recursive: true });

  const templateFiles = await listTemplateFiles(templatesDir);
  const generatedFiles = [];

  for (const templateFile of templateFiles) {
    const html = await fs.readFile(templateFile, "utf8");
    const scripts = extractScriptBlocks(html);
    if (!scripts.length) {
      continue;
    }

    const rel = path.relative(templatesDir, templateFile);
    const base = rel.replace(/\.html$/i, "").replace(/[\\/]/g, "__");
    for (let i = 0; i < scripts.length; i += 1) {
      const outputName = `${base}.script-${i + 1}.js`;
      const outputPath = path.join(tempDir, outputName);
      const sourceComment = `/* source: templates/${rel} script #${i + 1} */\n`;
      const body = sanitizeJinja(scripts[i]);
      await fs.writeFile(outputPath, sourceComment + body, "utf8");
      generatedFiles.push(outputPath);
    }
  }

  return generatedFiles;
}

async function run() {
  const generatedFiles = await buildLintFiles();
  if (!generatedFiles.length) {
    console.log("No inline JS scripts found in templates.");
    return;
  }

  const eslint = new ESLint({ fix: shouldFix });
  const results = await eslint.lintFiles([path.join(tempDir, "**/*.js")]);
  if (shouldFix) {
    await ESLint.outputFixes(results);
  }

  const formatter = await eslint.loadFormatter("stylish");
  const output = formatter.format(results);
  if (output) {
    console.log(output);
  }

  const totals = results.reduce(
    (acc, item) => {
      acc.errors += item.errorCount;
      acc.warnings += item.warningCount;
      return acc;
    },
    { errors: 0, warnings: 0 },
  );

  if (!keepTemp) {
    await fs.rm(tempDir, { recursive: true, force: true });
  }

  if (totals.errors > 0) {
    process.exitCode = 1;
  }
}

await run();
