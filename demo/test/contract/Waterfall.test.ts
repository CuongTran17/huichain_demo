import assert from "node:assert/strict";
import { describe, it } from "node:test";
import hre from "hardhat";

const { viem, networkHelpers } = await hre.network.create();

async function setup(ratio = 10000) {
  const wallets = await viem.getWalletClients();
  const addresses = wallets.slice(0, 5).map(w => w.account.address) as [`0x${string}`, `0x${string}`, `0x${string}`, `0x${string}`, `0x${string}`];
  const token = await viem.deployContract("TestTokens");
  const route = await viem.deployContract("TestV2", [token.address]);
  await token.write.mint([route.address, 1_000_000_000_000n]);
  const wire = await viem.deployContract("RoscaDemo", [addresses, ratio, token.address, route.address, route.address]);
  for (let i = 0; i < 5; i++) {
    await token.write.mint([addresses[i], 1_000_000_000n]);
    await token.write.approve([wire.address, 1_000_000_000n], { account: wallets[i].account });
    await wire.write.join([], { account: wallets[i].account });
  }
  await wire.write.start();
  return { wallets, token, route, wire };
}

async function round(env: Awaited<ReturnType<typeof setup>>, period: number, contributors: number[], winner?: number, bidBps = 0) {
  const { wire, wallets } = env;
  for (const i of contributors) await wire.write.contribute([], { account: wallets[i].account });
  if (winner === undefined) {
    await networkHelpers.time.increase(301);
    await wire.write.advance();
    return;
  }
  await wire.write.advance();
  for (let i = period; i < 5; i++) await wire.write.bid([i === winner ? bidBps : 0], { account: wallets[i].account });
  await wire.write.advance();
  await wire.write.claimPayout([], { account: wallets[winner].account, value: await wire.read.requiredCollateral() });
  await wire.write.advance();
}

async function member(wire: any, id: number) {
  return await wire.read.getMember([id]) as {
    principalAllocated: bigint; interestAllocated: bigint; claimableUsdc: bigint;
    claimableEth: bigint; remainingDebt: bigint; lockedEth: bigint;
  };
}

