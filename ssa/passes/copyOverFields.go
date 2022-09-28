package analysis

import (
	"go/types"
	"log"
	"strings"

	"github.com/xlab-uiuc/acto/ssa/util"
	"golang.org/x/tools/go/ssa"
)

func GetCopyOverFields(context *Context) (fields util.FieldSet) {
	// fieldToValueMap := context.FieldToValueMap
	ValueFieldMap := context.ValueFieldMap
	storeInsts := context.StoreInsts

	for _, storeInst := range storeInsts {
		storeInst := storeInst.(*ssa.Store)
		value := storeInst.Val
		addr := storeInst.Addr

		source := SimplyBackwardPropogation(context, addr)
		if source != nil && strings.Contains(source.Type().String(), "*k8s.io/api") {
			if _, ok := value.Type().Underlying().(*types.Struct); ok {
				fields.Extend(ValueFieldMap[value])
			} else if pointer, ok := value.Type().Underlying().(*types.Pointer); ok {
				if _, ok := pointer.Elem().Underlying().(*types.Struct); ok {
					fields.Extend(ValueFieldMap[value])
				} else if _, ok := pointer.Elem().Underlying().(*types.Slice); ok {
					fields.Extend(ValueFieldMap[value])
				}
			} else if _, ok := value.Type().Underlying().(*types.Slice); ok {
				fields.Extend(ValueFieldMap[value])
			}
			log.Printf("Found a copy over field: %s [%s] copied to [%s] at %s\n", ValueFieldMap[value], value, source.Type().String(), value.Parent().Pkg.Prog.Fset.Position(value.Pos()))
		}
	}
	return
}

func SimplyBackwardPropogation(context *Context, value ssa.Value) ssa.Value {
	switch typedValue := value.(type) {
	case *ssa.Alloc:
		return typedValue
	case *ssa.Call:
		// returned from a Call
		return typedValue
	case *ssa.ChangeType:
		return SimplyBackwardPropogation(context, typedValue.X)
	case *ssa.Convert:
		return SimplyBackwardPropogation(context, typedValue.X)
	case *ssa.Extract:
		// extracted from a tuple
		// XXX
		switch typedTuple := typedValue.Tuple.(type) {
		case *ssa.Lookup:
			return SimplyBackwardPropogation(context, typedTuple)
		case *ssa.TypeAssert:
			return SimplyBackwardPropogation(context, typedTuple)
		case *ssa.UnOp:
			log.Fatal("Back propogated to UnOp\n")
		}
		return typedValue
	case *ssa.FieldAddr:
		return SimplyBackwardPropogation(context, typedValue.X)
	case *ssa.FreeVar:
		return typedValue
	case *ssa.IndexAddr:
		return SimplyBackwardPropogation(context, typedValue.X)
	case *ssa.Lookup:
		return SimplyBackwardPropogation(context, typedValue.X)
	case *ssa.Parameter:
		return typedValue
	case *ssa.Phi:
		// XXX
		return typedValue
	case *ssa.MakeInterface:
		return SimplyBackwardPropogation(context, typedValue.X)
	case *ssa.MakeMap:
		return typedValue
	case *ssa.MakeSlice:
		return typedValue
	case *ssa.Slice:
		return SimplyBackwardPropogation(context, typedValue.X)
	case *ssa.TypeAssert:
		return SimplyBackwardPropogation(context, typedValue.X)
	case *ssa.UnOp:
		return SimplyBackwardPropogation(context, typedValue.X)
	default:
		log.Fatalf("Backward propogation: not handle %T: %s\n", typedValue, typedValue)
		return nil
	}
}
