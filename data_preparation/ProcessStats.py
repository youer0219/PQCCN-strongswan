## ProcessStats.py
# Path: data_preparation/ProcessStats.py
# Process Stats is a module that contains functions to the logfile dataframe (RunLogStatsDF) 

import re

def MarkLogs(DF,plvl):
    # Mark Logs looks for the string 'baseline' in the logs and marks it as as Baseline (Ture /False)
    # It also marks the Algorithm as Diffie-Helman or PostQuantum

    # Define a search function
    def search_string(s, search):
        return search in str(s).lower()

    def classify_algo(row):
        text = ' '.join(str(v).lower() for v in row.values)

        if re.search(r'hybridkex[_-]?pqcert|hybrid[_-]?kex', text):
            return 'Hybrid-KEX + PQ-Cert'
        if re.search(r'purepq[_-]?pqcert|pq[_-]?only', text):
            return 'PurePQ-KEX + PQ-Cert'
        if re.search(r'classic[_-]?classic|dh[_-]?dh|baseline', text):
            return 'Classic-KEX + Classic-Cert'
        if re.search(r'pq[_-]?pq|postquantum|post-quantum', text):
            return 'Hybrid-KEX + PQ-Cert'
        if 'dh' in text:
            return 'Classic-KEX + Classic-Cert'
        return 'Hybrid-KEX + PQ-Cert'

    # Search for the string 'al' in all columns
    Bmask = DF.apply(lambda x: x.map(lambda s: search_string(s, 'baseline'.lower())))
    DHmask = DF.apply(lambda x: x.map(lambda s: search_string(s, 'DH'.lower())))
    
    # Add column to DataFrame based on the mask
    DF['Baseline'] = Bmask.any(axis=1)
    DF['Algorithm'] = DF.apply(classify_algo, axis=1)
    
    if sum(Bmask.any(axis=1)==True) == 0:
        print('No Baseline Found, switching to DH as Baseline')
        DF['Baseline'] = DHmask.any(axis=1)
    # Keep backward-compatible baseline marker semantics.
    DF['Baseline'] = DF['Algorithm'].eq('Classic-KEX + Classic-Cert')
    
    return DF