describe("RoscaDemo terminal waterfall", () => {
  it("completion returns ETH and shares retained interest by economic wait", async () => {
    const env = await setup();
    for (let period = 0; period < 5; period++) await round(env, period, [0, 1, 2, 3, 4], period, period === 0 ? 2000 : 0);
    await env.wire.write.finalizeSettlement();
    const state = await env.wire.read.getState() as { phase: number; distributedInterest: bigint; retainedInterest: bigint; principalLoss: bigint };
    assert.equal(state.phase, 5);
    assert.equal(state.distributedInterest, 26_301_369n);
    assert.equal(state.retainedInterest, 26_301_369n);
    assert.equal(state.principalLoss, 0n);
    const allocations = await Promise.all([0, 1, 2, 3, 4].map(i => member(env.wire, i)));
    assert.equal(allocations.reduce((sum, m) => sum + m.claimableUsdc, 0n), 26_301_369n);
    assert.equal(allocations[0].interestAllocated, 0n);
    assert.ok(allocations[4].interestAllocated > allocations[3].interestAllocated);
    assert.ok(allocations[0].claimableEth > 0n);
    const cashBefore = await env.token.read.balanceOf([env.wire.address]) as bigint;
    await env.wire.write.withdrawUsdc([], { account: env.wallets[4].account });
    assert.equal((await env.token.read.balanceOf([env.wire.address]) as bigint), cashBefore - allocations[4].claimableUsdc);
    await assert.rejects(env.wire.write.withdrawUsdc([], { account: env.wallets[4].account }));
    await assert.rejects(env.wire.write.finalizeSettlement());
    await env.wire.write.withdrawEth([], { account: env.wallets[0].account });
    assert.equal((await member(env.wire, 0)).claimableEth, 0n);
  });

  it("cannot distribute while a paid defaulter still has unresolved collateral", async () => {
    const env = await setup();
    await round(env, 0, [0, 1, 2, 3, 4], 0, 2000);
    await round(env, 1, [1, 2, 3, 4]);
    await assert.rejects(env.wire.write.finalizeSettlement());
    const quote = await env.wire.read.previewLiquidation([0]) as { blockNumber: bigint };
    await env.wire.write.liquidate([0, quote.blockNumber]);
    await env.wire.write.finalizeSettlement();
    assert.equal((await env.wire.read.getState() as { phase: number }).phase, 6);
  });

  it("partial first round returns only actual principal, with no invented ETH", async () => {
    const env = await setup();
    await round(env, 0, [0, 1, 2, 3]);
    await env.wire.write.finalizeSettlement();
    const amounts = await Promise.all([0, 1, 2, 3, 4].map(i => member(env.wire, i)));
    assert.deepEqual(amounts.map(m => m.principalAllocated), [100_000_000n, 100_000_000n, 100_000_000n, 100_000_000n, 0n]);
    assert.equal(amounts.reduce((sum, m) => sum + m.claimableUsdc, 0n), 400_000_000n);
    assert.equal(amounts.reduce((sum, m) => sum + m.claimableEth, 0n), 0n);
  });

  it("uses default interest before common interest and does not erase unpaid debt", async () => {
    const env = await setup(5000);
    await round(env, 0, [0, 1, 2, 3, 4], 0, 2000);
    await round(env, 1, [1, 2, 3, 4]);
    const quote = await env.wire.read.previewLiquidation([0]) as { blockNumber: bigint };
    await env.wire.write.liquidate([0, quote.blockNumber]);
    const before = await env.token.read.balanceOf([env.wire.address]) as bigint;
    await env.wire.write.finalizeSettlement();
    const state = await env.wire.read.getState() as { principalLoss: bigint; usedInterest: bigint; defaultInterestUsed: bigint; commonInterestUsed: bigint; obligationUncollected: bigint; distributedInterest: bigint };
    const shares = await Promise.all([0, 1, 2, 3, 4].map(i => member(env.wire, i)));
    assert.equal(state.usedInterest, 26_301_369n);
    assert.equal(state.defaultInterestUsed, 26_301_369n);
    assert.equal(state.commonInterestUsed, 0n);
    assert.equal(state.principalLoss, 800_000_000n - before);
    assert.ok(state.obligationUncollected > 0n);
    assert.equal(state.distributedInterest, 0n);
    assert.equal(shares.reduce((sum, m) => sum + m.claimableUsdc, 0n), before);
    assert.equal(shares[0].interestAllocated, 0n);
  });

  it("keeps surplus labelled when every member is a trigger", async () => {
    const env = await setup(100000);
    await round(env, 0, [0, 1, 2, 3, 4], 0, 2000);
    await round(env, 1, []);
    const quote = await env.wire.read.previewLiquidation([0]) as { blockNumber: bigint };
    await env.wire.write.liquidate([0, quote.blockNumber]);
    await env.wire.write.finalizeSettlement();
    const state = await env.wire.read.getState() as { unallocatedUsdc: bigint; distributedInterest: bigint };
    assert.ok(state.unallocatedUsdc > 0n);
    assert.equal(state.distributedInterest, 0n);
    assert.equal((await env.token.read.balanceOf([env.wire.address]) as bigint), state.unallocatedUsdc + 400_000_000n);
  });

  it("uses common interest only when the defaulter retained none", async () => {
    const env = await setup(5000);
    await round(env, 0, [0, 1, 2, 3, 4], 0, 0);
    await round(env, 1, [0, 1, 2, 3, 4], 1, 2000);
    await round(env, 2, [1, 2, 3, 4]);
    await env.wire.write.repay([200_000_000n], { account: env.wallets[1].account });
    const quote = await env.wire.read.previewLiquidation([0]) as { blockNumber: bigint };
    await env.wire.write.liquidate([0, quote.blockNumber]);
    await env.wire.write.finalizeSettlement();
    const state = await env.wire.read.getState() as { defaultInterestUsed: bigint; commonInterestUsed: bigint; usedInterest: bigint };
    assert.equal(state.defaultInterestUsed, 0n);
    assert.ok(state.commonInterestUsed > 0n);
    assert.equal(state.usedInterest, state.commonInterestUsed);
  });

  it("two paid members can default together without double-counting cash or ETH", async () => {
    const env = await setup(5000);
    await round(env, 0, [0, 1, 2, 3, 4], 0, 2000);
    await round(env, 1, [0, 1, 2, 3, 4], 1, 2000);
    await round(env, 2, [2, 3, 4]);
    for (const id of [0, 1]) {
      const quote = await env.wire.read.previewLiquidation([id]) as { blockNumber: bigint };
      await env.wire.write.liquidate([id, quote.blockNumber]);
    }
    const cash = await env.token.read.balanceOf([env.wire.address]) as bigint;
    await env.wire.write.finalizeSettlement();
    const state = await env.wire.read.getState() as { principalLoss: bigint; obligationUncollected: bigint; unallocatedUsdc: bigint };
    const shares = await Promise.all([0, 1, 2, 3, 4].map(i => member(env.wire, i)));
    assert.equal(shares.reduce((sum, m) => sum + m.claimableUsdc, 0n) + state.unallocatedUsdc, cash);
    assert.equal(state.principalLoss, 900_000_000n - shares.slice(2).reduce((sum, m) => sum + m.principalAllocated, 0n));
    assert.ok(state.obligationUncollected > 0n);
    assert.equal(shares[0].lockedEth + shares[1].lockedEth, 0n);
  });
});
