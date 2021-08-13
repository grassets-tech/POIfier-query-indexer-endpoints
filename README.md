# POIfier
Python3 script to verify POI by quering multiple index-nodes of other indexers. 

## How to use
python3 poifier.v.2.py \
--indexer_node_endpoint <graphql node> \
--subgraph_ipfs_hash <subgraph ipfs hash or 'all' - for all subgraphs> 
--indexer_id <indexer id> \
--indexer_endpoint_list <list of indexer's endpoints who shared access to their graph-node endpoints>
  
## Requirements
pip3 install base58
pip3 install python-graphql-client
pip3 install PrettyTable
