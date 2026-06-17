import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
    vus: 30,
    duration: '60s',
};

export default function () {
    const url = 'http://localhost:8080/api/auth/';

    const params = {
        headers: {
            'Content-Type': 'application/json',
            "Authorization": "Bearer {}"
        },
    };

    const res = http.get(url, params);
    check(res, { 'status was 200': (r) => r.status == 200 });
}
