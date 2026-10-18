import assert from "node:assert/strict";
import { it } from "node:test";
import { assertWalletContext } from "../classroom/wallet.js";

it("refuses signatures after a wallet account or network switch", async () => {
  const account = "0x1111111111111111111111111111111111111111";
  const provider = { request: async ({ method }: { method: string }) =>
    method === "eth_chainId" ? "0xaa36a7" : [account] };
  await assertWalletContext(provider, account);
  await assert.rejects(assertWalletContext({ request: async ({ method }: { method: string }) =>
    method === "eth_chainId" ? "0x1" : [account] }, account));
  await assert.rejects(assertWalletContext({ request: async ({ method }: { method: string }) =>
    method === "eth_chainId" ? "0xaa36a7" : ["0x2222222222222222222222222222222222222222"] }, account));
});
