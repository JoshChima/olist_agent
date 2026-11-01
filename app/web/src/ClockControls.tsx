import { FIRST_DAY, LAST_DAY, step, type Step } from "./clock";
import { FOCUS, MUTED, SMALL } from "./tokens";

const STEPS: [Step, string][] = [
  ["month", "M"],
  ["week", "W"],
  ["day", "D"],
];

/** The date input bounded to the dataset, then the six step buttons: back (−1M −1W −1D), forward (+1D +1W +1M). */
export function ClockControls({ clock, onChange }: { clock: string; onChange: (day: string) => void }) {
  const stepButton = (unit: Step, short: string, dir: -1 | 1) => (
    <button
      key={`${dir}${unit}`}
      className={`btn btn-sm preset-tonal font-semibold ${SMALL} ${FOCUS}`}
      title={`${dir < 0 ? "Back" : "Forward"} one ${unit}`}
      disabled={dir < 0 ? clock <= FIRST_DAY : clock >= LAST_DAY}
      onClick={() => onChange(step(clock, unit, dir))}
    >
      {dir < 0 ? "−" : "+"}1{short}
    </button>
  );
  return (
    <div className={`flex items-center gap-2 ${SMALL}`}>
      <label htmlFor="clock" className={MUTED}>
        Clock
      </label>
      <input
        id="clock"
        type="date"
        className={`input w-auto px-2 py-1.5 ${SMALL} ${FOCUS}`}
        min={FIRST_DAY}
        max={LAST_DAY}
        value={clock}
        onChange={(e) => onChange(e.target.value)}
      />
      <div className="flex gap-1">{STEPS.map(([unit, short]) => stepButton(unit, short, -1))}</div>
      <div className="ml-2 flex gap-1">{[...STEPS].reverse().map(([unit, short]) => stepButton(unit, short, 1))}</div>
    </div>
  );
}
