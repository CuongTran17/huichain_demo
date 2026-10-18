import assert from "node:assert/strict";
import { describe, it } from "node:test";
import hre from "hardhat";

const { viem, networkHelpers } = await hre.network.create();

type State = { phase: number; deadline: bigint; currentCandidate: number; triggerMask: number; freezeReason: number };
type Member = { received: boolean; remainingDebt: bigint };
async function readState(wire: any): Promise<State> { return await wire.read.getState() as State; }
async function readMember(wire: any, id: number): Promise<Member> { return await wire.read.getMember([id]) as Member; }

async function fixture() {
  const wallets = await viem.getWalletClients();
  const addresses = wallets.slice(0, 5).map(w => w.account.address) as [`0x${string}`, `0x${string}`, `0x${string}`, `0x${string}`, `0x${string}`];
  const token = await viem.deployContract("TestTokens");
  const route = await viem.deployContract("TestV2", [token.address]);
  const wire = await viem.deployContract("RoscaDemo", [addresses, 10000, token.address, route.address, route.address]);
  for (let i = 0; i < 5; i++) {
    await token.write.mint([addresses[i], 1_000_000_000n]);
    await token.write.approve([wire.address, 1_000_000_000n], { account: wallets[i].account });
  }
  return { wallets, addresses, token, route, wire };
}

async function joined() {
  const env = await fixture();
  for (let i = 0; i < 5; i++) await env.wire.write.join([], { account: env.wallets[i].account });
  await env.wire.write.start();
  return env;
}

async function contributed() {
  const env = await joined();
  for (let i = 0; i < 5; i++) await env.wire.write.contribute([], { account: env.wallets[i].account });
  await env.wire.write.advance();
  return env;
}

describe("RoscaDemo lifecycle", () => {
  it("requires all five members to join before starting", async () => {
    const { wire, wallets } = await fixture();
    await assert.rejects(wire.write.start());
    await assert.rejects(wire.write.join([], { account: wallets[5].account }));
    for (let i = 0; i < 5; i++) await wire.write.join([], { account: wallets[i].account });
    await wire.write.start();
    assert.equal((await readState(wire)).phase, 1);
  });

  it("pot stays 500 USDC while prior interest is retained; paid member cannot bid again", async () => {
    const { wire, wallets, token } = await contributed();
    for (let i = 0; i < 5; i++) await wire.write.bid([i === 0 ? 2000 : 0], { account: wallets[i].account });
    await wire.write.advance();
    assert.equal((await readState(wire)).currentCandidate, 0);
    const required = await wire.read.requiredCollateral();
    await wire.write.claimPayout([], { account: wallets[0].account, value: required });
    assert.equal(await token.read.balanceOf([wire.address]), 26_301_369n);
    assert.equal((await readMember(wire, 0)).remainingDebt, 400_000_000n);
    await wire.write.advance();
    for (let i = 0; i < 5; i++) await wire.write.contribute([], { account: wallets[i].account });
    assert.equal((await readMember(wire, 0)).remainingDebt, 300_000_000n);
    await wire.write.advance();
    await assert.rejects(wire.write.bid([2000], { account: wallets[0].account }));
    assert.equal(await token.read.balanceOf([wire.address]), 526_301_369n);
  });

  it("breaks tied bids by ID, independent of transaction order", async () => {
    const { wire, wallets } = await contributed();
    for (const i of [4, 3, 2, 1, 0]) await wire.write.bid([i < 2 ? 1000 : 0], { account: wallets[i].account });
    await wire.write.advance();
    assert.equal((await readState(wire)).currentCandidate, 0);
  });

  it("rejects duplicate contribution and wrong ETH; claim is atomic", async () => {
    const { wire, wallets, token } = await joined();
    await wire.write.contribute([], { account: wallets[0].account });
    await assert.rejects(wire.write.contribute([], { account: wallets[0].account }));
    for (let i = 1; i < 5; i++) await wire.write.contribute([], { account: wallets[i].account });
    await wire.write.advance();
    for (let i = 0; i < 5; i++) await wire.write.bid([0], { account: wallets[i].account });
    await wire.write.advance();
    await assert.rejects(wire.write.claimPayout([], { account: wallets[0].account, value: 0n }));
    assert.equal((await readMember(wire, 0)).received, false);
    assert.equal(await token.read.balanceOf([wire.address]), 500_000_000n);
  });

  it("freezes partial-round cash and all missing contributors at the deadline", async () => {
    const { wire, wallets, token } = await joined();
    for (let i = 0; i < 3; i++) await wire.write.contribute([], { account: wallets[i].account });
    await networkHelpers.time.increase(301);
    await wire.write.advance();
    const state = await readState(wire);
    assert.equal(state.phase, 4);
    assert.equal(state.triggerMask, 0b11000);
    assert.equal(await token.read.balanceOf([wire.address]), 300_000_000n);
    await assert.rejects(wire.write.contribute([], { account: wallets[3].account }));
  });

  it("moves to the next candidate only after the claim window expires", async () => {
    const { wire, wallets } = await contributed();
    for (let i = 0; i < 5; i++) await wire.write.bid([i === 0 ? 2000 : 0], { account: wallets[i].account });
    await wire.write.advance();
    await assert.rejects(wire.write.advance());
    await networkHelpers.time.increase(301);
    await assert.rejects(wire.write.claimPayout([], { account: wallets[0].account, value: await wire.read.requiredCollateral() }));
    await wire.write.advance();
    assert.equal((await readState(wire)).currentCandidate, 1);
  });

  it("stops with no false defaulter when nobody bids", async () => {
    const { wire } = await contributed();
    await networkHelpers.time.increase(301);
    await wire.write.advance();
    const state = await readState(wire);
    assert.equal(state.phase, 4);
    assert.equal(state.triggerMask, 0);
    assert.equal(state.freezeReason, 2);
  });

  it("rejects a contribution included at or after the deadline", async () => {
    const { wire, wallets } = await joined();
    const deadline = (await readState(wire)).deadline;
    await networkHelpers.time.setNextBlockTimestamp(Number(deadline));
    await assert.rejects(wire.write.contribute([], { account: wallets[0].account }));
  });

  it("completes five rounds without rebidding or new ETH on the last claim", async () => {
    const { wire, wallets, token } = await joined();
    for (let period = 0; period < 5; period++) {
      for (let i = 0; i < 5; i++) await wire.write.contribute([], { account: wallets[i].account });
      await wire.write.advance();
      for (let i = period; i < 5; i++) await wire.write.bid([0], { account: wallets[i].account });
      await wire.write.advance();
      assert.equal((await readState(wire)).currentCandidate, period);
      const required = await wire.read.requiredCollateral();
      if (period === 4) assert.equal(required, 0n);
      await wire.write.claimPayout([], { account: wallets[period].account, value: required });
      await wire.write.advance();
    }
    assert.equal((await readState(wire)).phase, 5);
    assert.equal(await token.read.balanceOf([wire.address]), 0n);
    for (let i = 0; i < 5; i++) assert.equal((await readMember(wire, i)).remainingDebt, 0n);
  });
});
