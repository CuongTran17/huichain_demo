import assert from "node:assert/strict";
import { it } from "node:test";
import { decodeFunctionData, type PublicClient } from "viem";
import { assertWalletContext, sendAction } from "../classroom/wallet.js";
import { tokenAbi, type ClassroomSnapshot } from "../classroom/chain.js";
import { PAIR, ROUTER, USDC } from "../shared/config.js";

it("refuses signatures after a wallet account or network switch", async () => {
  const account = "0x1111111111111111111111111111111111111111";
  const provider = { request: async ({ method }: { method: string }) =>
    method === "eth_chainId" ? "0xaa36a7" : [account] };
  await assertWalletContext(provider, account);
  await assert.rejects(assertWalletContext({ request: async ({ method }: { method: string }) =>
    method === "eth_chainId" ? "0x1" : [account] }, account));
  await assert.rejects(assertWalletContext({ request: async ({ method }: { method: string }) =>
    method === "eth_chainId" ? "0xaa36a7" : ["0x2222222222222222222222222222222222222222"] }, account));
});

it("sends an exact 600 USDC approval for the six-period wire", async () => {
  const account = "0x1111111111111111111111111111111111111111";
  const wire = "0x2222222222222222222222222222222222222222";
  let transaction: { data: `0x${string}` } | undefined;
  const member = { account, joined: true, contributedThisPeriod: false, received: false,
    bidSubmitted: false, annualBps: 0, totalContributed: 0n, remainingDebt: 0n, lockedEth: 0n,
    winningInterest: 0n, payoutPeriod: 0, claimableUsdc: 0n, claimableEth: 0n, repaidUsdc: 0n,
    recoveredUsdc: 0n, ethSold: 0n, liquidationProcessed: false, principalAllocated: 0n, interestAllocated: 0n };
  const client = {
    getBlock: async () => ({ number: 10n, timestamp: 100n }),
    getBalance: async () => 1n,
    getLogs: async () => [],
    call: async () => ({ data: "0x" }),
    readContract: async ({ functionName }: { functionName: string }) => {
      if (functionName === "getState") return { phase: 0, period: 0, deadline: 0n, currentCandidate: 6, triggerMask: 0 };
      if (functionName === "host") return account;
      if (functionName === "memberCount") return 1;
      if (functionName === "settlementFinalized") return false;
      if (functionName === "usdc") return USDC;
      if (functionName === "pair") return PAIR;
      if (functionName === "router") return ROUTER;
      if (functionName === "POT") return 600_000_000n;
      if (functionName === "collateralRatioBps") return 18000;
      if (functionName === "getMember") return member;
      if (functionName === "getReserves") return [1n, 1n, 0];
      if (functionName === "balanceOf") return 600_000_000n;
      if (functionName === "allowance") return 0n;
      throw new Error(functionName);
    },
  } as unknown as PublicClient;
  const provider = { request: async ({ method, params }: { method: string; params?: unknown[] }) => {
    if (method === "eth_chainId") return "0xaa36a7";
    if (method === "eth_accounts") return [account];
    if (method === "eth_sendTransaction") { transaction = params![0] as { data: `0x${string}` }; return `0x${"a".repeat(64)}`; }
    throw new Error(method);
  } };
  await sendAction(provider, client, { wire } as unknown as ClassroomSnapshot, 1n, account, "approve");
  assert.ok(transaction);
  const decoded = decodeFunctionData({ abi: tokenAbi, data: transaction.data });
  assert.equal(decoded.functionName, "approve");
  assert.deepEqual(decoded.args, [wire, 600_000_000n]);
});
