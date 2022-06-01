package analysis

import (
	"go/token"
	"go/types"
	"log"
	"reflect"
	"sort"
	"strings"

	"github.com/xlab-uiuc/acto/ssa/util"
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
func GetValueToFieldMappingPass(prog *ssa.Program, seedType string) (map[ssa.Value]*FieldSet, map[ssa.Value]bool) {
	valueFieldSetMap := make(map[ssa.Value]*FieldSet)
	frontierValues := make(map[ssa.Value]bool)
	seedVariables := FindSeedValues(prog, seedType)

	allTypes := GetAllTypes(prog)

	for _, seedVariable := range seedVariables {
		rootField := []string{"root"}
		valueFieldSetMap[seedVariable] = NewFieldSet()
		valueFieldSetMap[seedVariable].Add(&Field{
			Path: rootField,
		})
	}

	valueSet := make(map[string]bool)
	instSet := make(map[string]bool)
	callValueSet := make(map[string]bool)
	for {
		changed := false
		for variable, parentFieldSet := range valueFieldSetMap {
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
							paramIndex := GetParamIndex(variable, typedValue.Common())
							if paramIndex == -1 {
								log.Println("Error, unable to find the param index")
							}
							switch callValue := typedValue.Call.Value.(type) {
							case *ssa.Function:
								// propogate to the function parameter
								// stop propogate if external library call
								if strings.Contains(callValue.Pkg.Pkg.Path(), "github.com/rabbitmq/cluster-operator") {
									log.Printf("value %s Propogate into function %s at %dth parameter with path %s\n", variable.Name(), callValue.String(), paramIndex, parentFieldSet.Fields())

									param := callValue.Params[paramIndex]
									for _, parentField := range parentFieldSet.Fields() {
										newField := parentField.Clone()
										ok := AddFieldToValueFieldSetMap(valueFieldSetMap, param, newField)
										if ok {
											changed = true
										}
									}
								} else {
									log.Printf("Stop propogating to external package %s\n", callValue.String())
									frontierValues[variable] = true
								}
							case *ssa.MakeClosure:
								// XXX could be closure, let's handle it if it's used
								log.Println("Warning, closure used")
							case *ssa.Builtin:
								// Stop propogation?
								frontierValues[variable] = true
							default:
								callValueSet[callValue.Name()] = true
								frontierValues[variable] = true
							}
						} else {
							// interface invocation
							// XXX: Do not handle for now
							interfaceType := typedValue.Call.Value.Type().Underlying()
							method := typedValue.Call.Method
							log.Printf("Interface type %s\n", interfaceType)
							for _, typ := range allTypes {
								if types.Implements(typ.Type(), interfaceType.(*types.Interface)) {
									log.Printf("%s implements %s\n", typ.Type(), interfaceType)
									if concreteType, ok := typ.Type().(*types.Named); ok {
										for i := 0; i < concreteType.NumMethods(); i++ {
											if concreteType.Method(i).Name() == method.Name() {
												log.Printf("Found concrete method for %s\n", method.FullName())
											}
										}
									} else {
										log.Fatalf("concrete type is not named, but %T\n", typ.Type())
									}
								}
							}
						}
					case *ssa.ChangeInterface:
						for _, parentField := range parentFieldSet.Fields() {
							newField := parentField.Clone()
							ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
							if ok {
								changed = true
							}
						}
					case *ssa.ChangeType:
						for _, parentField := range parentFieldSet.Fields() {
							newField := parentField.Clone()
							ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
							if ok {
								changed = true
							}
						}
					case *ssa.Convert:
						for _, parentField := range parentFieldSet.Fields() {
							newField := parentField.Clone()
							ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
							if ok {
								changed = true
							}
						}
					case *ssa.Field:
						for _, parentField := range parentFieldSet.Fields() {
							newField := NewSubField(typedValue.X.Type().(*types.Struct), parentField, typedValue.Field)
							ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
							if ok {
								changed = true
							}
						}
					case *ssa.FieldAddr:
						for _, parentField := range parentFieldSet.Fields() {
							newField := NewSubField(typedValue.X.Type().Underlying().(*types.Pointer).Elem().Underlying().(*types.Struct), parentField, typedValue.Field)
							ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
							if ok {
								changed = true
							}
						}
					case *ssa.Index:
						for _, parentField := range parentFieldSet.Fields() {
							newField := NewIndexField(parentField)
							ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
							if ok {
								changed = true
							}
						}
					case *ssa.IndexAddr:
						// accessing array index
						for _, parentField := range parentFieldSet.Fields() {
							newField := NewIndexField(parentField)
							ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
							if ok {
								changed = true
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
						for _, parentField := range mergedFieldSet.Fields() {
							newField := parentField.Clone()
							ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
							if ok {
								changed = true
							}
						}
					case *ssa.UnOp:
						switch typedValue.Op {
						case token.MUL:
							// If dereferenced, propogate
							for _, parentField := range parentFieldSet.Fields() {
								newField := parentField.Clone()
								ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
								if ok {
									changed = true
								}
							}
						default:
							// not dereference, do not propogate
							// frontier
							frontierValues[variable] = true
						}
					case *ssa.MakeInterface:
						// If variable is casted into another interface, propogate
						for _, parentField := range parentFieldSet.Fields() {
							newField := parentField.Clone()
							ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
							if ok {
								changed = true
							}
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
						log.Printf("Referred as the addr\n")
					} else {
						// referred as the value, propogate to addr
						// XXX: may need to propogate backward
						for _, parentField := range parentFieldSet.Fields() {
							newField := parentField.Clone()
							ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedInst.Addr, newField)
							if ok {
								changed = true
							}
						}
					}
				case *ssa.Return:
					// XXX: no need to handle them now
					log.Printf("CR fields propogated to return instructions in function %s\n", variable.Parent())
					log.Printf("Parent field %s\n", parentFieldSet)
					// let taint pass handle this
					frontierValues[variable] = true
				default:
					// Report any unhandled instruction type
					instSet[reflect.TypeOf(typedInst).String()] = true
					frontierValues[variable] = true
				}
			}
		}
		if !changed {
			break
		}

	}
	log.Println(valueSet)
	log.Println(instSet)
	log.Println(frontierValues)

	return valueFieldSetMap, frontierValues
}

