package analysis

import (
	"fmt"
	"go/types"
	"log"
	"sort"
	"strings"

	"github.com/xlab-uiuc/acto/ssa/util"
	. "github.com/xlab-uiuc/acto/ssa/util"
	"golang.org/x/tools/go/callgraph"
	"golang.org/x/tools/go/ssa"
)

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
func TaintAnalysisPass(context *Context, prog *ssa.Program, frontierValues map[ssa.Value]bool, valueFieldMap map[ssa.Value]*FieldSet) *FieldSet {

	tainted := make(map[ssa.Value]bool)
	taintedFieldSet := NewFieldSet()
	for value := range frontierValues {
		backCallStack := NewCallStack()
		// if value.String() == "make any <- string (t5)" && value.Parent().String() == "github.com/rabbitmq/cluster-operator/internal/resource.generateVaultTLSTemplate" {
		// 	if TaintK8sFromValue(value, valueFieldMap, callGraph, backCallStack) {
		// 		tainted[value] = true
		// 		log.Printf("Value [%s] taints", value.String())
		// 	} else {
		// 		log.Printf("Value [%s] with path [%s] does not taint", value.String(), valueFieldMap[value].Fields())
		// 	}
		// }
		log.Printf("Checking if value [%s] in function [%s] taints\n", value.String(), value.Parent().String())
		if TaintK8sFromValue(context, value, value, valueFieldMap, context.CallGraph, backCallStack, false) {
			tainted[value] = true
			log.Printf("Value [%s] with path [%s] taint", value.String(), valueFieldMap[value].Fields())
		} else {
			log.Printf("Value [%s] with path [%s] does not taint", value.String(), valueFieldMap[value].Fields())
		}
	}

	for tainted := range tainted {
		for _, path := range valueFieldMap[tainted].Fields() {
			log.Printf("Path [%s] taints\n", path.Path)
			taintedFieldSet.Add(&path)
		}
		log.Printf("value %s with path %s\n", tainted, valueFieldMap[tainted])
		// tainted.Parent().WriteTo(log.Writer())
	}

	for field, fs := range context.FieldDataDependencyMap {
		if taintedFieldSet.Contain(*FieldFromString(field)) {
			for _, dep := range fs.Fields() {
				taintedFieldSet.Add(&dep)
			}
		}
	}
	DumpKnownFunctions()
	return taintedFieldSet
}

// Represent a uniqle taint candidate
type ReferredInstruction struct {
	Instruction ssa.Instruction
	Value       ssa.Value
}

