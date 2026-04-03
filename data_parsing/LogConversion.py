import re
from pathlib import Path

import numpy as np
import pandas as pd


def get_Ike_State(logfile):
    ike_state = []
    ike_state_dict = {}
    with open(logfile, 'r', encoding='utf-8') as f:
        for line in f.readlines():
            if 'state change:' in line:
                line = line.split()
                ike_state.append([line[0], line[4], line[7], line[9]])
                ike_state_dict.setdefault('Time', []).append(float(line[0]))
                ike_state_dict.setdefault('Connection', []).append(line[4])
                ike_state_dict.setdefault('OldState', []).append(line[7])
                ike_state_dict.setdefault('NewState', []).append(line[9])

    return ike_state_dict


def Get_Ike_State_Stats(df):
    def _empty_stats(total=0, conn_pct=np.nan):
        return {
            'Q3': np.nan,
            'Q1': np.nan,
            'IQR': np.nan,
            'max': np.nan,
            'min': np.nan,
            'range': np.nan,
            'mean': np.nan,
            'median': np.nan,
            'p50': np.nan,
            'p95': np.nan,
            'p99': np.nan,
            'stdDev': np.nan,
            'Outliers': np.nan,
            'TotalConnections': int(total),
            'ConnectionPercent': conn_pct,
        }

    if df is None or len(df.columns) == 0:
        return _empty_stats()

    required_cols = {'NewState', 'Time'}
    if not required_cols.issubset(set(df.columns)):
        return _empty_stats()

    EST = df.loc[(df.loc[:, 'NewState'] == 'ESTABLISHED'), :]
    CON = df.loc[(df.loc[:, 'NewState'] == 'CONNECTING'), :]

    Deltas = np.array([], dtype=float)
    Q3 = np.nan
    Q1 = np.nan
    iqr = np.nan
    max_v = np.nan
    min_v = np.nan
    range_v = np.nan
    mean = np.nan
    median = np.nan
    p50 = np.nan
    p95 = np.nan
    p99 = np.nan
    stdDev = np.nan
    TotalConnections = 0
    ConnectionPercent = 0
    Outliers = np.nan

    if len(EST) <= len(CON) and len(EST) > 0:
        Deltas = (EST.Time.values[:len(EST)] - CON.Time.values[:len(EST)]).astype(float)

    if len(EST) <= len(CON):
        if len(Deltas) > 0:
            if len(Deltas) >= 4:
                Q3, Q1 = np.percentile(Deltas, [75, 25])
                iqr = Q3 - Q1
                lower = Q1 - 1.5 * iqr
                upper = Q3 + 1.5 * iqr
                upper_array = np.where(Deltas >= upper)[0]
                lower_array = np.where(Deltas <= lower)[0]
                drop_array = np.zeros(len(Deltas), dtype=bool)
                drop_array[upper_array] = True
                drop_array[lower_array] = True
                if sum(drop_array) < len(Deltas) / 4:
                    keep_array = ~drop_array
                else:
                    keep_array = np.ones(len(Deltas), dtype=bool)
            else:
                keep_array = np.ones(len(Deltas), dtype=bool)
                drop_array = np.zeros(len(Deltas), dtype=bool)

            max_v = np.max(Deltas)
            min_v = np.min(Deltas)
            range_v = max_v - min_v
            mean = np.mean(Deltas[keep_array])
            median = np.median(Deltas)
            p50 = np.percentile(Deltas, 50)
            p95 = np.percentile(Deltas, 95)
            p99 = np.percentile(Deltas, 99)
            stdDev = np.std(Deltas[keep_array])
            Outliers = int(sum(drop_array))
            TotalConnections = len(Deltas)
        else:
            TotalConnections = len(EST.index)

        if len(CON.index) > 0:
            ConnectionPercent = len(EST.index) / len(CON.index)
        else:
            ConnectionPercent = np.nan

    if TotalConnections == 0 and len(EST.index) == 0 and len(CON.index) == 0:
        return _empty_stats(total=0, conn_pct=np.nan)

    LogStats = {
        'Q3': Q3,
        'Q1': Q1,
        'IQR': iqr,
        'max': max_v,
        'min': min_v,
        'range': range_v,
        'mean': mean,
        'median': median,
        'p50': p50,
        'p95': p95,
        'p99': p99,
        'stdDev': stdDev,
        'Outliers': Outliers,
        'TotalConnections': TotalConnections,
        'ConnectionPercent': ConnectionPercent,
    }

    return LogStats


def _extract_numeric_text(value):
    if value is None:
        return ''
    match = re.search(r'-?\d+(?:\.\d+)?', str(value))
    return match.group(0) if match else ''


def _parse_runstats_segments(raw_line):
    segments = [segment.strip() for segment in str(raw_line).split(';') if segment.strip()]
    if not segments:
        return '', {}

    file_path = segments[0]
    fields = {}
    for segment in segments[1:]:
        if ':' not in segment:
            continue
        key, value = segment.split(':', 1)
        fields[key.strip()] = value.strip()
    return file_path, fields


