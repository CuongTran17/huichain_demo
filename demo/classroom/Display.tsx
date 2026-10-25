import type { ClassroomSnapshot } from "./chain.js";
import { GROSS_POT, MEMBER_COUNT, memberReturnSummary, micro, phaseNames } from "./model.js";

const short = (address: string) => `${address.slice(0, 6)}…${address.slice(-4)}`;
const eth = (wei: bigint) => (Number(wei) / 1e18).toLocaleString("vi-VN", { maximumFractionDigits: 6 });
const eventName: Record<string, string> = { JoinRequested: "Xin tham gia", Joined: "Được duyệt", PhaseChanged: "Chuyển bước",
  Contributed: "Góp 100 USDC", BidSubmitted: "Chào lãi", PayoutClaimed: "Lĩnh hụi", Frozen: "Dừng dây",
  DebtRepaid: "Trả nghĩa vụ", CollateralSold: "Bán ETH", SettlementFinalized: "Chốt quyết toán", Withdrawn: "Rút tài sản" };

export function Display({ snapshot, now, stale }: { snapshot: ClassroomSnapshot; now: bigint; stale: boolean }) {
  const contributed = Array.from({ length: MEMBER_COUNT }, (_, p) => snapshot.history.filter(h => h.event === "Contributed" && Number(h.args.period) === p)
    .reduce((sum, h) => sum + BigInt(String(h.args.amount)), 0n));
  const payouts = Array.from({ length: MEMBER_COUNT }, (_, p) => snapshot.history.filter(h => h.event === "PayoutClaimed" && Number(h.args.period) === p)
    .reduce((sum, h) => sum + BigInt(String(h.args.net)), 0n));
  const winners = Array.from({ length: MEMBER_COUNT }, (_, p) => snapshot.history.find(h => h.event === "PayoutClaimed" && Number(h.args.period) === p));
  const totalIn = contributed.reduce((a, b) => a + b, 0n);
  const totalOut = payouts.reduce((a, b) => a + b, 0n);
  const approxEthUsdc = snapshot.reserveWeth > 0n ? snapshot.ethBalance * snapshot.reserveUsdc / snapshot.reserveWeth : 0n;
  const left = snapshot.state.deadline > 0n ? Math.max(0, Number(snapshot.state.deadline - now)) : undefined;
  const returns = snapshot.members.map((_, id) => memberReturnSummary(snapshot, id));
  return <>
    <section className="display-hero"><div><p className="eyebrow">BẢNG CHIẾU · TRỰC TIẾP TỪ SEPOLIA</p><h1>Dây hụi đang ở <span>{phaseNames[snapshot.state.phase].toLowerCase()}.</span></h1>
      <p>Kỳ {snapshot.state.period + 1} trong {MEMBER_COUNT} · {snapshot.memberCount} trong {MEMBER_COUNT} ví đã được duyệt · Block {snapshot.blockNumber.toString()}</p></div>
      <div className="countdown"><small>{left === undefined ? "TRẠNG THÁI CUỐI" : "CÒN LẠI TRÊN ĐỒNG HỒ"}</small><strong>{left === undefined ? "—" : `${Math.floor(left / 60)}:${String(left % 60).padStart(2, "0")}`}</strong><span>Host phải ký chuyển bước; đồng hồ hết hạn không tự chuyển.</span></div></section>
    {stale && <div className="notice error" role="alert">Dữ liệu trên màn chiếu là block cũ. Không dùng số này để ký hoặc kết luận.</div>}
    <section className="projector-metrics" aria-label="Các số liệu hiện tại">
      <article><small>USDC thực ở contract</small><strong>{micro(snapshot.usdcBalance)}</strong><span>USDC · số dư thật</span></article>
      <article><small>Đã góp lũy kế</small><strong>{micro(totalIn)}</strong><span>USDC · từ sự kiện</span></article>
      <article><small>Đã lĩnh ròng</small><strong>{micro(totalOut)}</strong><span>USDC · từ sự kiện</span></article>
      <article><small>Lãi đã khấu trừ</small><strong>{micro(snapshot.state.retainedInterest)}</strong><span>USDC · lũy kế, không cộng vào số dư</span></article>
      <article><small>ETH còn khóa</small><strong>{eth(snapshot.ethBalance)}</strong><span>ETH · spot ≈ {micro(approxEthUsdc)} USDC</span></article>
    </section>
    <p className="disclaimer">USDC trong contract, lãi khấu trừ lũy kế và ETH quy đổi là các góc nhìn khác nhau, không cộng thành “tổng tài sản”. Giá ETH chỉ là spot của pool testnet; bán thật có thể thu ít hơn.</p>
    <section className="display-grid"><article className="card chart-card"><div className="section-heading"><span className="section-number">01</span><h2>Dòng USDC qua {MEMBER_COUNT} kỳ</h2></div>
      <div className="legend"><span className="legend-in" /> Góp vào <span className="legend-out" /> Lĩnh ra</div>
      {contributed.map((amount, p) => <div className="period-row" key={p}><div className="period-head"><strong>Kỳ {p + 1}</strong><span>{winners[p] ? `ID ${winners[p].args.memberId} lĩnh · lãi ${micro(BigInt(String(winners[p].args.interest)))} USDC` : p === snapshot.state.period && snapshot.state.phase === 4 ? "Dây dừng tại kỳ này" : "Chưa lĩnh"}</span></div>
        <div className="barline"><small>Góp</small><div className="track"><div className="bar in" style={{ width: `${Math.min(100, Number(amount * 100n / GROSS_POT))}%` }} /></div><b>{micro(amount)}</b></div>
        <div className="barline"><small>Lĩnh</small><div className="track"><div className="bar out" style={{ width: `${Math.min(100, Number(payouts[p] * 100n / GROSS_POT))}%` }} /></div><b>{micro(payouts[p])}</b></div>
      </div>)}</article>
      <article className="card member-card"><div className="section-heading"><span className="section-number">02</span><h2>Sáu người trong dây</h2></div>
        <div className="member-table"><div className="table-header"><span>ID và ví</span><span>Góp kỳ này</span><span>Chào</span><span>Đã lĩnh</span><span>Còn nợ</span></div>
          {snapshot.members.map((m, i) => <div className="table-row" key={i}><span><b>#{i}</b> {m.joined ? short(m.account) : "Chờ duyệt"}</span><span>{m.contributedThisPeriod ? "Đã góp" : "Chưa góp"}</span><span>{m.bidSubmitted ? `${m.annualBps / 100}%` : "—"}</span><span>{m.received ? `Kỳ ${m.payoutPeriod + 1}` : "Chưa"}</span><span>{micro(m.remainingDebt)} USDC</span></div>)}</div>
      </article></section>
    <section className="card return-card" aria-label="USDC từng người khi kết thúc dây"><div className="section-heading"><span className="section-number">03</span><h2>USDC của từng người</h2></div>
      <p className="fine-print">Lãi bid đã khấu trừ là số biết chắc. Lãi được chia chỉ chốt sau khi mọi khoản góp và nghĩa vụ được xử lý; quỹ lãi đã giữ hiện là {micro(snapshot.state.retainedInterest)} USDC, không phải số chắc chắn mỗi người sẽ nhận.</p>
      <div className="return-table-wrap"><table className="return-table"><thead><tr><th>ID</th><th>Đã góp</th><th>Đã lĩnh ròng</th><th>Lãi đã khấu trừ</th><th>Lãi được chia</th><th>USDC được phân bổ</th><th>USDC còn rút</th><th>USDC đã rút</th></tr></thead><tbody>
        {returns.map((row, id) => <tr key={id}><th scope="row">#{id}</th><td>{micro(row.totalContributed)}</td><td>{micro(row.payoutReceived)}</td><td>{micro(row.interestPaid)}</td><td>{row.interestReceived === undefined ? "Chưa chốt" : micro(row.interestReceived)}</td><td>{row.usdcEntitlement === undefined ? "Chưa chốt" : micro(row.usdcEntitlement)}</td><td>{snapshot.settlementFinalized ? micro(row.usdcAvailable) : "Chưa chốt"}</td><td>{micro(row.usdcWithdrawn)}</td></tr>)}
      </tbody></table></div>
      <p className="fine-print">“Đã lĩnh ròng” là tiền nhận ở lượt lĩnh. “USDC được phân bổ” là khoản riêng được quyền rút sau quyết toán, không phải nhận lại 600 USDC lần thứ hai. Số còn rút về 0 sau khi ví đã rút.</p>
    </section>
    <section className="card return-card" aria-label="ETH ký quỹ từng người"><div className="section-heading"><span className="section-number">04</span><h2>ETH ký quỹ của từng người</h2></div>
      <div className="return-table-wrap"><table className="return-table"><thead><tr><th>ID</th><th>ETH khóa lúc lĩnh</th><th>ETH đã bán khi quyết toán</th><th>ETH còn rút</th><th>ETH đã rút</th></tr></thead><tbody>
        {returns.map((row, id) => <tr key={id}><th scope="row">#{id}</th><td>{eth(row.ethInitiallyLocked)}</td><td>{eth(row.ethSold)}</td><td>{snapshot.settlementFinalized ? eth(row.ethAvailable) : "Chưa chốt"}</td><td>{eth(row.ethWithdrawn)}</td></tr>)}
      </tbody></table></div>
      <p className="fine-print">180% là tỷ lệ giá trị ETH yêu cầu khi lĩnh, không phải số ETH được thưởng. Nếu dây hoàn thành bình thường, người đã khóa được rút lại cùng lượng ETH; nếu phải thanh lý, chỉ phần còn dư mới được rút. Người lĩnh cuối không còn nghĩa vụ kỳ sau nên không cần khóa ETH.</p>
    </section>
    {(snapshot.state.phase === 4 || snapshot.state.phase === 6) && <section className="card settlement-card"><div className="section-heading"><span className="section-number">05</span><h2>Quyết toán khi dây dừng</h2></div>
      <div className="metric-grid"><div><small>Ví thiếu góp kỳ dừng</small><strong>{snapshot.members.map((_, i) => snapshot.state.triggerMask & (1 << i) ? `ID ${i}` : "").filter(Boolean).join(", ") || "Không có"}</strong></div>
        <div><small>Lãi của người bùng đã dùng</small><strong>{micro(snapshot.state.defaultInterestUsed)} USDC</strong></div><div><small>Lãi chung đã dùng</small><strong>{micro(snapshot.state.commonInterestUsed)} USDC</strong></div><div><small>Lãi đã phân bổ</small><strong>{micro(snapshot.state.distributedInterest)} USDC</strong></div>
        <div><small>Gốc chưa trả đủ</small><strong>{snapshot.settlementFinalized ? `${micro(snapshot.state.principalLoss)} USDC` : "Chưa chốt"}</strong></div><div><small>Nghĩa vụ chưa thu được</small><strong>{micro(snapshot.state.obligationUncollected)} USDC</strong></div></div>
      {!snapshot.settlementFinalized && <p className="fine-print">Chưa chốt quyết toán: số thiếu gốc có thể chưa phản ánh kết quả cuối. Host cần xử lý ETH và bấm chốt.</p>}
    </section>}
    <section className="card history-card"><div className="section-heading"><span className="section-number">06</span><h2>Giao dịch mới nhất</h2></div>
      {snapshot.history.length ? <ol>{snapshot.history.slice(-8).reverse().map((item, i) => <li key={`${item.transactionHash}-${i}`}><span>{eventName[item.event] ?? item.event}</span><span>Block {item.blockNumber.toString()}</span><a href={`https://sepolia.etherscan.io/tx/${item.transactionHash}`} target="_blank" rel="noreferrer">Xem tx ↗</a></li>)}</ol> : <p className="empty-state">Chưa có giao dịch nào của dây trong phạm vi block triển khai.</p>}
    </section>
  </>;
}
