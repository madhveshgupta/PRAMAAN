"use client";
/**
 * Risk, with its reasons attached.
 *
 *  A probability without attributions is not something an officer can put in an appraisal
 *  note, so the two never appear apart on this page: each figure is immediately followed by
 *  what moved it, largest first.
 *
 *  Two deliberate refusals, both from invariant 13 — never invent a statistical parameter:
 *    · there is no Monte Carlo fan chart here, because its correlation matrix would have to
 *      be fabricated. The outcome range is read off what comparable projects actually cost;
 *    · there is no confidence interval on the probability. The model does not produce one,
 *      and drawing an error bar we cannot source would be the most persuasive lie on the page.
 */
import { ForecastBand, PeerHistogram, ProbabilityScale, Tornado, type Driver }
  from "@/components/charts/Figures";
import { Empty } from "@/components/ui/bits";
import { Icon } from "@/components/ui/Icon";
import { useReveal } from "@/lib/motion";

export interface RiskPayload {
  prediction?: {
    delay_probability: number | null;
    overrun_probability?: number | null;
    drivers?: Driver[];
    delay_drivers?: Driver[];
    overrun_drivers?: Driver[];
    caveat?: string | null;
    model_version: string;
  };
  outcome_range?: {
    method?: string;
    peer_count: number;
    cost_p50_cr: number | null; cost_p80_cr: number | null; cost_p95_cr: number | null;
    months_p50?: number | null; months_p80?: number | null;
    peer_criteria?: Record<string, unknown> | null;
    peer_distribution?: { label: string; count: number }[] | null;
  };
}

function Panel({ title, hint, children }: {
  title: string; hint?: string; children: React.ReactNode;
}) {
  return (
    <section data-reveal className="card p-4 shadow-card">
      <h2 className="display text-sm font-bold text-ink">{title}</h2>
      {hint && (
        <p className="mt-0.5 text-2xs leading-relaxed text-ink-faint">{hint}</p>
      )}
      <div className="mt-3">{children}</div>
    </section>
  );
}

export function RiskView({ risk, claimedCostCr }: {
  risk: RiskPayload | null;
  /** The cost the report itself asks for, if it was extracted — what makes the band land. */
  claimedCostCr?: number | null;
}) {
  const reveal = useReveal<HTMLDivElement>({ immediate: true, deps: [Boolean(risk)] });
  const p = risk?.prediction;
  const o = risk?.outcome_range;

  if (!p && !o) {
    return <Empty title="No risk analysis for this report"
                  hint="Risk prediction runs only for sectors present in the historical data.
                        Its absence is a gap in our coverage, not a judgement about this
                        project — and it must not be read as one." />;
  }

  return (
    <div ref={reveal} className="space-y-4">
      <p data-reveal className="flex gap-2 rounded-card border border-sev-info/25
                                bg-sev-info-soft px-4 py-3 text-2xs leading-relaxed
                                text-ink-soft">
        <Icon name="shield" className="mt-px w-4 h-4 shrink-0 text-sev-info" />
        <span>
          Everything on this page is about the <b>class of project</b> — how comparable
          proposals have behaved historically — not about the competence of the submitting
          organisation. It is an input to how closely a project is monitored after sanction,
          never a reason to refuse one.
        </span>
      </p>

      <div className="grid gap-4 lg:grid-cols-2">
        {p && (
          <>
            <Panel title="Schedule delay"
                   hint="The chance a comparable project overran its stated timeline.">
              <ProbabilityScale value={p.delay_probability}
                                label="chance of a schedule overrun"
                                caveat={p.caveat} />
              {(p.delay_drivers ?? p.drivers ?? []).length > 0 && (
                <div className="mt-4 border-t border-paper-edge pt-3">
                  <p className="mb-2 text-2xs font-semibold uppercase tracking-wide text-ink-faint">
                    What moved this figure, largest first
                  </p>
                  <Tornado drivers={p.delay_drivers ?? p.drivers ?? []}
                           caption="Bar length is each factor's contribution to this score.
                                    Left lowers the risk, right raises it." />
                </div>
              )}
            </Panel>

            {p.overrun_probability != null && (
              <Panel title="Cost overrun"
                     hint="A separate model with its own reasons. The two are shown apart on
                           purpose — a project can be likely to slip its dates and still land
                           on budget.">
                <ProbabilityScale value={p.overrun_probability}
                                  label="chance of a cost overrun" />
                {(p.overrun_drivers ?? []).length > 0 && (
                  <div className="mt-4 border-t border-paper-edge pt-3">
                    <p className="mb-2 text-2xs font-semibold uppercase tracking-wide text-ink-faint">
                      What moved this figure, largest first
                    </p>
                    <Tornado drivers={p.overrun_drivers ?? []} />
                  </div>
                )}
              </Panel>
            )}
          </>
        )}

        {o && (
          <Panel title="Likely cost outcome"
                 hint="Read off the actual outcomes of comparable completed projects — not a
                       simulation. The width of the band is the message.">
            <ForecastBand p50={o.cost_p50_cr} p80={o.cost_p80_cr} p95={o.cost_p95_cr}
                          claimed={claimedCostCr ?? null} peerCount={o.peer_count} />
            {o.peer_distribution && o.peer_distribution.length > 0 && (
              <div className="mt-4 border-t border-paper-edge pt-3">
                <p className="mb-2 text-2xs font-semibold uppercase tracking-wide text-ink-faint">
                  Where those {o.peer_count} projects actually landed
                </p>
                <PeerHistogram bins={o.peer_distribution} />
              </div>
            )}
          </Panel>
        )}

        {o && (o.months_p50 != null || o.peer_criteria) && (
          <Panel title="What counted as comparable"
                 hint="The criteria are shown because they decide the whole forecast. A peer
                       group chosen loosely produces a tight band that means nothing.">
            <dl className="space-y-1.5 text-xs">
              {o.months_p50 != null && (
                <div className="flex justify-between gap-4">
                  <dt className="text-ink-soft">Median duration of comparable projects</dt>
                  <dd className="tabular-nums font-medium">{o.months_p50} months</dd>
                </div>
              )}
              {o.months_p80 != null && (
                <div className="flex justify-between gap-4">
                  <dt className="text-ink-soft">P80 duration</dt>
                  <dd className="tabular-nums font-medium">{o.months_p80} months</dd>
                </div>
              )}
              {o.peer_criteria && Object.entries(o.peer_criteria).map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4">
                  <dt className="capitalize text-ink-soft">{k.replace(/_/g, " ")}</dt>
                  <dd className="text-right font-medium">{String(v)}</dd>
                </div>
              ))}
              {o.method && (
                <div className="flex justify-between gap-4 border-t border-paper-edge pt-2">
                  <dt className="text-ink-soft">Method</dt>
                  <dd className="font-medium">{o.method.replace(/_/g, " ")}</dd>
                </div>
              )}
            </dl>
          </Panel>
        )}
      </div>

      {p?.model_version && (
        <p data-reveal className="text-2xs text-ink-faint">
          Model {p.model_version}. Trained on historical project outcomes and validated on a
          time-based split — never a random one, which would let the model see the future and
          turn the metrics into fiction.
        </p>
      )}
    </div>
  );
}
