import type { Address } from "viem";

type Props = { account?: Address; pending?: boolean; onConnect: () => void; onDisconnect: () => void };

export function WalletNav({ account, pending, onConnect, onDisconnect }: Props) {
  return <div className="wallet-nav">{account ? <>
    <span title={account}>Ví {account.slice(0, 6)}…{account.slice(-4)}</span>
    <button type="button" disabled={pending} onClick={onDisconnect}>Ngắt kết nối</button>
  </> : <button type="button" onClick={onConnect}>Kết nối ví</button>}</div>;
}
