package util

import (
	"log"

	"golang.org/x/tools/go/callgraph"
	"golang.org/x/tools/go/ssa"
)

// returns all the possible callees at the callSite in the callGraph
func CalleeSet(callGraph *callgraph.Graph, callSite ssa.CallInstruction) (calleeSet []*ssa.Function) {
	log.Printf("Trying to get the callee set for %s\n", callSite.String())
	node := callGraph.Nodes[callSite.Parent()]

	for _, outEdge := range node.Out {
		if outEdge.Site == callSite {
			calleeSet = append(calleeSet, outEdge.Callee.Func)
		}
	}
	log.Printf("Got %d callees\n", len(calleeSet))
	return
}
