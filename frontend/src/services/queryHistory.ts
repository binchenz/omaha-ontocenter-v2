export interface QueryHistoryEntry {
  id: string;
  timestamp: number;
  projectId: number;
  objectType: string;
  filters: Record<string, unknown>;
  resultCount: number;
}

const KEY = 'omaha_query_history';
const MAX = 100;

export const queryHistoryService = {
  list: (projectId: number): QueryHistoryEntry[] => {
    const all: QueryHistoryEntry[] = JSON.parse(localStorage.getItem(KEY) || '[]');
    return all.filter(e => e.projectId === projectId).sort((a, b) => b.timestamp - a.timestamp);
  },
  add: (entry: Omit<QueryHistoryEntry, 'id' | 'timestamp'>) => {
    const all: QueryHistoryEntry[] = JSON.parse(localStorage.getItem(KEY) || '[]');
    all.unshift({ ...entry, id: crypto.randomUUID(), timestamp: Date.now() });
    localStorage.setItem(KEY, JSON.stringify(all.slice(0, MAX)));
  },
  clear: (projectId: number) => {
    const all: QueryHistoryEntry[] = JSON.parse(localStorage.getItem(KEY) || '[]');
    localStorage.setItem(KEY, JSON.stringify(all.filter(e => e.projectId !== projectId)));
  },
};
