package analysis

import (
	"go/token"
	"log"

	"github.com/xlab-uiuc/acto/ssa/util"
	"golang.org/x/tools/go/ssa"
)

// Dominators finds the dominees of the fields, and store the relationship into
// the context.FieldToFieldDominees map
func Dominators(context *Context, frontierSet map[ssa.Value]bool) {
	frontierValuesByBlock := map[*ssa.BasicBlock]*[]ssa.Value{}
	fieldToValueMap := map[string]*[]ssa.Value{}
	fieldToValueConditionMap := map[string]map[ssa.Value]*ConcreteConditionSet{}

	for value := range frontierSet {
		// fill the frontierValuesByBlock
		if _, ok := value.(ssa.Instruction); !ok {
			continue
		}
		block := value.(ssa.Instruction).Block()
		if slice, ok := frontierValuesByBlock[block]; ok {
			*slice = append(*slice, value)
		} else {
			frontierValuesByBlock[block] = &[]ssa.Value{value}
		}

		// fill the fieldToValueMap
		for _, field := range context.ValueFieldMap[value].Fields() {
			if slice, ok := fieldToValueMap[field.String()]; ok {
				log.Printf("Appending %s:%s to field %s\n", value.Name(), value, field.String())
				*slice = append(*slice, value)
			} else {
				log.Printf("Constructing fieldToValueMap for field %s\n", field.String())
				fieldToValueMap[field.String()] = &[]ssa.Value{value}
			}
		}

		FindDirectBranches(context, value)
	}

	for ifStmt, condition := range context.IfToCondition {
		trueDominees := BlockDominees(context, ifStmt.Block(), true)
		trueFunctionDominees := FindFunctionDominees(context, trueDominees)
		if len(trueFunctionDominees) > 0 {
			log.Printf("Branch at %s [TRUE] has function dominees: %s", context.Program.Fset.Position(ifStmt.(*ssa.If).Cond.Pos()), trueFunctionDominees)
			for _, trueFunctionDominee := range trueFunctionDominees {
				trueDominees = append(trueDominees, trueFunctionDominee.Blocks...)
			}
		}
		log.Printf("Branch at %s [TRUE] has the block dominees: ", context.Program.Fset.Position(ifStmt.(*ssa.If).Cond.Pos()))
		for _, trueDominee := range trueDominees {
			log.Printf("%d ", trueDominee.Index)
		}
		falseDominees := BlockDominees(context, ifStmt.Block(), false)
		falseFunctionDominees := FindFunctionDominees(context, falseDominees)
		if len(falseFunctionDominees) > 0 {
			log.Printf("Branch at %s [FALSE] has function dominees: %s", context.Program.Fset.Position(ifStmt.(*ssa.If).Cond.Pos()), falseFunctionDominees)
			for _, falseFunctionDominee := range falseFunctionDominees {
				falseDominees = append(falseDominees, falseFunctionDominee.Blocks...)
			}
		}
		log.Printf("Branch at %s [FALSE] has the block dominees: ", context.Program.Fset.Position(ifStmt.(*ssa.If).Cond.Pos()))
		for _, falseDominee := range falseDominees {
			log.Printf("%d ", falseDominee.Index)
		}

		controlValue := condition.Source
		fieldSet := context.ValueFieldMap[controlValue]

		trueConditions := []ConcreteCondition{}
		for _, field := range fieldSet.Fields() {
			trueConditions = append(trueConditions, ConcreteCondition{
				Field: field.String(),
				Op:    condition.Op,
				Value: condition.Value,
			})
		}

		falseConditions := []ConcreteCondition{}
		for _, field := range fieldSet.Fields() {
			falseConditions = append(falseConditions, ConcreteCondition{
				Field: field.String(),
				Op:    Negation(condition.Op),
				Value: condition.Value,
			})
		}

		usesInTrueBranch := FindUsesInBlocks(context, trueDominees, frontierValuesByBlock)
		log.Printf("[TRUE] branch has the following uses:\n")
		for use := range usesInTrueBranch {
			log.Printf("%s\n", use)
		}
		usesInFalseBranch := FindUsesInBlocks(context, falseDominees, frontierValuesByBlock)
		log.Printf("[FALSE] branch has the following uses:\n")
		for use := range usesInFalseBranch {
			log.Printf("%s\n", use)
		}

		// first store all conditions to fieldToValueConditionMap
		for use := range usesInTrueBranch {
			fieldSet := context.ValueFieldMap[use]

			for _, field := range fieldSet.Fields() {
				if _, ok := fieldToValueConditionMap[field.String()]; !ok {
					log.Printf("Constructing value condition map for field %s\n", field.String()) //
					fieldToValueConditionMap[field.String()] = make(map[ssa.Value]*ConcreteConditionSet)
					for _, value := range *fieldToValueMap[field.String()] {
						log.Printf("Field %s map to %s:%s at %s", field.String(), value.Name(), value, context.Program.Fset.Position(value.Pos()))
						fieldToValueConditionMap[field.String()][value] = NewConcreteConditionSet()
					}
				}
				if _, ok := fieldToValueConditionMap[field.String()][use]; !ok {
					log.Printf("Value %s has path %s\n", use, context.ValueFieldMap[use])
					log.Fatalf("Should not happen, value not in fieldToValueMap %s:%s", use.Name(), use)
					fieldToValueConditionMap[field.String()][use] = NewConcreteConditionSet()
				}
				fieldToValueConditionMap[field.String()][use].Extend(trueConditions...)
			}
		}

		for use := range usesInFalseBranch {
			fieldSet := context.ValueFieldMap[use]

			for _, field := range fieldSet.Fields() {
				if _, ok := fieldToValueConditionMap[field.String()]; !ok {
					fieldToValueConditionMap[field.String()] = make(map[ssa.Value]*ConcreteConditionSet)
					for _, value := range *fieldToValueMap[field.String()] {
						log.Printf("Field %s map to %s:%s at %s", field.String(), value.Name(), value, context.Program.Fset.Position(value.Pos()))
						fieldToValueConditionMap[field.String()][value] = NewConcreteConditionSet()
					}
				}
				if _, ok := fieldToValueConditionMap[field.String()][use]; !ok {
					log.Fatalf("Should not happen, value not in fieldToValueMap %s:%s", use.Name(), use)
					fieldToValueConditionMap[field.String()][use] = NewConcreteConditionSet()
				}
				fieldToValueConditionMap[field.String()][use].Extend(falseConditions...)
			}
		}
	}

	// then take intersection of the conditions of the same field
	for field, valueToConditionMap := range fieldToValueConditionMap {
		log.Printf("Intersecting conditions for Field %s\n", field)
		var intersection *ConcreteConditionSet = nil
		for value, concreteConditionSet := range valueToConditionMap {
			// if value is only used in BinOp, then it is not a use
			referrers := value.Referrers()
			if len(*referrers) == 1 {
				if _, ok := (*referrers)[0].(*ssa.BinOp); ok {
					continue
				} else if s, ok := (*referrers)[0].(*ssa.Store); ok && value == s.Addr {
					continue
				}
			}

			if intersection == nil {
				intersection = NewConcreteConditionSet()
				for _, cc := range concreteConditionSet.ConcreteConditions {
					intersection.Add(cc)
				}
			} else {
				log.Printf("Intersecting with %s from value %s\n", concreteConditionSet, value)
				intersection = intersection.Intersect(concreteConditionSet)
				log.Printf("Intersection is %s\n", intersection)
			}
		}
		log.Printf("Intersection is %s\n", intersection)
		if intersection != nil && len(intersection.ConcreteConditions) > 0 {
			context.DomineeToConditions[field] = intersection
		}
	}
}

