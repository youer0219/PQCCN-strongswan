"""Transform run-log statistics into labeled experiment summaries."""

import re

import pandas as pd


def _clean_text_token(value):
    text = str(value or '').strip()
    text = text.strip().strip("[](){}")
    text = text.strip("'\"")
    return text


def _split_scenario_note(note_value):
    text = _clean_text_token(note_value)
    if not text:
        return '', ''
    parts = text.split('__')
    if len(parts) == 1:
        return text, ''
    return '__'.join(parts[:-1]), parts[-1]


def _extract_scenario_note_from_text(text_value):
    text = _clean_text_token(text_value)
    match = re.search(r'iter_\d+_(.+)\.log$', text)
    if match:
        return _clean_text_token(match.group(1))
    match = re.search(r'([a-z0-9_]+__(?:composite__)?[a-z0-9_]+)\.log$', text)
    if match:
        return _clean_text_token(match.group(1))
    return ''

def MarkLogs(DF,plvl):
    # Mark Logs looks for the string 'baseline' in the logs and marks it as as Baseline (Ture /False)
    # It also marks the Algorithm as Diffie-Helman or PostQuantum

    # Define a search function
    def search_string(s, search):
        return search in str(s).lower()

    def classify_algo(row):
        text = ' '.join(str(v).lower() for v in row.values)

        if re.search(r'hybrid2pq[_-]?pqcert|hybrid[_-]?2pq|hybrid2pq', text):
            return 'Hybrid(2PQ)-KEX + PQ-Cert'
        if re.search(r'hybrid1pq[_-]?pqcert|pq[_-]?only', text):
            return 'Hybrid(1PQ)-KEX + PQ-Cert'
        if re.search(r'classic[_-]?classic|dh[_-]?dh|baseline', text):
            return 'Classic-KEX + Classic-Cert'
        if re.search(r'pq[_-]?pq|postquantum|post-quantum', text):
            return 'Hybrid(2PQ)-KEX + PQ-Cert'
        if 'dh' in text:
            return 'Classic-KEX + Classic-Cert'
        return 'Hybrid(2PQ)-KEX + PQ-Cert'

    # Search for the string 'al' in all columns
    Bmask = DF.apply(lambda x: x.map(lambda s: search_string(s, 'baseline'.lower())))
    DHmask = DF.apply(lambda x: x.map(lambda s: search_string(s, 'DH'.lower())))
    
    # Add column to DataFrame based on the mask
    DF['Baseline'] = Bmask.any(axis=1)
    DF['Algorithm'] = DF.apply(classify_algo, axis=1)
    scenario_series = None
    if 'ScenarioNote' in DF.columns:
        scenario_series = DF['ScenarioNote'].fillna('').astype(str)
        scenario_series = scenario_series.where(scenario_series.str.len() > 0, None)
    if scenario_series is None or scenario_series.isna().all():
        source_series = DF['FileName'] if 'FileName' in DF.columns else DF.get('Source', '')
        scenario_series = source_series.apply(_extract_scenario_note_from_text) if hasattr(source_series, 'apply') else pd.Series([''] * len(DF), index=DF.index)

    split_vals = scenario_series.fillna('').apply(_split_scenario_note)
    DF['ScenarioGroup'] = split_vals.apply(lambda x: x[0])
    DF['ScenarioCase'] = split_vals.apply(lambda x: x[1])
    
    if sum(Bmask.any(axis=1)==True) == 0:
        if not DF['Algorithm'].eq('Classic-KEX + Classic-Cert').any() and sum(DHmask.any(axis=1)==True) == 0:
            print('No Baseline markers found; using Algorithm classification for baseline labels')
        DF['Baseline'] = DHmask.any(axis=1)
    # Keep backward-compatible baseline marker semantics.
    DF['Baseline'] = DF['Algorithm'].eq('Classic-KEX + Classic-Cert')
    
    return DF
