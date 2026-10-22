import assert from "node:assert/strict";
import { describe, it } from "node:test";
import hre from "hardhat";

const { viem, networkHelpers } = await hre.network.create();

async function fixture() {
  const wallets = await viem.getWalletClients();
  const token = await viem.deployContract("TestTokens");
  const route = await viem.deployContract("TestV2", [token.address]);
  await token.write.mint([route.address, 1_000_000_000_000n]);
  const wire = await viem.deployContract("RoscaClassroom", [wallets[0].account.address, token.address, route.address, route.address]);
  for (let id = 0; id < 6; id++) {
    await wire.write.requestJoin([], { account: wallets[id].account });
    await wire.write.approveJoin([wallets[id].account.address]);
    await token.write.mint([wallets[id].account.address, 1_000_000_000n]);
    await token.write.approve([wire.address, 1_000_000_000n], { account: wallets[id].account });
  }
  await wire.write.start();
  return { wallets, token, route, wire };
}

async function payout(env: Awaited<ReturnType<typeof fixture>>, winner: number) {
  const { wallets, wire } = env;
  for (let id = 0; id < 6; id++) await wire.write.contribute([], { account: wallets[id].account });
  await wire.write.advance();
  await wire.write.bid([2000], { account: wallets[winner].account });
  await networkHelpers.time.increase(301);
  await wire.write.advance();
  await wire.write.claimPayout([], { account: wallets[winner].account, value: await wire.read.requiredCollateral() });
  await wire.write.advance();
}

describe("six-member settlement", () => {
  it("liquidates one paid defaulter once and accounts for every USDC and ETH", async () => {
    const env = await fixture();
    const { wallets, token, wire } = env;
    await payout(env, 0);
    for (let id = 1; id < 6; id++) await wire.write.contribute([], { account: wallets[id].account });
    await networkHelpers.time.increase(301);
    await wire.write.advance();
    assert.equal((await wire.read.getState() as { triggerMask: number }).triggerMask, 1);
    const locked = (await wire.read.getMember([0]) as { lockedEth: bigint }).lockedEth;
    const quote = await wire.read.previewLiquidation([0]) as { blockNumber: bigint };
    await wire.write.liquidate([0, quote.blockNumber]);
    await assert.rejects(wire.write.liquidate([0, quote.blockNumber]));
    await wire.write.finalizeSettlement();
    const member = await wire.read.getMember([0]) as { ethSold: bigint; claimableEth: bigint };
    assert.equal(member.ethSold + member.claimableEth, locked);
    const cash = await token.read.balanceOf([wire.address]);
    const state = await wire.read.getState() as { unallocatedUsdc: bigint; usedInterest: bigint; defaultInterestUsed: bigint; commonInterestUsed: bigint };
    let claims = 0n;
    for (let id = 0; id < 6; id++) claims += (await wire.read.getMember([id]) as { claimableUsdc: bigint }).claimableUsdc;
    assert.equal(claims + state.unallocatedUsdc, cash);
    assert.equal(state.usedInterest, state.defaultInterestUsed + state.commonInterestUsed);
  });

  it("settles two previously paid defaulters after a reserve shock without inventing proceeds", async () => {
    const env = await fixture();
    const { wallets, token, route, wire } = env;
    await payout(env, 0);
    await payout(env, 1);
    const locked = [] as bigint[];
    for (let id = 0; id < 2; id++) locked.push((await wire.read.getMember([id]) as { lockedEth: bigint }).lockedEth);
    for (let id = 2; id < 6; id++) await wire.write.contribute([], { account: wallets[id].account });
    await networkHelpers.time.increase(301);
    await wire.write.advance();
    assert.equal((await wire.read.getState() as { triggerMask: number }).triggerMask, 3);
    await route.write.setReserves([800_000_000n, 1_000_000_000_000_000_000n]);
    await assert.rejects(wire.write.finalizeSettlement());
    for (let id = 0; id < 2; id++) {
      const quote = await wire.read.previewLiquidation([id]) as { blockNumber: bigint };
      await wire.write.liquidate([id, quote.blockNumber]);
      await assert.rejects(wire.write.liquidate([id, quote.blockNumber]));
    }
    const cash = await token.read.balanceOf([wire.address]);
    await wire.write.finalizeSettlement();
    const state = await wire.read.getState() as { unallocatedUsdc: bigint; usedInterest: bigint; defaultInterestUsed: bigint; commonInterestUsed: bigint; principalLoss: bigint };
    let claims = 0n;
    for (let id = 0; id < 6; id++) {
      const member = await wire.read.getMember([id]) as { claimableUsdc: bigint; ethSold: bigint; claimableEth: bigint; lockedEth: bigint };
      claims += member.claimableUsdc;
      if (id < 2) assert.equal(member.ethSold + member.claimableEth + member.lockedEth, locked[id]);
    }
    assert.equal(claims + state.unallocatedUsdc, cash);
    assert.equal(state.usedInterest, state.defaultInterestUsed + state.commonInterestUsed);
    assert.ok(state.principalLoss > 0n);
  });

  it("lets a non-defaulting paid member repay during grace and reclaim ETH", async () => {
    const env = await fixture();
    const { wallets, wire } = env;
    await payout(env, 0);
    await payout(env, 1);
    for (let id = 1; id < 6; id++) await wire.write.contribute([], { account: wallets[id].account });
    await networkHelpers.time.increase(301);
    await wire.write.advance();
    const debt = (await wire.read.getMember([1]) as { remainingDebt: bigint }).remainingDebt;
    await wire.write.repay([debt], { account: wallets[1].account });
    const member = await wire.read.getMember([1]) as { remainingDebt: bigint; lockedEth: bigint; claimableEth: bigint };
    assert.equal(member.remainingDebt, 0n);
    assert.equal(member.lockedEth, 0n);
    assert.ok(member.claimableEth > 0n);
    await networkHelpers.time.increase(301);
    await assert.rejects(wire.write.repay([1n], { account: wallets[1].account }));
    const quote = await wire.read.previewLiquidation([0]) as { blockNumber: bigint };
    await wire.write.liquidate([0, quote.blockNumber]);
    await wire.write.finalizeSettlement();
  });

  it("rejects stale quotes and a failing route without consuming ETH", async () => {
    const env = await fixture();
    const { wallets, route, wire } = env;
    await payout(env, 0);
    for (let id = 1; id < 6; id++) await wire.write.contribute([], { account: wallets[id].account });
    await networkHelpers.time.increase(301);
    await wire.write.advance();
    const quote = await wire.read.previewLiquidation([0]) as { blockNumber: bigint };
    await networkHelpers.mine(4);
    await assert.rejects(wire.write.liquidate([0, quote.blockNumber]));
    await route.write.setFail([true]);
    const fresh = await wire.read.previewLiquidation([0]) as { blockNumber: bigint };
    await assert.rejects(wire.write.liquidate([0, fresh.blockNumber]));
    const member = await wire.read.getMember([0]) as { liquidationProcessed: boolean; lockedEth: bigint };
    assert.equal(member.liquidationProcessed, false);
    assert.ok(member.lockedEth > 0n);
    await route.write.setFail([false]);
    const recovered = await wire.read.previewLiquidation([0]) as { blockNumber: bigint };
    await wire.write.liquidate([0, recovered.blockNumber]);
  });
});
