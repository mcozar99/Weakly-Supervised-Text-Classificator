import sys
sys.path.append('.')
sys.path.append('..')
sys.path.append('../../')
sys.path.append('../../../')
import pandas as pd
import numpy as np
from BERTclassifier import getTopics, loadPreprocessedText
from collections import Counter
import random
import matplotlib.pyplot as plt
from sklearn.metrics import f1_score, recall_score, accuracy_score, precision_score, confusion_matrix
import xlwt
from xlrd import open_workbook
from xlutils.copy import copy
from subprocess import call
from config import corpus, relabel, optimus_dictionary, effective_dictionary, evaluacion, label_importance_in_cluster
from config import model_label as model
from labels.common_functions import getTopicList, relabelDict, reclassify, get_label_set
r = lambda: random.randint(0,255) #Generador de numeros aleatorios para colores



def effectiveDictionary(corpus, model):
    # BUILDS THE MOST EFFECTIVE DICTIONARY DEPENDING ON THE TOPIC WITH MOST PRESENCE IN EACH CLUSTER
    topics = getTopicList(corpus)
    clusters = getTopics(model)
    n_clusters = list(dict.fromkeys(clusters))
    f = open('./labels/label_dict/effective_dictionary_%s.txt'%model, 'w', encoding='utf-8')
    for n_cluster in n_clusters:
        if n_cluster == -1:
            f.write('-1,descarte\n')
            continue
        lista_topics = []
        for i in range(len(clusters)):
            if n_cluster == clusters[i]:
                lista_topics.append(topics[i])
        f.write('%s,%s\n'%(n_cluster,Counter(lista_topics).most_common()[0][0]))
    f.close()
    print('DONE EFFECTIVE DICTIONARY')

def optimusDictionary(corpus, model):
    # BUILDS THE MOST OPTIMUS DICTIONARY DEPENDING ON THE TOPIC WITH MOST PRESENCE IN EACH CLUSTER
    topics = getTopicList(corpus)
    clusters = getTopics(model)
    n_clusters = list(dict.fromkeys(clusters))
    lista_perc = [1, 0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.65, 0.60, 0.55, 0.5, 0.45, 0.4, 0.35, 0.3, 0.25, 0.20, 0.15, 0.10, 0.05, 0]
    optimus_dict = {}
    w_prec = 0
    percent = 0
    for perc in lista_perc:
        new_dict = {}
        new_w_prec = 0
        for n_cluster in n_clusters:
            if n_cluster == -1:
                new_dict.update({n_cluster : 'descarte'})
                continue
            lista_topics = []
            for i in range(len(clusters)):
                if n_cluster == clusters[i]:
                    lista_topics.append(topics[i])
            primero = Counter(lista_topics).most_common()[0][1]
            if Counter(lista_topics).most_common().__len__() > 1:
                segundo = Counter(lista_topics).most_common()[1][1]
            else:
                segundo = 0
            if Counter(lista_topics).most_common()[0][0] in ['política', 'otros'] and segundo != 0 and Counter(lista_topics).most_common()[1][0] not in ['política', 'otros']:
                if (primero-segundo)/len(lista_topics) < perc:
                    new_dict.update({n_cluster : Counter(lista_topics).most_common()[1][0]})
                else:
                    new_dict.update({n_cluster : Counter(lista_topics).most_common()[0][0]})
            else:
                new_dict.update({n_cluster : Counter(lista_topics).most_common()[0][0]})
        new_w_prec = w_acc(new_dict, corpus, model)
        print(new_w_prec)
        if w_prec <= new_w_prec:
            optimus_dict = new_dict
            w_prec = new_w_prec
            percent = perc
    print('Final perc = %s \nFinal w_prec = %s'%(percent, w_prec))
    f = open('./labels/label_dict/optimus_dictionary_%s.txt'%model, 'w', encoding='utf-8')
    for i in range(optimus_dict.values().__len__()):
        f.write(str(list(optimus_dict.keys())[i]) + ',' + list(optimus_dict.values())[i] + '\n')
    f.close()
    print('DONE OPTIMUS DICTIONARY')

def w_acc(dictionary, corpus, model):
    y_pred = getTopics(model)
    for i in range(len(y_pred)):
        y_pred[i] = dictionary.get(y_pred[i])
    y_true = getTopicList(corpus)
    topic_set = list(dict.fromkeys(y_true))
    accuracy_list = []
    for topic in topic_set:
        corrects = 0
        for i in range(len(y_pred)):
            if topic in y_pred[i] and y_pred[i] in y_true[i]:
                corrects += 1
        accuracy_list.append(corrects / Counter(y_true)[topic])
    return sum(accuracy_list)/len(accuracy_list)


def accuracy(old_topics, new_topics):
    # CALCULATES GENERAL PRECISION
    a = 0
    for i in range(len(old_topics)):
        if new_topics[i] not in old_topics[i]:
            a +=1
    print('ENTRADAS CLASIFICADAS CORRECTAMENTE: %s'%(len(old_topics) - a))
    print('ENTRADAS MAL CLASIFICADAS: %s'%a)
    print('ACCURACY: ' + '{:.2%}'.format((len(old_topics)-a)/len(old_topics)))
    return (len(old_topics)-a) / len(old_topics)

