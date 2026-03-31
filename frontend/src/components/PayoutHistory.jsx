import { formatCurrency, formatDateTime } from "../utils/formatters";

export default function PayoutHistory({ data }) {
  if (!data) {
    return null;
  }

  return (
    <div className="panel p-6">
      <div className="mb-5 flex items-end justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-ink/45">Payout ledger</p>
          <h3 className="mt-1 text-2xl font-bold">Recent transfers</h3>
        </div>
        <div className="text-right">
          <p className="text-sm text-ink/55">Total amount</p>
          <p className="text-xl font-bold">{formatCurrency(data.total_amount)}</p>
        </div>
      </div>
      <div className="space-y-3">
        {(data.payouts || []).slice(0, 6).map((payout) => (
          <div key={payout.id} className="flex items-center justify-between rounded-2xl bg-black/[0.03] px-4 py-4">
            <div>
              <p className="font-semibold">{formatCurrency(payout.amount)}</p>
              <p className="text-sm text-ink/55">{payout.channel} · {payout.transaction_id}</p>
            </div>
            <p className="text-sm text-ink/55">{formatDateTime(payout.completed_at || payout.initiated_at)}</p>
          </div>
        ))}
        {!data.payouts?.length ? <p className="text-sm text-ink/55">No payouts yet.</p> : null}
      </div>
    </div>
  );
}
