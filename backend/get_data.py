from ingestion import initialize_db, get_or_create_table
db = initialize_db()
t = get_or_create_table(db, 'active_index')
print('Row count:', t.count_rows())
rows = t.to_pandas().head(3)
for _, r in rows.iterrows():
    print('---')
    print('Source:', r.get('metadata', {}).get('source', 'N/A') if isinstance(r.get('metadata'), dict) else r.get('metadata'))
    print('Text preview:', str(r.get('text',''))[:150])