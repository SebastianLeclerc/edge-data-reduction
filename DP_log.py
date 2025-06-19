import os
import datetime
import numpy as np

def load_csv(filename):
    with open(filename, 'r') as f:
        data = [line.strip().split(',') for line in f.readlines()]
    return data

# Load baseline dataset
baseline_data = load_csv('baseline_steady.csv')  # Adjust if needed

def run_dp_experiment(baseline_data, thresholds):
    print(f"{'Threshold':>10} | {'Reduced':>8} | {'%':>6} | {'TAD':>10} | {'MAD':>6} | {'MD':>6}")
    print("-" * 60)

    for drift_threshold in thresholds:
        saved_data = []
        last_value = None
        last_value_timestamp = None
        sent_value = None
        sent_value_timestamp = None
        value_coefficient = 0
        counter = 0
        max_interval = 30

        def is_value_in_predicted_line(value, timestamp):
            time_diff = (timestamp - sent_value_timestamp).total_seconds()
            predicted_value = sent_value + (value_coefficient * time_diff)
            return abs(predicted_value - value) < drift_threshold

        def save_data(timestamp, value):
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')
            if not saved_data or saved_data[-1][0] != timestamp_str:
                saved_data.append([timestamp_str, str(value)])

        for row in baseline_data:
            timestamp = datetime.datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S.%f')
            value = float(row[1])
            send = False
            calculated = False

            if counter >= max_interval:
                send = True
                counter = 0
            elif last_value is None:
                send = True
                calculated = True
            else:
                if is_value_in_predicted_line(value, timestamp):
                    counter += 1
                else:
                    value_coefficient = (value - last_value) / (timestamp - last_value_timestamp).total_seconds()
                    save_data(last_value_timestamp, last_value)
                    send = True
                    calculated = True

            last_value = value
            last_value_timestamp = timestamp

            if send:
                save_data(timestamp, value)
                if calculated:
                    sent_value_timestamp = timestamp
                    sent_value = value
                counter = 0
            else:
                counter += 1

        # Interpolation
        extended_data = []
        for row in baseline_data:
            ts_str = row[0]
            ts = datetime.datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S.%f')
            for i in range(len(saved_data) - 1):
                t_b = datetime.datetime.strptime(saved_data[i][0], '%Y-%m-%d %H:%M:%S.%f')
                t_a = datetime.datetime.strptime(saved_data[i + 1][0], '%Y-%m-%d %H:%M:%S.%f')
                if t_b <= ts <= t_a:
                    v_b = float(saved_data[i][1])
                    v_a = float(saved_data[i + 1][1])
                    ratio = (ts - t_b).total_seconds() / (t_a - t_b).total_seconds()
                    v_interp = v_b + ratio * (v_a - v_b)
                    extended_data.append((ts_str, v_interp))
                    break
            else:
                # Use nearest end value
                if ts < datetime.datetime.strptime(saved_data[0][0], '%Y-%m-%d %H:%M:%S.%f'):
                    extended_data.append((ts_str, float(saved_data[0][1])))
                else:
                    extended_data.append((ts_str, float(saved_data[-1][1])))

        # Accuracy
        tad, md = 0, 0
        for i, row in enumerate(baseline_data):
            baseline_value = float(row[1])
            new_value = float(extended_data[i][1])
            diff = abs(baseline_value - new_value)
            tad += diff
            if diff > md:
                md = diff
        mad = tad / len(baseline_data)
        percent_reduction = (len(saved_data) / len(baseline_data)) * 100

        print(f"{drift_threshold:10.4f} | {len(saved_data):8d} | {percent_reduction:6.2f} | {tad:10.2f} | {mad:6.2f} | {md:6.2f}")

# Run with log-scale thresholds
log_thresholds = np.logspace(-3, 0, num=10)  # From 0.001 to 1.0
run_dp_experiment(baseline_data, log_thresholds)
