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
				*slice = append(*slice, value)
			} else {
				fieldToValueMap[field.String()] = &[]ssa.Value{value}
			}
		}

		FindDirectBranches(context, value)
	}

	for ifStmt, condition := range context.IfToCondition {
		trueDominees := BlockDominees(context, ifStmt.Block(), true)
		log.Printf("Branch at %s [TRUE] has the block dominees: ", context.Program.Fset.Position(ifStmt.(*ssa.If).Cond.Pos()))
		for _, trueDominee := range trueDominees {
			log.Printf("%d ", trueDominee.Index)
		}
		falseDominees := BlockDominees(context, ifStmt.Block(), false)
		log.Printf("Branch at %s [FALSE] has the block dominees: ", context.Program.Fset.Position(ifStmt.(*ssa.If).Cond.Pos()))
		for _, falseDominee := range falseDominees {
			log.Printf("%d ", falseDominee.Index)
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

		fieldDomineesInTrueBranch := []ssa.Value{}
		for use := range usesInTrueBranch {
			fieldSet := context.ValueFieldMap[use]

			for _, field := range fieldSet.Fields() {
				values := fieldToValueMap[field.String()]

				otherUse := false
				for _, value := range *values {
					if use == value {
						continue
					}
					if _, ok := usesInTrueBranch[value]; ok {
						continue
					}
					if condition.Source == value {
						continue
					}
					log.Printf("Field %s used in other places\n", field.String())
					log.Printf("Used in %s\n", context.Program.Fset.Position(value.Pos()))
					otherUse = true
					break
				}
				if !otherUse {
					fieldDomineesInTrueBranch = append(fieldDomineesInTrueBranch, use)
				}
			}
		}

		fieldDomineesInFalseBranch := []ssa.Value{}
		for use := range usesInFalseBranch {
			fieldSet := context.ValueFieldMap[use]

			for _, field := range fieldSet.Fields() {
				values := fieldToValueMap[field.String()]

				otherUse := false
				for _, value := range *values {
					if use == value {
						continue
					}
					if _, ok := usesInFalseBranch[value]; ok {
						continue
					}
					otherUse = true
					break
				}
				if !otherUse {
					fieldDomineesInFalseBranch = append(fieldDomineesInFalseBranch, use)
				}
			}
		}

		if len(fieldDomineesInTrueBranch) > 0 || len(fieldDomineesInFalseBranch) > 0 {
			context.BranchValueDominees[ifStmt] = &UsesInBranch{
				TrueBranch:  &fieldDomineesInTrueBranch,
				FalseBranch: &fieldDomineesInFalseBranch,
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

			for _, field := range fieldSet.Fields() {
				trueConditions = append(trueConditions, ConcreteCondition{
					Field: field.String(),
					Op:    condition.Op,
					Value: condition.Value,
				})
			}

			for _, dominee := range fieldDomineesInTrueBranch {
				domineeFs := context.ValueFieldMap[dominee]
				for _, field := range domineeFs.Fields() {
					if _, ok := context.DomineeToConditions[field.String()]; ok {
						context.DomineeToConditions[field.String()].Extend(trueConditions...)
					} else {
						context.DomineeToConditions[field.String()] = &ConcreteConditionSet{
							ConcreteConditions: make(map[string]ConcreteCondition),
						}
						context.DomineeToConditions[field.String()].Extend(trueConditions...)
					}
				}
			}

			for _, dominee := range fieldDomineesInFalseBranch {
				domineeFs := context.ValueFieldMap[dominee]
				for _, field := range domineeFs.Fields() {
					if _, ok := context.DomineeToConditions[field.String()]; ok {
						context.DomineeToConditions[field.String()].Extend(falseConditions...)
					} else {
						context.DomineeToConditions[field.String()] = &ConcreteConditionSet{
							ConcreteConditions: make(map[string]ConcreteCondition),
						}
						context.DomineeToConditions[field.String()].Extend(falseConditions...)
					}
				}
			}
		}
	}
}

func FindUsesInBlocks(context *Context, blocks []*ssa.BasicBlock, frontierValuesByBlock map[*ssa.BasicBlock]*[]ssa.Value) map[ssa.Value]bool {
	uses := map[ssa.Value]bool{}
	for _, bb := range blocks {
		if _, ok := frontierValuesByBlock[bb]; ok {
			for _, value := range *frontierValuesByBlock[bb] {
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
