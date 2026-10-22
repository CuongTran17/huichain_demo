import type { Address } from "viem";
import type { ClassroomSnapshot } from "./chain.js";

export type Action = "request" | "approve" | "start" | "advance" | "contribute" | "bid" | "claim" | "repay" | "liquidate" | "finalize" | "withdrawUsdc" | "withdrawEth";
export const MEMBER_COUNT = 6;
export const CONTRIBUTION = 100_000_000n;
export const GROSS_POT = BigInt(MEMBER_COUNT) * CONTRIBUTION;
export const FULL_WIRE_ALLOWANCE = GROSS_POT;
export const phaseNames = ["Phòng chờ", "Góp USDC", "Chào lãi", "Lĩnh hụi", "Quyết toán", "Hoàn thành", "Đã quyết toán"] as const;
const same = (a: string, b: string) => a.toLowerCase() === b.toLowerCase();

export function memberIndex(snapshot: ClassroomSnapshot, account?: Address): number {
  return account ? snapshot.members.findIndex(member => member.joined && same(member.account, account)) : -1;
}

export function availableActions(snapshot: ClassroomSnapshot, account?: Address, now = BigInt(Math.floor(Date.now() / 1000))): Action[] {
  if (!account) return [];
  const { state, members } = snapshot;
  const id = memberIndex(snapshot, account);
  const member = id >= 0 ? members[id] : undefined;
  const host = same(snapshot.host, account);
  const before = now < state.deadline;
  const actions: Action[] = [];
  if (state.phase === 0) {
    if (!member && !snapshot.applicants.some(a => same(a, account))) actions.push("request");
    if (member && snapshot.readiness[id].allowance < FULL_WIRE_ALLOWANCE) actions.push("approve");
    if (host && snapshot.memberCount === MEMBER_COUNT) actions.push("start");
  }
  if (state.phase === 1) {
    if (member && !member.contributedThisPeriod && before) actions.push("contribute");
    if (host && (!before || members.every(m => m.contributedThisPeriod))) actions.push("advance");
  }
  if (state.phase === 2) {
    if (member && !member.received && !member.bidSubmitted && before) actions.push("bid");
    if (host && (!before || members.every(m => m.received || m.bidSubmitted))) actions.push("advance");
  }
  if (state.phase === 3) {
    const candidate = members[state.currentCandidate];
    if (member && id === state.currentCandidate && !candidate.received && before) actions.push("claim");
    if (host && (!before || candidate.received)) actions.push("advance");
  }
  if (state.phase === 4) {
    if (member?.received && member.remainingDebt > 0n && !member.liquidationProcessed &&
      (state.triggerMask & (1 << id)) === 0 && before) actions.push("repay");
    if (host && members.some((m, i) => m.received && m.remainingDebt > 0n && !m.liquidationProcessed && m.lockedEth > 0n &&
      ((state.triggerMask & (1 << i)) !== 0 || !before))) actions.push("liquidate");
  }
  if (host && !snapshot.settlementFinalized && (state.phase === 4 || state.phase === 5) && members.every(m => !m.received || m.remainingDebt === 0n || m.liquidationProcessed)) actions.push("finalize");
  if (snapshot.settlementFinalized) {
    if (member && member.claimableUsdc > 0n) actions.push("withdrawUsdc");
    if (member && member.claimableEth > 0n) actions.push("withdrawEth");
  }
  return actions;
}

export function micro(value: bigint): string {
  return (Number(value) / 1_000_000).toLocaleString("vi-VN", { maximumFractionDigits: 6 });
}

export function bidInterest(debt: bigint, bps: number, days: number): bigint {
  return debt * BigInt(bps) * BigInt(days) / (10_000n * 365n);
}

export function claimPreview(period: number, annualBps: number) {
  const remaining = MEMBER_COUNT - 1 - period;
  const debt = BigInt(remaining) * CONTRIBUTION;
  const interest = bidInterest(debt, annualBps, remaining * 30);
  return { debt, interest, net: GROSS_POT - interest };
}
