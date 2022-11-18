package analysis

import (
	"go/token"
	"go/types"
	"log"
	"reflect"
	"strings"

	. "github.com/xlab-uiuc/acto/ssa/util"
	"golang.org/x/tools/go/ssa"
)

// Forward pass
// Introduction:
// 	- all values of type seedType
// Propogation rule:
// 	- Call: to the specific parameter of the callee
// 	- ChangeInterface
//	- ChangeType
//	- Convert
//	- Field: propogate with field name
//	- FieldAddr: propogate with field name
//	- Index: propogate with index
//	- IndexAddr: propogate with index
//	- MakeInterface
//	- LookUp: TODO if used as X, propogate
//	- Phi: propogate with merged paths
//	- UnOp: propogate if dereference
//	- Store: TODO propogate backward
//	- Return + Extract: TODO propogate to function callsites
// Sink:
//	- Stop at all other instruction types
//	- Stop propogation when calling library functions
//
// Frontier values:
//	- if all a value's all referrers are propogated, it's not frontier
func GetValueToFieldMappingPass(context *Context, prog *ssa.Program, seedType *string, seedPkgPath *string) (map[ssa.Value]*FieldSet, map[ssa.Value]bool) {
	valueFieldSetMap := make(map[ssa.Value]*FieldSet)
	frontierValues := make(map[ssa.Value]bool)
	seedVariables := FindSeedValues(prog, seedType, seedPkgPath)
	worklist := []ssa.Value{}

	// this is the tree including all the direct subfields
	root := NewFieldNode()
	root.InitName(root, "root")
	context.FieldTree = root
	valueToFieldNodeSetMap := context.ValueToFieldNodeSetMap

	for _, seedVariable := range seedVariables {
		rootField := []string{"root"}
		valueFieldSetMap[seedVariable] = NewFieldSet()
		valueFieldSetMap[seedVariable].Add(&Field{
			Path: rootField,
		})

		root.AddValue(seedVariable)
		valueToFieldNodeSetMap.Add(seedVariable, root)

		worklist = append(worklist, seedVariable)
	}

	valueSet := make(map[string]bool)
	instSet := make(map[string]bool)
	callValueSet := make(map[string]bool)
	for len(worklist) > 0 {
		variable := worklist[len(worklist)-1]
		worklist = worklist[:len(worklist)-1]

		parentFieldSet := valueFieldSetMap[variable]
		parentFieldNodeSet, direct := valueToFieldNodeSetMap[variable]

		// stop if field is on metadata, status, or type meta
		if parentFieldSet.IsMetadata() || parentFieldSet.IsStatus() || parentFieldSet.IsTypeMeta() {
			continue
		}
		referrers := variable.Referrers()
		for _, instruction := range *referrers {
			switch typedInst := instruction.(type) {
			case ssa.Value:
				switch typedValue := typedInst.(type) {
				case *ssa.Call:
					// Inter-procedural
					// Two possibilities for Call: function call or interface invocation
					if !typedValue.Call.IsInvoke() {
						// ordinary function call
						callSiteTaintedParamIndexSet := GetCallsiteArgIndices(variable, typedValue.Common())
						if len(callSiteTaintedParamIndexSet) == 0 {
							log.Println("Error, unable to find the param index")
						}
						switch callValue := typedValue.Call.Value.(type) {
						case *ssa.Function:
							// propogate to the function parameter
							// propogate to return value if it is DeepCopy
							// stop propogate if external library call
							if callValue.Name() == "DeepCopy" || callValue.Name() == "String" || callValue.Name() == "Float64" {
								log.Printf("Propogate through %s\n", callValue.Name())
								for _, parentField := range parentFieldSet.Fields() {
									newField := parentField.Clone()
									ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
									if ok {
										worklist = append(worklist, typedValue)
									}
								}

								if direct {
									for parentFieldNode := range parentFieldNodeSet {
										parentFieldNode.AddValue(typedValue)
										valueToFieldNodeSetMap.Add(typedValue, parentFieldNode)
									}
								}
							} else if callValue.Name() == "DeepCopyInto" {
								for _, paramIndex := range callSiteTaintedParamIndexSet {
									if paramIndex == 0 {
										// the source of DeepCopyInto is tainted
										log.Printf("Propogate through %s\n", callValue.Name())
										target := typedValue.Call.Args[1] // the value that got deepcopied into
										for _, parentField := range parentFieldSet.Fields() {
											newField := parentField.Clone()
											ok := AddFieldToValueFieldSetMap(valueFieldSetMap, target, newField)
											if ok {
												worklist = append(worklist, target)
											}
										}

										if direct {
											for parentFieldNode := range parentFieldNodeSet {
												parentFieldNode.AddValue(target)
												valueToFieldNodeSetMap.Add(target, parentFieldNode)
											}
										}
									}
								}
							} else {
								PropogateToCallee(context, callValue, variable, callSiteTaintedParamIndexSet, parentFieldSet, &worklist, valueFieldSetMap, frontierValues, parentFieldNodeSet)
							}
						case *ssa.MakeClosure:
							// XXX could be closure, let's handle it if it's used
							log.Println("Warning, closure used")
							frontierValues[variable] = true
						case *ssa.Builtin:
							// Stop propogation?
							if callValue.Name() == "append" {
								context.AppendCalls = append(context.AppendCalls, typedValue)
							}
							frontierValues[variable] = true
						default:
							callValueSet[callValue.Name()] = true
							frontierValues[variable] = true
						}
					} else {
						if typedValue.Call.Method.Name() == "DeepCopy" {
							log.Printf("Propogate through DeepCopy\n")
							for _, parentField := range parentFieldSet.Fields() {
								newField := parentField.Clone()
								ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
								if ok {
									worklist = append(worklist, typedValue)
								}
							}

							if direct {
								for parentFieldNode := range parentFieldNodeSet {
									parentFieldNode.AddValue(typedValue)
									valueToFieldNodeSetMap.Add(typedValue, parentFieldNode)
								}
							}
						} else {
							// interface invocation
							callGraph := context.CallGraph
							calleeSet := CalleeSet(callGraph, typedValue)

							callSiteTaintedArgIndexSet := GetCallsiteArgIndices(variable, typedValue.Common())

							// Interface invocation's receiver is not in arg list
							// but the concrete callee's parameter has the receiver as the first item
							for i := range callSiteTaintedArgIndexSet {
								callSiteTaintedArgIndexSet[i] += 1
							}

							for _, callee := range calleeSet {
								PropogateToCallee(context, callee, variable, callSiteTaintedArgIndexSet, parentFieldSet, &worklist, valueFieldSetMap, frontierValues, parentFieldNodeSet)
							}
						}
					}

					frontierValues[variable] = true
				case *ssa.ChangeInterface:
					for _, parentField := range parentFieldSet.Fields() {
						newField := parentField.Clone()
						ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
						if ok {
							worklist = append(worklist, typedValue)
						}
					}

					if direct {
						for parentFieldNode := range parentFieldNodeSet {
							parentFieldNode.AddValue(typedValue)
							valueToFieldNodeSetMap.Add(typedValue, parentFieldNode)
						}
					}
				case *ssa.ChangeType:
					if UpdateValueInValueFieldSetMap(context, typedValue, parentFieldSet, valueFieldSetMap, parentFieldNodeSet) {
						worklist = append(worklist, typedValue)
					}
				case *ssa.Convert:
					if UpdateValueInValueFieldSetMap(context, typedValue, parentFieldSet, valueFieldSetMap, parentFieldNodeSet) {
						worklist = append(worklist, typedValue)
					}
				case *ssa.Field:
					changed := false
					for _, parentField := range parentFieldSet.Fields() {
						newField := NewSubField(typedValue.X.Type().Underlying().(*types.Struct), parentField, typedValue.Field)
						ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
						if ok {
							changed = true
						}
					}
					if changed {
						worklist = append(worklist, typedValue)
					}

					if direct {
						for parentFieldNode := range parentFieldNodeSet {
							node := parentFieldNode.SubFieldNode(typedValue.X.Type().Underlying().(*types.Struct), typedValue.Field)
							node.AddValue(typedValue)
							valueToFieldNodeSetMap.Add(typedValue, node)
						}
					}
				case *ssa.FieldAddr:
					changed := false
					for _, parentField := range parentFieldSet.Fields() {
						newField := NewSubField(typedValue.X.Type().Underlying().(*types.Pointer).Elem().Underlying().(*types.Struct), parentField, typedValue.Field)
						ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
						if ok {
							changed = true
						}
					}
					if changed {
						worklist = append(worklist, typedValue)
					}

					if direct {
						for parentFieldNode := range parentFieldNodeSet {
							node := parentFieldNode.SubFieldNode(typedValue.X.Type().Underlying().(*types.Pointer).Elem().Underlying().(*types.Struct), typedValue.Field)
							node.AddValue(typedValue)
							valueToFieldNodeSetMap.Add(typedValue, node)
						}
					}
				case *ssa.Index:
					changed := false
					for _, parentField := range parentFieldSet.Fields() {
						newField := NewIndexField(parentField)
						ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
						if ok {
							changed = true
						}
					}
					if changed {
						worklist = append(worklist, typedValue)
					}

					if direct {
						for parentFieldNode := range parentFieldNodeSet {
							newNode := parentFieldNode.IndexFieldNode()
							newNode.AddValue(typedValue)
							valueToFieldNodeSetMap.Add(typedValue, newNode)
						}
					}
				case *ssa.IndexAddr:
					// accessing array index
					changed := false
					for _, parentField := range parentFieldSet.Fields() {
						newField := NewIndexField(parentField)
						ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
						if ok {
							changed = true
						}
					}
					if changed {
						worklist = append(worklist, typedValue)
					}

					if direct {
						for parentFieldNode := range parentFieldNodeSet {
							newNode := parentFieldNode.IndexFieldNode()
							newNode.AddValue(typedValue)
							valueToFieldNodeSetMap.Add(typedValue, newNode)
						}
					}
				case *ssa.Lookup:
					if typedValue.X == variable {
						// XXX: accessed as a map, need to propogate, but how to resolve the key?
						log.Printf("variable is used as the X %s\n", parentFieldSet)
						// typedValue.Parent().WriteTo(os.Stdout)
					} else {
						// do not propogate
						log.Printf("variable is used as the index\n")
						frontierValues[variable] = true
					}
				case *ssa.Phi:
					// propogate with merged edges

					fieldSetSlice := []FieldSet{}
					for _, edge := range typedValue.Edges {
						if fieldSet, ok := valueFieldSetMap[edge]; ok {
							// field present
							fieldSetSlice = append(fieldSetSlice, *fieldSet)
						}
					}
					mergedFieldSet := MergeFieldSets(fieldSetSlice...)

					if UpdateValueInValueFieldSetMap(context, typedValue, mergedFieldSet, valueFieldSetMap, parentFieldNodeSet) {
						worklist = append(worklist, typedValue)
					}
				case *ssa.UnOp:
					switch typedValue.Op {
					case token.MUL:
						// If dereferenced, propogate
						if UpdateValueInValueFieldSetMap(context, typedValue, parentFieldSet, valueFieldSetMap, parentFieldNodeSet) {
							worklist = append(worklist, typedValue)
						}
						log.Printf("Propogate to dereference at [%s]\n", typedValue)
					default:
						// not dereference, do not propogate
						// frontier
						frontierValues[variable] = true
					}
				case *ssa.MakeInterface:
					// If variable is casted into another interface, propogate
					if UpdateValueInValueFieldSetMap(context, typedValue, parentFieldSet, valueFieldSetMap, parentFieldNodeSet) {
						worklist = append(worklist, typedValue)
					}
				default:
					// Other types, sink
					// since variable has at least one referrer in sink
					// it's frontier
					valueSet[reflect.TypeOf(typedValue).String()] = true
					frontierValues[variable] = true
				}
			case *ssa.Store:
				// Two cases, variable is referred as the addr, or the value
				if typedInst.Addr == variable {
					frontierValues[variable] = true
					log.Printf("Referred as the addr\n")
				} else {
					// referred as the value, propogate to addr
					// XXX: may need to propogate backward
					//
					// XXX: Handle this in taint pass
					// for _, parentField := range parentFieldSet.Fields() {
					// 	newField := parentField.Clone()
					// 	ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedInst.Addr, newField)
					// 	if ok {
					// 		changed = true
					// 	}
					// }
					if _, ok := typedInst.Addr.(*ssa.Alloc); ok {
						// only propogate to the address if it's alloc
						if UpdateValueInValueFieldSetMap(context, typedInst.Addr, parentFieldSet, valueFieldSetMap, nil) {
							worklist = append(worklist, typedInst.Addr)
						}
					} else {
						frontierValues[variable] = true
						context.StoreInsts = append(context.StoreInsts, typedInst)
					}
					// field sensitive
					source, path := StructBackwardPropagation(typedInst.Addr, []int{})
					if source != nil {
						if _, ok := source.Type().Underlying().(*types.Struct); ok {
							originalTaintedStructValue := TaintedStructValue{
								Value: source,
								Path:  path,
							}
							taintedSet := HandleStructField(context, &originalTaintedStructValue)
							for value := range taintedSet {
								if UpdateValueInValueFieldSetMap(context, value, parentFieldSet, valueFieldSetMap, nil) {
									worklist = append(worklist, value)
								}
							}
						} else if pointer, ok := source.Type().Underlying().(*types.Pointer); ok {
							if _, ok := pointer.Elem().Underlying().(*types.Struct); ok {
								log.Printf("Value %s stored in struct %s at %s", variable, source, source.Parent().Pkg.Prog.Fset.Position(source.Pos()))
								originalTaintedStructValue := TaintedStructValue{
									Value: source,
									Path:  path,
								}
								taintedSet := HandleStructField(context, &originalTaintedStructValue)
								for value := range taintedSet {
									if UpdateValueInValueFieldSetMap(context, value, parentFieldSet, valueFieldSetMap, nil) {
										worklist = append(worklist, value)
									}
								}
							}
						}
					}
				}
			case *ssa.Return:
				// TODO: handle this
				// Propogate to all callsites
				log.Printf("CR fields propogated to return instructions in function %s\n", variable.Parent())
				log.Printf("Parent field %s\n", parentFieldSet)

				returnSet := GetReturnIndices(variable, typedInst)
				node, ok := context.CallGraph.Nodes[variable.Parent()]
				if !ok {
					log.Printf("Failed to retrieve call graph node for %s %T\n", variable, variable)
				}
				if node == nil {
					log.Printf("No caller for %s %T at %s\n", variable, variable, variable.Parent().Pkg.Prog.Fset.Position(variable.Pos()))
				} else {
					for _, inEdge := range node.In {
						// if it returns to a K8s client function, skip
						if ExternalLibrary(context, inEdge.Caller.Func) {
							if inEdge.Caller.Func.Pkg != nil {
								log.Printf("Called by external function [%s], skip", inEdge.Caller.Func.Pkg.Pkg.Path())
							}
							continue
						}

						log.Printf("Return to caller %s", inEdge.Caller.Func)

						if callSiteReturnValue := inEdge.Site.Value(); callSiteReturnValue != nil {
							if typedInst.Parent().Signature.Results().Len() > 1 {
								for _, tainted := range getExtractTaint(callSiteReturnValue, returnSet) {
									if UpdateValueInValueFieldSetMap(context, tainted, parentFieldSet, valueFieldSetMap, parentFieldNodeSet) {
										worklist = append(worklist, tainted)
									}
								}
							} else {
								if UpdateValueInValueFieldSetMap(context, callSiteReturnValue, parentFieldSet, valueFieldSetMap, parentFieldNodeSet) {
									worklist = append(worklist, callSiteReturnValue)
								}
							}
						}
					}
				}
				frontierValues[variable] = true
			default:
				// Report any unhandled instruction type
				instSet[reflect.TypeOf(typedInst).String()] = true
				frontierValues[variable] = true
			}
		}
	}
	log.Println(valueSet)
	log.Println(instSet)
	log.Println(frontierValues)

	return valueFieldSetMap, frontierValues
}