func FindUsesInBlocks(context *Context, blocks []*ssa.BasicBlock, frontierValuesByBlock map[*ssa.BasicBlock]*[]ssa.Value) map[ssa.Value]bool {
	uses := map[ssa.Value]bool{}
	for _, bb := range blocks {
		if _, ok := frontierValuesByBlock[bb]; ok {
			for _, value := range *frontierValuesByBlock[bb] {

				// if value is only used in BinOp, then it is not a use
				referrers := value.Referrers()
				if len(*referrers) == 1 {
					if _, ok := (*referrers)[0].(*ssa.BinOp); ok {
						continue
					}
				}

				uses[value] = true
			}
		}
	}
	return uses
}

func FindDirectBranches(context *Context, source ssa.Value) {
	equivalentValues := findEquivalentValues(context, source)

	for _, equivalentValue := range equivalentValues {
		for _, instruction := range *equivalentValue.Referrers() {
			switch typedInst := instruction.(type) {
			case ssa.Value:
				switch typedValue := typedInst.(type) {
				case *ssa.BinOp:
					if len(*typedValue.Referrers()) == 1 {
						switch typedBinOpReferrer := (*typedValue.Referrers())[0].(type) {
						case *ssa.If:
							if typedValue.X == equivalentValue {
								log.Printf("%s used directly in a BinOp at %s\n", source, context.Program.Fset.Position(typedBinOpReferrer.Cond.Pos()))
								if resolved := TryResolveValue(typedValue.Y); resolved != nil {
									context.IfToCondition[typedBinOpReferrer] = &BranchCondition{
										Source: source,
										Op:     typedValue.Op,
										Value:  resolved,
									}
								}
							}
						case *ssa.Return:
							taintedReturnSet := util.GetReturnIndices(typedValue, typedBinOpReferrer)
							node, ok := context.CallGraph.Nodes[typedBinOpReferrer.Parent()]
							if !ok {
								log.Printf("Failed to retrieve call graph node for %s %T\n", typedBinOpReferrer, typedBinOpReferrer)
							}
							if node == nil {
								log.Printf("No caller for %s %T at %s\n", typedBinOpReferrer, typedBinOpReferrer, typedBinOpReferrer.Parent().Pkg.Prog.Fset.Position(typedBinOpReferrer.Pos()))
							} else {
								for _, inEdge := range node.In {

									if callSiteReturnValue := inEdge.Site.Value(); callSiteReturnValue != nil {
										if typedInst.Parent().Signature.Results().Len() > 1 {
											// if return value is a tuple
											// propogate to the callsite recursively
											for _, tainted := range getExtractTaint(callSiteReturnValue, taintedReturnSet) {
												FindDirectBranchesHelper(context, tainted, typedValue, source)
											}
										} else {
											log.Printf("Propogate to the callsites %s from function %s\n", inEdge.Site.Parent().String(), typedInst.Parent())
											FindDirectBranchesHelper(context, callSiteReturnValue, typedValue, source)
										}
									} else {
										log.Fatalf("return to a non-call callsite\n")
									}
								}
							}
						}
					}
				case *ssa.Call:
					if typedValue.Call.IsInvoke() {
						// invoke
					} else {
						if typedValue.Call.Value.String() == "strings.EqualFold" {
							if len(*typedValue.Referrers()) == 1 {
								switch typedBinOpReferrer := (*typedValue.Referrers())[0].(type) {
								case *ssa.If:
									log.Printf("%s used in EqualFold at %s", source, context.Program.Fset.Position(typedBinOpReferrer.Cond.Pos()))

									var compareValue ssa.Value
									if typedValue.Call.Args[0] == equivalentValue {
										compareValue = typedValue.Call.Args[1]
									} else {
										compareValue = typedValue.Call.Args[0]
									}
									if resolved := TryResolveValue(compareValue); resolved != nil {
										context.IfToCondition[typedBinOpReferrer] = &BranchCondition{
											Source: source,
											Op:     token.EQL,
											Value:  resolved,
										}
									}
								}
							}
						}
					}
				}
			case *ssa.If:
				context.IfToCondition[typedInst] = &BranchCondition{
					Source: source,
					Op:     token.EQL,
					Value:  nil,
				}
			}
		}
	}
}

