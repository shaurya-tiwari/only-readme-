import { formatCurrency, formatDateTime } from "../utils/formatters";

export default function PayoutHistory({ data }) {
  if (!data) {
    return null;
  }

  return (
    <div className="panel p-6">
      <div className="mb-5 flex items-end justify-between gap-4">
        <div>
          <p className="eyebrow">Payout ledger</p>
          <h3 className="mt-2 text-2xl font-bold text-[#173126]">Recent transfers</h3>
        </div>
        <div className="text-right">
          <p className="text-sm text-ink/55">Total amount</p>
          <p className="text-xl font-bold text-[#173126]">{formatCurrency(data.total_amount)}</p>
        </div>
      </div>

      <div className="space-y-3">
        {(data.payouts || []).slice(0, 6).map((payout) => (
          <div key={payout.id} className="panel-quiet flex items-center justify-between rounded-[24px] px-4 py-4">
            <div>
              <p className="font-semibold text-[#173126]">{formatCurrency(payout.amount)}</p>
              <p className="mt-1 text-sm text-ink/55">
                {payout.channel} · {payout.transaction_id}
              </p>
            </div>
            <p className="text-sm text-ink/55">{formatDateTime(payout.completed_at || payout.initiated_at)}</p>
          </div>
        ))}
        {!data.payouts?.length ? <p className="text-sm text-ink/55">No payouts yet.</p> : null}
      </div>
    </div>
  );
}
