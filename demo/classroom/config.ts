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
