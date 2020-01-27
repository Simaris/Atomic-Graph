import rdflib
from atomicgraphs.coloring import IsomorphicPartitioner


class AtomicGraphFactory:
    def __init__(self, graph):
        self.graph = rdflib.Graph('AtomicStore')
        # make a copy of the graph so the original does not get consumed
        self.graph += graph
        self.atomicGraphs = set()
        self.currentAtomicGraph = rdflib.Graph(store=self.graph.store)
        self.nextNodeOther = []
        self.nextNodeBlank = []
        self.nextNodeCurrent = []
        self.iter = None

    def __iter__(self):
        if self.iter is None:
            self._run()
            self.iter = iter(self.atomicGraphs)
        return self

    def __next__(self):
        graph = next(self.iter)
        if graph:
            partitioner = IsomorphicPartitioner()
            aGraph = AtomicGraph(store=graph.store, identifier=graph.identifier,
                                 namespace_manager=graph.namespace_manager)
            aGraph.colourPartitions = partitioner.partitionIsomorphic(graph)
            return aGraph
        else:
            raise StopIteration

    def _blank_node_adding(self, node):
        if(isinstance(node, rdflib.BNode)):
            self.nextNodeCurrent.append(node)
        else:
            self.nextNodeOther.append(node)

    def _atomic(self, statement, newNode):
        if(not isinstance(statement[newNode], rdflib.BNode)):
            newAtomicGraph = rdflib.Graph(store=self.graph.store)
            self.graph.store.moveStatement(statement, source=self.graph, destination=newAtomicGraph)
            self.atomicGraphs.add(newAtomicGraph)
            self.nextNodeOther.append(statement[newNode])
        else:
            self.nextNodeBlank.append(statement[newNode])

    def _analyse_node(self, node):
        if(isinstance(node, rdflib.BNode)):
            for tupel in iter(self.graph.predicate_objects(node)):
                self.graph.store.moveStatement((node, tupel[0], tupel[1]), source=self.graph,
                                               destination=self.currentAtomicGraph)
                self._blank_node_adding(tupel[1])
            for tupel in iter(self.graph.subject_predicates(node)):
                self.graph.store.moveStatement((tupel[0], tupel[1], node), source=self.graph,
                                               destination=self.currentAtomicGraph)
                self._blank_node_adding(tupel[0])
        else:
            for tupel in iter(self.graph.predicate_objects(node)):
                self._atomic((node, tupel[0], tupel[1]), 2)

            for tupel in iter(self.graph.subject_predicates(node)):
                self._atomic((tupel[0], tupel[1], node), 0)

    def _next_node(self):
        if(self.nextNodeCurrent):
            return self.nextNodeCurrent.pop()
        # if no further nodes are found the current atomic graph is done
        if(self.currentAtomicGraph):
            self.atomicGraphs.add(self.currentAtomicGraph)
            self.currentAtomicGraph = rdflib.Graph(store=self.graph.store)
        if(self.nextNodeBlank):
            return self.nextNodeBlank.pop()
        if(self.nextNodeOther):
            return self.nextNodeOther.pop()
        return False

    def _run(self):
        for subjectsOrObjects in [self.graph.subjects(), self.graph.objects()]:
            for node in subjectsOrObjects:
                self._analyse_node(node)
                node = self._next_node()
                while(node):  # empty lists are falsy
                    self._analyse_node(node)
                    node = self._next_node()


class AtomicGraph(rdflib.Graph):
    def __init__(self, store='default', identifier=None, namespace_manager=None):
        super().__init__(store, identifier, namespace_manager)
        self._hashOn = False

    def __eq__(self, value):
        if isinstance(value, AtomicGraph):
            return self.__hash__() == value.__hash__()
        else:
            return super().__eq__(value)

    def __hash__(self):
        if(self._hashOn):
            return self.colourPartitions.__hash__()
        else:
            return super().__hash__()

    def __str__(self):
        result = ""
        for subj, pred, obj in self:
            result += "{0} {1} {2}.\n".format(self.colourPartitions[subj],
                                              self.colourPartitions[pred],
                                              self.colourPartitions[obj])
        return result

    def __repr__(self):
        return "AtomicHashGraph(#IsoPartitions: {})".format(len(self.colourPartitions))

    def switchOnHash(self):
        self._hashOn = True

    @property
    def colourPartitions(self):
        return self._colourPartitions

    @colourPartitions.setter
    def colourPartitions(self, partition):
        self._colourPartitions = partition
        self.store.switchID(self)