func PropogateToCallee(context *Context, callee *ssa.Function, value ssa.Value, callSiteTaintedArgIndexSet []int,
	parentFieldSet *FieldSet, worklist *[]ssa.Value, valueFieldSetMap map[ssa.Value]*FieldSet, frontierValues map[ssa.Value]bool, parentFieldNodeSet map[*FieldNode]struct{}) {
	if callee.Pkg != nil && strings.Contains(callee.Pkg.Pkg.Path(), context.RootModule.Path) {
		for _, paramIndex := range callSiteTaintedArgIndexSet {

			param := callee.Params[paramIndex]
			for _, parentField := range parentFieldSet.Fields() {
				newField := parentField.Clone()
				ok := AddFieldToValueFieldSetMap(valueFieldSetMap, param, newField)
				if ok {
					*worklist = append(*worklist, param)
				}
			}

			if parentFieldNodeSet != nil {
				for parentFieldNode := range parentFieldNodeSet {
					parentFieldNode.AddValue(param)
					context.ValueToFieldNodeSetMap.Add(param, parentFieldNode)
				}
			}
		}
	} else {
		log.Printf("Stop propogating to external package %s\n", callee.String())
		frontierValues[value] = true
	}
}

func ExternalLibrary(context *Context, fn *ssa.Function) bool {
	return fn.Pkg == nil || !strings.Contains(fn.Pkg.Pkg.Path(), context.RootModule.Path)
}

