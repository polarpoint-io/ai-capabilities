import json
from collections import Counter

with open('scripts/metrics/sample-data.json') as f:
    data = json.load(f)

requests = data['requests']

count = len(requests)
avg_days = sum(r['handled_days'] for r in requests) / count
requesters = Counter(r['requester'] for r in requests)
types = Counter(r['type'] for r in requests)

print(f"requests_total: {count}")
print(f"avg_handled_days: {avg_days:.2f}")
print(f"top_requester: {requesters.most_common(1)[0][0]}")
print(f"top_request_type: {types.most_common(1)[0][0]}")
