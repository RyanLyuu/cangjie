# commons-graph cjpm build 结果

```
[31merror[0m: undeclared type name 'Set'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/collections/FibonacciHeap.cj:11:24:
   [36m| [0m
[36m11[0m [36m| [0m    let elementsIndex: Set<Any> = throw Exception('TODO')[0m
   [36m| [0m                       [31m^ [0m
   [36m| [0m

[31merror[0m: type argument's number does not match type parameter's number
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/collections/DisjointSet.cj:10:36:
   [36m| [0m
[36m10[0m [36m| [0m    let disjointSets: HashMap<Any, DisjointSetNode<Any>> = throw Exception('TODO')[0m
   [36m| [0m                                   [31m^^^^^^^^^^^^^^^^^^^^ [0m
   [36m| [0m

[31merror[0m: generics type arguments do not match the constraint of 'Class-HashMap<Generics-K, Generics-V>'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/collections/DisjointSet.cj:10:31:
   [36m| [0m
[36m10[0m [36m| [0m    let disjointSets: HashMap<Any, DisjointSetNode<Any>> = throw Exception('TODO')[0m
   [36m| [0m                              [31m^ [0m
   [36m| [0m
[34mnote[0m: 'Interface-Any' is not a subtype of 'Interface-Hashable'
   [36m==>[0m (package std.collection)hash_map.cj:335:47:

[31merror[0m: type argument's number does not match type parameter's number
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/collections/DisjointSet.cj:14:52:
   [36m| [0m
[36m14[0m [36m| [0m    private func find(node: DisjointSetNode<Any>): DisjointSetNode<Any> {[0m
   [36m| [0m                                                   [31m^^^^^^^^^^^^^^^^^^^^ [0m
   [36m| [0m

[31merror[0m: type argument's number does not match type parameter's number
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/collections/DisjointSet.cj:14:29:
   [36m| [0m
[36m14[0m [36m| [0m    private func find(node: DisjointSetNode<Any>): DisjointSetNode<Any> {[0m
   [36m| [0m                            [31m^^^^^^^^^^^^^^^^^^^^ [0m
   [36m| [0m

[31merror[0m: type argument's number does not match type parameter's number
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/collections/DisjointSet.cj:22:35:
   [36m| [0m
[36m22[0m [36m| [0m    private func getNode(e: Any): DisjointSetNode<Any> {[0m
   [36m| [0m                                  [31m^^^^^^^^^^^^^^^^^^^^ [0m
   [36m| [0m

[31merror[0m: type argument's number does not match type parameter's number
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/collections/DisjointSetNode.cj:11:17:
   [36m| [0m
[36m11[0m [36m| [0m    var parent: DisjointSetNode<Any> = throw Exception('TODO')[0m
   [36m| [0m                [31m^^^^^^^^^^^^^^^^^^^^ [0m
   [36m| [0m

[31merror[0m: type argument's number does not match type parameter's number
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/collections/DisjointSetNode.cj:20:35:
   [36m| [0m
[36m20[0m [36m| [0m    public open func compareTo(o: DisjointSetNode<Any>): Int32 {[0m
   [36m| [0m                                  [31m^^^^^^^^^^^^^^^^^^^^ [0m
   [36m| [0m

33 errors generated, 8 errors printed.
Error: failed to compile package `commons_graph.collections`, return code is 1
[31merror[0m: undeclared type name 'DirectedGraph'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/elo/DefaultKFactorBuilder.cj:13:26:
   [36m| [0m
[36m13[0m [36m| [0m    let tournamentGraph: DirectedGraph<Any, Any> = throw Exception('TODO')[0m
   [36m| [0m                         [31m^ [0m
   [36m| [0m

[31merror[0m: undeclared type name 'DirectedGraph'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/elo/DefaultKFactorBuilder.cj:22:34:
   [36m| [0m
[36m22[0m [36m| [0m    public init(tournamentGraph: DirectedGraph<Any, Any>, playerRanking: PlayersRank<Any>) {[0m
   [36m| [0m                                 [31m^ [0m
   [36m| [0m

[31merror[0m: undeclared type name 'DirectedGraph'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/elo/DefaultRankingSelector.cj:10:26:
   [36m| [0m
[36m10[0m [36m| [0m    let tournamentGraph: DirectedGraph<Any, Any> = throw Exception('TODO')[0m
   [36m| [0m                         [31m^ [0m
   [36m| [0m

[31merror[0m: undeclared type name 'DirectedGraph'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/elo/DefaultRankingSelector.cj:14:34:
   [36m| [0m
[36m14[0m [36m| [0m    public init(tournamentGraph: DirectedGraph<Any, Any>) {[0m
   [36m| [0m                                 [31m^ [0m
   [36m| [0m

[31merror[0m: type argument's number does not match type parameter's number
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/elo/DefaultKFactorBuilder.cj:14:24:
   [36m| [0m
[36m14[0m [36m| [0m    let playerRanking: PlayersRank<Any> = throw Exception('TODO')[0m
   [36m| [0m                       [31m^^^^^^^^^^^^^^^^ [0m
   [36m| [0m

[31merror[0m: type argument's number does not match type parameter's number
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/elo/DefaultKFactorBuilder.cj:22:74:
   [36m| [0m
[36m22[0m [36m| [0m    public init(tournamentGraph: DirectedGraph<Any, Any>, playerRanking: PlayersRank<Any>) {[0m
   [36m| [0m                                                                         [31m^^^^^^^^^^^^^^^^ [0m
   [36m| [0m

[31merror[0m: type argument's number does not match type parameter's number
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/elo/DefaultRankingSelector.cj:18:78:
   [36m| [0m
[36m18[0m [36m| [0m    public open func wherePlayersAreRankedIn(playersRank: PlayersRank<Any>): KFactorBuilder<Any> {[0m
   [36m| [0m                                                                             [31m^^^^^^^^^^^^^^^^^^^ [0m
   [36m| [0m

[31merror[0m: type argument's number does not match type parameter's number
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/elo/DefaultRankingSelector.cj:18:59:
   [36m| [0m
[36m18[0m [36m| [0m    public open func wherePlayersAreRankedIn(playersRank: PlayersRank<Any>): KFactorBuilder<Any> {[0m
   [36m| [0m                                                          [31m^^^^^^^^^^^^^^^^ [0m
   [36m| [0m

10 errors generated, 8 errors printed.
Error: failed to compile package `commons_graph.elo`, return code is 1
[31merror[0m: undeclared type name 'ColorsBuilder'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/CommonsGraph.cj:13:46:
   [36m| [0m
[36m13[0m [36m| [0m    public static func coloring(graph: Any): ColorsBuilder<Any, Any> {[0m
   [36m| [0m                                             [31m^ [0m
   [36m| [0m

[31merror[0m: undeclared type name 'RankingSelector'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/CommonsGraph.cj:17:55:
   [36m| [0m
[36m17[0m [36m| [0m    public static func eloRate(tournamentGraph: Any): RankingSelector<Any> {[0m
   [36m| [0m                                                      [31m^ [0m
   [36m| [0m

[31merror[0m: undeclared type name 'NamedExportSelector'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/CommonsGraph.cj:21:44:
   [36m| [0m
[36m21[0m [36m| [0m    public static func export(graph: Any): NamedExportSelector<Any, Any> {[0m
   [36m| [0m                                           [31m^ [0m
   [36m| [0m

[31merror[0m: undeclared type name 'ConnectivityBuilder'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/CommonsGraph.cj:25:60:
   [36m| [0m
[36m25[0m [36m| [0m    public static func findConnectedComponent(graph: Any): ConnectivityBuilder<Any, Any> {[0m
   [36m| [0m                                                           [31m^ [0m
   [36m| [0m

[31merror[0m: undeclared type name 'FlowWeightedEdgesBuilder'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/CommonsGraph.cj:29:49:
   [36m| [0m
[36m29[0m [36m| [0m    public static func findMaxFlow(graph: Any): FlowWeightedEdgesBuilder<Any, Any> {[0m
   [36m| [0m                                                [31m^ [0m
   [36m| [0m

[31merror[0m: undeclared type name 'PathWeightedEdgesBuilder'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/CommonsGraph.cj:33:54:
   [36m| [0m
[36m33[0m [36m| [0m    public static func findShortestPath(graph: Any): PathWeightedEdgesBuilder<Any, Any> {[0m
   [36m| [0m                                                     [31m^ [0m
   [36m| [0m

[31merror[0m: undeclared type name 'SccAlgorithmSelector'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/CommonsGraph.cj:37:68:
   [36m| [0m
[36m37[0m [36m| [0m    public static func findStronglyConnectedComponent(graph: Any): SccAlgorithmSelector<Any, Any> {[0m
   [36m| [0m                                                                   [31m^ [0m
   [36m| [0m

[31merror[0m: undeclared type name 'SpanningWeightedEdgeMapperBuilder'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/CommonsGraph.cj:41:57:
   [36m| [0m
[36m41[0m [36m| [0m    public static func minimumSpanningTree(graph: Any): SpanningWeightedEdgeMapperBuilder<Any, Any> {[0m
   [36m| [0m                                                        [31m^ [0m
   [36m| [0m

31 errors generated, 8 errors printed.
Error: failed to compile package `commons_graph`, return code is 1
[31merror[0m: undeclared type name 'MutableGraph'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/builder/DefaultGrapher.cj:10:16:
   [36m| [0m
[36m10[0m [36m| [0m    let graph: MutableGraph<Any, Any> = throw Exception('TODO')[0m
   [36m| [0m               [31m^ [0m
   [36m| [0m

[31merror[0m: undeclared type name 'MutableGraph'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/builder/DefaultGrapher.cj:14:24:
   [36m| [0m
[36m14[0m [36m| [0m    public init(graph: MutableGraph<Any, Any>) {[0m
   [36m| [0m                       [31m^ [0m
   [36m| [0m

[31merror[0m: undeclared type name 'MutableGraph'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/builder/DefaultHeadVertexConnector.cj:10:16:
   [36m| [0m
[36m10[0m [36m| [0m    let graph: MutableGraph<Any, Any> = throw Exception('TODO')[0m
   [36m| [0m               [31m^ [0m
   [36m| [0m

[31merror[0m: undeclared type name 'MutableGraph'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/builder/DefaultHeadVertexConnector.cj:15:24:
   [36m| [0m
[36m15[0m [36m| [0m    public init(graph: MutableGraph<Any, Any>, edge: Any) {[0m
   [36m| [0m                       [31m^ [0m
   [36m| [0m

[31merror[0m: undeclared type name 'MutableGraph'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/builder/DefaultTailVertexConnector.cj:10:16:
   [36m| [0m
[36m10[0m [36m| [0m    let graph: MutableGraph<Any, Any> = throw Exception('TODO')[0m
   [36m| [0m               [31m^ [0m
   [36m| [0m

[31merror[0m: undeclared type name 'MutableGraph'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/builder/DefaultTailVertexConnector.cj:16:24:
   [36m| [0m
[36m16[0m [36m| [0m    public init(graph: MutableGraph<Any, Any>, edge: Any, head: Any) {[0m
   [36m| [0m                       [31m^ [0m
   [36m| [0m

[31merror[0m: type argument's number does not match type parameter's number
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/builder/AbstractGraphConnection.cj:10:20:
   [36m| [0m
[36m10[0m [36m| [0m    var connector: GraphConnector<Any, Any> = throw Exception('TODO')[0m
   [36m| [0m                   [31m^^^^^^^^^^^^^^^^^^^^^^^^ [0m
   [36m| [0m

[31merror[0m: type argument's number does not match type parameter's number
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-graph/src/builder/AbstractGraphConnection.cj:14:39:
   [36m| [0m
[36m14[0m [36m| [0m    protected func addEdge(arc: Any): HeadVertexConnector<Any, Any> {[0m
   [36m| [0m                                      [31m^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ [0m
   [36m| [0m

16 errors generated, 8 errors printed.
Error: failed to compile package `commons_graph.builder`, return code is 1
Error: cjpm build failed
```