func UpdateValueInValueFieldSetMap(context *Context, value ssa.Value, parentFieldSet *FieldSet, valueFieldSetMap map[ssa.Value]*FieldSet, parentFieldNodeSet FieldNodeSet) (changed bool) {
	for _, parentField := range parentFieldSet.Fields() {
		newField := parentField.Clone()
		ok := AddFieldToValueFieldSetMap(valueFieldSetMap, value, newField)
		if ok {
			changed = true
		}
	}

	if parentFieldNodeSet != nil {
		for parentFieldNode := range parentFieldNodeSet {
			parentFieldNode.AddValue(value)
			context.ValueToFieldNodeSetMap.Add(value, parentFieldNode)
		}
	}
	return
}

func StructBackwardPropagation(value ssa.Value, path []int) (ssa.Value, []int) {
	switch typedValue := value.(type) {
	case *ssa.Alloc:
		return typedValue, path
	case *ssa.Call:
		// returned from a Call
		return typedValue, path
	case *ssa.ChangeType:
		return StructBackwardPropagation(typedValue.X, path)
	case *ssa.Convert:
		return StructBackwardPropagation(typedValue.X, path)
	case *ssa.Extract:
		return typedValue, path
	case *ssa.FieldAddr:
		src, p := StructBackwardPropagation(typedValue.X, path)
		return src, append(p, typedValue.Field)
	case *ssa.FreeVar:
		return typedValue, path
	case *ssa.IndexAddr:
		return typedValue, path
	case *ssa.Lookup:
		return typedValue, path
	case *ssa.Parameter:
		return typedValue, path
	case *ssa.Phi:
		// XXX
		return typedValue, path
	case *ssa.MakeInterface:
		return StructBackwardPropagation(typedValue.X, path)
	case *ssa.MakeMap:
		return typedValue, path
	case *ssa.MakeSlice:
		return typedValue, path
	case *ssa.Slice:
		return StructBackwardPropagation(typedValue.X, path)
	case *ssa.TypeAssert:
		return StructBackwardPropagation(typedValue.X, path)
	case *ssa.UnOp:
		return StructBackwardPropagation(typedValue.X, path)
	default:
		log.Fatalf("Backward propogation: not handle %T: %s\n", typedValue, typedValue)
		return nil, nil
	}
}

