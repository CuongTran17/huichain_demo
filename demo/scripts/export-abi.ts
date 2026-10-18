import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

for (const [contract, targetName, symbol] of [
  ["RoscaDemo", "abi", "rosca"],
  ["RoscaClassroom", "classroom-abi", "classroom"],
]) {
  const source = resolve(`artifacts/contracts/${contract}.sol/${contract}.json`);
  const target = resolve(`shared/${targetName}.ts`);
  const artifact = JSON.parse(await readFile(source, "utf8"));
  if (artifact._format !== "hh3-artifact-1" || !artifact.bytecode.startsWith("0x") || artifact.bytecode.length < 4) {
    throw new Error(`${contract} compiled artifact is missing or invalid`);
  }
  const deployedBytes = (artifact.deployedBytecode.length - 2) / 2;
  if (deployedBytes > 24_576) throw new Error(`${contract} exceeds EIP-170: ${deployedBytes} bytes`);
  await writeFile(target,
    `// Generated from solc 0.8.28 ${contract} artifact. Run npm run export:abi.\n` +
    `export const ${symbol}Abi = ${JSON.stringify(artifact.abi, null, 2)} as const;\n` +
    `export const ${symbol}Bytecode = ${JSON.stringify(artifact.bytecode)} as const;\n`);
  console.log(`Exported ${contract} ABI and creation bytecode; runtime ${deployedBytes}/24576 bytes`);
}
