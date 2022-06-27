package analysis

import (
	"bytes"
	"fmt"

	"github.com/xlab-uiuc/acto/ssa/util"
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
	PostDominators map[*ssa.Function]*PostDominator

	ValueFieldMap   map[ssa.Value]*util.FieldSet
	DefaultValueMap map[ssa.Value]*ssa.Const
}

func (c *Context) String() string {
	var b bytes.Buffer
	b.WriteString(fmt.Sprintf("Root module: %s\n", c.RootModule.Path))
	b.WriteString("Post Dominators:\n")

	for fn, pd := range c.PostDominators {
		b.WriteString(fmt.Sprintf("%s\n", fn.String()))
		b.WriteString(pd.String())
	}

	b.WriteString("Default value map:\n")
	for v, constant := range c.DefaultValueMap {
		b.WriteString(fmt.Sprintf("%v: %s\n", c.ValueFieldMap[v].String(), constant.Value.ExactString()))
	}
	return b.String()
}
