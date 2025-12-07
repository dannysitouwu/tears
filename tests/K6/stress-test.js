import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 100 },   // Ramp up to 100 users
    { duration: '3m', target: 100 },   // Stay at 100 users
    { duration: '1m', target: 200 },   // Ramp up to 200 users
    { duration: '3m', target: 200 },   // Stay at 200 users
    { duration: '1m', target: 0 },     // Ramp down
  ],
};

const BASE_URL = 'http://localhost:8000';

export default function () {
  const responses = http.batch([
    ['GET', `${BASE_URL}/users?page=1&per_page=50`],
    ['GET', `${BASE_URL}/chats?page=1&per_page=50`],
    ['GET', `${BASE_URL}/messages?page=1&per_page=100`],
  ]);

  responses.forEach((res) => {
    check(res, {
      'status is 200': (r) => r.status === 200,
    });
  });

  sleep(0.5);
}