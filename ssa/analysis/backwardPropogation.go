package analysis

import (
	"log"

	"golang.org/x/tools/go/ssa"
)

// propogate backward until find the source
// it may find a value, or a parameter
// in case of parameter, we need to propogate back to callee via ContextAware analysis
func BackwardPropogation(addr ssa.Value, taintedSet map[ssa.Value]bool) (taintedParam int, changed bool) {
	log.Printf("Doing backward propogation on the inst [%s] in function [%s]\n", addr.String(), addr.Parent().String())
	source, _ := BackwardPropogationHelper(addr, []int{}, taintedSet)
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
	return
}

func BackwardPropogationHelper(value ssa.Value, path []int,
	taintedSet map[ssa.Value]bool) (addrSource ssa.Value, fullPath []int) {

	switch typedValue := value.(type) {
	case *ssa.Alloc:
		return value, path
	case *ssa.Call:
		// returned from a Call
		// XXX: assume the Call is just some New function
		return value, path
	case *ssa.ChangeType:
		return BackwardPropogationHelper(typedValue.X, path, taintedSet)
	case *ssa.Extract:
		// extracted from a tuple
		// XXX
		return value, path
	case *ssa.FieldAddr:
		path := append([]int{typedValue.Field}, path...)
		return BackwardPropogationHelper(typedValue.X, path, taintedSet)
	case *ssa.IndexAddr:
		path := append([]int{tryResolveIndex(typedValue.Index)}, path...)
		return BackwardPropogationHelper(typedValue.X, path, taintedSet)
	case *ssa.Parameter:
		return value, path
	case *ssa.MakeInterface:
		return BackwardPropogationHelper(typedValue.X, path, taintedSet)
	case *ssa.Global:
		return value, path
	case *ssa.MakeSlice:
		return value, path
	case *ssa.TypeAssert:
		return BackwardPropogationHelper(typedValue.X, path, taintedSet)
	case *ssa.UnOp:
		return BackwardPropogationHelper(typedValue.X, path, taintedSet)
	default:
		log.Fatalf("Backward propogation: not handle %T: %s\n", typedValue, typedValue)
		return nil, path
	}
}

// try to resolve the dynamic index of a slice
func tryResolveIndex(value ssa.Value) int {
	switch typedValue := value.(type) {
	case *ssa.Const:
		return int(typedValue.Int64())
	}
	return 0
}
