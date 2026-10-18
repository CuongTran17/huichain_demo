import assert from "node:assert/strict";
import { it } from "node:test";
import { parseClassroomConfig } from "../classroom/config.js";

it("requires an explicit Sepolia contract and deployment block", () => {
  assert.throws(() => parseClassroomConfig({}));
  assert.throws(() => parseClassroomConfig({ wire: "0xabc", deployBlock: "42" }));
  assert.throws(() => parseClassroomConfig({ wire: "0x1234567890123456789012345678901234567890", deployBlock: "-1" }));
  assert.deepEqual(parseClassroomConfig({
    wire: "0x1234567890123456789012345678901234567890", deployBlock: "42", rpcUrl: "https://rpc.sepolia.org",
  }), {
    wire: "0x1234567890123456789012345678901234567890", deployBlock: 42n, rpcUrl: "https://rpc.sepolia.org",
  });
});