func FindDirectBranchesHelper(context *Context, conditionValue ssa.Value, binopValue *ssa.BinOp, source ssa.Value) {
	if len(*conditionValue.Referrers()) == 1 {
		switch typedBinOpReferrer := (*conditionValue.Referrers())[0].(type) {
		case *ssa.If:
			if binopValue.X == source {
				log.Printf("%s used directly in a BinOp at %s\n", source, context.Program.Fset.Position(typedBinOpReferrer.Cond.Pos()))
				if resolved := TryResolveValue(binopValue.Y); resolved != nil {
					context.IfToCondition[typedBinOpReferrer] = &BranchCondition{
						Source: source,
						Op:     binopValue.Op,
						Value:  resolved,
					}
				}
			}
		}
	}
}

func findEquivalentValues(context *Context, source ssa.Value) (equivalentValues []ssa.Value) {
	worklist := []ssa.Value{source}
	equivalentValues = append(equivalentValues, source)

	for len(worklist) > 0 {
		workitem := worklist[len(worklist)-1]
		worklist = worklist[:len(worklist)-1]

		referrers := workitem.Referrers()
		for _, instruction := range *referrers {
			switch typedInst := instruction.(type) {
			case ssa.Value:
				switch typedValue := typedInst.(type) {
				case *ssa.ChangeInterface:
					worklist = append(worklist, typedValue)
					equivalentValues = append(equivalentValues, typedValue)
				case *ssa.ChangeType:
					worklist = append(worklist, typedValue)
					equivalentValues = append(equivalentValues, typedValue)
				case *ssa.Convert:
					worklist = append(worklist, typedValue)
					equivalentValues = append(equivalentValues, typedValue)
				case *ssa.MakeInterface:
					worklist = append(worklist, typedValue)
					equivalentValues = append(equivalentValues, typedValue)
				}
			}
		}
	}
	return
}

func Negation(op token.Token) token.Token {
	switch op {
	case token.EQL:
		return token.NEQ
	case token.LSS:
		return token.GEQ
	case token.GTR:
		return token.LEQ
	case token.NEQ:
		return token.EQL
	case token.LEQ:
		return token.GTR
	case token.GEQ:
		return token.LSS
	}
	return token.ILLEGAL
}

// naive way to find function dominees
// it only find the direct function dominees, does not propogate
// it also does not consider functions called at different place but with the same conditions
func FindFunctionDominees(context *Context, bbs []*ssa.BasicBlock) (dominees []*ssa.Function) {
	if len(bbs) == 0 {
		return
	}

	bbSet := make(map[*ssa.BasicBlock]bool)
	for _, bb := range bbs {
		bbSet[bb] = true
	}

	f := bbs[0].Parent()
	log.Printf("Find function dominees for %s\n", f.Name())
	if context.CallGraph.Nodes[f] == nil {
		return
	}
	outedges := context.CallGraph.Nodes[f].Out
	for _, outedge := range outedges {
		callee := outedge.Callee
		callers := callee.In

		called_elsewhere := false
		for _, caller := range callers {
			if _, ok := bbSet[caller.Site.Block()]; !ok {
				called_elsewhere = true
			}
		}
		if !called_elsewhere {
			dominees = append(dominees, callee.Func)
		}
	}

	return
}
