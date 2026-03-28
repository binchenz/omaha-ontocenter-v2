import axios from 'axios';

const PUBLIC_API = '/api/public/v1';

export interface WatchlistItem {
  id: number;
  ts_code: string;
  note: string | null;
  added_at: string;
}

function getToken(): string | null {
  return localStorage.getItem('public_api_token');
}

function headers() {
  return { Authorization: `Bearer ${getToken()}` };
}

export const watchlistService = {
  list: async (): Promise<WatchlistItem[]> => {
    const res = await axios.get(`${PUBLIC_API}/watchlist`, { headers: headers() });
    return res.data.items;
  },
  add: async (ts_code: string, note?: string): Promise<WatchlistItem> => {
    const res = await axios.post(`${PUBLIC_API}/watchlist`, { ts_code, note }, { headers: headers() });
    return res.data;
  },
  remove: async (id: number): Promise<void> => {
    await axios.delete(`${PUBLIC_API}/watchlist/${id}`, { headers: headers() });
  },
};
