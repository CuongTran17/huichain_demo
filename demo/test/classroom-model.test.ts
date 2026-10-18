import assert from "node:assert/strict";
import { it } from "node:test";
import { availableActions } from "../classroom/model.js";
import type { ClassroomSnapshot } from "../classroom/chain.js";

const a = "0x1111111111111111111111111111111111111111";
function snapshot(): ClassroomSnapshot {
  return { wire: "0x2222222222222222222222222222222222222222", host: a,
    blockNumber: 1n, blockTimestamp: 100n, memberCount: 1, applicants: [], history: [], settlementFinalized: false,
    usdcBalance: 0n, ethBalance: 0n, reserveUsdc: 1n, reserveWeth: 1n,
    readiness: [{ usdc: 500_000_000n, eth: 1n, allowance: 0n }],
    members: [{ account: a, joined: true, contributedThisPeriod: false, received: false,
      bidSubmitted: false, annualBps: 0, totalContributed: 0n, remainingDebt: 0n,
      lockedEth: 0n, winningInterest: 0n, payoutPeriod: 0, claimableUsdc: 0n,
      claimableEth: 0n, repaidUsdc: 0n, recoveredUsdc: 0n, ethSold: 0n,
      liquidationProcessed: false, principalAllocated: 0n, interestAllocated: 0n },
      ...Array.from({ length: 4 }, () => ({ account: "0x0000000000000000000000000000000000000000" as const,
        joined: false, contributedThisPeriod: false, received: false, bidSubmitted: false,
        annualBps: 0, totalContributed: 0n, remainingDebt: 0n, lockedEth: 0n,
        winningInterest: 0n, payoutPeriod: 0, claimableUsdc: 0n, claimableEth: 0n,
        repaidUsdc: 0n, recoveredUsdc: 0n, ethSold: 0n, liquidationProcessed: false,
        principalAllocated: 0n, interestAllocated: 0n }))],
    state: { phase: 0, period: 0, deadline: 0n, currentCandidate: 5, triggerMask: 0,
      freezeReason: 0, retainedInterest: 0n, usedInterest: 0n, distributedInterest: 0n,
      principalLoss: 0n, obligationUncollected: 0n, defaultInterestUsed: 0n,
      commonInterestUsed: 0n, unallocatedUsdc: 0n } };
}

it("approval is separate from contribution and a paid member cannot bid again", () => {
  const s = snapshot();
  assert.deepEqual(availableActions(s, a, 100n), ["approve"]);
  s.readiness[0].allowance = 500_000_000n;
  assert.deepEqual(availableActions(s, a, 100n), []);
  s.state.phase = 1; s.state.deadline = 200n;
  assert.deepEqual(availableActions(s, a, 100n), ["contribute"]);
  s.members[0].contributedThisPeriod = true;
  assert.deepEqual(availableActions(s, a, 100n), []);
  assert.deepEqual(availableActions(s, a, 201n), ["advance"]);
  s.state.phase = 2; s.members[0].received = true;
  assert.deepEqual(availableActions(s, a, 201n), ["advance"]);
});
