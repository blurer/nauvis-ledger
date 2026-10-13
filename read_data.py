import pandas as pd

snapshot_data = 'data/snapshots.jsonl'

df = pd.read_json(snapshot_data, lines=True)
print(df.info())

#df['tick'] = '47111784' 
#df['backfill'] = '47111784'

#df = df['surfaces']

#print(df.iloc[14]['nauvis']['items']['produced'])

#print(df.iloc[14]['nauvis']['items']['consumed'])

df = df.iloc[-1]

print(df)
# items 
#  - produced
#  - consumed

# fluids
#  - produced
#  - consumed