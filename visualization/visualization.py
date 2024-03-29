import pandas as pd
import hdbscan
import numpy as np
import random
import sys
sys.path.append('.')
sys.path.append('..')
sys.path.append('../../')
sys.path.append('../../../')
import os.path
from subprocess import call

from BERTclassifier import getTopics, loadModel
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt

import umap.umap_ as umap

from scipy.sparse.csr import csr_matrix
from typing import List, Tuple, Dict, Union
from config import formato

r = lambda: random.randint(0,255) #Generador de numeros aleatorios para colores

if not os.path.exists('./images'):
        call('mkdir ./images', shell=True)

def seed(df):
    np.random.seed(42)
    rndperm = np.random.permutation(df.shape[0])
    print('DONE SEED')
    return  rndperm

def borraNulos(embeddings, model):
    df = pd.DataFrame(getTopics(model=model), columns = ['cluster'])
    df = df.assign(embeddings=[*embeddings])
    df = df[df['cluster'] != -1]
    print('DELETED -1 TOPICS')
    return df['embeddings'].tolist()

def asignaColores(model, negros, embeddings):
    topics = getTopics(model=model)
    # LOS -1 SE COLOREAN A NEGRO
    topic_list = list(dict.fromkeys(topics))
    topic_none = "#000000"
    color_list = []
    for i in range(len(topic_list)-1):
        color_list.append('#%02X%02X%02X' % (r(),r(),r()))
    topic_color_list = []
    if negros:
        for topic in topics:
            if topic == -1:
                topic_color_list.append(topic_none)
            else:
                topic_color_list.append(color_list[topic])
        print('ASIGNED COLORS')
        return embeddings, topic_color_list
    else:
        embeddings = borraNulos(embeddings, model)
        for topic in topics:
            if topic != -1:
                topic_color_list.append(color_list[topic])
        print('ASIGNED COLORS')
        return embeddings, topic_color_list

def hdbscanFit(embeddings):
    # NO SE USA AUN
    clusterer = hdbscan.HDBSCAN(algorithm='best', alpha=1.0, approx_min_span_tree=True,
        gen_min_span_tree=False, leaf_size=40,
        metric='euclidean', min_cluster_size=250, min_samples=None, p=None)
    print('Clusterer generado, entrenando')
    clusterer.fit(embeddings)

def pca(model, df, embeddings, rndperm, negros):
    if not negros:
        embeddigns = borraNulos(embeddings, model)
    print('TRANSFORMING TO 3D')
    pca = PCA(n_components=3)
    #pca_result = pca.fit_transform(df[feat_cols].values)
    pca_result = pca.fit_transform(embeddings)
    df = df.drop(columns=[0, len(df.columns)-1]) #720 , 129

    #pk.dump(pca, open("pca.pkl","wb")) #GUARDAMOS EL PCA"""
    print('DONE, REPRESENTING')
    df['pca-one'] = pca_result[:,0]
    df['pca-two'] = pca_result[:,1]
    df['pca-three'] = pca_result[:,2]

    print('Explained variation per principal component: {}'.format(pca.explained_variance_ratio_))
    ax = plt.figure(figsize=(160,100)).gca(projection='3d')
    ax.scatter(
        xs=df.loc[rndperm,:]["pca-one"],
        ys=df.loc[rndperm,:]["pca-two"],
        zs=df.loc[rndperm,:]["pca-three"],
        c=colors
    )
    ax.set_xlabel('pca-one')
    ax.set_ylabel('pca-two')
    ax.set_zlabel('pca-three')
    plt.savefig('./images/PCA_3D_%s.png'%model)
    plt.show()

def pca2D(model, embeddings, negros, modo):
    if not negros:
        embeddings = borraNulos(embeddings, model)
    print('TRANSFORMING TO 2D')
    pca = PCA(n_components=2)
    #pca_result = pca.fit_transform(df[feat_cols].values)
    pca_result = pca.fit_transform(embeddings)
    #pk.dump(pca, open("pca.pkl","wb")) #GUARDAMOS EL PCA (OPCIONAL)
    print('ENDED, REPRESENTING')
    print('Explained variation per principal component: {}'.format(pca.explained_variance_ratio_))
    plotColores(pca_result[:,0], pca_result[:,1], [], 'Modelo %s, PCA 2 Dimensiones'%model, model, negros, modo)

def tsne(model, embeddings, negros, modo):
    if not negros:
        embeddings = borraNulos(embeddings, model)
    if embeddings[0].__len__() > 100:
        print('TOO MANY DIMENSIONS, FIRST REDUCE WITH PCA TO 50 DIMENSIONS')
        pca = PCA(n_components=50)
        print('done pca')
        embeddings = pca.fit_transform(embeddings)
        print('done training')
    print(embeddings[0].__len__())
    tsne = TSNE(n_components=2,
                verbose=1,
                perplexity=40,
                init="pca",
                n_iter=250)#300)
    tsne_results = tsne.fit_transform(embeddings)
    print('REDUCED DIMENSIONALITY WITH TSNE, SAVING MODEL')
    saveTSNE(tsne_results=tsne_results, file='tsne_result_%s_negros_%s'%(model, negros))
    print('SAVED MODEL, REPRESENTING')
    plotColores(tsne_results[:,0], tsne_results[:,1], [], 'Modelo %s, TSNE 2 Dimensiones'%model, model, negros, modo)

