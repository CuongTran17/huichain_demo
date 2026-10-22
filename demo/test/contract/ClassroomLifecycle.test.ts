import assert from "node:assert/strict";
import { describe, it } from "node:test";
import hre from "hardhat";

const { viem, networkHelpers } = await hre.network.create();

async function started() {
  const wallets = await viem.getWalletClients();
  const token = await viem.deployContract("TestTokens");
  const route = await viem.deployContract("TestV2", [token.address]);
  await token.write.mint([route.address, 1_000_000_000_000n]);
  const wire = await viem.deployContract("RoscaClassroom", [wallets[0].account.address, token.address, route.address, route.address]);
  for (let i = 0; i < 6; i++) {
    await wire.write.requestJoin([], { account: wallets[i].account });
    await wire.write.approveJoin([wallets[i].account.address]);
    await token.write.mint([wallets[i].account.address, 600_000_000n]);
    await token.write.approve([wire.address, 600_000_000n], { account: wallets[i].account });
  }
  await wire.write.start();
  return { wallets, token, route, wire };
}

describe("classroom economics", () => {
  it("completes six payouts, requires no ETH on the last claim, and settles once", async () => {
    const { wallets, wire, token } = await started();
    for (let period = 0; period < 6; period++) {
      for (let id = 0; id < 6; id++) await wire.write.contribute([], { account: wallets[id].account });
      await wire.write.advance();
      await wire.write.bid([2000], { account: wallets[period].account });
      await networkHelpers.time.increase(301);
      await wire.write.advance();
      const needed = await wire.read.requiredCollateral();
      if (period === 5) assert.equal(needed, 0n);
      await wire.write.claimPayout([], { account: wallets[period].account, value: needed });
      await wire.write.advance();
    }
    assert.equal((await wire.read.getState() as { phase: number; period: number }).period, 5);
    assert.equal((await wire.read.getMember([5]) as { remainingDebt: bigint; lockedEth: bigint }).remainingDebt, 0n);
    const cash = await token.read.balanceOf([wire.address]);
    await wire.write.finalizeSettlement();
    let claims = 0n;
    for (let id = 0; id < 6; id++) {
      const member = await wire.read.getMember([id]) as { claimableUsdc: bigint; lockedEth: bigint; claimableEth: bigint };
      claims += member.claimableUsdc;
      assert.equal(member.lockedEth, 0n);
      if (id < 5) assert.ok(member.claimableEth > 0n);
    }
    assert.equal(claims, cash);
    await assert.rejects(wire.write.finalizeSettlement());
  });
  it("accepts only the five preset bids, retains first interest and locks 180 percent", async () => {
    const { wallets, token, wire } = await started();
    for (let i = 0; i < 6; i++) await wire.write.contribute([], { account: wallets[i].account });
    await wire.write.advance();
    for (const bad of [1, 499, 2001]) await assert.rejects(wire.write.bid([bad], { account: wallets[0].account }));
    for (let i = 5; i >= 0; i--) await wire.write.bid([i < 2 ? 2000 : 0], { account: wallets[i].account });
    await wire.write.advance();
    const state = await wire.read.getState() as { currentCandidate: number };
    assert.equal(state.currentCandidate, 0);
    assert.equal(await wire.read.requiredCollateral(), 450_000_000_000_000_000n);
    await wire.write.claimPayout([], { account: wallets[0].account, value: 450_000_000_000_000_000n });
    assert.equal(await token.read.balanceOf([wallets[0].account.address]), 1_058_904_110n);
    assert.equal(await token.read.balanceOf([wire.address]), 41_095_890n);
    await wire.write.advance();
    for (let i = 0; i < 6; i++) await wire.write.contribute([], { account: wallets[i].account });
    await wire.write.advance();
    await assert.rejects(wire.write.bid([0], { account: wallets[0].account }));
  });

  it("freezes only after missed-contribution deadline, and host alone may advance", async () => {
    const { wallets, wire } = await started();
    for (let i = 0; i < 5; i++) await wire.write.contribute([], { account: wallets[i].account });
    await assert.rejects(wire.write.advance());
    await networkHelpers.time.increase(301);
    await assert.rejects(wire.write.advance([], { account: wallets[1].account }));
    await wire.write.advance();
    const state = await wire.read.getState() as { phase: number; triggerMask: number };
    assert.equal(state.phase, 4);
    assert.equal(state.triggerMask, 32);
  });

  it("lets only host sell defaulted collateral and settles real cash once", async () => {
    const { wallets, wire, token } = await started();
    for (let i = 0; i < 6; i++) await wire.write.contribute([], { account: wallets[i].account });
    await wire.write.advance();
    for (let i = 0; i < 6; i++) await wire.write.bid([i === 0 ? 2000 : 0], { account: wallets[i].account });
    await wire.write.advance();
    await wire.write.claimPayout([], { account: wallets[0].account, value: await wire.read.requiredCollateral() });
    await wire.write.advance();
    for (let i = 1; i < 6; i++) await wire.write.contribute([], { account: wallets[i].account });
    await networkHelpers.time.increase(301);
    await wire.write.advance();
    await assert.rejects(wire.write.repay([500_000_000n], { account: wallets[0].account }));
    const quote = await wire.read.previewLiquidation([0]) as { blockNumber: bigint };
    await assert.rejects(wire.write.liquidate([0, quote.blockNumber], { account: wallets[1].account }));
    await wire.write.liquidate([0, quote.blockNumber]);
    assert.equal((await wire.read.getMember([0]) as { remainingDebt: bigint }).remainingDebt, 0n);
    const before = await token.read.balanceOf([wire.address]) as bigint;
    await assert.rejects(wire.write.finalizeSettlement([], { account: wallets[1].account }));
    await wire.write.finalizeSettlement();
    await assert.rejects(wire.write.finalizeSettlement());
    const claimable = (await wire.read.getMember([1]) as { claimableUsdc: bigint }).claimableUsdc;
    assert.ok(claimable > 0n);
    await wire.write.withdrawUsdc([], { account: wallets[1].account });
    assert.equal(await token.read.balanceOf([wire.address]), before - claimable);
  });
});