func HandleStructField(context *Context, originalTaintedStructValue *TaintedStructValue) (ret map[ssa.Value]bool) {
	ret = make(map[ssa.Value]bool)

	handledPhiMap := make(map[*ssa.Phi]map[ssa.Value]bool) // phi -> set of handled edges
	handledRetMap := make(map[ssa.Value]bool)
	worklist := []*TaintedStructValue{originalTaintedStructValue}
	for len(worklist) > 0 {
		taintedStructValue := worklist[len(worklist)-1]
		worklist = worklist[:len(worklist)-1]

		if len(taintedStructValue.Path) == 0 {
			ret[taintedStructValue.Value] = true
			continue
		}

		referrers := taintedStructValue.Value.Referrers()
		for _, instruction := range *referrers {
			log.Printf("HandleStructField: %s", instruction)
			switch typedInst := instruction.(type) {
			case ssa.Value:
				switch typedValue := typedInst.(type) {
				case *ssa.Call:
					// Inter-procedural
					// Two possibilities for Call: function call or interface invocation
					if !typedValue.Call.IsInvoke() {
						// ordinary function call
						callSiteTaintedParamIndexSet := GetCallsiteArgIndices(taintedStructValue.Value, typedValue.Common())
						if len(callSiteTaintedParamIndexSet) == 0 {
							log.Println("Error, unable to find the param index")
						}
						switch callValue := typedValue.Call.Value.(type) {
						case *ssa.Function:
							// propogate to the function parameter
							// propogate to return value if it is DeepCopy
							// stop propogate if external library call
							if callValue.Name() == "DeepCopy" || callValue.Name() == "String" || callValue.Name() == "Float64" {
								newTaintedStructValue := TaintedStructValue{
									Value: typedValue,
									Path:  taintedStructValue.Path,
								}
								worklist = append(worklist, &newTaintedStructValue)
							} else {
								StructFieldPropagateToCallee(context, &worklist, callValue, taintedStructValue, callSiteTaintedParamIndexSet)
							}
						case *ssa.Builtin:
							// Stop propogation?
						}
					} else {
						if typedValue.Call.Method.Name() == "DeepCopy" {
							log.Printf("Propogate through DeepCopy\n")
							newTaintedStructValue := TaintedStructValue{
								Value: typedValue,
								Path:  taintedStructValue.Path,
							}
							worklist = append(worklist, &newTaintedStructValue)
						} else {
							// interface invocation
							callGraph := context.CallGraph
							calleeSet := CalleeSet(callGraph, typedValue)

							callSiteTaintedArgIndexSet := GetCallsiteArgIndices(taintedStructValue.Value, typedValue.Common())

							// Interface invocation's receiver is not in arg list
							// but the concrete callee's parameter has the receiver as the first item
							for i := range callSiteTaintedArgIndexSet {
								callSiteTaintedArgIndexSet[i] += 1
							}

							for _, callee := range calleeSet {
								StructFieldPropagateToCallee(context, &worklist, callee, taintedStructValue, callSiteTaintedArgIndexSet)
							}
						}
					}
				case *ssa.Field:
					if typedValue.Field == taintedStructValue.Path[0] {
						newTaintedStructValue := TaintedStructValue{
							Value: typedValue,
							Path:  taintedStructValue.Path[1:],
						}
						worklist = append(worklist, &newTaintedStructValue)
					}
				case *ssa.FieldAddr:
					if typedValue.Field == taintedStructValue.Path[0] {
						newTaintedStructValue := TaintedStructValue{
							Value: typedValue,
							Path:  taintedStructValue.Path[1:],
						}
						worklist = append(worklist, &newTaintedStructValue)
					}
				case *ssa.Phi:
					// TODO: handle phi
					if edgeMap, ok := handledPhiMap[typedValue]; !ok {
						handledPhiMap[typedValue] = make(map[ssa.Value]bool)
						handledPhiMap[typedValue][taintedStructValue.Value] = true
						newTaintedStructValue := TaintedStructValue{
							Value: typedValue,
							Path:  taintedStructValue.Path,
						}
						worklist = append(worklist, &newTaintedStructValue)
					} else {
						if _, ok := edgeMap[taintedStructValue.Value]; !ok {
							handledPhiMap[typedValue][taintedStructValue.Value] = true
							newTaintedStructValue := TaintedStructValue{
								Value: typedValue,
								Path:  taintedStructValue.Path,
							}
							worklist = append(worklist, &newTaintedStructValue)
						}
					}
				case *ssa.UnOp:
					switch typedValue.Op {
					case token.MUL:
						// If dereferenced, propogate
						newTaintedStructValue := TaintedStructValue{
							Value: typedValue,
							Path:  taintedStructValue.Path,
						}
						worklist = append(worklist, &newTaintedStructValue)
					}
				case *ssa.MakeInterface:
					// If variable is casted into another interface, propogate
					newTaintedStructValue := TaintedStructValue{
						Value: typedValue,
						Path:  taintedStructValue.Path,
					}
					worklist = append(worklist, &newTaintedStructValue)
				}
			case *ssa.Return:
				log.Printf("CR fields propogated to return instructions in function %s\n", taintedStructValue.Value.Parent())

				returnSet := GetReturnIndices(taintedStructValue.Value, typedInst)
				node, ok := context.CallGraph.Nodes[taintedStructValue.Value.Parent()]
				if !ok {
					log.Printf("Failed to retrieve call graph node for %s %T\n", taintedStructValue.Value, taintedStructValue.Value)
				}
				if node == nil {
					log.Printf("No caller for %s %T at %s\n", taintedStructValue.Value, taintedStructValue.Value, taintedStructValue.Value.Parent().Pkg.Prog.Fset.Position(taintedStructValue.Value.Pos()))
				} else {
					for _, inEdge := range node.In {
						// if it returns to a K8s client function, skip
						if ExternalLibrary(context, inEdge.Caller.Func) {
							if inEdge.Caller.Func.Pkg != nil {
								log.Printf("Called by external function [%s], skip", inEdge.Caller.Func.Pkg.Pkg.Path())
							}
							continue
						}

						log.Printf("Return to caller %s", inEdge.Caller.Func)

						if callSiteReturnValue := inEdge.Site.Value(); callSiteReturnValue != nil {
							if typedInst.Parent().Signature.Results().Len() > 1 {
								for _, tainted := range getExtractTaint(callSiteReturnValue, returnSet) {
									if _, ok := handledRetMap[tainted]; ok {
										newTaintedStructValue := TaintedStructValue{
											Value: tainted,
											Path:  taintedStructValue.Path,
										}
										worklist = append(worklist, &newTaintedStructValue)
									}
								}
							} else {
								if _, ok := handledRetMap[callSiteReturnValue]; ok {
									newTaintedStructValue := TaintedStructValue{
										Value: callSiteReturnValue,
										Path:  taintedStructValue.Path,
									}
									worklist = append(worklist, &newTaintedStructValue)
								}
							}
						}
					}
				}
			}
		}
	}
	return
}

func StructFieldPropagateToCallee(context *Context, worklist *[]*TaintedStructValue,
	callee *ssa.Function, taintedStructValue *TaintedStructValue, callSiteTaintedArgIndexSet []int) {
	if callee.Pkg != nil && strings.Contains(callee.Pkg.Pkg.Path(), context.RootModule.Path) {
		for _, paramIndex := range callSiteTaintedArgIndexSet {

			param := callee.Params[paramIndex]
			newTaintedStructValue := TaintedStructValue{
				Value: param,
				Path:  taintedStructValue.Path,
			}
			*worklist = append(*worklist, &newTaintedStructValue)
		}
	}
}
