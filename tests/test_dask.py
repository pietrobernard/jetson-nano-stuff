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

# let's generate some data in a cudf DataFrame
# cudf's DataFrame offers an interface that is 'nearly' identical to that of Pandas'
def load_data(n_rows):
  df = cudf.DataFrame()
  random_state = np.random.RandomState(43210)
  df['key'] = random_state.binomial(n=1, p=0.5, size=(n_rows,))
  df['value'] = random_state.normal(size=(n_rows,))
  return df

def groupby(dataframe):
  return dataframe.groupby('key')['value'].mean()

if __name__=='__main__':
  # this script runs on the scheduler so:
  client = Client("127.0.0.1:8786")
  n_workers = 3
  n_rows = 5000
  
  # let's start with delaying data load on each worker
  dfs = [delayed(load_data)(n_rows) for i in range(n_workers)]
  print("dfs:",dfs)
  
  # group bys ops
  groupbys = [delayed(groupby)(df) for df in dfs]
  groupby_dfs = client.compute(groupbys)
  # let's wait for dask
  wait(groupby_dfs)
  print(groupby_dfs)
  
  # getting results
  results = client.gather(groupby_dfs)
  print(results)
  
  for i, result in enumerate(results):
    print('cuDF DataFrame:', i)
  
  # freeing memory
  client.restart()
