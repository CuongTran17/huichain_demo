import assert from "node:assert/strict";
import { describe, it } from "node:test";
import hre from "hardhat";

const { viem, networkHelpers } = await hre.network.create();

async function wireWithFirstPayout(ratio = 10000) {
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
  for (let i = 0; i < 5; i++) await wire.write.contribute([], { account: wallets[i].account });
  await wire.write.advance();
  for (let i = 0; i < 5; i++) await wire.write.bid([i === 0 ? 2000 : 0], { account: wallets[i].account });
  await wire.write.advance();
  await wire.write.claimPayout([], { account: wallets[0].account, value: await wire.read.requiredCollateral() });
  await wire.write.advance();
  return { wallets, token, route, wire };
}

async function freezeFirst(ratio = 10000) {
  const env = await wireWithFirstPayout(ratio);
  for (let i = 1; i < 5; i++) await env.wire.write.contribute([], { account: env.wallets[i].account });
  await networkHelpers.time.increase(301);
  await env.wire.write.advance();
  return env;
}

describe("RoscaDemo liquidation", () => {
  it("trigger has no grace, sells only ETH needed and leaves a real zero debt", async () => {
    const { wire, token } = await freezeFirst(20000);
    const before = await token.read.balanceOf([wire.address]) as bigint;
    const quote = await wire.read.previewLiquidation([0]) as { mode: number; ethIn: bigint; usdcOut: bigint; blockNumber: bigint };
    assert.equal(quote.mode, 0);
    assert.equal(quote.usdcOut, 400_000_000n);
    await wire.write.liquidate([0, quote.blockNumber]);
    const member = await wire.read.getMember([0]) as { remainingDebt: bigint; lockedEth: bigint; claimableEth: bigint; liquidationProcessed: boolean };
    assert.equal(member.remainingDebt, 0n);
    assert.equal(member.liquidationProcessed, true);
    assert.ok(member.claimableEth > 0n);
    assert.equal((await token.read.balanceOf([wire.address]) as bigint) - before, 400_000_000n);
    await assert.rejects(wire.write.liquidate([0, quote.blockNumber]));
  });

  it("records actual shortfall when all pledged ETH is insufficient", async () => {
    const { wire, token } = await freezeFirst(5000);
    const before = await token.read.balanceOf([wire.address]) as bigint;
    const quote = await wire.read.previewLiquidation([0]) as { mode: number; ethIn: bigint; usdcOut: bigint; blockNumber: bigint };
    assert.equal(quote.mode, 1);
    await wire.write.liquidate([0, quote.blockNumber]);
    const member = await wire.read.getMember([0]) as { remainingDebt: bigint; lockedEth: bigint; liquidationProcessed: boolean };
    assert.equal(member.liquidationProcessed, true);
    assert.equal(member.lockedEth, 0n);
    assert.ok(member.remainingDebt > 0n);
    assert.equal((await token.read.balanceOf([wire.address]) as bigint) - before, quote.usdcOut);
    assert.equal((await wire.read.getState() as { obligationUncollected: bigint }).obligationUncollected, member.remainingDebt);
  });

  it("rejects stale quote without losing the pledged ETH or changing debt", async () => {
    const { wire } = await freezeFirst();
    const quote = await wire.read.previewLiquidation([0]) as { blockNumber: bigint };
    await networkHelpers.mine(4);
    await assert.rejects(wire.write.liquidate([0, quote.blockNumber]));
    const member = await wire.read.getMember([0]) as { remainingDebt: bigint; lockedEth: bigint; liquidationProcessed: boolean };
    assert.equal(member.remainingDebt, 400_000_000n);
    assert.ok(member.lockedEth > 0n);
    assert.equal(member.liquidationProcessed, false);
  });

  it("nontrigger paid member may repay partially within grace and reclaim ETH on full repayment", async () => {
    const { wire, wallets, token } = await wireWithFirstPayout();
    for (let i = 0; i < 5; i++) await wire.write.contribute([], { account: wallets[i].account });
    await wire.write.advance();
    for (let i = 1; i < 5; i++) await wire.write.bid([i === 1 ? 2000 : 0], { account: wallets[i].account });
    await wire.write.advance();
    await wire.write.claimPayout([], { account: wallets[1].account, value: await wire.read.requiredCollateral() });
    await wire.write.advance();
    for (let i = 1; i < 5; i++) await wire.write.contribute([], { account: wallets[i].account });
    await networkHelpers.time.increase(301);
    await wire.write.advance();
    await assert.rejects(wire.write.repay([1n], { account: wallets[0].account }));
    await wire.write.repay([50_000_000n], { account: wallets[1].account });
    assert.equal((await wire.read.getMember([1]) as { remainingDebt: bigint }).remainingDebt, 150_000_000n);
    await wire.write.repay([150_000_000n], { account: wallets[1].account });
    const member = await wire.read.getMember([1]) as { remainingDebt: bigint; lockedEth: bigint; claimableEth: bigint };
    assert.equal(member.remainingDebt, 0n);
    assert.equal(member.lockedEth, 0n);
    assert.ok(member.claimableEth > 0n);
    assert.ok((await token.read.balanceOf([wire.address]) as bigint) > 0n);
  });

  it("swap failure keeps settlement open and permits retry after route recovers", async () => {
    const { wire, route } = await freezeFirst();
    const quote = await wire.read.previewLiquidation([0]) as { blockNumber: bigint };
    await route.write.setFail([true]);
    await assert.rejects(wire.write.liquidate([0, quote.blockNumber]));
    assert.equal((await wire.read.getMember([0]) as { liquidationProcessed: boolean }).liquidationProcessed, false);
    await route.write.setFail([false]);
    const fresh = await wire.read.previewLiquidation([0]) as { blockNumber: bigint };
    await wire.write.liquidate([0, fresh.blockNumber]);
    assert.equal((await wire.read.getMember([0]) as { liquidationProcessed: boolean }).liquidationProcessed, true);
  });
});
