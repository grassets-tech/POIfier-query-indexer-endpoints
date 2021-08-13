import argparse
import requests
from python_graphql_client import GraphqlClient
from string import Template
from prettytable import PrettyTable
import base58

# pip3 install base58
# pip3 install python-graphql-client
# pip3 install PrettyTable

def parseArguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--subgraph_ipfs_hash',
        help='subgraph ipfs_hash',
        required=True,
        type=str)
    parser.add_argument('--mainnet_subgraph_endpoint',
        help='graph network endpoint (default: %(default)s)',
        default='https://gateway.network.thegraph.com/network',
        type=str)
    parser.add_argument('--indexer_node_endpoint',
        help='endpoint available from internet',
        required=True,
        type=str)
    parser.add_argument('--indexer_id',
        help='indexer_id',
        default='0x',
        required=True,
        type=str)
    parser.add_argument('--ethereum_endpoint',
        help='ethereum endpoint to request block hash (default: %(default)s)',
        default='https://eth-mainnet.alchemyapi.io/v2/demo',
        type=str)
    parser.add_argument('--indexer_endpoint_list',
        help='file with list of endpoints (will be stored on server)',
        default="all",
        type=str)
    return parser.parse_args()


def getIndexerEndpointList(filename):
    content = []
    with open(filename,'r') as f:
        for line in f.readlines():
            l = line.strip('\n')
            content.append(l)
    return content

def getIPFS(id):
    return base58.b58encode(bytes.fromhex("1220"+id[2:])).decode('utf-8')

def get_allocations(indexer_id, graphql_endpoint):
    client = GraphqlClient(endpoint=graphql_endpoint)
    query = """
    {
      allocations(where: { indexer: "%s", status: "Active"}){
        id
        subgraphDeployment{
          id
          versions (orderBy: createdAt, orderDirection:desc, first:1){
            subgraph{
            displayName
           }
          }
        }
      }
    }
    """ % (indexer_id)
    data = client.execute(query=query)
    allocations = data['data']['allocations']
    subgraphs = []
    for allocation in allocations:
        subgraphs.append(getIPFS(allocation['subgraphDeployment']['id']))
    return list(set(subgraphs))

def getCurrentEpoch(subgraph_endpoint):
    client = GraphqlClient(endpoint=subgraph_endpoint)
    query = """{ graphNetworks { currentEpoch } }"""
    data = client.execute(query=query)
    return data['data']['graphNetworks'][0]['currentEpoch']

def getStartBlock(epoch, subgraph_endpoint):
    t = Template("""query StartBlock { epoch(id: $epoch) { startBlock } }""")
    client = GraphqlClient(endpoint=subgraph_endpoint)
    query = t.substitute(epoch=epoch)
    data = client.execute(query=query)
    return data['data']['epoch']['startBlock']

def getStartBlockHash(block_number, ethereum_endpoint):
    payload = {
        "method": "eth_getBlockByNumber",
        "params": ['{}'.format(hex(block_number)), False],
        "jsonrpc": "2.0",
        "id": 1,
    }
    response = requests.post(ethereum_endpoint, json=payload).json()
    return response["result"]["hash"]

def getPoi(indexer_id, block_number, block_hash, subgraph_ipfs_hash, graphql_endpoint):
    client = GraphqlClient(endpoint=graphql_endpoint)
    t = Template("""query MyPOI {
        proofOfIndexing(
          subgraph: "$subgraph_ipfs_hash",
          blockNumber: $block_number,
          blockHash: "$block_hash",
          indexer: "$indexer_id")
       }""")
    query = t.substitute(subgraph_ipfs_hash=subgraph_ipfs_hash,
                              block_number=block_number,
                              block_hash=block_hash,
                              indexer_id=indexer_id)
    data = client.execute(query=query)
    if data.get('errors'):
        return ''
    return data["data"]["proofOfIndexing"]

def getPoiPerAllocation():
    pass

def getIndexersPoi(indexer_id, block_number, block_hash, subgraph_ipfs_hash, indexer_node_endpoint, indexer_endpoint_list, poi):
    indexer_count = 0
    poi_match = 0
    poi_not_match = 0
    poi_null = 0
    for indexer_endpoint in indexer_endpoint_list:
        if indexer_endpoint == indexer_node_endpoint:
            continue
        indexer_count += 1
        indexer_poi = getPoi(indexer_id, block_number, block_hash, subgraph_ipfs_hash, indexer_endpoint)
        if indexer_poi == '':
            poi_null += 1
        elif indexer_poi == poi:
            poi_match += 1
        else:
            poi_not_match +=1
    return indexer_count, poi_match, poi_not_match, poi_null

def getPoifierResult(t, indexer_id, block_number, block_hash, subgraph_ipfs_hash, indexer_node_endpoint, indexer_endpoint_list, poi):
    # t = PrettyTable(['Subgraph', 'POI', 'Match', 'Not Match', 'Null', 'Indexers'])
    indexer_count, poi_match, poi_not_match, poi_null = getIndexersPoi(indexer_id,
                                                                       block_number,
                                                                       block_hash,
                                                                       subgraph_ipfs_hash,
                                                                       indexer_node_endpoint,
                                                                       indexer_endpoint_list,
                                                                       poi)
    t.add_row([subgraph_ipfs_hash, poi, poi_match, poi_not_match, poi_null, indexer_count])
    #t.align="r"
    #print(t)

if __name__ == "__main__":
    args = parseArguments()
    indexer_endpoint_list = getIndexerEndpointList(args.indexer_endpoint_list)
    epoch = getCurrentEpoch(args.mainnet_subgraph_endpoint)
    block_number = getStartBlock(epoch, args.mainnet_subgraph_endpoint)
    block_hash = getStartBlockHash(block_number, args.ethereum_endpoint)
    t = PrettyTable(['Subgraph', 'POI', 'Match', 'Not Match', 'Null', 'Indexers'])
    if args.subgraph_ipfs_hash == 'all':
        for subgraph in get_allocations(args.indexer_id, args.mainnet_subgraph_endpoint):
            poi = getPoi(args.indexer_id, block_number, block_hash, subgraph, args.indexer_node_endpoint)
            getPoifierResult(t, args.indexer_id, block_number, block_hash, subgraph, args.indexer_node_endpoint, indexer_endpoint_list, poi)
    else:
        poi = getPoi(args.indexer_id, block_number, block_hash, args.subgraph_ipfs_hash, args.indexer_node_endpoint)
        getPoifierResult(t, args.indexer_id, block_number, block_hash, args.subgraph_ipfs_hash, args.indexer_node_endpoint, indexer_endpoint_list, poi)
    t.align="r"
    print("Epoch:{} (StartBlock: {}) ".format(epoch, block_number))
    print("Indexer: ", args.indexer_id)
    print(t)