// returns true if value taints k8s API calls
func TaintK8sFromValue(context *Context, value ssa.Value, originalValue ssa.Value, valueFieldMap map[ssa.Value]*FieldSet, callGraph *callgraph.Graph, backCallStack *CallStack, fromArg bool) bool {
	log.Printf("Checking if value [%s] in function [%s] taints\n", value.String(), value.Parent().String())
	// Maintain backCallStack
	functionCall := FunctionCall{
		FunctionName: value.Parent().String(),
		TaintSource:  fmt.Sprint(value),
	}
	if backCallStack.Contain(functionCall) {
		log.Printf("Recursive taint detected, directly return %s\n", functionCall)
		return false
	} else {
		backCallStack.Push(functionCall)
		defer backCallStack.Pop()
	}

	// Initialize the tainted set
	// The taint analysis surrounds this taintedSet map
	// Whenever a value is tainted, it is added to this map
	// Whenever we add a new value to this map, we change the variable `changed` to true
	// If no new value is tainted in one iteration, we stop the tainting and return
	taintedSet := make(map[ssa.Value]bool)
	taintedSet[value] = true

	// do a backward propogation on the taint source
	// similar to intraprocedural pointer analysis
	if IsPointerType(value) && fromArg {
		taintedParamIndex, _ := BackwardPropogation(value, taintedSet)
		if taintedParamIndex != -1 {
			node := callGraph.Nodes[value.Parent()]
			for _, inEdge := range node.In {
				// XXX avoid going into external libs
				if IsK8sStaticFunction(inEdge.Site.Parent()) {
					return true
				}
				var taintedParam ssa.Value
				if inEdge.Site.Common().IsInvoke() {
					// if the callsite is an invoke, we need to decrement the param index
					// because invoke call does not have receiver in parameter
					localParamIndex := taintedParamIndex - 1
					if localParamIndex == -1 {
						// taint the receiver
						taintedParam = inEdge.Site.Common().Value
					} else {
						taintedParam = inEdge.Site.Common().Args[localParamIndex]
					}
				} else {
					taintedParam = inEdge.Site.Common().Args[taintedParamIndex]
				}
				if TaintK8sFromValue(context, taintedParam, originalValue, valueFieldMap, callGraph, backCallStack, true) {
					return true
				}
			}
		}
	}

	// cache
	// when we finish tainting all the referrers of a value, no need to taint again
	propogatedSet := make(map[ssa.Value]bool)

	callStack := NewCallStack()
	callStack.Push(functionCall)

	for {
		changed := false
		for taintedValue := range taintedSet {
			if _, ok := propogatedSet[taintedValue]; ok {
				log.Printf("The value %s is already propogated\n", taintedValue)
				continue
			}
			referrers := taintedValue.Referrers()
			for _, instruction := range *referrers {
				// XXX: Need to maintain a callstack to handle recursive functions
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
						if typedValue.Parent().Pkg != nil {
							log.Printf("Propogate to callee %s at %s\n", typedValue.String(), typedValue.Parent().Pkg.Prog.Fset.Position(typedValue.Pos()))
						} else {
							log.Printf("Propogate to shared callee %s \n", typedValue.String())
						}
						end, taintedArgs, taintedRets := ContextAwareFunctionAnalysis(context, taintedValue, typedValue, callGraph, taintedSet, valueFieldMap, callStack)
						if end {
							return true
						}

						for _, taintedArg := range taintedArgs {
							if _, ok := taintedSet[taintedArg]; !ok {
								taintedSet[taintedArg] = true
								changed = true
							}

							// TODO: backward propogation in case of map, pointer, slice, interface
							switch taintedArg.Type().(type) {
							case *types.Map:
								end, chg := handlePointerArgBackwardPropogation(context, taintedArg, originalValue, valueFieldMap, taintedSet, callGraph, backCallStack)
								if end {
									return true
								}
								if chg {
									changed = true
								}
							case *types.Pointer:
								end, chg := handlePointerArgBackwardPropogation(context, taintedArg, originalValue, valueFieldMap, taintedSet, callGraph, backCallStack)
								if end {
									return true
								}
								if chg {
									changed = true
								}
							case *types.Slice:
								end, chg := handlePointerArgBackwardPropogation(context, taintedArg, originalValue, valueFieldMap, taintedSet, callGraph, backCallStack)
								if end {
									return true
								}
								if chg {
									changed = true
								}
							case *types.Interface:
								end, chg := handlePointerArgBackwardPropogation(context, taintedArg, originalValue, valueFieldMap, taintedSet, callGraph, backCallStack)
								if end {
									return true
								}
								if chg {
									changed = true
								}
							}
						}

						for _, taintedRet := range taintedRets {
							if _, ok := taintedSet[taintedRet]; !ok {
								taintedSet[taintedRet] = true
								changed = true
							}
						}
					case *ssa.ChangeInterface:
						if _, ok := taintedSet[typedValue]; !ok {
							taintedSet[typedValue] = true
							changed = true
						}
					case *ssa.ChangeType:
						if _, ok := taintedSet[typedValue]; !ok {
							taintedSet[typedValue] = true
							changed = true
						}
					case *ssa.Extract:
						if _, ok := taintedSet[typedValue]; !ok {
							taintedSet[typedValue] = true
							changed = true
						}
					case *ssa.Field:
						if _, ok := taintedSet[typedValue]; !ok {
							taintedSet[typedValue] = true
							changed = true
						}
					case *ssa.FieldAddr:
						if _, ok := taintedSet[typedValue]; !ok {
							taintedSet[typedValue] = true
							changed = true
						}
					case *ssa.Index:
						if _, ok := taintedSet[typedValue]; !ok {
							taintedSet[typedValue] = true
							changed = true
						}
					case *ssa.IndexAddr:
						if _, ok := taintedSet[typedValue]; !ok {
							taintedSet[typedValue] = true
							changed = true
						}
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
							log.Printf("Referred as Index in Lookup\n")
						}
					case *ssa.MakeChan:
						// skip
					case *ssa.MakeClosure:
						log.Println("Propogate to closure function as freevar")

						// compute the index of tainted freevar
						indices := []ssa.Value{}
						for i, binding := range typedValue.Bindings {
							if binding == taintedValue {
								freeVar := typedValue.Fn.(*ssa.Function).FreeVars[i]
								indices = append(indices, freeVar)
							}
						}
						end, _, _ := TaintFunction(context, typedValue.Fn.(*ssa.Function), indices, callGraph, valueFieldMap, callStack)
						if end {
							return true
						}
						// XXX: this may taint the return value and other freevars
						// this also could be used in k8s library functions
					case *ssa.MakeInterface:
						if _, ok := taintedSet[typedValue]; !ok {
							taintedSet[typedValue] = true
							changed = true
						}
					case *ssa.MakeMap:
						// skip
					case *ssa.MakeSlice:
						// skip
					case *ssa.Next:
						if _, ok := taintedSet[typedValue]; !ok {
							taintedSet[typedValue] = true
							changed = true
						}
					case *ssa.Phi:
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
						}
						// do not propogate in 2) case
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
					case *ssa.UnOp:
						if _, ok := taintedSet[typedValue]; !ok {
							taintedSet[typedValue] = true
							changed = true
						}
					default:
						log.Printf("Hit sink %T\n", typedValue)
					}
				case *ssa.DebugRef:
					// skip
				case *ssa.Defer:
					ContextAwareFunctionAnalysis(context, taintedValue, typedInst, callGraph, taintedSet, valueFieldMap, callStack)
				case *ssa.Go:
					ContextAwareFunctionAnalysis(context, taintedValue, typedInst, callGraph, taintedSet, valueFieldMap, callStack)
				case *ssa.If:
					// skip
				case *ssa.Jump:
					// skip
				case *ssa.MapUpdate:
					// TODO: field sensitive taint
					// Three cases
					// 1) used as Map
					// 2) used as Key - taint Map
					// 3) used as Value - taint Map

					// Need to further taint backward, because map is pass by reference
					if taintedValue == typedInst.Key {
						if _, ok := taintedSet[typedInst.Map]; !ok {
							log.Printf("%s -> %s\n", taintedValue, typedInst.Map)
							taintedSet[typedInst.Map] = true
							changed = true
						}
					} else if taintedValue == typedInst.Value {
						if _, ok := taintedSet[typedInst.Map]; !ok {
							log.Printf("%s -> %s\n", taintedValue, typedInst.Map)
							taintedSet[typedInst.Map] = true
							changed = true
						}

						end, chg := handlePointerArgBackwardPropogation(context, typedInst.Map, originalValue, valueFieldMap, taintedSet, callGraph, backCallStack)
						if end {
							return true
						}
						if chg {
							changed = true
						}

						// XXX: Handle parameter
						if param, ok := typedInst.Map.(*ssa.Parameter); ok {
							// updating map directly from the parameter
							// since map is pass by reference, need to taint to callsite

							// Figure out the parameter index at function body
							paramIndex := GetCalleeParamIndex(param, typedInst.Parent())

							node := callGraph.Nodes[taintedValue.Parent()]
							for _, inEdge := range node.In {
								if IsK8sStaticFunction(inEdge.Site.Parent()) {
									return true
								}

								// Two cases:
								// 1) Callsite is an invoke
								// 2) Callsite is ordinary function call
								// We need to distinguish here because the parameter index will be different
								localParamIndex := paramIndex
								if inEdge.Site.Common().IsInvoke() {
									// in invoke case, we need to decrement the parameter index
									// because the receiver is not in the parameter
									localParamIndex--
								}
								callsiteParamValue := inEdge.Site.Common().Args[localParamIndex]
								if TaintK8sFromValue(context, callsiteParamValue, originalValue, valueFieldMap, callGraph, backCallStack, true) {
									return true
								}
							}
						}
					}
				case *ssa.Panic:
					// skip
				case *ssa.Return:
					// Find all possible callsites, taint the return value

					// find the tainted index in the returned value (hanlde the case of returning tuple)
					// TODO Handle call stack carefully here
					taintedReturnSet := GetReturnIndices(taintedValue, typedInst)
					node, ok := callGraph.Nodes[taintedValue.Parent()]
					if !ok {
						log.Printf("Failed to retrieve call graph node for %s %T\n", taintedValue, taintedValue)
					}
					if node == nil {
						log.Printf("No caller for %s %T at %s\n", taintedValue, taintedValue, taintedValue.Parent().Pkg.Prog.Fset.Position(taintedValue.Pos()))
					} else {
						for _, inEdge := range node.In {
							// if it returns to a K8s client function, return true to end
							if IsK8sStaticFunction(inEdge.Site.Parent()) {
								return true
							}

							if callSiteReturnValue := inEdge.Site.Value(); callSiteReturnValue != nil {
								if typedInst.Parent().Signature.Results().Len() > 1 {
									// if return value is a tuple
									// propogate to the callsite recursively
									for _, tainted := range getExtractTaint(callSiteReturnValue, taintedReturnSet) {
										if TaintK8sFromValue(context, tainted, originalValue, valueFieldMap, callGraph, backCallStack, false) {
											return true
										}
									}
								} else {
									log.Printf("Propogate to the callsites %s from function %s\n", inEdge.Site.Parent().String(), typedInst.Parent())
									if TaintK8sFromValue(context, callSiteReturnValue, originalValue, valueFieldMap, callGraph, backCallStack, false) {
										return true
									}
								}
							} else {
								log.Fatalf("return to a non-call callsite from function %s\n", taintedValue.Parent().Pkg.Prog.Fset.Position(taintedValue.Pos()))
							}
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
					// Two cases
					// used as Addr
					// used as Val
					if taintedValue == typedInst.Val {
						// used as Val, propogate back
						// XXX need to taint to callsite

						if addrFieldSet, ok := context.ValueToFieldNodeSetMap[typedInst.Addr]; ok {
							// if val is stored into a CR field, don't run backward propogation
							// handle this case later

							for addrField := range addrFieldSet {
								if fs, ok := context.FieldDataDependencyMap[addrField.EncodedPath()]; ok {
									fs.Extend(valueFieldMap[originalValue])
								} else {
									newFieldSet := util.NewFieldSet()
									newFieldSet.Extend(valueFieldMap[originalValue])
									context.FieldDataDependencyMap[addrField.EncodedPath()] = newFieldSet
								}
							}
						} else {
							taintedParamIndex, chg := BackwardPropogation(typedInst.Addr, taintedSet)
							if chg {
								changed = true
							}
							if taintedParamIndex != -1 {
								node := callGraph.Nodes[taintedValue.Parent()]
								for _, inEdge := range node.In {
									// XXX avoid going into external libs
									if IsK8sStaticFunction(inEdge.Site.Parent()) {
										return true
									}
									// if !strings.Contains(inEdge.Site.Parent().Pkg.String(), "github.com/rabbitmq/cluster-operator") {
									// 	if IsK8sStaticFunction(inEdge.Site.Parent()) {
									// 		return true
									// 	}
									// 	continue
									// }
									var taintedParam ssa.Value
									localTaintedParamIndex := taintedParamIndex
									if inEdge.Site.Common().IsInvoke() {
										// if the callsite is an invoke, we need to decrement the param index
										// because invoke call does not have receiver in parameter
										localTaintedParamIndex--
										if localTaintedParamIndex == -1 {
											// taint the receiver
											taintedParam = inEdge.Site.Common().Value
										} else {
											taintedParam = inEdge.Site.Common().Args[localTaintedParamIndex]
										}
									} else {
										taintedParam = inEdge.Site.Common().Args[localTaintedParamIndex]
									}
									if TaintK8sFromValue(context, taintedParam, originalValue, valueFieldMap, callGraph, backCallStack, true) {
										return true
									}
								}
							}
						}
					}
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
// returns if the taint hits k8s client call, if taintedSet is updated
//
// Params:
// @value is the source of the taint
// @callInst is the call instruction
//
// TODO: XXX Do backward propogation for tainted parameters
func ContextAwareFunctionAnalysis(context *Context, value ssa.Value, callInst ssa.CallInstruction, callGraph *callgraph.Graph,
	taintedSet map[ssa.Value]bool, valueFieldMap map[ssa.Value]*FieldSet,
	callStack *CallStack) (end bool, taintedArgs []ssa.Value, taintedRets []ssa.Value) {

	end = false

	callSiteTaintedArgIndexSet := GetCallsiteArgIndices(value, callInst.Common())
	if value.Parent().Pkg != nil {
		log.Printf("Propogate to callee %s at %s with args %v\n", callInst.String(), callInst.Parent().Pkg.Prog.Fset.Position(callInst.Pos()), callSiteTaintedArgIndexSet)
	} else {
		log.Printf("Propogate to shared callee %s \n", callInst.String())
	}
	if callInst.Common().IsInvoke() {
		// invoke case
		// dynamic dispatched call, use callGraph to find all possible callees

		// determine if the callee is sink
		if IsInterfaceFunctionSink(callInst.Common().Method) {
			end = false
			return
		}

		if IsK8sInterfaceFunction(callInst.Common().Method) {
			end = true
			return
		}

		// callValue is the ret value of the call instruction
		if callValue := callInst.Value(); callValue != nil {
			taintedArgSet := NewSet[int]()
			taintedRetSet := NewSet[int]()

			// construct this function call signiture
			functionCall := FunctionCall{
				FunctionName: callInst.Common().Method.FullName(),
				TaintSource:  fmt.Sprint(callSiteTaintedArgIndexSet),
			}

			if taintResult := GetKnownInterfaceFunction(functionCall); taintResult != nil {
				endCache := taintResult.End
				taintedArgsCache := taintResult.TaintedArgs
				taintedRetsCache := taintResult.TaintedRets

				if endCache {
					end = true
					return
				}

				for _, taintedParam := range taintedArgsCache {
					taintedArgSet.Add(taintedParam)
				}
				for _, taintedRet := range taintedRetsCache {
					taintedRetSet.Add(taintedRet)
				}
			} else {
				if !strings.Contains(callInst.Common().Method.Pkg().Path(), context.RootModule.Path) {
					log.Printf("Interface Callee [%s] in package [%s] is in external library\n", callInst.Common().Method.FullName(), callInst.Common().Method.Pkg().Path())
				}
				calleeSet := CalleeSet(callGraph, callInst)
				if len(calleeSet) > 20 {
					log.Printf("Found more than 20 possible callees, skip\n")
					return
				}

				// iterate through all the possible callees
				for _, callee := range calleeSet {
					log.Printf("Propogate into concrete callee %s\n", callee.String())
					// initialize the entryPoints to taint when propogating to the callee
					// 1) taint the parameters
					// Caveat: the callsite is invoke, the callee is concrete function
					//			the parameter index should be offset because the callee's parameter
					//			contains the receiver
					entryPoints := []ssa.Value{}
					for _, callSiteTaintedArgIndex := range callSiteTaintedArgIndexSet {
						entryPoints = append(entryPoints, callee.Params[callSiteTaintedArgIndex+1])
					}

					// Run recursive function and check if the parameter is tainted
					endCache, taintedArgsCache, taintedRetsCache := TaintFunction(context, callee,
						entryPoints, callGraph, valueFieldMap, callStack)
					if endCache {
						end = true
						break
					}

					// Note: we offset Parameter index here because the args at invoke callsite does
					// not contain receiver
					for _, taintedParam := range taintedArgsCache {
						taintedArgSet.Add(taintedParam - 1)
					}
					for _, taintedRet := range taintedRetsCache {
						taintedRetSet.Add(taintedRet)
					}
				}
			}

			// Save the taint result in map
			KnownInterfaceFunction[functionCall] = FunctionTaintResult{
				End:         end,
				TaintedArgs: taintedArgSet.Items(),
				TaintedRets: taintedRetSet.Items(),
			}
			if end {
				return
			}

			// taint the callsite's return values
			resultTuple := callInst.Common().Signature().Results()
			if resultTuple != nil && taintedRetSet.Len() > 0 {
				if resultTuple.Len() > 1 {
					// handle extract
					taintedRets = append(taintedRets, getExtractTaint(callValue, taintedRetSet.Items())...)
				} else {
					taintedRets = append(taintedRets, callValue)
				}
			}

			// taint the callsite's parameter values
			for _, taintedArgIndex := range taintedArgSet.Items() {
				var taintedArg ssa.Value
				if taintedArgIndex == -1 {
					// receiver is tainted
					taintedArg = callInst.Common().Value
				} else {
					taintedArg = callInst.Common().Args[taintedArgIndex]
				}
				taintedArgs = append(taintedArgs, taintedArg)
			}
		}
		// ELSE Go, Defer instruction
	} else {
		// ordinary call case
		switch callee := callInst.Common().Value.(type) {
		case *ssa.Function:

			if IsStaticFunctionSink(callee) {
				return
			}

			if IsK8sStaticFunction(callee) {
				end = true
				return
			}

			if callValue := callInst.Value(); callValue != nil {
				// if it's a Call instruction

				if taintResult := GetKnownStaticFunction(callee, callSiteTaintedArgIndexSet); taintResult != nil {
					endCache := taintResult.End
					taintedArgsCache := taintResult.TaintedArgs
					taintedRetsCache := taintResult.TaintedRets

					if endCache {
						end = true
						return
					} else if len(taintedArgsCache) == 0 && len(taintedRetsCache) == 0 {
						return
					}

					// taint the callsite's return values
					resultTuple := callee.Signature.Results()
					if resultTuple != nil && len(taintedRetsCache) > 0 {
						if resultTuple.Len() > 1 {
							// handle extract
							taintedRets = append(taintedRets, getExtractTaint(callValue, taintedRetsCache)...)
						} else {
							taintedRets = append(taintedRets, callValue)
						}
					}

					// taint the callsite's parameter values
					for _, taintedArgIndex := range taintedArgsCache {
						taintedArg := callInst.Common().Args[taintedArgIndex]
						taintedArgs = append(taintedArgs, taintedArg)
					}
				} else {
					if !strings.Contains(callee.Pkg.Pkg.Path(), context.RootModule.Path) {
						log.Printf("Static callee [%s] is in external library [%s]\n", callee.String(), callee.Pkg.Pkg.Path())
					}

					// initialize the entryPoints to taint when propogating to the callee
					// In static call case, we only need to taint the parameter,
					// as the receiver will be included in the parameter
					entryPoints := []ssa.Value{}
					for _, callSiteTaintedArgIndex := range callSiteTaintedArgIndexSet {
						entryPoints = append(entryPoints, callee.Params[callSiteTaintedArgIndex])
					}
					endCache, taintedArgsCache, taintedRetsCache := TaintFunction(context, callee,
						entryPoints, callGraph, valueFieldMap, callStack)

					// save this taint result in cache
					functionCall := FunctionCall{
						FunctionName: callee.String(),
						TaintSource:  fmt.Sprint(callSiteTaintedArgIndexSet),
					}
					KnownStaticFunction[functionCall] = FunctionTaintResult{
						End:         endCache,
						TaintedArgs: taintedArgsCache,
						TaintedRets: taintedRetsCache,
					}
					log.Printf("Saved known static function taint result for %s\n", callee.String())
					log.Printf("The saved result is %s\n", KnownStaticFunction[functionCall])

					if endCache {
						end = true
						return
					} else if len(taintedArgsCache) == 0 && len(taintedRetsCache) == 0 {
						return
					}

					// taint the callsite's return values
					resultTuple := callee.Signature.Results()
					if resultTuple != nil && len(taintedRetsCache) > 0 {
						if resultTuple.Len() > 1 {
							// handle extract
							taintedRets = append(taintedRets, getExtractTaint(callValue, taintedRetsCache)...)
						} else {
							taintedRets = append(taintedRets, callValue)
						}
						log.Printf("Returning the taintedRet set: %s\n", taintedRets)
					} else if resultTuple == nil {
						log.Printf("The result tuple is nil\n")
					} else {
						log.Printf("The length of rets is %d\n", len(taintedRetsCache))
					}

					// taint the callsite's parameter values
					for _, taintedArgIndex := range taintedArgsCache {
						taintedArg := callInst.Common().Args[taintedArgIndex]
						taintedArgs = append(taintedArgs, taintedArg)
					}
				}
			}
			// Go, Defer instruction
		case *ssa.MakeClosure:
			functionBody := callee.Fn.(*ssa.Function)
			if callValue := callInst.Value(); callValue != nil && functionBody != nil {
				// initialize the entryPoints to taint when propogating to the callee
				// In static call case, we only need to taint the parameter,
				// as the receiver will be included in the parameter

				if taintResult := GetKnownStaticFunction(functionBody, callSiteTaintedArgIndexSet); taintResult != nil {
					endCache := taintResult.End
					taintedArgsCache := taintResult.TaintedArgs
					taintedRetsCache := taintResult.TaintedRets

					if endCache {
						end = true
						return
					} else if len(taintedArgs) == 0 && len(taintedRets) == 0 {
						return
					}

					// taint the callsite's return values
					resultTuple := functionBody.Signature.Results()
					if resultTuple != nil && len(taintedRetsCache) > 0 {
						if resultTuple.Len() > 1 {
							// handle extract
							taintedRets = append(taintedRets, getExtractTaint(callValue, taintedRetsCache)...)
						} else {
							taintedRets = append(taintedRets, callValue)
						}
					}

					// taint the callsite's parameter values
					for _, taintedArgIndex := range taintedArgsCache {
						taintedArg := callInst.Common().Args[taintedArgIndex]
						taintedArgs = append(taintedArgs, taintedArg)
					}
				} else {
					entryPoints := []ssa.Value{}
					for _, callSiteTaintedArgIndex := range callSiteTaintedArgIndexSet {
						entryPoints = append(entryPoints, functionBody.Params[callSiteTaintedArgIndex])
					}
					endCache, taintedArgsCache, taintedRetsCache := TaintFunction(context, functionBody,
						entryPoints, callGraph, valueFieldMap, callStack)

					// save this taint result in cache
					functionCall := FunctionCall{
						FunctionName: callee.String(),
						TaintSource:  fmt.Sprint(callSiteTaintedArgIndexSet),
					}
					KnownStaticFunction[functionCall] = FunctionTaintResult{
						End:         endCache,
						TaintedArgs: taintedArgsCache,
						TaintedRets: taintedRetsCache,
					}

					if endCache {
						end = true
						return
					} else if len(taintedArgsCache) == 0 && len(taintedRetsCache) == 0 {
						return
					}

					// taint the callsite's return values
					resultTuple := functionBody.Signature.Results()
					if resultTuple != nil && len(taintedRetsCache) > 0 {
						if resultTuple.Len() > 1 {
							// handle extract
							taintedRets = append(taintedRets, getExtractTaint(callValue, taintedRetsCache)...)
						} else {
							taintedRets = append(taintedRets, callValue)
						}
					}

					// taint the callsite's parameter values
					for _, taintedArgIndex := range taintedArgsCache {
						taintedArg := callInst.Common().Args[taintedArgIndex]
						taintedArgs = append(taintedArgs, taintedArg)
					}
				}
			}
		case *ssa.Builtin:
			// need to define the buildins to propogate
			if _, ok := BUILTIN_PROPOGATE[callee.Name()]; ok {
				log.Printf("Builtin function %s, propogate to return value\n", callee.Name())
				if callValue := callInst.Value(); callValue != nil {
					taintedRets = append(taintedRets, callValue)
				}
			}
		default:
		}
	}
	return
}

// XXX: May also need to taint the receiver
//
// TaintFunction tries to run taint analysis on the functionBody
// The initial taints are specified in the
// returns the indices of the tainted return values
func TaintFunction(context *Context, functionBody *ssa.Function, entryPoints []ssa.Value, callGraph *callgraph.Graph,
	valueFieldMap map[ssa.Value]*FieldSet,
	callStack *CallStack) (end bool, taintedParams []int, taintedRets []int) {

	log.Printf("Stack %s\n", *callStack)
	funcCall := FunctionCall{
		FunctionName: functionBody.String(),
		TaintSource:  fmt.Sprint(entryPoints),
	}
	if callStack.Contain(funcCall) {
		log.Printf("Recursive taint detected, directly return %s\n", funcCall)
		return false, []int{}, []int{}
	} else {
		callStack.Push(funcCall)
		defer callStack.Pop()
	}

	taintedSet := make(map[ssa.Value]bool)
	for _, entryPoint := range entryPoints {
		taintedSet[entryPoint] = true
	}

	taintedParamIndexSet := NewSet[int]()  // used to store param index for return
	taintedReturnIndexSet := NewSet[int]() // used to store return index for return

	// cache
	// when we finish tainting all the referrers of a value, no need to taint again
	propogatedSet := make(map[ssa.Value]bool)

	// loop until there is no new change
	for {
		changed := false
		for taintedValue := range taintedSet {
			if _, ok := propogatedSet[taintedValue]; ok {
				continue
			}
			referrers := taintedValue.Referrers()
			if referrers == nil {
				log.Printf("%s: %s referrer not defined\n", taintedValue.Name(), taintedValue.String())
				propogatedSet[taintedValue] = true
				continue
			}
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

						end, taintedArgs, taintedRets := ContextAwareFunctionAnalysis(context, taintedValue, typedValue, callGraph, taintedSet, valueFieldMap, callStack)

						for _, taintedArg := range taintedArgs {
							if _, ok := taintedSet[taintedArg]; !ok {
								taintedSet[taintedArg] = true
								changed = true
							}
						}

						for _, taintedRet := range taintedRets {
							if _, ok := taintedSet[taintedRet]; !ok {
								log.Printf("Got tainted return value [%s]\n", taintedRet.Name())
								taintedSet[taintedRet] = true
								changed = true
							} else {
								log.Printf("Got tainted return value [%s], but already tainted\n", taintedRet.Name())
							}
						}
						if end {
							return true, taintedParamIndexSet.Items(), taintedReturnIndexSet.Items()
						}
					case *ssa.ChangeInterface:
						if _, ok := taintedSet[typedValue]; !ok {
							taintedSet[typedValue] = true
							changed = true
						}
					case *ssa.ChangeType:
						if _, ok := taintedSet[typedValue]; !ok {
							taintedSet[typedValue] = true
							changed = true
						}
					case *ssa.Extract:
						if _, ok := taintedSet[typedValue]; !ok {
							taintedSet[typedValue] = true
							changed = true
						}
					case *ssa.Field:
						if _, ok := taintedSet[typedValue]; !ok {
							taintedSet[typedValue] = true
							changed = true
						}
					case *ssa.FieldAddr:
						if _, ok := taintedSet[typedValue]; !ok {
							taintedSet[typedValue] = true
							changed = true
						}
					case *ssa.Index:
						if _, ok := taintedSet[typedValue]; !ok {
							taintedSet[typedValue] = true
							changed = true
						}
					case *ssa.IndexAddr:
						if _, ok := taintedSet[typedValue]; !ok {
							taintedSet[typedValue] = true
							changed = true
						}
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
							log.Printf("Referred as Index in Lookup\n")
						}
					case *ssa.MakeChan:
						// skip
					case *ssa.MakeClosure:
						log.Println("Propogate to closure function as freevar")

						// compute the index of tainted freevar
						indices := []ssa.Value{}
						for i, binding := range typedValue.Bindings {
							if binding == taintedValue {
								freeVar := typedValue.Fn.(*ssa.Function).FreeVars[i]
								indices = append(indices, freeVar)
							}
						}
						end, _, _ := TaintFunction(context, typedValue.Fn.(*ssa.Function), indices, callGraph, valueFieldMap, callStack)
						if end {
							return true, taintedParamIndexSet.Items(), taintedReturnIndexSet.Items()
						}
						// XXX: this may taint the return value and other freevars
						// this also could be used in k8s library functions
					case *ssa.MakeInterface:
						if _, ok := taintedSet[typedValue]; !ok {
							taintedSet[typedValue] = true
							changed = true
						}
					case *ssa.MakeMap:
						// skip
					case *ssa.MakeSlice:
						// skip
					case *ssa.Next:
						if _, ok := taintedSet[typedValue]; !ok {
							taintedSet[typedValue] = true
							changed = true
						}
					case *ssa.Phi:
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
						// skip
					case *ssa.Slice:
						// Two cases: 1) referred as the X 2) referred as the Low, High, Max
						if taintedValue == typedValue.X {
							if _, ok := taintedSet[typedValue]; !ok {
								taintedSet[typedValue] = true
								changed = true
							}
						}
						// do not propogate in 2) case
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
					case *ssa.UnOp:
						if _, ok := taintedSet[typedValue]; !ok {
							taintedSet[typedValue] = true
							changed = true
						}
					default:
						log.Printf("Hit sink %T\n", typedValue)
					}
				case *ssa.DebugRef:
					// skip
				case *ssa.Defer:
					end, taintedArgs, taintedRets := ContextAwareFunctionAnalysis(context, taintedValue, typedInst, callGraph, taintedSet, valueFieldMap, callStack)

					for _, taintedArg := range taintedArgs {
						if _, ok := taintedSet[taintedArg]; !ok {
							taintedSet[taintedArg] = true
							changed = true
						}
					}

					for _, taintedRet := range taintedRets {
						if _, ok := taintedSet[taintedRet]; !ok {
							taintedSet[taintedRet] = true
							changed = true
						}
					}
					if end {
						return true, taintedParamIndexSet.Items(), taintedReturnIndexSet.Items()
					}
				case *ssa.Go:
					end, taintedArgs, taintedRets := ContextAwareFunctionAnalysis(context, taintedValue, typedInst, callGraph, taintedSet, valueFieldMap, callStack)

					for _, taintedArg := range taintedArgs {
						if _, ok := taintedSet[taintedArg]; !ok {
							taintedSet[taintedArg] = true
							changed = true
						}
					}

					for _, taintedRet := range taintedRets {
						if _, ok := taintedSet[taintedRet]; !ok {
							taintedSet[taintedRet] = true
							changed = true
						}
					}
					if end {
						return true, taintedParamIndexSet.Items(), taintedReturnIndexSet.Items()
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
						taintedParam, chg := BackwardPropogation(typedInst.Map, taintedSet)
						if chg {
							changed = true
						}
						if taintedParam != -1 {
							taintedParamIndexSet.Add(taintedParam)
						}

						// XXX: Handle parameter
						if param, ok := typedInst.Map.(*ssa.Parameter); ok {
							// updating map directly from the parameter
							// since map is pass by reference, need to taint to callsite

							// Figure out the parameter index at function body
							paramIndex := GetCalleeParamIndex(param, typedInst.Parent())
							taintedParamIndexSet.Add(paramIndex)
						}
					}
				case *ssa.Panic:
					// skip
				case *ssa.Return:
					log.Printf("Hit return, tainting the return index set\n")
					for i, result := range typedInst.Results {
						if result == taintedValue {
							log.Printf("Tainted %dth return value\n", i)
							taintedReturnIndexSet.Add(i)
						}
					}
				case *ssa.RunDefers:
					// skip
				case *ssa.Send:
					// Two cases
					// used as X
					// used as Chan
				case *ssa.Store:
					if taintedValue == typedInst.Val {
						// used as Val, propogate back
						// backward propogation may propogate to parameter, need to taint the callsite
						// through context aware analysis
						taintedParam, chg := BackwardPropogation(typedInst.Addr, taintedSet)
						if chg {
							changed = true
						}
						if taintedParam != -1 {
							taintedParamIndexSet.Add(taintedParam)
						}
					}
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

	return false, taintedParamIndexSet.Items(), taintedReturnIndexSet.Items()
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

// Same as handleExtractTaint, except this directly returns the tainted values
func getExtractTaint(taintSource ssa.Value, retIndices []int) (tainted []ssa.Value) {
	sort.Ints(retIndices)
	referrers := taintSource.Referrers()
	for _, referrer := range *referrers {
		extractInst, ok := referrer.(*ssa.Extract)
		if !ok {
			log.Fatalf("Tuple used by other instructions other than Extract %T\n", referrer)
		}
		pos := sort.SearchInts(retIndices, extractInst.Index)
		if pos < len(retIndices) && retIndices[pos] == extractInst.Index {
			// right index
			tainted = append(tainted, extractInst)
		}
	}
	return
}

// This function handles the tainted argument from function callsite
// if the tainted argument is map, pointer, slice, interface, we need to propogate backwards
func handlePointerArgBackwardPropogation(context *Context, taintedArg ssa.Value, originalValue ssa.Value, valueFieldMap map[ssa.Value]*FieldSet,
	taintedSet map[ssa.Value]bool, callGraph *callgraph.Graph, backCallStack *CallStack) (end bool, changed bool) {

	taintedParamIndex, chg := BackwardPropogation(taintedArg, taintedSet)
	if chg {
		changed = true
	}
	if taintedParamIndex != -1 {
		node := callGraph.Nodes[taintedArg.Parent()]
		for _, inEdge := range node.In {
			// XXX avoid going into external libs
			if IsK8sStaticFunction(inEdge.Site.Parent()) {
				end = true
				return
			}
			var taintedParam ssa.Value
			if inEdge.Site.Common().IsInvoke() {
				// if the callsite is an invoke, we need to decrement the param index
				// because invoke call does not have receiver in parameter
				localParamIndex := taintedParamIndex - 1
				if localParamIndex == -1 {
					// taint the receiver
					taintedParam = inEdge.Site.Common().Value
				} else {
					taintedParam = inEdge.Site.Common().Args[localParamIndex]
				}
			} else {
				taintedParam = inEdge.Site.Common().Args[taintedParamIndex]
			}
			if TaintK8sFromValue(context, taintedParam, originalValue, valueFieldMap, callGraph, backCallStack, true) {
				end = true
				return
			}
		}
	}
	return
}
