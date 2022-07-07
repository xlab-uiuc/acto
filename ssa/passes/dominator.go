package analysis

import (
	"fmt"
	"log"

	"github.com/xlab-uiuc/acto/ssa/util"
	"golang.org/x/tools/go/ssa"
)

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

		backCallStack := NewCallStack()
		FindBranches(context, value, value, backCallStack)
	}

	for ifStmt := range context.BranchStmts {
		trueDominees := BlockDominees(context, ifStmt.Block(), true)
		log.Printf("Branch at %s [TRUE] has the block dominees: ", context.Program.Fset.Position(ifStmt.(*ssa.If).Cond.Pos()))
		for _, trueDominee := range trueDominees {
			log.Printf("%d ", trueDominee.Index)
		}
		falseDominees := BlockDominees(context, ifStmt.Block(), false)
		log.Printf("\nBranch at %s [FALSE] has the block dominees: ", context.Program.Fset.Position(ifStmt.(*ssa.If).Cond.Pos()))
		for _, falseDominee := range falseDominees {
			log.Printf("%d ", falseDominee.Index)
		}

		usesInTrueBranch := FindUsesInBlocks(context, trueDominees, frontierValuesByBlock)
		usesInFalseBranch := FindUsesInBlocks(context, falseDominees, frontierValuesByBlock)

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

func FindBranches(context *Context, source ssa.Value, localSource ssa.Value, backCallStack *CallStack) {
	// Maintain backCallStack
	functionCall := FunctionCall{
		FunctionName: source.Parent().String(),
		TaintSource:  fmt.Sprint(source),
	}
	if backCallStack.Contain(functionCall) {
		log.Printf("Recursive taint detected, directly return %s\n", functionCall)
		return
	} else {
		backCallStack.Push(functionCall)
		defer backCallStack.Pop()
	}

	worklist := []ssa.Value{source}
	phiSet := map[ssa.Value]bool{}

	for len(worklist) > 0 {
		workitem := worklist[len(worklist)-1]
		worklist = worklist[:len(worklist)-1]

		referrers := workitem.Referrers()
		for _, instruction := range *referrers {
			switch typedInst := instruction.(type) {
			case ssa.Value:
				switch typedValue := typedInst.(type) {
				case *ssa.Alloc:
					// skip
				case *ssa.BinOp:
					worklist = append(worklist, typedValue)
				case *ssa.Call:
					// XXX: let's try if this works
					// worklist = append(worklist, typedValue)
				case *ssa.ChangeInterface:
					worklist = append(worklist, typedValue)
				case *ssa.ChangeType:
					worklist = append(worklist, typedValue)
				case *ssa.Convert:
					worklist = append(worklist, typedValue)
				case *ssa.Extract:
					// skip
				case *ssa.Field:
					// skip
				case *ssa.FieldAddr:
					// skip
				case *ssa.Index:
					// skip
				case *ssa.IndexAddr:
					// skip
				case *ssa.Lookup:
					// skip
				case *ssa.MakeChan:
					// skip
				case *ssa.MakeClosure:
					// skip
				case *ssa.MakeInterface:
					worklist = append(worklist, typedValue)
				case *ssa.MakeMap:
					// skip
				case *ssa.MakeSlice:
					// skip
				case *ssa.Next:
					// skip
				case *ssa.Phi:
					if _, ok := phiSet[typedValue]; !ok {
						// avoid circular dependency
						worklist = append(worklist, typedValue)
						phiSet[typedValue] = true
					}
				case *ssa.Range:
					// skip
				case *ssa.Select:
					// skip
				case *ssa.Slice:
					// skip
				case *ssa.SliceToArrayPointer:
					// skip
				case *ssa.TypeAssert:
					worklist = append(worklist, typedValue)
				case *ssa.UnOp:
					worklist = append(worklist, typedValue)
				}
			case *ssa.Defer:
				// skip
			case *ssa.Go:
				// skip
			case *ssa.If:
				// TODO
				if valueList, ok := context.BranchStmts[typedInst]; ok {
					*valueList = append(*valueList, source)
				} else {
					context.BranchStmts[typedInst] = &[]ssa.Value{source}
				}
			case *ssa.Jump:
				// skip
			case *ssa.MapUpdate:
				// skip
			case *ssa.Panic:
				// skip
			case *ssa.Return:
				taintedReturnSet := util.GetReturnIndices(workitem, typedInst)
				node, ok := context.CallGraph.Nodes[workitem.Parent()]
				if !ok {
					log.Printf("Failed to retrieve call graph node for %s %T\n", workitem, workitem)
				}
				if node == nil {
					log.Printf("No caller for %s %T at %s\n", workitem, workitem, workitem.Parent().Pkg.Prog.Fset.Position(workitem.Pos()))
				} else {
					for _, inEdge := range node.In {

						if callSiteReturnValue := inEdge.Site.Value(); callSiteReturnValue != nil {
							if typedInst.Parent().Signature.Results().Len() > 1 {
								// if return value is a tuple
								// propogate to the callsite recursively
								for _, tainted := range getExtractTaint(callSiteReturnValue, taintedReturnSet) {
									FindBranches(context, source, tainted, backCallStack)
								}
							} else {
								log.Printf("Propogate to the callsites %s from function %s\n", inEdge.Site.Parent().String(), typedInst.Parent())
								FindBranches(context, source, callSiteReturnValue, backCallStack)
							}
						} else {
							log.Fatalf("return to a non-call callsite\n")
						}
					}
				}
			case *ssa.RunDefers:
				// skip
			case *ssa.Send:
				// skip
			case *ssa.Store:
				// skip
			}
		}
	}
}
