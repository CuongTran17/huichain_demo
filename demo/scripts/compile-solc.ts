import { readdir, readFile, mkdir, writeFile, unlink } from "node:fs/promises";
import { join, relative, resolve } from "node:path";
import { createRequire } from "node:module";
import { createHash } from "node:crypto";

const solc = createRequire(import.meta.url)("solc") as {
  compile(input: string, options: { import: (name: string) => { contents?: string; error?: string } }): string;
  version(): string;
};

const root = resolve("contracts");
const artifactsRoot = resolve("artifacts");

async function soliditySources(dir: string): Promise<Record<string, { content: string }>> {
  const sources: Record<string, { content: string }> = {};
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) Object.assign(sources, await soliditySources(path));
    else if (entry.name.endsWith(".sol")) sources[relative(process.cwd(), path).replaceAll("\\", "/")] = { content: await readFile(path, "utf8") };
  }
  return sources;
}

async function main() {
  const sources = await soliditySources(root);
  if (!Object.keys(sources).length) throw new Error("no Solidity sources");
  const input = {
    language: "Solidity",
    sources,
    settings: {
      optimizer: { enabled: true, runs: 200 },
      outputSelection: { "*": { "": ["ast"], "*": ["abi", "evm.bytecode", "evm.deployedBytecode", "evm.methodIdentifiers", "metadata"] } },
    },
  };
  const compiled = JSON.parse(solc.compile(JSON.stringify(input), {
    import: (name: string) => {
      const path = name.startsWith("@openzeppelin/") ? resolve("node_modules", name) : resolve(name);
      try {
        const contents = requireRead(path);
        sources[name] = { content: contents };
        return { contents };
      }
      catch { return { error: `unavailable import: ${name}` }; }
    },
  }));
  const errors = (compiled.errors ?? []).filter((item: { severity: string }) => item.severity === "error");
  if (errors.length) throw new Error(errors.map((item: { formattedMessage: string }) => item.formattedMessage).join("\n"));
  const buildInfoId = `solc-0_8_28-solc-${createHash("sha256").update(JSON.stringify(input)).digest("hex").slice(0, 16)}`;
  const buildInfoRoot = join(artifactsRoot, "build-info");
  await mkdir(buildInfoRoot, { recursive: true });
  for (const entry of await readdir(buildInfoRoot)) {
    if (/^solc-0_8_28-solc-[0-9a-f]{16}\.(?:json|output\.json)$/.test(entry)
      && !entry.startsWith(`${buildInfoId}.`)) await unlink(join(buildInfoRoot, entry));
  }
  await writeFile(join(buildInfoRoot, `${buildInfoId}.json`), JSON.stringify({
    _format: "hh3-sol-build-info-1", id: buildInfoId, solcVersion: "0.8.28",
    solcLongVersion: solc.version(), compilerType: "solc", userSourceNameMap: {}, input,
  }));
  await writeFile(join(buildInfoRoot, `${buildInfoId}.output.json`), JSON.stringify({
    _format: "hh3-sol-build-info-output-1", id: buildInfoId, output: compiled,
  }));
  let count = 0;
  for (const [sourceName, entries] of Object.entries(compiled.contracts ?? {})) {
    for (const [contractName, contract] of Object.entries(entries as Record<string, any>)) {
      if (!sourceName.startsWith("contracts/")) continue;
      const artifact = {
        _format: "hh3-artifact-1", contractName, sourceName, inputSourceName: sourceName, buildInfoId,
        abi: contract.abi, bytecode: `0x${contract.evm.bytecode.object}`,
        deployedBytecode: `0x${contract.evm.deployedBytecode.object}`,
        linkReferences: contract.evm.bytecode.linkReferences ?? {},
        deployedLinkReferences: contract.evm.deployedBytecode.linkReferences ?? {},
        immutableReferences: contract.evm.deployedBytecode.immutableReferences ?? {},
      };
      const target = join(artifactsRoot, sourceName, `${contractName}.json`);
      await mkdir(resolve(target, ".."), { recursive: true });
      await writeFile(target, JSON.stringify(artifact, null, 2) + "\n");
      count++;
    }
  }
  console.log(`Compiled ${count} local contracts with solc ${solc.version()}`);
}

import { readFileSync } from "node:fs";
const requireRead = (path: string) => readFileSync(path, "utf8");
await main();
