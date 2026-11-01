import type { ComponentProps, ReactNode } from "react";
import { AppBar, Navigation } from "@skeletonlabs/skeleton-react";
import { ClockControls } from "./ClockControls";
import { DeltaStrip } from "./Delta";
import { CARD, FOCUS, LINE, MUTED, SMALL, STATUS } from "./tokens";

// One tile per page, in rail order. Every href carries the clock (ADR-0009).
const PAGES = [
  ["Explorer", "/explore"],
  ["Orders", "/orders"],
  ["Funnel", "/funnel"],
] as const;

/**
 * Everything that is not the current page (GLOSSARY.md "Shell"): the app bar with the product name and
 * the clock controls, the navigation rail, the delta strip under the app bar, and the content column,
 * which scrolls on its own while the bar and rail stay put. Cards over the page ground, hairlines, no shadows.
 */
export function Shell({
  clock,
  onClock,
  loaded,
  title,
  children,
}: {
  clock: string;
  onClock: (day: string) => void;
  loaded: boolean;
  title?: string;
  children: ReactNode;
}) {
  const here = location.pathname === "/" ? "/orders" : location.pathname;
  return (
    <div className="grid h-screen grid-cols-[72px_1fr] grid-rows-[56px_minmax(0,1fr)]">
      {/* Skeleton's base CSS makes the AppBar a padded column over surface-100-900 and the Toolbar a grid;
          the rail is 100px wide with 10px labels. The classes below set the design system's sizes instead. */}
      <AppBar className={`col-span-2 h-14 justify-center gap-0 border-b px-4 py-0 ${CARD} ${LINE}`}>
        <AppBar.Toolbar className="grid-cols-[auto_auto]">
          {/* Skeleton renders Lead and Trail as nav landmarks; a title and the clock controls are not
              navigation, so both become divs and the rail is the page's one nav. */}
          <AppBar.Lead element={(attrs) => <div {...(attrs as ComponentProps<"div">)}><span className="h3 text-[17px] leading-6">olist_agent</span></div>} />
          <AppBar.Trail
            element={(attrs) => (
              <div {...(attrs as ComponentProps<"div">)}>
                <ClockControls clock={clock} onChange={onClock} />
              </div>
            )}
          />
        </AppBar.Toolbar>
      </AppBar>
      <Navigation
        layout="rail"
        element={(attrs) => (
          <nav aria-label="Pages" {...attrs}>
            <Navigation.Menu className="justify-start gap-1">
              {PAGES.map(([label, path]) => (
                <Navigation.TriggerAnchor
                  key={path}
                  href={`${path}?clock=${clock}`}
                  aria-current={path === here ? "page" : undefined}
                  className={`justify-center px-0 font-semibold ${FOCUS} ${path === here ? "preset-tonal-brand" : MUTED}`}
                >
                  <Navigation.TriggerText className={SMALL}>{label}</Navigation.TriggerText>
                </Navigation.TriggerAnchor>
              ))}
            </Navigation.Menu>
          </nav>
        )}
        className={`w-[72px] gap-1 border-r px-1 pt-2 pb-1 ${CARD} ${LINE}`}
      />
      <div className="flex min-h-0 min-w-0 flex-col">
        <div className="flex flex-col gap-2 px-4 pt-2 empty:hidden">
          {!loaded && (
            <p role="status" className={STATUS}>
              No data loaded yet.
            </p>
          )}
          <DeltaStrip clock={clock} />
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto">
          <main className="mx-auto flex w-full max-w-[1200px] flex-col gap-6 px-4 py-8">
            {title && <h1 className="h1 text-[28px] leading-[34px]">{title}</h1>}
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}
