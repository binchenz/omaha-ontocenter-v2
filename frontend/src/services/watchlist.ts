import api from './api';

export interface WatchlistItem {
  id: number;
  ts_code: string;
  note: string | null;
  added_at: string;
}

export const watchlistService = {
  list: async (): Promise<WatchlistItem[]> => {
    const res = await api.get('/watchlist/');
    return res.data;
  },
  add: async (ts_code: string, note?: string): Promise<WatchlistItem> => {
    const res = await api.post('/watchlist/', { ts_code, note });
    return res.data;
  },
  update: async (id: number, note: string): Promise<WatchlistItem> => {
    const res = await api.patch(`/watchlist/${id}`, { note });
    return res.data;
  },
  remove: async (id: number): Promise<void> => {
    await api.delete(`/watchlist/${id}`);
  },
};
