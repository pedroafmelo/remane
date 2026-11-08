import { COVERAGE_DEFAULT, COVERAGE_MAX, COVERAGE_MIN, clampCoverage, fitsBelowFloor } from "@/lib/confirm";
import { personHours } from "@/lib/format";
import type { CapacityCheck } from "@/lib/types";
import { Button } from "../Button";
import { Muted } from "./ui";

/** A conta antes do solver e a cobertura-alvo por loja (50 a 120%, padrão 100). */
export function CapacityPanel({
  capacity,
  stores,
  coverage,
  onChange,
  onFit,
}: {
  capacity: CapacityCheck;
  stores: { id: string; name: string }[];
  coverage: Record<string, number>;
  onChange: (storeId: string, pct: number) => void;
  onFit: () => void;
}) {
  const demand = personHours(capacity.demand_person_hours);
  const supply = personHours(capacity.capacity_person_hours);
  return (
    <div className="mt-5">
      <h3 className="mb-2 text-base font-bold tracking-[-0.02em]">A demanda cabe no quadro?</h3>
      <p className={`rounded-bubble border px-4 py-3 text-[15px] ${capacity.fits ? "border-line bg-paper" : "border-[#f4d6ad] bg-warning-soft text-warning-ink"}`}>
        {capacity.fits ? (
          <>
            Sua cobertura atual pede <strong className="tabular">{demand}</strong>; com as regras desta semana, o quadro dá <strong className="tabular">{supply}</strong>. Cabe.
          </>
        ) : (
          <>
            Sua cobertura atual pede <strong className="tabular">{demand}</strong>; com as regras desta semana, o quadro dá no máximo <strong className="tabular">{supply}</strong>
            , o que cobre cerca de <strong className="tabular">{capacity.max_fitting_pct}%</strong> da demanda inferida.
          </>
        )}
      </p>
      <p className="mt-2 text-xs text-ink-muted">A demanda é inferida do arquivo (premissa a confirmar): ela herda o excesso ou a falta da escala antiga.</p>

      {stores.length > 0 ? (
        <div className="mt-4">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <h4 className="text-sm font-bold">Cobertura-alvo por loja</h4>
            {!capacity.fits && (
              <Button size="sm" variant="secondary" onClick={onFit}>
                Ajustar para caber ({clampCoverage(capacity.max_fitting_pct)}%)
              </Button>
            )}
          </div>
          {!capacity.fits && fitsBelowFloor(capacity.max_fitting_pct) && (
            <Muted>O quadro cobre só {capacity.max_fitting_pct}% da demanda: abaixo do piso de {COVERAGE_MIN}% do seletor. O ajuste usa {COVERAGE_MIN}%.</Muted>
          )}
          <ul className="mt-2 flex flex-col gap-3">
            {stores.map((s) => {
              const value = coverage[s.id] ?? COVERAGE_DEFAULT;
              const id = `cov-${s.id}`;
              return (
                <li key={s.id} className="grid grid-cols-[1fr_auto] items-center gap-x-4 gap-y-1 sm:grid-cols-[minmax(0,12rem)_1fr_auto]">
                  <label htmlFor={id} className="text-[15px] font-medium sm:col-auto">
                    {s.name === s.id ? s.id : `${s.name} (${s.id})`}
                  </label>
                  <output htmlFor={id} className="tabular text-right text-[15px] font-bold sm:order-last">
                    {value}%
                  </output>
                  <input
                    id={id}
                    type="range"
                    min={COVERAGE_MIN}
                    max={COVERAGE_MAX}
                    step={1}
                    value={value}
                    aria-valuetext={`${value} por cento da demanda inferida`}
                    onChange={(e) => onChange(s.id, clampCoverage(Number(e.target.value)))}
                    className="col-span-2 w-full accent-accent-strong sm:col-span-1"
                  />
                </li>
              );
            })}
          </ul>
          <p className="mt-2 text-xs text-ink-muted">
            100% cobre a demanda inferida: se não couber, o Pat cobre o que dá e avisa a falta. Abaixo de 100% a escala fica mais barata porque cobre menos, e o antes e depois mostra as duas coberturas.
          </p>
        </div>
      ) : (
        <div className="mt-3">
          <Muted>A lista de lojas ainda não chegou do servidor: a cobertura-alvo fica em {COVERAGE_DEFAULT}% para todas.</Muted>
        </div>
      )}
    </div>
  );
}
