import assert from "node:assert/strict";
import { it } from "node:test";
import type { PublicClient } from "viem";
import { readClassroomSnapshot } from "../classroom/chain.js";

const wire = "0x1111111111111111111111111111111111111111";
const emptyMember = { account: "0x0000000000000000000000000000000000000000", joined: false,
  contributedThisPeriod: false, received: false, bidSubmitted: false, annualBps: 0,
  totalContributed: 0n, remainingDebt: 0n, lockedEth: 0n, winningInterest: 0n, payoutPeriod: 0,
  claimableUsdc: 0n, claimableEth: 0n, repaidUsdc: 0n, recoveredUsdc: 0n, ethSold: 0n,
  liquidationProcessed: false, principalAllocated: 0n, interestAllocated: 0n };
const state = { phase: 0, period: 0, deadline: 0n, currentCandidate: 5, triggerMask: 0, freezeReason: 0,
  retainedInterest: 0n, usedInterest: 0n, distributedInterest: 0n, principalLoss: 0n,
  obligationUncollected: 0n, defaultInterestUsed: 0n, commonInterestUsed: 0n, unallocatedUsdc: 0n };

it("reads a single block and rejects missing event history instead of inventing zero", async () => {
  const seen: bigint[] = [];
  const client = {
    getBlock: async () => ({ number: 42n, timestamp: 100n }),
    getBalance: async ({ blockNumber }: { blockNumber: bigint }) => { seen.push(blockNumber); return 0n; },
    getLogs: async ({ fromBlock, toBlock }: { fromBlock: bigint; toBlock: bigint }) => {
      assert.equal(fromBlock, 10n); assert.equal(toBlock, 42n); return [];
    },
    readContract: async ({ functionName, blockNumber }: { functionName: string; blockNumber: bigint }) => {
      seen.push(blockNumber);
      if (functionName === "getState") return state;
      if (functionName === "host") return wire;
      if (functionName === "memberCount") return 0;
      if (functionName === "settlementFinalized") return false;
      if (functionName === "getMember") return emptyMember;
      if (functionName === "balanceOf") return 0n;
      if (functionName === "getReserves") return [1n, 1n, 0];
      throw new Error(`unexpected ${functionName}`);
    },
  } as unknown as PublicClient;
  const result = await readClassroomSnapshot(client, wire, 10n);
  assert.equal(result.blockNumber, 42n);
  assert.ok(seen.length > 5 && seen.every(n => n === 42n));
  const broken = { ...client, getLogs: async () => { throw new Error("RPC logs unavailable"); } } as unknown as PublicClient;
  await assert.rejects(readClassroomSnapshot(broken, wire, 10n), /RPC logs unavailable/);
});
