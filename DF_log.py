import numpy as np
from datetime import datetime

def load_csv(filename):
    with open(filename, 'r') as f:
        data = [line.strip().split(',') for line in f.readlines()]
    return data

# Load baseline
baseline_data = load_csv('baseline_steady.csv')
baseline_data = [[data[0], float(data[1])] for data in baseline_data]

# Logarithmic sweep values from 0.001 to 1.0
sweep_values = np.logspace(-3, 0, num=10)  # 10 values between 10^-3 and 10^0

print(f"{'Threshold':>9} | {'Reduced':>8} | {'%':>6} | {'TAD':>10} | {'MAD':>6} | {'MD':>6}")
print("-" * 60)

for drift_threshold in sweep_values:
    # Global variables
    saved_data = []
    min_interval = 1
    max_interval = 30
    current_interval = min_interval
    last_sent_value = None
    counter = 0

    def save_data(timestamp, value):
        saved_data.append([timestamp, str(value)])

    def handle_new_data(timestamp, value, callback=None):
        global last_sent_value, counter, current_interval
        value = float(value)
        send = False

        if last_sent_value is None:
            send = True
        else:
            if abs(value - last_sent_value) >= drift_threshold:
                send = True
                current_interval = min_interval
            elif counter >= current_interval:
                send = True
                current_interval = min(max_interval, current_interval * 2)

        if send:
            if callback:
                callback(timestamp, value)
            last_sent_value = value
            counter = 0
        else:
            counter += 1

    # Run filtering
    for data_point in baseline_data:
        handle_new_data(data_point[0], data_point[1], save_data)

    # Interpolate for comparison
    def calculate_new_value(timestamp, new_data):
        nearest_value_before = None
        nearest_value_after = new_data[0]

        for i in range(len(new_data) - 1):
            t_i = datetime.strptime(new_data[i][0], '%Y-%m-%d %H:%M:%S.%f')
            t_next = datetime.strptime(new_data[i + 1][0], '%Y-%m-%d %H:%M:%S.%f')
            if t_i < datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f') < t_next:
                nearest_value_before = new_data[i]
                nearest_value_after = new_data[i + 1]
                break
        if nearest_value_before and nearest_value_after:
            t_b = datetime.strptime(nearest_value_before[0], '%Y-%m-%d %H:%M:%S.%f')
            t_a = datetime.strptime(nearest_value_after[0], '%Y-%m-%d %H:%M:%S.%f')
            time_diff = (t_a - t_b).total_seconds()
            value_diff = float(nearest_value_after[1]) - float(nearest_value_before[1])
            ratio = (datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f') - t_b).total_seconds() / time_diff
            return float(nearest_value_before[1]) + ratio * value_diff
        elif nearest_value_before:
            return float(nearest_value_before[1])
        elif nearest_value_after:
            return float(nearest_value_after[1])
        return float(new_data[0][1])  # fallback

    extended_new_data = []
    for data_point in baseline_data:
        match = next((d for d in saved_data if d[0] == data_point[0]), None)
        if match:
            extended_new_data.append([data_point[0], float(match[1])])
        else:
            interpolated = calculate_new_value(data_point[0], saved_data)
            extended_new_data.append([data_point[0], interpolated])

    # Accuracy metrics
    compounded_value = 0
    largest_difference = 0
    for i in range(len(extended_new_data)):
        baseline_value = float(baseline_data[i][1])
        new_value = float(extended_new_data[i][1])
        diff = abs(baseline_value - new_value)
        compounded_value += diff
        if diff > largest_difference:
            largest_difference = diff

    # Reporting
    reduced_count = len(saved_data)
    reduction_pct = 100 * reduced_count / len(baseline_data)
    print(f"{drift_threshold:>9.4f} | {reduced_count:>8} | {reduction_pct:>6.2f} | {compounded_value:>10.4f} | "
      f"{(compounded_value / len(extended_new_data)):>6.4f} | {largest_difference:>6.4f}")
