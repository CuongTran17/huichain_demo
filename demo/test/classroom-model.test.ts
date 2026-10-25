import assert from "node:assert/strict";
import { it } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { availableActions, claimPreview, memberReturnSummary } from "../classroom/model.js";
import { Display } from "../classroom/Display.js";
import { Player } from "../classroom/Player.js";
import type { ClassroomSnapshot } from "../classroom/chain.js";

const a = "0x1111111111111111111111111111111111111111";
function snapshot(): ClassroomSnapshot {
  return { wire: "0x2222222222222222222222222222222222222222", host: a,
    blockNumber: 1n, blockTimestamp: 100n, memberCount: 1, applicants: [], history: [], settlementFinalized: false,
    usdcBalance: 0n, ethBalance: 0n, reserveUsdc: 1n, reserveWeth: 1n,
    readiness: [{ usdc: 600_000_000n, eth: 1n, allowance: 0n }, ...Array.from({ length: 5 }, () => ({ usdc: 0n, eth: 0n, allowance: 0n }))],
    members: [{ account: a, joined: true, contributedThisPeriod: false, received: false,
      bidSubmitted: false, annualBps: 0, totalContributed: 0n, remainingDebt: 0n,
      lockedEth: 0n, winningInterest: 0n, payoutPeriod: 0, claimableUsdc: 0n,
      claimableEth: 0n, repaidUsdc: 0n, recoveredUsdc: 0n, ethSold: 0n,
      liquidationProcessed: false, principalAllocated: 0n, interestAllocated: 0n },
      ...Array.from({ length: 5 }, () => ({ account: "0x0000000000000000000000000000000000000000" as const,
        joined: false, contributedThisPeriod: false, received: false, bidSubmitted: false,
        annualBps: 0, totalContributed: 0n, remainingDebt: 0n, lockedEth: 0n,
        winningInterest: 0n, payoutPeriod: 0, claimableUsdc: 0n, claimableEth: 0n,
        repaidUsdc: 0n, recoveredUsdc: 0n, ethSold: 0n, liquidationProcessed: false,
        principalAllocated: 0n, interestAllocated: 0n }))],
    state: { phase: 0, period: 0, deadline: 0n, currentCandidate: 6, triggerMask: 0,
      freezeReason: 0, retainedInterest: 0n, usedInterest: 0n, distributedInterest: 0n,
      principalLoss: 0n, obligationUncollected: 0n, defaultInterestUsed: 0n,
      commonInterestUsed: 0n, unallocatedUsdc: 0n } };
}

it("approval is separate from contribution and a paid member cannot bid again", () => {
  const s = snapshot();
  assert.deepEqual(availableActions(s, a, 100n), ["approve"]);
  s.readiness[0].allowance = 600_000_000n;
  assert.deepEqual(availableActions(s, a, 100n), []);
  s.state.phase = 1; s.state.deadline = 200n;
  assert.deepEqual(availableActions(s, a, 100n), ["contribute"]);
  s.members[0].contributedThisPeriod = true;
  assert.deepEqual(availableActions(s, a, 100n), []);
  assert.deepEqual(availableActions(s, a, 201n), ["advance"]);
  s.state.phase = 2; s.members[0].received = true;
  assert.deepEqual(availableActions(s, a, 201n), ["advance"]);
});

it("requires 600 USDC allowance and all six approvals before host can start", () => {
  const s = snapshot();
  s.readiness[0].allowance = 500_000_000n;
  s.memberCount = 5;
  assert.deepEqual(availableActions(s, a, 100n), ["approve"]);
  s.readiness[0].allowance = 600_000_000n;
  assert.deepEqual(availableActions(s, a, 100n), []);
  s.memberCount = 6;
  assert.deepEqual(availableActions(s, a, 100n), ["start"]);
});

it("previews six-member first and last claims from the gross 600 USDC pot", () => {
  assert.deepEqual(claimPreview(0, 2000), { debt: 500_000_000n, interest: 41_095_890n, net: 558_904_110n });
  assert.deepEqual(claimPreview(5, 2000), { debt: 0n, interest: 0n, net: 600_000_000n });
});

