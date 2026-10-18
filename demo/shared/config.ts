export const SEPOLIA = 11155111;
export const USDC = "0x1c7d4b196cb0c7b01d743fbc6116a902379c7238";
export const WETH = "0xfff9976782d46cc05630d1f6ebab18b2324d6b14";
export const PAIR = "0x72e46e15ef83c896de44b1874b4af7ddab5b4f74";
export const FACTORY = "0xf62c03e08ada871a0beb309762e260a7a6a880e6";
export const ROUTER = "0xee567fe1712faf6149d80da1e6934e354124cfe3";

export type RouteSnapshot = {
  chainId: number;
  blockNumber: string;
  blockHash: string;
  usdc: string;
  weth: string;
  pair: string;
  factory: string;
  router: string;
  token0: string;
  token1: string;
  pairFactory: string;
  routerFactory: string;
  routerWeth: string;
  factoryPair: string;
  usdcDecimals: number;
  wethDecimals: number;
  reserveUsdc: string;
  reserveWeth: string;
  codeHashes: Record<"usdc" | "weth" | "pair" | "router" | "factory", string>;
};

export type RouteQuote = {
  debtUsdc: string;
  ethRequired: string;
  usdcFromRequiredEth: string;
  priceImpactBps: string;
};

export type RouteEvidence = RouteSnapshot & {
  collateralRatioBps: number;
  usable: boolean;
  reasons: string[];
  quotes: RouteQuote[];
};

const same = (a: string, b: string) => a.toLowerCase() === b.toLowerCase();
const validHash = (value: string) => /^0x[0-9a-f]{64}$/i.test(value) && !/^0x0{64}$/i.test(value);

export function toPublicRouteConfig(_privateConfig: { rpcUrl?: string; botPrivateKey?: string }) {
  return { chainId: SEPOLIA, usdc: USDC, weth: WETH, pair: PAIR, factory: FACTORY, router: ROUTER };
}

export function validateRouteSnapshot(snapshot: RouteSnapshot, collateralRatioBps: number): RouteEvidence {
  const reasons: string[] = [];
  if (snapshot.chainId !== SEPOLIA) reasons.push("wrong chain");
  for (const [label, actual, expected] of [
    ["USDC", snapshot.usdc, USDC], ["WETH", snapshot.weth, WETH],
    ["pair", snapshot.pair, PAIR], ["factory", snapshot.factory, FACTORY],
    ["router", snapshot.router, ROUTER], ["token0", snapshot.token0, USDC],
    ["token1", snapshot.token1, WETH], ["pair factory", snapshot.pairFactory, FACTORY],
    ["router factory", snapshot.routerFactory, FACTORY],
    ["router WETH", snapshot.routerWeth, WETH], ["factory pair", snapshot.factoryPair, PAIR],
  ]) {
    if (!same(actual!, expected!)) reasons.push(`${label} mismatch`);
  }
  if (snapshot.usdcDecimals !== 6 || snapshot.wethDecimals !== 18) reasons.push("decimals mismatch");
  if (!validHash(snapshot.blockHash) || !Object.values(snapshot.codeHashes).every(validHash)) reasons.push("missing code or block hash");
  if (!Number.isInteger(collateralRatioBps) || collateralRatioBps < 1 || collateralRatioBps > 100000) reasons.push("invalid collateral ratio");
  let reserveUsdc = 0n;
  let reserveWeth = 0n;
  try {
    reserveUsdc = BigInt(snapshot.reserveUsdc);
    reserveWeth = BigInt(snapshot.reserveWeth);
  } catch {
    reasons.push("invalid reserves");
  }
  if (reserveUsdc <= 0n || reserveWeth <= 0n) reasons.push("empty reserves");
  const quotes: RouteQuote[] = [];
  if (reasons.length === 0) {
    const maxDebt = (1000_000_000n * BigInt(collateralRatioBps) + 9999n) / 10000n;
    for (const debtUsdc of [100_000_000n, 400_000_000n, 600_000_000n, maxDebt]) {
      if (debtUsdc <= 0n || debtUsdc >= reserveUsdc) {
        reasons.push(`insufficient USDC reserves for ${debtUsdc}`);
        break;
      }
      // Uniswap v2 Router02 getAmountIn/getAmountOut, 0.3% fee.
      const ethRequired = reserveWeth * debtUsdc * 1000n / ((reserveUsdc - debtUsdc) * 997n) + 1n;
      const ethWithFee = ethRequired * 997n;
      const usdcFromRequiredEth = ethWithFee * reserveUsdc / (reserveWeth * 1000n + ethWithFee);
      if (ethRequired <= 0n || usdcFromRequiredEth < debtUsdc || ethRequired >= reserveWeth) {
        reasons.push(`zero or unusable quote for ${debtUsdc}`);
        break;
      }
      const spotUsdc = ethRequired * reserveUsdc / reserveWeth;
      const priceImpactBps = spotUsdc > 0n && spotUsdc > debtUsdc
        ? (spotUsdc - debtUsdc) * 10000n / spotUsdc : 0n;
      quotes.push({
        debtUsdc: debtUsdc.toString(),
        ethRequired: ethRequired.toString(),
        usdcFromRequiredEth: usdcFromRequiredEth.toString(),
        priceImpactBps: priceImpactBps.toString(),
      });
    }
  }
  return { ...snapshot, collateralRatioBps, usable: reasons.length === 0, reasons, quotes: reasons.length ? [] : quotes };
}
