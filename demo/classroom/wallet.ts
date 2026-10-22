import { encodeFunctionData, toHex, type Address, type PublicClient } from "viem";
import { classroomAbi } from "../shared/classroom-abi.js";
import { SEPOLIA, USDC } from "../shared/config.js";
import { readClassroomSnapshot, tokenAbi, type ClassroomSnapshot } from "./chain.js";
import { availableActions, FULL_WIRE_ALLOWANCE, MEMBER_COUNT, memberIndex, type Action } from "./model.js";

export type Provider = { request(args: { method: string; params?: unknown[] }): Promise<unknown>;
  on?(event: string, listener: (...args: unknown[]) => void): void;
  removeListener?(event: string, listener: (...args: unknown[]) => void): void };

export async function assertWalletContext(provider: Provider, expected: Address): Promise<void> {
  const [chain, accounts] = await Promise.all([
    provider.request({ method: "eth_chainId" }), provider.request({ method: "eth_accounts" }),
  ]);
  if (Number(chain) !== SEPOLIA) throw new Error("Hãy chuyển ví sang Sepolia rồi thử lại.");
  if (!Array.isArray(accounts) || String(accounts[0]).toLowerCase() !== expected.toLowerCase())
    throw new Error("Ví đã đổi tài khoản. Tải lại trạng thái trước khi ký.");
}

export async function connectWallet(provider: Provider): Promise<Address> {
  const accounts = await provider.request({ method: "eth_requestAccounts" });
  if (!Array.isArray(accounts) || !accounts[0]) throw new Error("Ví chưa trả địa chỉ tài khoản.");
  const account = String(accounts[0]) as Address;
  await assertWalletContext(provider, account);
  return account;
}

export async function sendAction(provider: Provider, client: PublicClient, snapshot: ClassroomSnapshot,
  deployBlock: bigint, account: Address, action: Action, options: { bidBps?: number; memberId?: number } = {}) {
  await assertWalletContext(provider, account);
  const fresh = await readClassroomSnapshot(client, snapshot.wire, deployBlock);
  if (!availableActions(fresh, account).includes(action)) throw new Error("Bước này đã đổi hoặc ví không có quyền. Hãy làm mới.");
  const id = memberIndex(fresh, account);
  let to: Address = fresh.wire;
  let data: `0x${string}`;
  let value = 0n;
  if (action === "approve") {
    to = USDC;
    data = encodeFunctionData({ abi: tokenAbi, functionName: "approve", args: [fresh.wire, FULL_WIRE_ALLOWANCE] });
  } else {
    let name: "requestJoin" | "start" | "advance" | "contribute" | "bid" | "claimPayout" | "repay" | "liquidate" | "finalizeSettlement" | "withdrawUsdc" | "withdrawEth";
    let args: readonly unknown[] = [];
    if (action === "request") name = "requestJoin";
    else if (action === "start") name = "start";
    else if (action === "advance") name = "advance";
    else if (action === "contribute") name = "contribute";
    else if (action === "bid") {
      if (![0, 500, 1000, 1500, 2000].includes(options.bidBps ?? -1)) throw new Error("Chọn một trong năm mức lãi.");
      name = "bid"; args = [options.bidBps];
    } else if (action === "claim") {
      name = "claimPayout";
      value = await client.readContract({ address: fresh.wire, abi: classroomAbi, functionName: "requiredCollateral" });
    } else if (action === "repay") { name = "repay"; args = [fresh.members[id].remainingDebt]; }
    else if (action === "liquidate") {
      if (options.memberId === undefined) throw new Error("Chọn người cần thanh lý.");
      const quote = await client.readContract({ address: fresh.wire, abi: classroomAbi,
        functionName: "previewLiquidation", args: [options.memberId] });
      name = "liquidate"; args = [options.memberId, quote.blockNumber];
    } else if (action === "finalize") name = "finalizeSettlement";
    else if (action === "withdrawUsdc") name = "withdrawUsdc";
    else name = "withdrawEth";
    data = encodeFunctionData({ abi: classroomAbi, functionName: name, args } as never);
  }
  await client.call({ account, to, data, value });
  await assertWalletContext(provider, account);
  const hash = await provider.request({ method: "eth_sendTransaction", params: [{ from: account, to, data, value: toHex(value) }] });
  if (typeof hash !== "string" || !/^0x[0-9a-f]{64}$/i.test(hash)) throw new Error("Ví không trả hash giao dịch hợp lệ.");
  return hash as `0x${string}`;
}

export async function approveRepay(provider: Provider, client: PublicClient, snapshot: ClassroomSnapshot,
  deployBlock: bigint, account: Address): Promise<`0x${string}`> {
  await assertWalletContext(provider, account);
  const fresh = await readClassroomSnapshot(client, snapshot.wire, deployBlock);
  if (!availableActions(fresh, account).includes("repay")) throw new Error("Không còn quyền trả trong giai đoạn này.");
  const id = memberIndex(fresh, account);
  const amount = fresh.members[id].remainingDebt;
  const data = encodeFunctionData({ abi: tokenAbi, functionName: "approve", args: [fresh.wire, amount] });
  await client.call({ account, to: USDC, data });
  await assertWalletContext(provider, account);
  return await provider.request({ method: "eth_sendTransaction", params: [{ from: account, to: USDC, data }] }) as `0x${string}`;
}

export async function approveApplicant(provider: Provider, client: PublicClient, snapshot: ClassroomSnapshot,
  deployBlock: bigint, account: Address, applicant: Address): Promise<`0x${string}`> {
  await assertWalletContext(provider, account);
  const fresh = await readClassroomSnapshot(client, snapshot.wire, deployBlock);
  if (fresh.state.phase !== 0 || fresh.memberCount >= MEMBER_COUNT || account.toLowerCase() !== fresh.host.toLowerCase() ||
    !fresh.applicants.some(value => value.toLowerCase() === applicant.toLowerCase())) throw new Error("Yêu cầu tham gia không còn hợp lệ.");
  const data = encodeFunctionData({ abi: classroomAbi, functionName: "approveJoin", args: [applicant] });
  await client.call({ account, to: fresh.wire, data });
  await assertWalletContext(provider, account);
  return await provider.request({ method: "eth_sendTransaction", params: [{ from: account, to: fresh.wire, data }] }) as `0x${string}`;
}
