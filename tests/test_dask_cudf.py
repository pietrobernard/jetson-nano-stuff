########################################################################################
## To run this script make sure you are inside your 'gpudist' conda environment
## This script runs on the scheduler so the address is just 127.0.0.1
## If you're running it from another machine, change that to the proper address.
########################################################################################
import dask_cudf
import cudf
import numpy as np
from dask.distributed import Client, wait
from dask.delayed import delayed

# generating some data
def load_data(n_rows):
 df = cudf.DataFrame()
 random_state = np.random.RandomState(43210)
 df['key'] = random_state.binomial(n=1, p=0.5, size=(n_rows,))
 df['value'] = random_state.normal(size=(n_rows,))
 return df

def groupby(dataframe):
 return dataframe.groupby('key')['value'].mean()

if __name__=='__main__':
  # connecting to the scheduler (this script is run on the scheduler)
  client = Client("127.0.0.1:8786")
  
  n_workers = 3
  n_rows = 5000
  dfs = [delayed(load_data)(n_rows) for i in range(n_workers)]
  print("dfs:",dfs)

  # distributing the dataframe with dask_cudf
  distributed_df = dask_cudf.from_delayed(dfs)
  print('Type:', type(distributed_df))
  print(distributed_df)

  # getting result
  result = distributed_df.groupby('key')['value'].mean().compute()
  print(result)
  
  # stopping
  client.restart()
