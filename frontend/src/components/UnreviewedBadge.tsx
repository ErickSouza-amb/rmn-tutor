export function UnreviewedBadge() {
  return (
    <span
      data-testid="unreviewed-badge"
      title="Valores didáticos simulados, ainda não conferidos por um especialista."
      className="inline-flex items-center rounded-full border border-warn/40 bg-warn-soft px-2 py-0.5 text-xs font-medium text-warn"
    >
      dados não revisados
    </span>
  );
}
