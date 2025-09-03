// Minimal, non-react zustand-like create for type-checking and simple state access
export function create<TState>(
  initializer: (set: (partial: Partial<TState>) => void, get: () => TState) => TState,
) {
  let state = {} as TState;
  const set = (partial: Partial<TState>) => {
    state = { ...state, ...partial } as TState;
  };
  const get = () => state;
  state = initializer(set, get);
  const useStore = ((selector?: (s: TState) => unknown) => (selector ? selector(state) : state)) as unknown as {
    <R>(selector: (s: TState) => R): R;
    getState: () => TState;
  };
  (useStore as { getState: () => TState }).getState = () => state;
  return useStore;
}

