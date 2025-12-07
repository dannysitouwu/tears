import http from 'k6/http';
import { check } from 'k6';

export const options = { vus: 10, duration: '30s' };
const BASE = 'http://localhost:8000';
export default function () {
  const r = http.get(`${BASE}/users?page=1&per_page=10`);
  check(r, { 'status 200': (res) => res.status === 200 });
}