// Alloc
// BinOp
// Call
// ChangeInterface
// ChangeType
// Convert
// DebugRef
// Defer
// Extract
// Field
// FieldAddr
// Go
// If
// Index
// IndexAddr
// Jump
// Lookup
// MakeChan
// MakeClosure
// MakeInterface
// MakeMap
// MakeSlice
// MapUpdate
// Next
// Panic
// Phi
// Range
// Return
// RunDefers
// Select
// Send
// Slice
// SliceToArrayPointer
// Store
// TypeAssert
// UnOp
func TaintAnalysisPass(prog *ssa.Program, frontierValues map[ssa.Value]bool) map[ssa.Value]bool {
	tainted := make(map[ssa.Value]bool)
	for value := range frontierValues {
		if TaintK8sFromValue(value) {
			tainted[value] = true
		}
	}
	return tainted
}

// returns true if value taints k8s API calls
func TaintK8sFromValue(value ssa.Value) bool {
	taintedSet := make(map[ssa.Value]bool)
	taintedSet[value] = true

	propogatedSet := make(map[ssa.Value]bool) // cache

	for {
		changed := false
		for taintedValue := range taintedSet {
			if _, ok := propogatedSet[taintedValue]; ok {
				continue
			}
			referrers := taintedValue.Referrers()
			for _, instruction := range *referrers {
				switch typedInst := instruction.(type) {
				case ssa.Value:
					switch typedValue := typedInst.(type) {
					case *ssa.Alloc:
						// skip
						log.Panic("Alloc referred\n")
					case *ssa.BinOp:
						// propogate to the result
						if _, ok := taintedSet[typedValue]; !ok {
							taintedSet[typedValue] = true
							changed = true
						}
					case *ssa.Call:
						// context aware
						// if making k8s library call, sink
						if typedValue.Call.IsInvoke() {
							if functionSink(typedValue.Call.Method) {
								continue
							}
							if strings.Contains(typedValue.Call.Method.Pkg().Name(), "sigs.k8s.io/controller-runtime/pkg") {
								log.Println(typedValue.Call.Method.Id())
							}
						}
						log.Printf("Propogate to callee %s\n", typedValue.String())
						ContextAwareFunctionAnalysis(taintedValue, typedValue, taintedSet)
					case *ssa.Extract:
						// Handle with call
					case *ssa.Lookup:
						// Two cases: 1) referred as the X 2) referred as the Index
						if taintedValue == typedValue.X {
							if typedValue.CommaOk {
								if handleExtractTaint(typedValue, &taintedSet, []int{0, 1}) {
									changed = true
								}
							} else {
								if _, ok := taintedSet[typedValue]; !ok {
									taintedSet[typedValue] = true
									changed = true
								}
							}
						} else {
							// skip
							log.Fatal("Referred as Index in Lookup\n")
						}
					case *ssa.MakeChan:
						// skip
					case *ssa.MakeClosure:
					case *ssa.MakeMap:
						// skip
					case *ssa.MakeSlice:
						// skip
					case *ssa.Next:
						if _, ok := taintedSet[typedValue]; !ok {
							taintedSet[typedValue] = true
							changed = true
						}
					case *ssa.Range:
						// TODO
						if _, ok := taintedSet[typedValue]; !ok {
							taintedSet[typedValue] = true
							changed = true
						}
					case *ssa.Select:
						log.Fatalf("Referred in Select\n")
					case *ssa.Slice:
						// Two cases: 1) referred as the X 2) referred as the Low, High, Max
						if taintedValue == typedValue.X {
							if _, ok := taintedSet[typedValue]; !ok {
								taintedSet[typedValue] = true
								changed = true
							}
						} else {
							// do not propogate
						}
					case *ssa.TypeAssert:
						if typedValue.CommaOk {
							// returns a tuple, need to extract
							if handleExtractTaint(typedValue, &taintedSet, []int{0, 1}) {
								changed = true
							}
						} else {
							if _, ok := taintedSet[typedValue]; !ok {
								taintedSet[typedValue] = true
								changed = true
							}
						}
					default:
						log.Printf("Hit sink %T\n", typedValue)
					}
				case *ssa.DebugRef:
					// skip
				case *ssa.Defer:
					ContextAwareFunctionAnalysis(taintedValue, typedInst.Value(), taintedSet)
				case *ssa.Go:
					ContextAwareFunctionAnalysis(taintedValue, typedInst.Value(), taintedSet)
				case *ssa.Jump:
					// skip
				case *ssa.MapUpdate:
					// TODO: field sensitive taint
					// Three cases
					// 1) used as Map
					// 2) used as Key - taint Map
					// 3) used as Value - taint Map
					if taintedValue == typedInst.Key {
						if _, ok := taintedSet[typedInst.Map]; !ok {
							taintedSet[typedInst.Map] = true
							changed = true
						}
					} else if taintedValue == typedInst.Value {
						if _, ok := taintedSet[typedInst.Map]; !ok {
							taintedSet[typedInst.Map] = true
							changed = true
						}
					}
				case *ssa.Panic:
					// skip
				case *ssa.Return:
					// Find all possible callsites
				case *ssa.RunDefers:
					// skip
				case *ssa.Send:
					// Two cases
					// used as X
					// used as Chan
				case *ssa.Store:
					// TODO: propogate back
				default:
					log.Printf("Hit sink %T\n", typedInst)
				}
			}
			propogatedSet[taintedValue] = true
		}
		if !changed {
			break
		}
	}
	return false
}

