package analysis

import (
	"bytes"
	"fmt"

	"github.com/xlab-uiuc/acto/ssa/util"
	"golang.org/x/tools/go/callgraph"
	"golang.org/x/tools/go/packages"
	"golang.org/x/tools/go/ssa"
)

type FunctionCall struct {
	FunctionName string
	TaintSource  string
}

type FunctionTaintResult struct {
	End         bool
	TaintedArgs []int
	TaintedRets []int
}

func (r FunctionTaintResult) String() string {
	return fmt.Sprintf("{End : %t, TaintedArgs: %v, TaintedRets: %v}", r.End, r.TaintedArgs, r.TaintedRets)
}

type CallStack []FunctionCall

func (cs *CallStack) Push(call FunctionCall) {
	*cs = append(*cs, call)
}

func (cs *CallStack) Pop() (FunctionCall, bool) {
	if cs.IsEmpty() {
		return FunctionCall{}, false
	} else {
		index := len(*cs) - 1   // Get the index of the top most element.
		element := (*cs)[index] // Index into the slice and obtain the element.
		*cs = (*cs)[:index]     // Remove it from the stack by slicing it off.
		return element, true
	}
}

func (cs *CallStack) IsEmpty() bool {
	return len(*cs) == 0
}

func (cs *CallStack) Contain(call FunctionCall) bool {
	for _, functionCall := range *cs {
		if functionCall == call {
			return true
		}
	}
	return false
}

func NewCallStack() *CallStack {
	return &CallStack{}
}

type Context struct {
	Program        *ssa.Program
	MainPackages   []*ssa.Package
	RootModule     *packages.Module
	CallGraph      *callgraph.Graph
	PostDominators map[*ssa.Function]*PostDominator

	ValueFieldMap        map[ssa.Value]*util.FieldSet
	DefaultValueMap      map[ssa.Value]*ssa.Const
	BranchStmts          map[ssa.Instruction]*[]ssa.Value
	BranchValueDominees  map[ssa.Instruction]*UsesInBranch
	FieldToFieldDominees map[string]*util.FieldSet
}

type UsesInBranch struct {
	TrueBranch  *[]ssa.Value
	FalseBranch *[]ssa.Value
}

func (c *Context) String() string {
	var b bytes.Buffer
	b.WriteString(fmt.Sprintf("Root module: %s\n", c.RootModule.Path))
	b.WriteString("ValueFieldMap:\n")

	b.WriteString("Post Dominators:\n")

	for fn, pd := range c.PostDominators {
		b.WriteString(fmt.Sprintf("%s\n", fn.String()))
		b.WriteString(pd.String())
	}

	b.WriteString("Default value map:\n")
	for v, constant := range c.DefaultValueMap {
		b.WriteString(fmt.Sprintf("%v: %s\n", c.ValueFieldMap[v].String(), constant.Value.ExactString()))
	}

	b.WriteString("Dominators:\n")
	for inst := range c.BranchStmts {
		b.WriteString(fmt.Sprintf("%s at %s\n", inst, c.Program.Fset.Position(inst.(*ssa.If).Cond.Pos())))
	}

	for ifInst, usesInBranch := range c.BranchValueDominees {
		for _, v := range *usesInBranch.TrueBranch {
			b.WriteString(fmt.Sprintf("%s is dominated by %s's true branch at %s\n", c.ValueFieldMap[v], v, c.Program.Fset.Position(ifInst.(*ssa.If).Cond.Pos())))
		}

		for _, v := range *usesInBranch.FalseBranch {
			b.WriteString(fmt.Sprintf("%s is dominated by %s's false branch at %s\n", c.ValueFieldMap[v], v, c.Program.Fset.Position(ifInst.(*ssa.If).Cond.Pos())))
		}
	}

	for dominator, dominees := range c.FieldToFieldDominees {
		b.WriteString(fmt.Sprintf("%s has the following dominees:\n", dominator))
		b.WriteString(dominees.String())
		b.WriteString("\n\n")
	}
	return b.String()
}
