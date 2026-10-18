import { decodeEventLog, type Address, type PublicClient } from "viem";
import { classroomAbi } from "../shared/classroom-abi.js";
import { PAIR, USDC } from "../shared/config.js";

export const tokenAbi = [
  { type: "function", name: "balanceOf", stateMutability: "view", inputs: [{ name: "owner", type: "address" }], outputs: [{ type: "uint256" }] },
  { type: "function", name: "allowance", stateMutability: "view", inputs: [{ name: "owner", type: "address" }, { name: "spender", type: "address" }], outputs: [{ type: "uint256" }] },
  { type: "function", name: "approve", stateMutability: "nonpayable", inputs: [{ name: "spender", type: "address" }, { name: "amount", type: "uint256" }], outputs: [{ type: "bool" }] },
] as const;
const pairAbi = [
  { type: "function", name: "getReserves", stateMutability: "view", inputs: [], outputs: [{ type: "uint112" }, { type: "uint112" }, { type: "uint32" }] },
] as const;

export type State = {
  phase: number; period: number; deadline: bigint; currentCandidate: number; triggerMask: number;
  freezeReason: number; retainedInterest: bigint; usedInterest: bigint; distributedInterest: bigint;
  principalLoss: bigint; obligationUncollected: bigint; defaultInterestUsed: bigint;
  commonInterestUsed: bigint; unallocatedUsdc: bigint;
};
export type Member = {
  account: Address; joined: boolean; contributedThisPeriod: boolean; received: boolean;
  bidSubmitted: boolean; annualBps: number; totalContributed: bigint; remainingDebt: bigint;
  lockedEth: bigint; winningInterest: bigint; payoutPeriod: number; claimableUsdc: bigint;
  claimableEth: bigint; repaidUsdc: bigint; recoveredUsdc: bigint; ethSold: bigint;
  liquidationProcessed: boolean; principalAllocated: bigint; interestAllocated: bigint;
};
export type HistoryItem = { event: string; blockNumber: bigint; transactionHash: `0x${string}`; args: Record<string, unknown> };
export type ClassroomSnapshot = {
  blockNumber: bigint; blockTimestamp: bigint; state: State; members: Member[];
  applicants: Address[]; host: Address; memberCount: number; history: HistoryItem[];
  settlementFinalized: boolean;
  usdcBalance: bigint; ethBalance: bigint; reserveUsdc: bigint; reserveWeth: bigint;
  claimEth?: bigint;
  readiness: { usdc: bigint; eth: bigint; allowance: bigint }[]; wire: Address;
};

export async function readClassroomSnapshot(client: PublicClient, wire: Address, deployBlock: bigint): Promise<ClassroomSnapshot> {
  const block = await client.getBlock();
  const blockNumber = block.number;
  const readWire = (functionName: "getState" | "getMember" | "host" | "memberCount" | "settlementFinalized", args?: readonly [number]) =>
    client.readContract({ address: wire, abi: classroomAbi, functionName, args, blockNumber } as never);
  const [state, host, memberCount, settlementFinalized, usdcBalance, ethBalance, reserves, logs] = await Promise.all([
    readWire("getState") as Promise<State>, readWire("host") as Promise<Address>, readWire("memberCount") as Promise<number>,
    readWire("settlementFinalized") as Promise<boolean>,
    client.readContract({ address: USDC, abi: tokenAbi, functionName: "balanceOf", args: [wire], blockNumber }),
    client.getBalance({ address: wire, blockNumber }),
    client.readContract({ address: PAIR, abi: pairAbi, functionName: "getReserves", blockNumber }),
    client.getLogs({ address: wire, fromBlock: deployBlock, toBlock: blockNumber }),
  ]);
  const members = await Promise.all(Array.from({ length: 5 }, (_, i) => readWire("getMember", [i]) as Promise<Member>));
  const readiness = await Promise.all(members.map(async member => {
    if (!member.joined) return { usdc: 0n, eth: 0n, allowance: 0n };
    const [usdc, eth, allowance] = await Promise.all([
      client.readContract({ address: USDC, abi: tokenAbi, functionName: "balanceOf", args: [member.account], blockNumber }),
      client.getBalance({ address: member.account, blockNumber }),
      client.readContract({ address: USDC, abi: tokenAbi, functionName: "allowance", args: [member.account, wire], blockNumber }),
    ]);
    return { usdc, eth, allowance };
  }));
  const history: HistoryItem[] = logs.map(log => {
    const decoded = decodeEventLog({ abi: classroomAbi, data: log.data, topics: log.topics });
    return { event: decoded.eventName, blockNumber: log.blockNumber, transactionHash: log.transactionHash,
      args: decoded.args as Record<string, unknown> };
  });
  const approved = new Set(members.filter(member => member.joined).map(member => member.account.toLowerCase()));
  const applicants = [...new Set(history.filter(item => item.event === "JoinRequested")
    .map(item => String(item.args.account) as Address))].filter(account => !approved.has(account.toLowerCase()));
  const claimEth = state.phase === 3 && !members[state.currentCandidate]?.received
    ? await client.readContract({ address: wire, abi: classroomAbi, functionName: "requiredCollateral", blockNumber })
    : undefined;
  return { blockNumber, blockTimestamp: block.timestamp, state, members, applicants, host, memberCount, settlementFinalized,
    history, usdcBalance, ethBalance, reserveUsdc: reserves[0], reserveWeth: reserves[1], claimEth, readiness, wire };
}