// only taint the callsite
func ContextAwareFunctionAnalysis(value ssa.Value, callInst ssa.CallInstruction, taintedSet map[ssa.Value]bool) bool {
	changed := false
	index := util.GetParamIndex(value, callInst.Common())
	if callInst.Common().IsInvoke() {
		// invoke case
	} else {
		// ordinary call case
		switch callee := callInst.Common().Value.(type) {
		case *ssa.Function:
			if callValue := callInst.Value(); callValue != nil {
				// if it's a Call instruction
				taintedIndices := TaintFunction(callee, index)
				if len(taintedIndices) == 0 {
					return false
				}
				resultTuple := callee.Signature.Results()
				if resultTuple != nil {
					if resultTuple.Len() > 1 {
						// handle extract
						if handleExtractTaint(callValue, &taintedSet, taintedIndices) {
							changed = true
						}
					} else {
						if _, ok := taintedSet[callValue]; !ok {
							taintedSet[callValue] = true
							changed = true
						}
					}
				}
			} else {
				// Go, Defer instruction
			}
		case *ssa.MakeClosure:
			log.Panic("TODO: MakeClosure not properly handled\n")
		case *ssa.Builtin:
			// need to define the buildins to propogate
		default:
		}
	}
	return changed
}

// returns the indices of the tainted return values
func TaintFunction(functionBody *ssa.Function, paramIndex int) []int {
	param := functionBody.Params[paramIndex]
	taintedSet := make(map[ssa.Value]bool)
	taintedSet[param] = true

	indexSet := make(map[int]bool) // used to store index for return

	for {
		changed := false
		for taintedValue := range taintedSet {
			referrers := taintedValue.Referrers()
			for _, instruction := range *referrers {
				switch typedInst := instruction.(type) {
				case ssa.Value:
					switch typedValue := typedInst.(type) {
					case *ssa.Alloc:
						// skip
						log.Panic("Alloc referred\n")
					case *ssa.BinOp:
						// propogate to the result
						if _, ok := taintedSet[typedValue]; !ok {
							taintedSet[typedValue] = true
							changed = true
						}
					case *ssa.Call:
						// context aware
						if typedValue.Call.IsInvoke() {
							if functionSink(typedValue.Call.Method) {
								continue
							}
							if strings.Contains(typedValue.Call.Method.Pkg().Name(), "sigs.k8s.io/controller-runtime/pkg") {
								log.Println(typedValue.Call.Method.Id())
							}
						}
						log.Printf("Propogate to callee %s\n", typedValue.String())
						if ContextAwareFunctionAnalysis(taintedValue, typedValue, taintedSet) {
							changed = true
						}
					case *ssa.Extract:
						// Handle with call
						log.Panic("Extract not handled properly\n")
					case *ssa.Lookup:
						// Two cases: 1) referred as the X 2) referred as the Index
						if taintedValue == typedValue.X {
							if typedValue.CommaOk {
								if handleExtractTaint(typedValue, &taintedSet, []int{0, 1}) {
									changed = true
								}
							} else {
								if _, ok := taintedSet[typedValue]; !ok {
									taintedSet[typedValue] = true
									changed = true
								}
							}
						} else {
							// skip
							log.Fatal("Referred as Index in Lookup\n")
						}
					case *ssa.MakeChan:
						// skip
					case *ssa.MakeClosure:
						log.Panic("MakeClosure tainted\n")
					case *ssa.MakeMap:
						// skip
					case *ssa.MakeSlice:
						// skip
					case *ssa.Next:
						if _, ok := taintedSet[typedValue]; !ok {
							taintedSet[typedValue] = true
							changed = true
						}
					case *ssa.Range:
						// TODO
						if _, ok := taintedSet[typedValue]; !ok {
							taintedSet[typedValue] = true
							changed = true
						}
					case *ssa.Select:
						log.Fatalf("Referred in Select\n")
					case *ssa.Slice:
						// Two cases: 1) referred as the X 2) referred as the Low, High, Max
						if taintedValue == typedValue.X {
							if _, ok := taintedSet[typedValue]; !ok {
								taintedSet[typedValue] = true
								changed = true
							}
						} else {
							// do not propogate
						}
					case *ssa.TypeAssert:
						if typedValue.CommaOk {
							// returns a tuple, need to extract
							if handleExtractTaint(typedValue, &taintedSet, []int{0, 1}) {
								changed = true
							}
						} else {
							if _, ok := taintedSet[typedValue]; !ok {
								taintedSet[typedValue] = true
								changed = true
							}
						}
					default:
						log.Printf("Hit sink %T\n", typedValue)
					}
				case *ssa.DebugRef:
					// skip
				case *ssa.Defer:
					if ContextAwareFunctionAnalysis(taintedValue, typedInst, taintedSet) {
						changed = true
					}
				case *ssa.Go:
					if ContextAwareFunctionAnalysis(taintedValue, typedInst, taintedSet) {
						changed = true
					}
				case *ssa.Jump:
					// skip
				case *ssa.MapUpdate:
					// TODO: field sensitive taint
					// Three cases
					// 1) used as Map
					// 2) used as Key - taint Map
					// 3) used as Value - taint Map
					if taintedValue == typedInst.Key {
						if _, ok := taintedSet[typedInst.Map]; !ok {
							taintedSet[typedInst.Map] = true
							changed = true
						}
					} else if taintedValue == typedInst.Value {
						if _, ok := taintedSet[typedInst.Map]; !ok {
							taintedSet[typedInst.Map] = true
							changed = true
						}
					}
				case *ssa.Panic:
					// skip
				case *ssa.Return:
					for i, result := range typedInst.Results {
						if result == taintedValue {
							indexSet[i] = true
						}
					}
				case *ssa.RunDefers:
					// skip
				case *ssa.Send:
					// Two cases
					// used as X
					// used as Chan
				case *ssa.Store:
					// TODO: propogate back
				default:
					log.Printf("Hit sink %T\n", typedInst)
				}
			}
		}
		if !changed {
			break
		}
	}

	ret := []int{}
	for k, _ := range indexSet {
		ret = append(ret, k)
	}
	sort.Ints(ret)
	return ret
}

func handleExtractTaint(typeAssertValue ssa.Value, taintedSet *map[ssa.Value]bool, retIndices []int) bool {
	changed := false
	sort.Ints(retIndices)
	typeAssertReferrers := typeAssertValue.Referrers()
	for _, typeAssertReferrer := range *typeAssertReferrers {
		extractInst, ok := typeAssertReferrer.(*ssa.Extract)
		if !ok {
			log.Fatalf("Tuple used by other instructions other than Extract %T\n", typeAssertReferrer)
		}
		pos := sort.SearchInts(retIndices, extractInst.Index)
		if pos < len(retIndices) && retIndices[pos] == extractInst.Index {
			// right index
			if _, ok := (*taintedSet)[extractInst]; !ok {
				(*taintedSet)[extractInst] = true
				changed = true
			}
		}
	}
	return changed
}

func functionSink(function *types.Func) bool {
	if _, ok := sinks[function.Id()]; ok {
		return true
	}
	return false
}

var sinks = map[string]bool{
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil.ContainsFinalizer(t11, \"deletion.finalize...\":string)": true,
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil.SetControllerReference(t25, t26, t24)":                   true,
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil.SetControllerReference(t138, t139, t137)":                true,
}
