export default function SectionHeader({ eyebrow, title, description, action }) {
  return (
    <div className="mb-5 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow ? <p className="mb-2 text-xs font-semibold uppercase tracking-[0.28em] text-ink/45">{eyebrow}</p> : null}
        <h2 className="text-2xl font-bold">{title}</h2>
        {description ? <p className="mt-2 max-w-2xl text-sm text-ink/65">{description}</p> : null}
      </div>
      {action}
    </div>
  );
}