def _parse_tc_metadata(tc_cmd):
    if not tc_cmd:
        return '', '', '', {}

    tc_cmd = str(tc_cmd).strip()
    if '| moon[' in tc_cmd:
        tc_cmd = tc_cmd.split('|', 1)[0].strip()
    if ': ' in tc_cmd:
        tc_cmd = tc_cmd.split(': ', 1)[1].strip()

    tokens = tc_cmd.split()
    if len(tokens) < 2:
        return '', '', '', {}

    tc_cmd_arg = tokens[3] if len(tokens) > 3 else ''
    tc_interface = ''
    tc_type = ''
    params = {}

    if 'dev' in tokens:
        dev_idx = tokens.index('dev')
        if dev_idx + 1 < len(tokens):
            tc_interface = tokens[dev_idx + 1]
    if 'root' in tokens:
        root_idx = tokens.index('root')
        if root_idx + 1 < len(tokens):
            tc_type = tokens[root_idx + 1]
            param_tokens = tokens[root_idx + 2:]
        else:
            param_tokens = []
    else:
        param_tokens = []

    keywords = {'delay', 'loss', 'duplicate', 'corrupt', 'reorder', 'rate'}
    skip_tokens = {'normal', 'pareto', 'paretonormal', 'uniform'}
    i = 0
    while i < len(param_tokens):
        key = param_tokens[i]
        nxt = param_tokens[i + 1] if i + 1 < len(param_tokens) else ''

        if key == 'delay' and nxt:
            params['delay'] = nxt
            i += 2
            if i < len(param_tokens) and param_tokens[i] not in keywords:
                params['jitter'] = param_tokens[i]
                i += 1
            continue

        if key == 'reorder' and nxt:
            params['reorder'] = nxt
            i += 2
            if i < len(param_tokens) and param_tokens[i] not in keywords:
                params['reorder_corr'] = param_tokens[i]
                i += 1
            continue

        if key in {'loss', 'duplicate', 'corrupt', 'rate'} and nxt:
            params[key] = nxt
            i += 2
            continue

        if key in {'distribution'} and nxt:
            i += 2
            continue

        if key in skip_tokens:
            i += 1
            continue

        if nxt and key not in keywords:
            params[key] = nxt
            i += 2
            continue

        i += 1

    return tc_cmd_arg, tc_interface, tc_type, params


def RunStats(log_dir, FileMode):
    logs = Path(log_dir)
    output_csv = log_dir + '/runstats.csv'

    if FileMode == 'w':
        with open(output_csv, 'w', encoding='utf-8') as f:
            f.write('')

    for x in logs.rglob('*.txt'):
        with open(x, 'r', encoding='utf-8') as file:
            for raw_line in file.read().splitlines():
                file_path, fields = _parse_runstats_segments(raw_line)
                if not file_path:
                    continue

                scenario_note = fields.get('ScenarioNote', '').strip().strip('"\'[]')
                sweep_key = fields.get('SweepKey', '').strip().lower()
                network_profile = fields.get('NetworkProfile', '').strip()
                carol_profile = fields.get('CarolProfile', '').strip()
                moon_profile = fields.get('MoonProfile', '').strip()
                tc_cmd = fields.get('tc_command', '').strip()

                total_time = _extract_numeric_text(fields.get('Total Time') or fields.get('TotalRunTime') or fields.get('TotalTime'))
                iteration_time = _extract_numeric_text(fields.get('IterationTime'))

                tc_cmd_arg, tc_interface, tc_type, params = _parse_tc_metadata(tc_cmd)

                if sweep_key and sweep_key != 'none':
                    vari_param = sweep_key
                elif params:
                    vari_param = next(iter(params.keys()))
                else:
                    vari_param = 'network_profile'

                logfilename = file_path.rsplit('/', -1)

                runstats_parts = [
                    'FilePath: ' + str(x.parent) + '/',
                    'Source: ' + str(x.name),
                    'FileName: ' + logfilename[-1],
                    'TotalTime: ' + total_time,
                    'IterationTime: ' + iteration_time,
                    'ScenarioNote: ' + scenario_note,
                    'SweepKey: ' + sweep_key,
                    'NetworkProfile: ' + network_profile,
                    'CarolProfile: ' + carol_profile,
                    'MoonProfile: ' + moon_profile,
                    'tc_cmd_str: "' + tc_cmd + '"',
                    'tc_cmd_arg: "' + tc_cmd_arg + '"',
                    'tc_interface: "' + tc_interface + '"',
                    'tc_type: "' + tc_type + '"',
                    'VariParam: "' + vari_param + '"',
                ]

                for key, value in params.items():
                    runstats_parts.append(f'{key}: "{value}"')

                runstats_temp = ','.join(runstats_parts)
                with open(output_csv, 'a', encoding='utf-8') as f:
                    f.writelines(runstats_temp + '\n')

    return output_csv