def weightedAccuracy(accuracy_list):
    weighted_accuracy = sum(accuracy_list)/len(accuracy_list)
    print('WEIGHTED ACCURACY: %s'%weighted_accuracy)
    return weighted_accuracy

def topicsEnCluster(n_cluster, model, corpus):
    # GETS THE DISTRIBUTION OF LABELS THAT HAS A GIVEN CLUSTER
    clusters = getTopics(model)
    old_topics = getTopicList(corpus)
    lista_topics = []
    for i in range(len(clusters)):
        if n_cluster == clusters[i]:
            lista_topics.append(old_topics[i])
    print('LISTA TEMAS CLUSTER %s'%n_cluster)
    print(Counter(lista_topics))


def accuracyXTopic(corpus, model, relabel):
    # HISTOGRAM OF PRECISION IN EACH TOPIC OF A MODEL
    clasification = reclassify(relabel, model)
    topics = getTopicList(corpus)
    topic_set = get_label_set(corpus)
    accuracy_list = []
    df = pd.DataFrame(columns = ['Corrects', 'Total', 'Accuracy'], index=topic_set)
    for topic in topic_set:
        corrects = 0
        for i in range(len(clasification)):
            if topic in clasification[i] and clasification[i] in topics[i]:
                corrects+=1
        accuracy_list.append(corrects/Counter(topics)[topic])
        df.loc[topic] = [corrects, Counter(topics)[topic], '{:.2%}'.format(corrects/Counter(topics)[topic])]
    print(df)
    x_values = np.arange(1, len(topic_set) + 1, 1)
    plt.bar(x_values, accuracy_list).set_label('Accuracy per topic')
    plt.title("Distribución de accuracy por tema en modelo %s"%model)
    plt.xticks(x_values, topic_set)
    plt.xlabel("Topics")
    plt.axhline(y=accuracy(topics, clasification), color="red", linestyle="--").set_label('Global Accuracy')
    plt.axhline(y=weightedAccuracy(accuracy_list), color='black', linestyle='--').set_label('Weighted Accuracy')
    plt.grid()
    plt.legend()
    plt.ylabel("Accuracy")
    plt.show()

def evaluation(corpus, model, relabel):
    call('mkdir ./results/%s/evaluation'%model, shell=True)
    print('EVALUATING MODEL: %s'%model)
    y_pred = reclassify(relabel, model)
    y_true = getTopicList(corpus)
    label_set = get_label_set(corpus)
    acc = accuracy_score(y_true=y_true, y_pred=y_pred)
    prec = precision_score(y_true=y_true, y_pred=y_pred, labels=label_set, average='weighted')
    recall = recall_score(y_true=y_true, y_pred=y_pred, labels=label_set, average='weighted')
    f1 = f1_score(y_true=y_true, y_pred=y_pred, labels=label_set, average='weighted')
    print('ACC: %s \nPREC: %s \nRECALL: %s \nF1: %s'%(acc, prec, recall, f1))
    cm = confusion_matrix(y_true, y_pred, label_set)
    confusion_m = []
    for line in cm:
        confusion_m.append(line)
    ##################################### RESULTS TO EXCEL
    matrix = pd.DataFrame(confusion_m, index=label_set,columns=label_set)
    matrix.to_excel('./results/%s/evaluation/first_evaluation.xls'%model, columns=label_set, index=label_set, startcol=1, startrow=1, merge_cells=True)
    rb = open_workbook('./results/%s/evaluation/first_evaluation.xls'%model)
    wb = copy(rb)
    w_sheet = wb.get_sheet(0)
    w_sheet.write(0, 0, model)
    w_sheet.write(len(label_set) + 2, 1, 'ACC', xlwt.easyxf('font: bold 1'))
    w_sheet.write(len(label_set) + 3, 1, 'PREC', xlwt.easyxf('font: bold 1'))
    w_sheet.write(len(label_set) + 4, 1, 'RECALL', xlwt.easyxf('font: bold 1'))
    w_sheet.write(len(label_set) + 5, 1, 'F1', xlwt.easyxf('font: bold 1'))
    w_sheet.write(len(label_set) + 2, 2, acc)
    w_sheet.write(len(label_set) + 3, 2, prec)
    w_sheet.write(len(label_set) + 4, 2, recall)
    w_sheet.write(len(label_set) + 5, 2, f1)
    wb.save('./results/%s/evaluation/first_evaluation.xls'%model)
    #################################### EDIT EXCEL
    print(matrix.to_string())



if effective_dictionary:
    effectiveDictionary(corpus, model)
if optimus_dictionary:
    optimusDictionary(corpus, model)
if label_importance_in_cluster:
    clusters = list(dict.fromkeys(getTopics(model)))
    for cluster in clusters:
        topicsEnCluster(cluster, model, corpus)
if evaluacion:
    evaluation(corpus, model, relabel)
    accuracyXTopic(corpus,model,relabel)
