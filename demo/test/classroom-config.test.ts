import assert from "node:assert/strict";
import { it } from "node:test";
import { assertSixMemberBuildTarget, parseClassroomConfig, resolveClassroomConfig, wireLink } from "../classroom/config.js";

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

it("blocks a six-member build from targeting the historical five-member contract", () => {
  assert.throws(() => assertSixMemberBuildTarget("0xa28B310Cc345E693bc468829b08e1f08a50d6c47"), /năm người|5 người/);
  assert.doesNotThrow(() => assertSixMemberBuildTarget("0x1111111111111111111111111111111111111111"));
});

it("opens a new wire from a shared link without changing the default wire", () => {
  const defaults = { wire: "0x1234567890123456789012345678901234567890", deployBlock: "42", rpcUrl: "https://rpc.sepolia.org" };
  const other = "0x1111111111111111111111111111111111111111";
  const url = wireLink("https://example.org/display", other, 123n);
  assert.equal(url, `https://example.org/display?wire=${other}&block=123`);
  assert.deepEqual(resolveClassroomConfig(defaults, new URL(url).search), { wire: other, deployBlock: 123n, rpcUrl: defaults.rpcUrl });
  assert.equal(resolveClassroomConfig(defaults, "").wire, defaults.wire);
  assert.throws(() => resolveClassroomConfig(defaults, `?wire=${other}`), /block/i);
  assert.throws(() => resolveClassroomConfig(defaults, "?wire=0xabc&block=123"), /contract/i);
  assert.throws(() => resolveClassroomConfig(defaults, `?wire=${other}&block=0`), /block/i);
  assert.throws(() => resolveClassroomConfig(defaults, `?wire=0xa28B310Cc345E693bc468829b08e1f08a50d6c47&block=123`), /năm người|5 người/);
});
