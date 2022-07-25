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

	for _, seedVariable := range seedVariables {
		rootField := []string{"root"}
		valueFieldSetMap[seedVariable] = NewFieldSet()
		valueFieldSetMap[seedVariable].Add(&Field{
			Path: rootField,
		})
		worklist = append(worklist, seedVariable)
	}

	valueSet := make(map[string]bool)
	instSet := make(map[string]bool)
	callValueSet := make(map[string]bool)
	for len(worklist) > 0 {
		variable := worklist[len(worklist)-1]
		worklist = worklist[:len(worklist)-1]

		parentFieldSet := valueFieldSetMap[variable]

		// stop if field is on metadata, status, or type meta
		if parentFieldSet.IsMetadata() || parentFieldSet.IsStatus() || parentFieldSet.IsTypeMeta() {
			continue
		}
		referrers := variable.Referrers()
		if variable.String() == "*t256" {
			log.Printf("&t227.AdvancedConfig [#2] has %d referrers\n", len(*referrers))
		}
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
							if callValue.Name() == "DeepCopy" {
								log.Printf("Propogate through DeepCopy\n")
								for _, parentField := range parentFieldSet.Fields() {
									newField := parentField.Clone()
									ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
									if ok {
										worklist = append(worklist, typedValue)
									}
								}
							} else {
								PropogateToCallee(context, callValue, variable, callSiteTaintedParamIndexSet, parentFieldSet, &worklist, valueFieldSetMap, frontierValues)
							}
						case *ssa.MakeClosure:
							// XXX could be closure, let's handle it if it's used
							log.Println("Warning, closure used")
							frontierValues[variable] = true
						case *ssa.Builtin:
							// Stop propogation?
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
								PropogateToCallee(context, callee, variable, callSiteTaintedArgIndexSet, parentFieldSet, &worklist, valueFieldSetMap, frontierValues)
							}
						}
					}
				case *ssa.ChangeInterface:
					for _, parentField := range parentFieldSet.Fields() {
						newField := parentField.Clone()
						ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
						if ok {
							worklist = append(worklist, typedValue)
						}
					}
				case *ssa.ChangeType:
					if UpdateValueInValueFieldSetMap(typedValue, parentFieldSet, valueFieldSetMap) {
						worklist = append(worklist, typedValue)
					}
				case *ssa.Convert:
					if UpdateValueInValueFieldSetMap(typedValue, parentFieldSet, valueFieldSetMap) {
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

					if UpdateValueInValueFieldSetMap(typedValue, mergedFieldSet, valueFieldSetMap) {
						worklist = append(worklist, typedValue)
					}
				case *ssa.UnOp:
					switch typedValue.Op {
					case token.MUL:
						// If dereferenced, propogate
						if UpdateValueInValueFieldSetMap(typedValue, parentFieldSet, valueFieldSetMap) {
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
					if UpdateValueInValueFieldSetMap(typedValue, parentFieldSet, valueFieldSetMap) {
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
						if UpdateValueInValueFieldSetMap(typedInst.Addr, parentFieldSet, valueFieldSetMap) {
							worklist = append(worklist, typedInst.Addr)
						}
					} else {
						frontierValues[variable] = true
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

						if callSiteReturnValue := inEdge.Site.Value(); callSiteReturnValue != nil {
							if typedInst.Parent().Signature.Results().Len() > 1 {
								for _, tainted := range getExtractTaint(callSiteReturnValue, returnSet) {
									if UpdateValueInValueFieldSetMap(tainted, parentFieldSet, valueFieldSetMap) {
										worklist = append(worklist, tainted)
									}
								}
							} else {
								if UpdateValueInValueFieldSetMap(callSiteReturnValue, parentFieldSet, valueFieldSetMap) {
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
	parentFieldSet *FieldSet, worklist *[]ssa.Value, valueFieldSetMap map[ssa.Value]*FieldSet, frontierValues map[ssa.Value]bool) {
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
		}
	} else {
		log.Printf("Stop propogating to external package %s\n", callee.String())
		frontierValues[value] = true
	}
}

func ExternalLibrary(context *Context, fn *ssa.Function) bool {
	return fn.Pkg == nil || !strings.Contains(fn.Pkg.Pkg.Path(), context.RootModule.Path)
}

func UpdateValueInValueFieldSetMap(value ssa.Value, parentFieldSet *FieldSet, valueFieldSetMap map[ssa.Value]*FieldSet) (changed bool) {
	for _, parentField := range parentFieldSet.Fields() {
		newField := parentField.Clone()
		ok := AddFieldToValueFieldSetMap(valueFieldSetMap, value, newField)
		if ok {
			changed = true
		}
	}
	return
}
