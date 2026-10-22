import { useCallback, useEffect, useMemo, useState } from "react";
import { createPublicClient, http, type Address } from "viem";
import { sepolia } from "viem/chains";
import { parseClassroomConfig } from "./config.js";
import { readClassroomSnapshot, type ClassroomSnapshot } from "./chain.js";
import { approveApplicant, approveRepay, assertWalletContext, connectWallet, sendAction, type Provider } from "./wallet.js";
import { MEMBER_COUNT, phaseNames, type Action } from "./model.js";
import { Player } from "./Player.js";
import { Display } from "./Display.js";
import { WalletNav } from "./WalletNav.js";

declare global { interface Window { ethereum?: Provider } }

type Tx = { stage: "signing" | "submitted" | "confirmed" | "failed"; message: string; hash?: `0x${string}` };
const raw = { wire: import.meta.env.VITE_WIRE_ADDRESS, deployBlock: import.meta.env.VITE_DEPLOY_BLOCK,
  rpcUrl: import.meta.env.VITE_SEPOLIA_RPC_URL };
let config: ReturnType<typeof parseClassroomConfig> | undefined;
let configError = "";
try { config = parseClassroomConfig(raw); } catch (error) { configError = String(error); }

export function App() {
  const isDisplay = location.pathname === "/display";
  const client = useMemo(() => config ? createPublicClient({ chain: sepolia, transport: http(config.rpcUrl) }) : undefined, []);
  const [snapshot, setSnapshot] = useState<ClassroomSnapshot>();
  const [readError, setReadError] = useState("");
  const [account, setAccount] = useState<Address>();
  const [connectError, setConnectError] = useState("");
  const [tx, setTx] = useState<Tx>();
  const [now, setNow] = useState(BigInt(Math.floor(Date.now() / 1000)));

  const refresh = useCallback(async () => {
    if (!client || !config) return;
    try {
      const next = await readClassroomSnapshot(client, config.wire, config.deployBlock);
      setSnapshot(next);
      setReadError("");
    } catch (error) { setReadError(`Không đọc được toàn bộ dữ liệu Sepolia: ${String(error)}`); }
  }, [client]);

  useEffect(() => {
    void refresh();
    const poll = setInterval(() => void refresh(), 8_000);
    const clock = setInterval(() => setNow(BigInt(Math.floor(Date.now() / 1000))), 1_000);
    return () => { clearInterval(poll); clearInterval(clock); };
  }, [refresh]);

  useEffect(() => {
    const provider = window.ethereum;
    if (!provider || isDisplay) return;
    const changed = () => { setAccount(undefined); setTx(undefined); setConnectError("Ví hoặc mạng đã đổi. Hãy kết nối lại trước khi ký."); };
    provider.on?.("accountsChanged", changed);
    provider.on?.("chainChanged", changed);
    return () => { provider.removeListener?.("accountsChanged", changed); provider.removeListener?.("chainChanged", changed); };
  }, [isDisplay]);

  async function connect() {
    try {
      if (!window.ethereum) throw new Error("Cần cài ví trình duyệt tương thích Ethereum.");
      const next = await connectWallet(window.ethereum);
      setAccount(next); setConnectError("");
    } catch (error) { setConnectError(String(error)); }
  }

  function disconnect() {
    setAccount(undefined);
    setTx(undefined);
    setConnectError("");
  }

  async function execute(label: string, operation: () => Promise<`0x${string}`>) {
    if (!client || !account || readError) return;
    setTx({ stage: "signing", message: `Đang chờ ví ký: ${label}` });
    try {
      const hash = await operation();
      setTx({ stage: "submitted", message: `${label}: đã gửi, chờ Sepolia xác nhận.`, hash });
      const receipt = await client.waitForTransactionReceipt({ hash, timeout: 180_000 });
      if (receipt.status !== "success") throw new Error("Giao dịch đã lên chain nhưng bị revert.");
      let ownerNote = "";
      try { await assertWalletContext(window.ethereum!, account); }
      catch { ownerNote = " Ví hiện tại đã đổi; kết quả này thuộc tài khoản đã gửi giao dịch."; }
      setTx({ stage: "confirmed", message: `${label}: đã xác nhận ở block ${receipt.blockNumber}.${ownerNote}`, hash });
      await refresh();
    } catch (error) { setTx(old => ({ stage: "failed", message: `${label}: ${String(error)}`, hash: old?.hash })); }
  }

  function run(action: Action, options?: { bidBps?: number; memberId?: number }) {
    if (!window.ethereum || !client || !snapshot || !config || !account) return;
    const labels: Record<Action, string> = { request: "Xin tham gia", approve: "Cấp quyền 600 USDC", start: "Bắt đầu dây",
      advance: "Chuyển bước", contribute: "Góp 100 USDC", bid: "Chào lãi", claim: "Lĩnh hụi và khóa ETH",
      repay: "Trả nghĩa vụ USDC", liquidate: "Bán ETH ký quỹ", finalize: "Chốt quyết toán",
      withdrawUsdc: "Rút USDC", withdrawEth: "Nhận lại ETH" };
    void execute(labels[action], () => sendAction(window.ethereum!, client, snapshot, config.deployBlock, account, action, options));
  }

  function admit(applicant: Address) {
    if (!window.ethereum || !client || !snapshot || !config || !account) return;
    void execute(`Duyệt ví ${applicant.slice(0, 8)}…`, () => approveApplicant(window.ethereum!, client, snapshot, config.deployBlock, account, applicant));
  }

  function repayApproval() {
    if (!window.ethereum || !client || !snapshot || !config || !account) return;
    void execute("Cấp quyền trả USDC còn nợ", () => approveRepay(window.ethereum!, client, snapshot, config.deployBlock, account));
  }

  return <>
    <a className="skip-link" href="#main">Bỏ qua điều hướng</a>
    <header className="site-header">
      <a className="brand" href="/" aria-label="Hụi Chain, về trang người chơi"><span className="brand-mark">PTIT</span><span>Hụi Chain <small>SEPOLIA · LỚP HỌC</small></span></a>
      <nav aria-label="Chế độ xem"><a className={!isDisplay ? "active" : ""} href="/">Người chơi</a><a className={isDisplay ? "active" : ""} href="/display">Bảng chiếu</a></nav>
      {!isDisplay && <WalletNav account={account} pending={tx?.stage === "signing" || tx?.stage === "submitted"} onConnect={() => void connect()} onDisconnect={disconnect} />}
    </header>
    <main id="main" className={isDisplay ? "display-shell" : "page-shell"}>
      {!config && <section className="notice error"><h1>Chưa cấu hình dây hụi</h1><p>{configError}</p><p>Người tổ chức cần đặt địa chỉ contract, block triển khai và RPC Sepolia trước khi chia sẻ liên kết.</p></section>}
      {config && <>
        {readError && <div className="notice error" role="alert"><strong>Dữ liệu chưa được xác minh ở lần tải này.</strong><p>{readError}</p><button onClick={() => void refresh()}>Thử đọc lại</button></div>}
        {connectError && !isDisplay && <div className="notice error" role="alert">{connectError}</div>}
        {!snapshot && !readError && <div className="skeleton"><div /><div /><div /></div>}
        {snapshot && <>
          <div className="status-line"><span className="status-pill">Kỳ {snapshot.state.period + 1} / {MEMBER_COUNT} · {phaseNames[snapshot.state.phase]}</span><span>Block xác minh: {snapshot.blockNumber.toString()}</span><span>{snapshot.state.deadline > 0n ? `Hạn: ${Math.max(0, Number(snapshot.state.deadline - now))} giây` : "Không có hạn đang chạy"}</span></div>
          {isDisplay ? <Display snapshot={snapshot} now={now} stale={Boolean(readError)} /> : <Player snapshot={snapshot} account={account} now={now} stale={Boolean(readError)} tx={tx} run={run} admit={admit} approveRepay={repayApproval} connect={connect} />}
        </>}
      </>}
    </main>
    <footer className="site-footer"><span>Demo testnet PTIT · Không dùng tiền thật · 180% không bảo đảm an toàn tuyệt đối</span><a href="https://sepolia.etherscan.io/" target="_blank" rel="noreferrer">Sepolia Etherscan</a></footer>
  </>;
}
