import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';
import { htmlReport } from "https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js";

const errorRate = new Rate('errors');
const responseTime = new Trend('response_time');

export const options = {
  stages: [
    { duration: '30s', target: 10 },
    { duration: '1m', target: 50 },
    { duration: '30s', target: 100 },
    { duration: '1m', target: 50 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    errors: ['rate<0.1'],
  },
};

const BASE_URL = 'http://localhost:8000';

export default function () {
  let res = http.get(`${BASE_URL}/users?page=1&per_page=10`);
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
  errorRate.add(res.status !== 200);
  responseTime.add(res.timings.duration);
  
  sleep(1);

  res = http.get(`${BASE_URL}/chats?page=1&per_page=10`);
  check(res, { 'status is 200': (r) => r.status === 200 });
  errorRate.add(res.status !== 200);
  responseTime.add(res.timings.duration);

  sleep(1);

  res = http.get(`${BASE_URL}/messages?page=1&per_page=50`);
  check(res, { 'status is 200': (r) => r.status === 200 });
  errorRate.add(res.status !== 200);
  responseTime.add(res.timings.duration);

  sleep(1);
}

export function handleSummary(data) {
  return {
    "load-test-report.html": htmlReport(data),
  };
}