it("offers host liquidation for the sixth paid member when they default", () => {
  const s = snapshot();
  s.state.phase = 4;
  s.state.triggerMask = 1 << 5;
  s.state.deadline = 200n;
  s.members[5].received = true;
  s.members[5].remainingDebt = 100_000_000n;
  s.members[5].lockedEth = 1n;
  assert.deepEqual(availableActions(s, a, 100n), ["liquidate"]);
});

it("shows interest paid and separate USDC and ETH entitlements after settlement", () => {
  const s = snapshot();
  s.members[0].received = true;
  s.members[0].winningInterest = 41_095_890n;
  s.members[0].principalAllocated = 100_000_000n;
  s.members[0].interestAllocated = 26_000_000n;
  s.members[0].claimableUsdc = 126_000_000n;
  s.members[0].claimableEth = 450_000_000_000_000_000n;
  s.settlementFinalized = true;
  const result = memberReturnSummary(s, 0);
  assert.equal(result.interestPaid, 41_095_890n);
  assert.equal(result.interestReceived, 26_000_000n);
  assert.equal(result.usdcEntitlement, 126_000_000n);
  assert.equal(result.usdcAvailable, 126_000_000n);
  assert.equal(result.ethAvailable, 450_000_000_000_000_000n);
});

it("does not invent a personal interest forecast before settlement", () => {
  const s = snapshot();
  s.members[0].winningInterest = 41_095_890n;
  s.state.retainedInterest = 41_095_890n;
  assert.equal(memberReturnSummary(s, 0).interestReceived, undefined);
});

it("keeps withdrawn assets visible in the history instead of showing them as lost", () => {
  const s = snapshot();
  s.settlementFinalized = true;
  s.members[0].principalAllocated = 100_000_000n;
  s.members[0].interestAllocated = 26_000_000n;
  s.history = [
    { event: "PayoutClaimed", blockNumber: 2n, transactionHash: `0x${"1".repeat(64)}`, args: { memberId: 0, net: 558_904_110n, ethLocked: 450_000_000_000_000_000n } },
    { event: "Withdrawn", blockNumber: 3n, transactionHash: `0x${"2".repeat(64)}`, args: { memberId: 0, asset: "0x1c7d4b196cb0c7b01d743fbc6116a902379c7238", amount: 126_000_000n } },
    { event: "Withdrawn", blockNumber: 4n, transactionHash: `0x${"3".repeat(64)}`, args: { memberId: 0, asset: "0x0000000000000000000000000000000000000000", amount: 450_000_000_000_000_000n } },
  ];
  const result = memberReturnSummary(s, 0);
  assert.equal(result.payoutReceived, 558_904_110n);
  assert.equal(result.ethInitiallyLocked, 450_000_000_000_000_000n);
  assert.equal(result.usdcEntitlement, 126_000_000n);
  assert.equal(result.usdcWithdrawn, 126_000_000n);
  assert.equal(result.ethWithdrawn, 450_000_000_000_000_000n);
  assert.equal(result.usdcAvailable, 0n);
  assert.equal(result.ethAvailable, 0n);
});

it("shows each member's USDC and ETH return breakdown on the projector", () => {
  const s = snapshot();
  s.settlementFinalized = true;
  s.state.phase = 6;
  s.members[0].winningInterest = 41_095_890n;
  s.members[0].interestAllocated = 26_000_000n;
  s.members[0].claimableUsdc = 26_000_000n;
  s.members[0].claimableEth = 450_000_000_000_000_000n;
  const html = renderToStaticMarkup(createElement(Display, { snapshot: s, now: 100n, stale: false }));
  assert.match(html, /Lãi đã khấu trừ/);
  assert.match(html, /Lãi được chia/);
  assert.match(html, /USDC còn rút/);
  assert.match(html, /ETH còn rút/);
});

it("shows the player's own return details without promising interest before finalization", () => {
  const s = snapshot();
  s.members[0].winningInterest = 41_095_890n;
  const render = () => renderToStaticMarkup(createElement(Player, { snapshot: s, account: a, now: 100n,
    stale: false, run: () => {}, admit: () => {}, approveRepay: () => {}, connect: () => {} }));
  assert.match(render(), /Lãi nhận thêm/);
  assert.match(render(), /Chưa chốt/);
  s.settlementFinalized = true;
  s.state.phase = 6;
  s.members[0].interestAllocated = 26_000_000n;
  s.members[0].claimableUsdc = 26_000_000n;
  assert.match(render(), /26 USDC/);
});
