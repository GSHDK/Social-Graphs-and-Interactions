import pandas as pd
import json
import networkx as nx
import numpy as np
from collections import Counter
import urllib
from datetime import datetime
import re

# Only for cleanup of notebook 
# Don't code like this :)
def create_df_G_from_path(path: str):
    RELATIVE_FILE_PATH=path
    movies = pd.read_csv(RELATIVE_FILE_PATH+'tmdb_5000_movies.csv')
    credits = pd.read_csv(RELATIVE_FILE_PATH + 'tmdb_5000_credits.csv')
    # Creating DF
    df = movies.merge(right = credits, left_on = 'id', right_on = 'movie_id')
    df['release_date'] = pd.to_datetime(df['release_date'])


    #Convert JSON to dict and extract the names of each actor in each movie
    actors_per_movie = df['cast'].apply(lambda x: ','.join([y['name'] for y in json.loads(x)])).str.split(',', expand = True).fillna('')
    actors_per_movie = df[['original_title', 'id']].merge(right = actors_per_movie, left_index = True, right_index = True)

    #Unpivot
    actors_per_movie = actors_per_movie.melt(id_vars=['original_title', 'id'])

    #Remove empty rows
    actors_per_movie = actors_per_movie[actors_per_movie['value'] != '']

    #Number of movies per actor
    pt = actors_per_movie.pivot_table(index = 'value', values='id', aggfunc = len).reset_index().sort_values(by='id', ascending = False).reset_index()
    
    #Select top N actors by number of movies
    pt = pt.nlargest(500, 'id')
    #Top N actors as Nodes
    nodes = pt['value'].tolist()

    # Extracting genre
    movie_genre={}
    for x in movies.iterrows():
        movie_genre[x[1]['original_title']]=[y['name'] for y in json.loads(x[1]['genres'])]


    #Create edges between actors that have been in the same movie
    edges = []
    actor_genre = {}
    actor_movies_count = {}
    actor_movies_list = {}
    edge_movie_lookup = {}
    for node in nodes:
        actor_movies = actors_per_movie[actors_per_movie['value'] == node]['original_title'].tolist()
        edges += [(node, x) for x in\
                  actors_per_movie[(actors_per_movie['original_title'].isin(actor_movies)) \
                    & (actors_per_movie['value'].isin(nodes))]['value'] if node != x]

        # Actor
        cnt=len(actor_movies)
        actor_movies_count[node] = cnt
        actor_movies_list[node] = actor_movies
        actor_genre[node]=[movie_genre[y] for y in actor_movies]
    
    # Init graph
    G = nx.Graph()

    # Add nodes and edges
    G.add_nodes_from(nodes)
    G.add_edges_from(edges)
    
    # Set attributes

    ct=Counter(edges)
    # Add weights
    for key, value in ct.items():
        G.edges[key]['weight'] = value

    # Generate list of movies for edges
    for key, value in edge_movie_lookup.items():
        G.edges[key]['movies']=value

    # Add most frequent genre
    for actor in G.nodes:
        G.nodes[actor]['genre']=Counter([x for y in actor_genre[actor] for x in y])
        G.nodes[actor]['top_genre']=G.nodes[actor]['genre'].most_common(1)[0][0]
        G.nodes[actor]['top_genre']
        G.nodes[actor]['movies_count']=actor_movies_count[actor]
        G.nodes[actor]['movies']=actor_movies_list[actor]
        
    return df, G

def look_up_decade(year: int)-> str:
    baseurl = 'https://en.wikipedia.org/w/api.php?'
    action = 'action=query'
    title = 'titles='
    content = 'prop=revisions&rvprop=content'
    dataformat = 'format=json'
    decade_start=int(year/10)*10
    query = '%s%s&%s&%s&%s' % (baseurl,action,f'titles={decade_start}s',content,dataformat)
    res = json.loads(urllib.request.urlopen(query).read().decode('utf-8'))
    pages = res.get('query').get('pages')
    if not pages:
        raise Exception('No pages found')
    data = []
    for page in pages.keys():
        try:
            data.append(res['query']['pages'][page]['revisions'][0]['*'])
        except:
            print(f"Failed on pages{page}")
    return data

def process_data(d:list, limit=3)->list:
    data_string = ''
    temp_str = ''
    
    i=0
    for x in d:
        if i>=limit:
            break
        # Remove special chars and data in links
        temp_str=re.sub("[\{\<.*?[\}\>]", "", x)
        # Remove links
        temp_str=re.sub('url=.\S*','',temp_str)
        # Weird chars
        temp_str=re.sub('[^a-zA-Z0-9 \n\.]', '', temp_str)
        # Remaning links
        temp_str=re.sub('http.\S*','',re.sub('[^a-zA-Z0-9 \n\.]', '', temp_str))
        # Remaning links
        temp_str=re.sub('redirect.\S*','',temp_str)
        data_string += temp_str
        i+=1
    return data_string    
