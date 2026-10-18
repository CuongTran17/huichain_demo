import assert from "node:assert/strict";
import { describe, it } from "node:test";
import hre from "hardhat";

const { viem } = await hre.network.create();

async function fixture() {
  const wallets = await viem.getWalletClients();
  const token = await viem.deployContract("TestTokens");
  const route = await viem.deployContract("TestV2", [token.address]);
  const wire = await viem.deployContract("RoscaClassroom", [wallets[0].account.address, token.address, route.address, route.address]);
  return { wallets, wire };
}

describe("classroom access", () => {
  it("only the host admits five distinct applicants; requests never reserve a slot", async () => {
    const { wallets, wire } = await fixture();
    await wire.write.requestJoin([], { account: wallets[0].account });
    await wire.write.requestJoin([], { account: wallets[0].account });
    assert.equal(await wire.read.memberCount(), 0);
    await assert.rejects(wire.write.approveJoin([wallets[0].account.address], { account: wallets[1].account }));
    for (let i = 0; i < 5; i++) {
      if (i > 0) await wire.write.requestJoin([], { account: wallets[i].account });
      await wire.write.approveJoin([wallets[i].account.address]);
      assert.equal(await wire.read.memberIdPlusOne([wallets[i].account.address]), i + 1);
    }
    assert.equal(await wire.read.memberCount(), 5);
    await assert.rejects(wire.write.approveJoin([wallets[0].account.address]));
    await wire.write.requestJoin([], { account: wallets[5].account });
    await assert.rejects(wire.write.approveJoin([wallets[5].account.address]));
    await wire.write.start();
    await assert.rejects(wire.write.requestJoin([], { account: wallets[6].account }));
    await assert.rejects(wire.write.approveJoin([wallets[6].account.address]));
  });

  it("does not start early and only host advances the five-minute round", async () => {
    const { wallets, wire } = await fixture();
    await assert.rejects(wire.write.start());
    for (let i = 0; i < 5; i++) {
      await wire.write.requestJoin([], { account: wallets[i].account });
      await wire.write.approveJoin([wallets[i].account.address]);
    }
    await assert.rejects(wire.write.start([], { account: wallets[1].account }));
    await wire.write.start();
    await assert.rejects(wire.write.advance([], { account: wallets[1].account }));
  });
});
