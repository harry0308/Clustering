import itertools
import pandas as pd
from tqdm.auto import tqdm
from algorithms.chameleon.graphtools import *


def len_edges(graph, cluster):
    cluster = graph.subgraph(cluster)
    edges = cluster.edges()
    return len(edges)


def internal_interconnectivity(graph, cluster):
    return np.sum(bisection_weights(graph, cluster))


def relative_interconnectivity(graph, cluster_i, cluster_j):
    edges = connecting_edges((cluster_i, cluster_j), graph)
    if not edges:
        return 0.0
    EC = np.sum(get_weights(graph, edges))
    ECci, ECcj = internal_interconnectivity(graph, cluster_i), internal_interconnectivity(graph, cluster_j)
    return EC / ((ECci + ECcj) / 2.0)


def internal_closeness(graph, cluster):
    cluster = graph.subgraph(cluster)
    edges = cluster.edges()
    weights = get_weights(cluster, edges)
    return np.sum(weights)


def relative_closeness(graph, cluster_i, cluster_j):
    edges = connecting_edges((cluster_i, cluster_j), graph)
    if not edges:
        return 0.0
    else:
        SEC = np.mean(get_weights(graph, edges))
    # originally by Moonpuck
    # Ci, Cj = internal_closeness(graph, cluster_i), internal_closeness(graph, cluster_j)
    # original paper
    Ci, Cj = len(cluster_i), len(cluster_j)
    # paper of chameleon2
    # Ci,Cj = len_edges(graph, cluster_i), len_edges(graph, cluster_j)
    SECci, SECcj = np.mean(bisection_weights(graph, cluster_i)), np.mean(bisection_weights(graph, cluster_j))
    return SEC / ((Ci / (Ci + Cj) * SECci) + (Cj / (Ci + Cj) * SECcj))


def merge_score(g, ci, cj, a):
    ri = relative_interconnectivity(g, ci, cj)
    rc_pot = np.power(relative_closeness(g, ci, cj), a)
    # print("relative_interconnectivity: ", ri)
    # print("relative_closeness^alpha: ", rc_pot)
    if (ri != 0) and (rc_pot != 0):
        return ri * rc_pot
    else:
        return ri + rc_pot


def merge_best(graph, df, a, k, verbose=False, verbose2=True):
    clusters = np.unique(df['cluster'])
    max_score = 0
    ci, cj = -1, -1
    if len(clusters) <= k:
        return False

    for combination in itertools.combinations(clusters, 2):
        i, j = combination
        if i != j:
            if verbose:
                print("Checking c%d c%d" % (i, j))
            gi = get_cluster(graph, [i])
            gj = get_cluster(graph, [j])
            edges = connecting_edges((gi, gj), graph)
            if not edges:
                continue
            ms = merge_score(graph, gi, gj, a)
            if verbose:
                print("Merge score: %f" % ms)
            if ms > max_score:
                if verbose:
                    print("Better than: %f" % max_score)
                max_score = ms
                ci, cj = i, j

    if max_score > 0:
        if verbose2:
            print("Merging c%d and c%d" % (ci, cj))
            print("score: ", max_score)

        df.loc[df['cluster'] == cj, 'cluster'] = ci
        for i, p in enumerate(graph.nodes()):
            if graph.node[p]['cluster'] == cj:
                graph.node[p]['cluster'] = ci
    else:
        print("No Merging")
        print("score: ", max_score)
        print("early stopping")

    return df, max_score, ci


def cluster(df, k, knn=10, m=30, alpha=2.0, verbose=True, verbose2=True, plot=True):
    if k is None:
        k = 1

    print("Building kNN graph (k = %d)..." % knn)
    graph = knn_graph(df, knn, verbose)

    plot2d_graph(graph, print_clust=False)

    graph = pre_part_graph(graph, m, df, verbose, plotting=plot)

    # to account for cases where initial_clust is too big or k is already reached before the merging phase
    cl_dict = {list(graph.node)[i]: graph.node[i]["cluster"] for i in range(len(graph))}
    m = len(Counter(cl_dict.values()))
    print("actual init_clust: {}".format(m))

    dendr_height = {}
    iterm = tqdm(enumerate(range(m - k)), total=m - k) if verbose else enumerate(range(m - k))

    for i, _ in iterm:

        df, ms, ci = merge_best(graph, df, alpha, k, False, verbose2)

        if ms == 0:
            break

        dendr_height[m - (i + 1)] = ms

        if plot:
            plot2d_data(df, ci)

    res = rebuild_labels(df)

    return res, dendr_height


def rebuild_labels(df):
    ans = df.copy()
    clusters = list(pd.DataFrame(df['cluster'].value_counts()).index)
    c = 1
    for i in clusters:
        ans.loc[df['cluster'] == i, 'cluster'] = c
        c = c + 1
    return ans
