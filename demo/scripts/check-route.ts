import { mkdir, writeFile } from "node:fs/promises";
import { createPublicClient, http, keccak256, parseAbi, type Address, type PublicClient } from "viem";
import { sepolia } from "viem/chains";
import {
  FACTORY, PAIR, ROUTER, SEPOLIA, USDC, WETH,
  validateRouteSnapshot, type RouteEvidence, type RouteSnapshot,
} from "../shared/config.ts";

const pairAbi = parseAbi([
  "function token0() view returns (address)",
  "function token1() view returns (address)",
  "function factory() view returns (address)",
  "function getReserves() view returns (uint112,uint112,uint32)",
]);
const factoryAbi = parseAbi(["function getPair(address,address) view returns (address)"]);
const routerAbi = parseAbi([
  "function factory() view returns (address)",
  "function WETH() view returns (address)",
  "function getAmountsIn(uint256,address[]) view returns (uint256[])",
  "function getAmountsOut(uint256,address[]) view returns (uint256[])",
]);
const tokenAbi = parseAbi(["function decimals() view returns (uint8)"]);

export async function verifyRoute(
  client: PublicClient,
  config: { usdc: Address; weth: Address; pair: Address; router: Address; factory: Address },
  blockNumber: bigint,
  collateralRatioBps = 10000,
): Promise<RouteEvidence> {
  const block = await client.getBlock({ blockNumber });
  const chainId = await client.getChainId();
  const named = async <T>(name: string, operation: Promise<T>): Promise<T> => {
    try { return await operation; }
    catch (error) {
      const detail = error instanceof Error && "shortMessage" in error
        ? String(error.shortMessage) : error instanceof Error ? error.message : "unknown";
      throw new Error(`${name}: ${detail.replace(/https?:\/\/\S+/g, "[rpc]")}`);
    }
  };
  const [token0, token1, pairFactory, rawReserves, routerFactory, routerWeth, factoryPair,
    usdcDecimals, wethDecimals, usdcCode, wethCode, pairCode, routerCode, factoryCode] = await Promise.all([
    named("pair.token0", client.readContract({ address: config.pair, abi: pairAbi, functionName: "token0", blockNumber })),
    named("pair.token1", client.readContract({ address: config.pair, abi: pairAbi, functionName: "token1", blockNumber })),
    named("pair.factory", client.readContract({ address: config.pair, abi: pairAbi, functionName: "factory", blockNumber })),
    named("pair.getReserves", client.readContract({ address: config.pair, abi: pairAbi, functionName: "getReserves", blockNumber })),
    named("router.factory", client.readContract({ address: config.router, abi: routerAbi, functionName: "factory", blockNumber })),
    named("router.WETH", client.readContract({ address: config.router, abi: routerAbi, functionName: "WETH", blockNumber })),
    named("factory.getPair", client.readContract({ address: config.factory, abi: factoryAbi, functionName: "getPair", args: [config.usdc, config.weth], blockNumber })),
    named("usdc.decimals", client.readContract({ address: config.usdc, abi: tokenAbi, functionName: "decimals", blockNumber })),
    named("weth.decimals", client.readContract({ address: config.weth, abi: tokenAbi, functionName: "decimals", blockNumber })),
    named("usdc.code", client.getCode({ address: config.usdc, blockNumber })),
    named("weth.code", client.getCode({ address: config.weth, blockNumber })),
    named("pair.code", client.getCode({ address: config.pair, blockNumber })),
    named("router.code", client.getCode({ address: config.router, blockNumber })),
    named("factory.code", client.getCode({ address: config.factory, blockNumber })),
  ]);
  const codeHash = (code: `0x${string}` | undefined) => code && code !== "0x" ? keccak256(code) : "0x";
  const snapshot: RouteSnapshot = {
    chainId, blockNumber: blockNumber.toString(), blockHash: block.hash,
    usdc: config.usdc, weth: config.weth, pair: config.pair, router: config.router, factory: config.factory,
    token0, token1, pairFactory, routerFactory, routerWeth, factoryPair,
    usdcDecimals, wethDecimals,
    reserveUsdc: rawReserves[0].toString(), reserveWeth: rawReserves[1].toString(),
    codeHashes: { usdc: codeHash(usdcCode), weth: codeHash(wethCode), pair: codeHash(pairCode), router: codeHash(routerCode), factory: codeHash(factoryCode) },
  };
  const result = validateRouteSnapshot(snapshot, collateralRatioBps);
  if (!result.usable) return result;
  const reasons: string[] = [];
  for (const quote of result.quotes) {
    try {
      const amountIn = await client.readContract({
        address: config.router, abi: routerAbi, functionName: "getAmountsIn",
        args: [BigInt(quote.debtUsdc), [config.weth, config.usdc]], blockNumber,
      });
      const amountOut = await client.readContract({
        address: config.router, abi: routerAbi, functionName: "getAmountsOut",
        args: [BigInt(quote.ethRequired), [config.weth, config.usdc]], blockNumber,
      });
      if (amountIn[0] !== BigInt(quote.ethRequired) || amountOut[1] !== BigInt(quote.usdcFromRequiredEth)) {
        reasons.push(`router quote mismatch for ${quote.debtUsdc}`);
      }
    } catch (error) {
      reasons.push(`router quote failed for ${quote.debtUsdc}: ${error instanceof Error ? error.name : "unknown"}`);
    }
  }
  return { ...result, usable: reasons.length === 0, reasons, quotes: reasons.length ? [] : result.quotes };
}

async function main() {
  const rpcUrl = process.env.SEPOLIA_RPC_URL || "https://ethereum-sepolia-rpc.publicnode.com";
  const ratio = Number(process.env.COLLATERAL_RATIO_BPS || "10000");
  const client = createPublicClient({ chain: sepolia, transport: http(rpcUrl, { timeout: 20_000 }) });
  let evidence: RouteEvidence;
  try {
    const blockNumber = await client.getBlockNumber();
    evidence = await verifyRoute(client, {
      usdc: USDC as Address, weth: WETH as Address, pair: PAIR as Address,
      router: ROUTER as Address, factory: FACTORY as Address,
    }, blockNumber, ratio);
  } catch (error) {
    console.error(`Route check failed: ${error instanceof Error ? error.message : "unknown RPC error"}`);
    process.exitCode = 1;
    return;
  }
  await mkdir(new URL("../.runtime/", import.meta.url), { recursive: true });
  await writeFile(new URL("../.runtime/route-evidence.json", import.meta.url), JSON.stringify(evidence, null, 2) + "\n");
  console.log(JSON.stringify(evidence, null, 2));
  if (!evidence.usable || evidence.chainId !== SEPOLIA) process.exitCode = 1;
}

if (process.argv[1]?.replaceAll("\\", "/").endsWith("/scripts/check-route.ts")) {
  await main();
}
