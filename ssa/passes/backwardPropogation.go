package analysis

import (
	"log"

	"golang.org/x/tools/go/ssa"
)

// propogate backward until find the source
// it may find a value, or a parameter
// in case of parameter, we need to propogate back to callee via ContextAware analysis
func BackwardPropogation(addr ssa.Value, taintedSet map[ssa.Value]bool) (taintedParam int, changed bool) {
	if addr.Parent() != nil {
		log.Printf("Doing backward propogation on the inst [%s] in function [%s]\n", addr.String(), addr.Parent().String())
	}

	addrSources := BackwardPropogationHelper(addr, []int{}, taintedSet, map[ssa.Value]bool{})

	for _, source := range addrSources {
		log.Printf("It is from %s\n", source)
		if _, ok := taintedSet[source]; !ok {
			taintedSet[source] = true
			changed = true
		}
		taintedParam = -1
		if sourceParam, ok := source.(*ssa.Parameter); ok {
			for i, param := range addr.Parent().Params {
				if param == sourceParam {
					taintedParam = i
					log.Printf("Tainted %dth parameter\n", i)
				}
			}
		}
	}
	return
}

func BackwardPropogationHelper(value ssa.Value, path []int,
	taintedSet map[ssa.Value]bool, phiSet map[ssa.Value]bool) (addrSources []ssa.Value) {

	switch typedValue := value.(type) {
	case *ssa.Alloc:
		return []ssa.Value{value}
	case *ssa.Call:
		// returned from a Call
		// XXX: assume the Call is just some New function
		return []ssa.Value{value}
	case *ssa.ChangeInterface:
		return BackwardPropogationHelper(typedValue.X, path, taintedSet, phiSet)
	case *ssa.ChangeType:
		return BackwardPropogationHelper(typedValue.X, path, taintedSet, phiSet)
	case *ssa.Const:
		if typedValue.Value == nil {
			return []ssa.Value{}
		}
		log.Printf("Const: %s\n", typedValue.Value)
		log.Fatalf("Backward propogation: not handle %T: %s\n", typedValue, typedValue)
	case *ssa.Convert:
		return BackwardPropogationHelper(typedValue.X, path, taintedSet, phiSet)
	case *ssa.Extract:
		// extracted from a tuple
		// XXX
		switch typedTuple := typedValue.Tuple.(type) {
		case *ssa.Lookup:
			return BackwardPropogationHelper(typedTuple, path, taintedSet, phiSet)
		case *ssa.TypeAssert:
			return BackwardPropogationHelper(typedTuple, path, taintedSet, phiSet)
		case *ssa.UnOp:
			log.Fatal("Back propogated to UpOp\n")
		}
		return []ssa.Value{value}
	case *ssa.FieldAddr:
		path := append([]int{typedValue.Field}, path...)
		return BackwardPropogationHelper(typedValue.X, path, taintedSet, phiSet)
	case *ssa.FreeVar:
		return []ssa.Value{value}
	case *ssa.IndexAddr:
		path := append([]int{tryResolveIndex(typedValue.Index)}, path...)
		return BackwardPropogationHelper(typedValue.X, path, taintedSet, phiSet)
	case *ssa.Lookup:
		return BackwardPropogationHelper(typedValue.X, path, taintedSet, phiSet)
	case *ssa.Parameter:
		return []ssa.Value{value}
	case *ssa.Phi:
		ret := []ssa.Value{}
		for _, edge := range typedValue.Edges {
			if _, ok := phiSet[edge]; !ok {
				// edge could be itself, avoid infinite loop
				// XXX: still possibly circular dependency
				phiSet[edge] = true
				ret = append(ret, BackwardPropogationHelper(edge, path, taintedSet, phiSet)...)
			}
		}
		return ret
	case *ssa.MakeInterface:
		return BackwardPropogationHelper(typedValue.X, path, taintedSet, phiSet)
	case *ssa.Global:
		addrSources = append(addrSources, value)
	case *ssa.MakeMap:
		return []ssa.Value{value}
	case *ssa.MakeSlice:
		addrSources = append(addrSources, value)
	case *ssa.Slice:
		return BackwardPropogationHelper(typedValue.X, path, taintedSet, phiSet)
	case *ssa.TypeAssert:
		return BackwardPropogationHelper(typedValue.X, path, taintedSet, phiSet)
	case *ssa.UnOp:
		return BackwardPropogationHelper(typedValue.X, path, taintedSet, phiSet)
	default:
		log.Fatalf("Backward propogation: not handle %T: %s\n", typedValue, typedValue)
		return
	}
	return
}

// try to resolve the dynamic index of a slice
func tryResolveIndex(value ssa.Value) int {
	switch typedValue := value.(type) {
	case *ssa.Const:
		return int(typedValue.Int64())
	}
	return 0
}
