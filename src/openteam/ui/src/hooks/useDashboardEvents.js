/**
 * useDashboardEvents — a tiny per-hub event-bus factory.
 *
 * `DashboardPanel` (from @agent-foundation/shared-ui) is context-free: it
 * subscribes to a `wsEvents$` prop via `wsEvents$.subscribe(cb) => unsub` and
 * feeds every emitted event into its own reducer as `{type:'DASHBOARD_EVENT', event}`.
 *
 * Each dashboard subtab needs its OWN live-update stream so a `dashboard_event`
 * for `hub_id=A` never leaks into hub B's reducer. `useManagerChat` creates one
 * bus per hub (keyed by `hubId`) with `makeWsEvents()` and calls `bus.next(evt)`
 * when a matching `dashboard_event` WS frame arrives; the bus is then handed to
 * `DashboardPanel` as the `wsEvents$` prop.
 *
 * This is the dashboard analog of `useGraphState`'s per-task routing, but kept
 * deliberately minimal per the framework contract: the bus only needs
 * `subscribe`/`next` (no reducer of its own — `DashboardPanel` owns that).
 */

/**
 * Create a standalone pub/sub bus for one hub's live `dashboard_event` stream.
 *
 * Shape (matches what DashboardPanel.useEffect expects):
 *   bus.subscribe(cb) -> unsubscribe()   // cb receives each emitted event
 *   bus.next(event)                       // emit an event to all subscribers
 *
 * Returns a plain object (NOT a hook) so it can be stored inside `useState`
 * maps and survive re-renders with a stable identity. Subscriber errors are
 * isolated so one bad listener can't break delivery to the others.
 */
export function makeWsEvents() {
  const subscribers = new Set();
  return {
    subscribe(cb) {
      if (typeof cb !== 'function') return () => {};
      subscribers.add(cb);
      return () => {
        subscribers.delete(cb);
      };
    },
    next(event) {
      // Snapshot first so a subscriber that unsubscribes during delivery
      // (e.g. an effect cleanup) doesn't mutate the set we're iterating.
      for (const cb of Array.from(subscribers)) {
        try {
          cb(event);
        } catch (e) {
          console.error('[useDashboardEvents] subscriber threw:', e);
        }
      }
    },
    // Exposed for completeness/teardown; DashboardPanel never calls this.
    clear() {
      subscribers.clear();
    },
  };
}

export default makeWsEvents;
