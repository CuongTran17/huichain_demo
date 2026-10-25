import { isAddress, type Address } from "viem";

export type ClassroomConfig = { wire: Address; deployBlock: bigint; rpcUrl: string };

export function assertSixMemberBuildTarget(wire?: string): void {
  if (wire?.toLowerCase() === "0xa28b310cc345e693bc468829b08e1f08a50d6c47")
    throw new Error("Không thể build bản sáu người với địa chỉ contract năm người cũ. Hãy triển khai contract mới trước khi cập nhật Vercel.");
}

export function parseClassroomConfig(raw: { wire?: string; deployBlock?: string; rpcUrl?: string }): ClassroomConfig {
  if (!raw.wire || !isAddress(raw.wire, { strict: false })) throw new Error("Chưa cấu hình địa chỉ contract Sepolia hợp lệ.");
  if (!raw.deployBlock || !/^\d+$/.test(raw.deployBlock)) throw new Error("Chưa cấu hình block triển khai hợp lệ.");
  if (!raw.rpcUrl || !/^https:\/\//.test(raw.rpcUrl)) throw new Error("Chưa cấu hình RPC Sepolia HTTPS.");
  return { wire: raw.wire as Address, deployBlock: BigInt(raw.deployBlock), rpcUrl: raw.rpcUrl };
}

export function resolveClassroomConfig(raw: { wire?: string; deployBlock?: string; rpcUrl?: string }, search: string): ClassroomConfig {
  const query = new URLSearchParams(search);
  if (!query.has("wire") && !query.has("block")) return parseClassroomConfig(raw);
  if (!query.has("wire") || !query.has("block")) throw new Error("Liên kết dây hụi cần cả địa chỉ contract và block triển khai.");
  const wire = query.get("wire") ?? "";
  const deployBlock = query.get("block") ?? "";
  assertSixMemberBuildTarget(wire);
  if (!/^\d+$/.test(deployBlock) || BigInt(deployBlock) === 0n) throw new Error("Block triển khai phải là số nguyên dương.");
  return parseClassroomConfig({ ...raw, wire, deployBlock });
}

export function wireLink(baseUrl: string, wire: string, deployBlock: bigint): string {
  const url = new URL(baseUrl);
  url.searchParams.set("wire", wire);
  url.searchParams.set("block", String(deployBlock));
  return url.toString();
}