def saveTSNE(tsne_results, file):
    pd.DataFrame(tsne_results).to_csv('./visualization/TSNE/%s.csv'%file, index=None, header=None)

def loadTSNE(file, model, embeddings, negros, title, modo):
    tsne_results = pd.read_csv('./visualization/TSNE/%s.csv'%file, header = None).to_numpy()
    print('LOADED RESULTS, PLOTTING')
    embeddings = borraNulos(embeddings, model)
    plotColores(x_coor=tsne_results[:, 0], y_coor=tsne_results[:, 1], colors=[], title=title, model=model, negros=negros, modo=modo)

def uMAP(model, embeddings, n_neighbors, n_components):
    umap_model = umap.UMAP(n_neighbors=n_neighbors,
                                n_components=n_components,
                                min_dist=0.0,
                                metric='cosine').fit(embeddings)

    umap_embeddings = umap_model.transform(embeddings)
    print("Reduced dimensionality with UMAP, proceeding to save")
    umap_embeddings = pd.DataFrame(umap_embeddings)
    umap_embeddings.to_csv("./visualization/UMAP_reducedDimensionality/%s_%sD_%sneighbors.csv"%(model, n_components, n_neighbors), header=None, index=None)

def umapping(model, negros, embeddings, df, rndperm, file):
    umap_embeddings = np.array(pd.read_csv('%s'%file, header=None))
    #df['y'] = classes
    if not negros:
        embeddings = borraNulos(embeddings, model)
    ######################
    df['UMAP-one'] = umap_embeddings[:,0]
    df['UMAP-two'] = umap_embeddings[:,1]
    df['UMAP-three'] = umap_embeddings[:,2]
    ######################
    #PARA 3 DIMENSIONES DE UMAP
    ax = plt.figure(figsize=(16,10)).gca(projection='3d')
    ax.scatter(
        ########################
        xs=df.loc[rndperm,:]["UMAP-one"],
        ys=df.loc[rndperm,:]["UMAP-two"],
        zs=df.loc[rndperm,:]["UMAP-three"],
        x = 'x', y = 'y',
        palette= sns.color_palette("hls", list(dict.fromkeys(getTopics(model))).__len__()),
        hue = getTopics(model)
        ################################
        #c=df.loc[rndperm,:]["y"],
        #zs=umap_embeddings[:, 2],
    )
    ax.set_xlabel('UMAP-one')
    ax.set_ylabel('UMAP-two')
    ax.set_zlabel('UMAP-three')
    plt.show()

def processUMAP(file, model, embeddings, negros, modo):
    if not negros:
        embeddings = borraNulos(embeddings, model)
    coor = np.array(pd.read_csv('%s'%file, header=None))
    x_coor = coor[:, 0]
    y_coor = coor[:, 1]
    plotColores(x_coor, y_coor, colors, 'Modelo %s, UMAP 2 Dimensiones'%model, model, negros, modo)

def plotColores(x_coor, y_coor, colors, title, model, negros, modo):
    text = []
    if modo == 'texto':
        text = readTopicText2(model)
        if not negros:
            text = deleteNull(text=text, model=model)
    elif modo == 'topic':
        text =readTopicText(model)
        if not negros:
            text = deleteNull(text=text, model=model)
    if negros:
        hue = getTopics(model)
    else:
        hue = pd.DataFrame(getTopics(model), columns=['cluster'])
        hue = hue[hue['cluster'] != -1]['cluster'].tolist()
    data = pd.DataFrame(np.column_stack([x_coor, y_coor]), columns=['x', 'y'])
    plt.figure(figsize=(25, 9))
    sns.scatterplot(
        x = 'x', y = 'y',
        palette= sns.color_palette("hls", n_colors=list(dict.fromkeys(hue)).__len__()),
        data=data,
        hue = hue,
        legend="brief"
    )
    if text != []:
        for i in range(len(x_coor)):
            plt.text(x_coor[i], y_coor[i], text[i])
    plt.title(title)
    plt.savefig('./images/%s_%s_%s.png'%(model, "_".join(title.split(',')[1].split(' ')), formato))
    plt.show()

def readTopicText(model):
    text=[]
    for line in open('./results/%s/relevant_topics.csv'%model, 'r', encoding='utf-8'):
        text.append(line.replace('\n', '').replace('"',''))
    return text

def readTopicText2(model):
    text=[]
    for line in open('./results/%s/relevants.csv'%model, 'r', encoding='utf-8'):
        text.append(line.replace('\n', '').replace('"',''))
    return text

def deleteNull(text, model):
    topics = getTopics(model=model)
    borrar = []
    i = 0
    for topic in topics:
        i += 1
        if topic == -1:
            borrar.append(i)
    print('DELETED -1 POINTS')
    return np.delete(text, borrar, axis=0)

def visualizeModel(model):
    if not os.path.exists('./visualization/Intertopic'):
        call('mkdir ./visualization/Intertopic', shell=True)

    print('IF DOESN´T WORK GO TO ./anaconda3/lib/python3.8/site-packages/bertopic/_bertopic.py or similar (bertopics library)')
    print('WRITE    fig.write_html(\'./visualization/Intertopic/intertopic.html\') IN LINE 1102')
    modelo = loadModel(model)
    modelo.visualize_topics()
    call('mv ./visualization/Intertopic/intertopic.html ./visualization/Intertopic/%s_intertopic.html'%model, shell=True)
    print('FILE DONE')
