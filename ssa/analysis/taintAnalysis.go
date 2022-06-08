package analysis

import (
	"fmt"
	"log"
	"sort"
	"strings"

	. "github.com/xlab-uiuc/acto/ssa/util"
	"golang.org/x/tools/go/callgraph"
	"golang.org/x/tools/go/pointer"
	"golang.org/x/tools/go/ssa"
	"golang.org/x/tools/go/ssa/ssautil"
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
func TaintAnalysisPass(prog *ssa.Program, frontierValues map[ssa.Value]bool, valueFieldMap map[ssa.Value]*FieldSet) map[ssa.Value]bool {
	log.Println("Constructing call graph using pointer analysis")
	cfg := pointer.Config{
		Mains:          ssautil.MainPackages(prog.AllPackages()),
		BuildCallGraph: true,
	}
	log.Printf("Main packages %s\n", ssautil.MainPackages(prog.AllPackages()))
	result, err := pointer.Analyze(&cfg)
	if err != nil {
		log.Fatalf("Failed to run pointer analysis to construct callgraph %V\n", err)
	}
	callGraph := result.CallGraph
	callGraph.Root.Func.WriteTo(log.Writer())
	log.Println("Finished constructing call graph")

	tainted := make(map[ssa.Value]bool)
	for value := range frontierValues {
		// if value.String() == "*t127" && value.Parent().String() == "(*github.com/rabbitmq/cluster-operator/controllers.RabbitmqClusterReconciler).Reconcile" {
		// 	log.Printf("Checking if value [%s] in function [%s] taints\n", value.String(), value.Parent().String())
		// 	if !TaintK8sFromValue(value, valueFieldMap, callGraph) {
		// 		tainted[value] = true
		// 	}
		// }
		log.Printf("Checking if value [%s] in function [%s] taints\n", value.String(), value.Parent().String())
		if TaintK8sFromValue(value, valueFieldMap, callGraph) {
			tainted[value] = true
			log.Printf("Value [%s] taints", value.String())
		} else {
			log.Printf("Value [%s] with path [%s] does not taint", value.String(), valueFieldMap[value].Fields())
		}
	}
	return tainted
}

// Represent a uniqle taint candidate
type ReferredInstruction struct {
	Instruction ssa.Instruction
	Value       ssa.Value
}

// returns true if value taints k8s API calls
func TaintK8sFromValue(value ssa.Value, valueFieldMap map[ssa.Value]*FieldSet, callGraph *callgraph.Graph) bool {
	// Initialize the tainted set
	// The taint analysis surrounds this taintedSet map
	// Whenever a value is tainted, it is added to this map
	// Whenever we add a new value to this map, we change the variable `changed` to true
	// If no new value is tainted in one iteration, we stop the tainting and return
	taintedSet := make(map[ssa.Value]bool)
	taintedSet[value] = true

	// cache
	// when we finish tainting all the referrers of a value, no need to taint again
	propogatedSet := make(map[ssa.Value]bool)

	callStack := NewCallStack()

	// cache
	// if we already tried to taint this instruction from the same referrer
	// no need to try again
	//
	// The key is a composite of the instruction and the value
	handledInstructionSet := make(map[ReferredInstruction]bool)

	for {
		changed := false
		for taintedValue := range taintedSet {
			if _, ok := propogatedSet[taintedValue]; ok {
				continue
			}
			referrers := taintedValue.Referrers()
			for _, instruction := range *referrers {
				referredInstruction := ReferredInstruction{
					Instruction: instruction,
					Value:       taintedValue,
				}
				// XXX: Need to maintain a callstack to handle recursive functions
				if _, ok := handledInstructionSet[referredInstruction]; ok {
					continue
				} else {
					handledInstructionSet[referredInstruction] = true
				}
				switch typedInst := instruction.(type) {
				case ssa.Value:
					if _, exist := valueFieldMap[typedInst]; exist {
						// quick return, if the referrer is already a field
						continue
					}
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
							log.Printf("Propogate to callee %s in package %s\n", typedValue.String(), typedValue.Parent().Pkg.Pkg.Name())
						} else {
							log.Printf("Propogate to shared callee %s \n", typedValue.String())
						}
						end, chg := ContextAwareFunctionAnalysis(taintedValue, typedValue, callGraph, taintedSet,
							valueFieldMap, callStack)
						if end {
							return true
						}
						if chg {
							changed = true
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
							log.Fatal("Referred as Index in Lookup\n")
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
						end, _, _ := TaintFunction(typedValue.Fn.(*ssa.Function), indices, callGraph, valueFieldMap, callStack)
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
					ContextAwareFunctionAnalysis(taintedValue, typedInst.Value(), callGraph, taintedSet, valueFieldMap, callStack)
				case *ssa.Go:
					ContextAwareFunctionAnalysis(taintedValue, typedInst.Value(), callGraph, taintedSet, valueFieldMap, callStack)
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
					// Find all possible callsites, taint the return value

					// find the tainted index in the returned value (hanlde the case of returning tuple)
					// TODO Handle call stack carefully here
					taintedReturnSet := GetReturnIndices(taintedValue, typedInst)
					node := callGraph.Nodes[taintedValue.Parent()]
					for _, inEdge := range node.In {
						if callSiteReturnValue := inEdge.Site.Value(); callSiteReturnValue != nil {
							if typedInst.Parent().Signature.Results().Len() > 1 {
								// if return value is a tuple
								if handleExtractTaint(callSiteReturnValue, &taintedSet, taintedReturnSet) {
									changed = true
								}
							} else {
								if _, ok := taintedSet[callSiteReturnValue]; !ok {
									taintedSet[callSiteReturnValue] = true
									changed = true
								}
							}
						} else {
							log.Fatalf("return to a non-call callsite\n")
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
						_, chg := BackwardPropogation(typedInst, taintedSet)
						if chg {
							changed = true
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
func ContextAwareFunctionAnalysis(value ssa.Value, callInst ssa.CallInstruction, callGraph *callgraph.Graph,
	taintedSet map[ssa.Value]bool, valueFieldMap map[ssa.Value]*FieldSet,
	callStack *CallStack) (end bool, changed bool) {

	callSiteTaintedParamIndexSet := GetParamIndices(value, callInst.Common())
	if callInst.Common().IsInvoke() {
		// invoke case
		// dynamic dispatched call, use callGraph to find all possible callees

		// determine if the callee is sink
		if IsInterfaceFunctionSink(callInst.Common().Method) {
			return false, false
		}

		if IsK8sInterfaceFunction(callInst.Common().Method) {
			return true, false
		}

		// callValue is the ret value of the call instruction
		if callValue := callInst.Value(); callValue != nil {
			taintedParamSet := NewSet[int]()
			taintedRetSet := NewSet[int]()
			var taintedReceiver ssa.Value = nil

			// if the receiver is tainted, taint the receiver at the callee
			if value == callInst.Common().Value {
				taintedReceiver = value
			}

			if taintResult := GetKnownInterfaceFunction(callInst.Common().Method, callSiteTaintedParamIndexSet); taintResult != nil {
				end := taintResult.End
				taintedParams := taintResult.TaintedParams
				taintedRets := taintResult.TaintedRets

				if end {
					return true, false
				}

				for _, taintedParam := range taintedParams {
					taintedParamSet.Add(taintedParam)
				}
				for _, taintedRet := range taintedRets {
					taintedRetSet.Add(taintedRet)
				}
			} else {
				if !strings.Contains(callInst.Common().Method.Pkg().String(), "github.com/rabbitmq/cluster-operator") {
					log.Printf("Interface Callee [%s] in package [%s] is in external library\n", callInst.Common().Method.FullName(), callInst.Common().Method.Pkg().Name())
				}
				calleeSet := CalleeSet(callGraph, callInst)
				if len(calleeSet) > 20 {
					log.Printf("Found more than 20 possible callees, skip\n")
					return false, false
				}

				// iterate through all the possible callees
				for _, callee := range calleeSet {
					// initialize the entryPoints to taint when propogating to the callee
					// 1) taint the parameters
					entryPoints := []ssa.Value{}
					for _, callSiteTaintedParamIndex := range callSiteTaintedParamIndexSet {
						entryPoints = append(entryPoints, callee.Params[callSiteTaintedParamIndex])
					}
					// 2) taint the receiver
					if taintedReceiver != nil {
						entryPoints = append(entryPoints, taintedReceiver)
					}

					// Run recursive function and check if the parameter is tainted
					end, taintedParams, taintedRets := TaintFunction(callee,
						entryPoints, callGraph, valueFieldMap, callStack)
					if end {
						return true, false
					}

					for _, taintedParam := range taintedParams {
						taintedParamSet.Add(taintedParam)
					}
					for _, taintedRet := range taintedRets {
						taintedRetSet.Add(taintedRet)
					}
				}
			}

			// taint the callsite's return values
			resultTuple := callInst.Common().Signature().Results()
			if resultTuple != nil {
				if resultTuple.Len() > 1 {
					// handle extract
					if handleExtractTaint(callValue, &taintedSet, taintedRetSet.Items()) {
						changed = true
					}
				} else {
					if _, ok := taintedSet[callValue]; !ok {
						taintedSet[callValue] = true
						changed = true
					}
				}
			}

			// taint the callsite's parameter values
			for _, taintedParamIndex := range taintedParamSet.Items() {
				taintedParam := callInst.Common().Args[taintedParamIndex]
				if _, ok := taintedSet[taintedParam]; ok {
					taintedSet[taintedParam] = true
					changed = true
				}
			}
		}
		// Go, Defer instruction
	} else {
		// ordinary call case
		switch callee := callInst.Common().Value.(type) {
		case *ssa.Function:

			if IsStaticFunctionSink(callee) {
				return false, false
			}

			if IsK8sStaticFunction(callee) {
				return true, false
			}

			// KnownStaticFunction()
			if callValue := callInst.Value(); callValue != nil {
				// if it's a Call instruction

				if taintResult := GetKnownStaticFunction(callee, callSiteTaintedParamIndexSet); taintResult != nil {
					end := taintResult.End
					taintedParams := taintResult.TaintedParams
					taintedRets := taintResult.TaintedRets
					if end {
						return true, false
					} else if len(taintedParams) == 0 && len(taintedRets) == 0 {
						return false, false
					}

					// taint the callsite's return values
					resultTuple := callee.Signature.Results()
					if resultTuple != nil {
						if resultTuple.Len() > 1 {
							// handle extract
							if handleExtractTaint(callValue, &taintedSet, taintedRets) {
								changed = true
							}
						} else {
							if _, ok := taintedSet[callValue]; !ok {
								taintedSet[callValue] = true
								changed = true
							}
						}
					}

					// taint the callsite's parameter values
					for _, taintedParamIndex := range taintedParams {
						taintedParam := callInst.Common().Args[taintedParamIndex]
						if _, ok := taintedSet[taintedParam]; ok {
							taintedSet[taintedParam] = true
							changed = true
						}
					}
				} else {
					if !strings.Contains(callee.Pkg.String(), "github.com/rabbitmq/cluster-operator") {
						log.Printf("Callee [%s] is in external library\n", callee.String())
					}

					// initialize the entryPoints to taint when propogating to the callee
					// In static call case, we only need to taint the parameter,
					// as the receiver will be included in the parameter
					entryPoints := []ssa.Value{}
					for _, callSiteTaintedParamIndex := range callSiteTaintedParamIndexSet {
						entryPoints = append(entryPoints, callee.Params[callSiteTaintedParamIndex])
					}
					end, taintedParams, taintedRets := TaintFunction(callee,
						entryPoints, callGraph, valueFieldMap, callStack)
					if end {
						return true, false
					} else if len(taintedParams) == 0 && len(taintedRets) == 0 {
						return false, false
					}

					// taint the callsite's return values
					resultTuple := callee.Signature.Results()
					if resultTuple != nil {
						if resultTuple.Len() > 1 {
							// handle extract
							if handleExtractTaint(callValue, &taintedSet, taintedRets) {
								changed = true
							}
						} else {
							if _, ok := taintedSet[callValue]; !ok {
								taintedSet[callValue] = true
								changed = true
							}
						}
					}

					// taint the callsite's parameter values
					for _, taintedParamIndex := range taintedParams {
						taintedParam := callInst.Common().Args[taintedParamIndex]
						if _, ok := taintedSet[taintedParam]; ok {
							taintedSet[taintedParam] = true
							changed = true
						}
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

				if taintResult := GetKnownStaticFunction(functionBody, callSiteTaintedParamIndexSet); taintResult != nil {
					end := taintResult.End
					taintedParams := taintResult.TaintedParams
					taintedRets := taintResult.TaintedRets
					if end {
						return true, false
					} else if len(taintedParams) == 0 && len(taintedRets) == 0 {
						return false, false
					}

					// taint the callsite's return values
					resultTuple := functionBody.Signature.Results()
					if resultTuple != nil {
						if resultTuple.Len() > 1 {
							// handle extract
							if handleExtractTaint(callValue, &taintedSet, taintedRets) {
								changed = true
							}
						} else {
							if _, ok := taintedSet[callValue]; !ok {
								taintedSet[callValue] = true
								changed = true
							}
						}
					}

					// taint the callsite's parameter values
					for _, taintedParamIndex := range taintedParams {
						taintedParam := callInst.Common().Args[taintedParamIndex]
						if _, ok := taintedSet[taintedParam]; ok {
							taintedSet[taintedParam] = true
							changed = true
						}
					}
				} else {
					entryPoints := []ssa.Value{}
					for _, callSiteTaintedParamIndex := range callSiteTaintedParamIndexSet {
						entryPoints = append(entryPoints, functionBody.Params[callSiteTaintedParamIndex])
					}
					end, taintedParams, taintedRets := TaintFunction(functionBody,
						entryPoints, callGraph, valueFieldMap, callStack)
					if end {
						return true, false
					} else if len(taintedParams) == 0 && len(taintedRets) == 0 {
						return false, false
					}

					// taint the callsite's return values
					resultTuple := functionBody.Signature.Results()
					if resultTuple != nil {
						if resultTuple.Len() > 1 {
							// handle extract
							if handleExtractTaint(callValue, &taintedSet, taintedRets) {
								changed = true
							}
						} else {
							if _, ok := taintedSet[callValue]; !ok {
								taintedSet[callValue] = true
								changed = true
							}
						}
					}

					// taint the callsite's parameter values
					for _, taintedParamIndex := range taintedParams {
						taintedParam := callInst.Common().Args[taintedParamIndex]
						if _, ok := taintedSet[taintedParam]; ok {
							taintedSet[taintedParam] = true
							changed = true
						}
					}
				}
			}
		case *ssa.Builtin:
			// need to define the buildins to propogate
			if _, ok := BUILTIN_PROPOGATE[callee.Name()]; ok {
				log.Printf("Builtin function %s, propogate to return value\n", callee.Name())
				if callValue := callInst.Value(); callValue != nil {
					if _, ok := taintedSet[callValue]; !ok {
						taintedSet[callValue] = true
						changed = true
					}
				}
			}
		default:
		}
	}
	return false, changed
}

// XXX: May also need to taint the receiver
//
// TaintFunction tries to run taint analysis on the functionBody
// The initial taints are specified in the
// returns the indices of the tainted return values
func TaintFunction(functionBody *ssa.Function, entryPoints []ssa.Value, callGraph *callgraph.Graph,
	valueFieldMap map[ssa.Value]*FieldSet,
	callStack *CallStack) (end bool, taintedParams []int, taintedRets []int) {

	funcCall := FunctionCall{
		FunctionName: functionBody.String(),
		TaintSource:  fmt.Sprint(entryPoints),
	}
	if callStack.Contain(funcCall) {
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
					if _, exist := valueFieldMap[typedInst]; exist {
						// quick return, if the referrer is already a field
						continue
					}
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
							if IsK8sUpdateCall(&typedValue.Call) {
								return true, taintedParamIndexSet.Items(), taintedReturnIndexSet.Items()
							}
						}
						if typedValue.Parent().Pkg != nil {
							log.Printf("Propogate to callee %s in package %s\n", typedValue.String(), typedValue.Parent().Pkg.Pkg.Name())
						} else {
							log.Printf("Propogate to shared callee %s \n", typedValue.String())
						}

						if end, chg := ContextAwareFunctionAnalysis(taintedValue, typedValue, callGraph, taintedSet, valueFieldMap, callStack); chg {
							changed = true
						} else if end {
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
						end, _, _ := TaintFunction(typedValue.Fn.(*ssa.Function), indices, callGraph, valueFieldMap, callStack)
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
					if end, chg := ContextAwareFunctionAnalysis(taintedValue, typedInst, callGraph, taintedSet, valueFieldMap, callStack); chg {
						changed = true
					} else if end {
						return true, taintedParamIndexSet.Items(), taintedReturnIndexSet.Items()
					}
				case *ssa.Go:
					if end, chg := ContextAwareFunctionAnalysis(taintedValue, typedInst, callGraph, taintedSet, valueFieldMap, callStack); chg {
						changed = true
					} else if end {
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
					}
				case *ssa.Panic:
					// skip
				case *ssa.Return:
					for i, result := range typedInst.Results {
						if result == taintedValue {
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
					// TODO: propogate back
					if taintedValue == typedInst.Val {
						// used as Val, propogate back
						// backward propogation may propogate to parameter, need to taint the callsite
						// through context aware analysis
						taintedParam, chg := BackwardPropogation(typedInst, taintedSet)
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
