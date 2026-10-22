import assert from "node:assert/strict";
import { describe, it } from "node:test";
import hre from "hardhat";

const { viem } = await hre.network.create();

describe("RoscaMath", () => {
  it("accepts the six-member first claim's 150-day interest and rejects 151 days", async () => {
    const math = await viem.deployContract("MathHarness");
    assert.equal(await math.read.annualInterest([500_000_000n, 2000, 150]), 41_095_890n);
    await assert.rejects(math.read.annualInterest([500_000_000n, 2000, 151]));
    await assert.rejects(math.read.annualInterest([500_000_000n, 2001, 150]));
  });
  it("first bid at 20 percent keeps 26.301369 USDC", async () => {
    const math = await viem.deployContract("MathHarness");
    const interest = await math.read.annualInterest([400_000_000n, 2000, 120]);
    assert.equal(interest, 26_301_369n);
    assert.equal(500_000_000n - interest, 473_698_631n);
  });

  it("last period has no interest or new ETH collateral", async () => {
    const math = await viem.deployContract("MathHarness");
    assert.equal(await math.read.annualInterest([0n, 2000, 0]), 0n);
    assert.equal(await math.read.collateralWei([0n, 10000, 2_000_000_000n, 10n ** 18n]), 0n);
  });

  it("collateral is calculated from full debt and rounded up", async () => {
    const math = await viem.deployContract("MathHarness");
    assert.equal(await math.read.collateralWei([400_000_000n, 10000, 2_000_000_000n, 10n ** 18n]), 200_000_000_000_000_000n);
    assert.equal(await math.read.collateralWei([1n, 10001, 3n, 10n]), 4n);
  });

  it("allocates every micro USDC by largest remainder and member ID", async () => {
    const math = await viem.deployContract("MathHarness");
    assert.deepEqual(await math.read.allocate([7n, [1n, 1n, 1n, 0n, 0n]]), [3n, 2n, 2n, 0n, 0n]);
    assert.deepEqual(await math.read.allocate([100n, [0n, 1n, 2n, 0n, 0n]]), [0n, 33n, 67n, 0n, 0n]);
  });

  it("allocates six-way remainders exactly and accepts all-zero weights only for zero cash", async () => {
    const math = await viem.deployContract("MathHarness");
    assert.deepEqual(await math.read.allocateSix([8n, [1n, 1n, 1n, 1n, 1n, 1n]]), [2n, 2n, 1n, 1n, 1n, 1n]);
    assert.deepEqual(await math.read.allocateSix([0n, [0n, 0n, 0n, 0n, 0n, 0n]]), [0n, 0n, 0n, 0n, 0n, 0n]);
    await assert.rejects(math.read.allocateSix([1n, [0n, 0n, 0n, 0n, 0n, 0n]]));
  });

  it("rejects rate, ratio and reserve values outside valid bounds", async () => {
    const math = await viem.deployContract("MathHarness");
    await assert.rejects(math.read.annualInterest([400_000_000n, 2001, 120]));
    await assert.rejects(math.read.annualInterest([400_000_000n, 2000, 151]));
    await assert.rejects(math.read.collateralWei([400_000_000n, 0, 2_000_000_000n, 10n ** 18n]));
    await assert.rejects(math.read.collateralWei([400_000_000n, 100001, 2_000_000_000n, 10n ** 18n]));
    await assert.rejects(math.read.collateralWei([400_000_000n, 10000, 0n, 10n ** 18n]));
  });
});
