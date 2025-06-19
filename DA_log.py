import sys
import os
import math
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def load_csv(filename):
    with open(filename, 'r') as f:
        data = [line.strip().split(',') for line in f.readlines()]
    return data

# Load baseline
baseline_data = load_csv('baseline_fluctuating.csv')
baseline_data = [[datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S.%f'), float(row[1])] for row in baseline_data]
baseline_len = len(baseline_data)

# Log-like spaced intervals
intervals = [5, 6, 8, 10, 13, 17, 22, 29, 38, 50]

def avg(datetimes):
    ref = datetime(1900, 1, 1)
    return ref + sum([dt - ref for dt in datetimes], timedelta()) / len(datetimes)

print(f"{'Interval':>9} | {'Reduced':>8} | {'%':>6} | {'TAD':>10} | {'MAD':>6} | {'MD':>6}")
print("-" * 60)

for interval in intervals:
    saved_data = []
    current_intervals_data = []
    is_first = True

    def save_data(timestamp, value):
        saved_data.append([timestamp, value])

    def handle_new_data(timestamp, value):
        global current_intervals_data, is_first
        current_intervals_data.append((timestamp, value))

        if is_first:
            save_data(timestamp, value)
            is_first = False
            return

        if len(current_intervals_data) == interval:
            avg_val = sum([v for _, v in current_intervals_data]) / interval
            avg_time = avg([t for t, _ in current_intervals_data])
            save_data(avg_time, avg_val)
            current_intervals_data = []

    for ts, val in baseline_data:
        handle_new_data(ts, val)

    # If any remaining
    if current_intervals_data:
        avg_val = sum([v for _, v in current_intervals_data]) / len(current_intervals_data)
        avg_time = avg([t for t, _ in current_intervals_data])
        save_data(avg_time, avg_val)

    # Interpolation
    def interpolate(ts, data):
        before = None
        after = None
        for i in range(len(data) - 1):
            if data[i][0] <= ts < data[i + 1][0]:
                before = data[i]
                after = data[i + 1]
                break
        if not before:
            return data[0][1]
        if not after:
            return data[-1][1]
        total = (after[0] - before[0]).total_seconds()
        ratio = (ts - before[0]).total_seconds() / total
        return before[1] + ratio * (after[1] - before[1])

    extended_data = []
    for ts, _ in baseline_data:
        val = interpolate(ts, saved_data)
        extended_data.append(val)

    original_values = [v for _, v in baseline_data]
    diffs = [abs(a - b) for a, b in zip(original_values, extended_data)]
    TAD = sum(diffs)
    MAD = TAD / len(diffs)
    MD = max(diffs)

    print(f"{interval:>9} | {len(saved_data):>8} | {len(saved_data)/baseline_len*100:6.2f} | {TAD:10.2f} | {MAD:6.2f} | {MD:6.2f}")
