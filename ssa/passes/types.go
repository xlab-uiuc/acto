package analysis

import (
	"bytes"
	"encoding/json"
	"fmt"
	"go/token"

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
	Program                *ssa.Program
	MainPackages           []*ssa.Package
	RootModule             *packages.Module
	CallGraph              *callgraph.Graph
	PostDominators         map[*ssa.Function]*PostDominator
	FieldDataDependencyMap map[string]*util.FieldSet // map's key's value depends on value

	ValueFieldMap       map[ssa.Value]*util.FieldSet
	FieldToValueMap     map[string]*[]ssa.Value
	StoreInsts          []ssa.Instruction
	AppendCalls         []ssa.Instruction
	DefaultValueMap     map[ssa.Value]*ssa.Const
	IfToCondition       map[ssa.Instruction]*BranchCondition
	BranchValueDominees map[ssa.Instruction]*UsesInBranch
	DomineeToConditions map[string]*ConcreteConditionSet
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
	for inst := range c.IfToCondition {
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

	for dominee, ccs := range c.DomineeToConditions {
		b.WriteString(fmt.Sprintf("%s needs the following conditions:\n", dominee))
		b.WriteString("\n")
		for _, cg := range ccs.ConcreteConditionGroups {
			b.WriteString(cg.Encode())
		}
		b.WriteString("\n")
	}
	b.WriteString("\n")
	return b.String()
}

type BranchCondition struct {
	Source ssa.Value
	Op     token.Token
	Value  *ssa.Const
}

type ConditionGroupType string

const (
	AndConditionGroup ConditionGroupType = "AND"
	OrConditionGroup  ConditionGroupType = "OR"
)

type ConditionGroup struct {
	Typ                ConditionGroupType
	ConcreteConditions []*ConcreteCondition
}

func (cg *ConditionGroup) String() string {
	var b bytes.Buffer
	b.WriteString(string(cg.Typ))
	for _, cc := range cg.ConcreteConditions {
		b.WriteString(fmt.Sprintf("\n%s\n", cc.String()))
	}
	return b.String()
}

func (cg *ConditionGroup) Encode() string {
	var b bytes.Buffer
	b.WriteString(string(cg.Typ))
	for _, cc := range cg.ConcreteConditions {
		b.WriteString(cc.Encode())
	}
	return b.String()
}

func (cg *ConditionGroup) ToPlainCondition() *PlainConditionGroup {
	var plainConditionGroup PlainConditionGroup
	plainConditionGroup.Typ = cg.Typ
	for _, cc := range cg.ConcreteConditions {
		plainConditionGroup.ConcreteConditions = append(plainConditionGroup.ConcreteConditions, cc.ToPlainCondition())
	}
	return &plainConditionGroup
}

type PlainConditionGroup struct {
	Typ                ConditionGroupType `json:"type"`
	ConcreteConditions []*PlainCondition  `json:"conditions"`
}

type ConcreteCondition struct {
	Field string
	Op    token.Token
	Value *ssa.Const
}

func (c *ConcreteCondition) String() string {
	var b bytes.Buffer
	b.WriteString(c.Field)
	b.WriteString(fmt.Sprintf("\n%s\n", c.Op.String()))
	if c.Value == nil {
		b.WriteString("true")
	} else {
		b.WriteString(c.Value.String())
	}
	b.WriteString("\n")
	return b.String()
}

func (c *ConcreteCondition) Encode() string {
	var b bytes.Buffer
	b.WriteString(c.Field)
	b.WriteString(fmt.Sprintf(" %s ", c.Op.String()))
	if c.Value == nil {
		b.WriteString("true")
	} else {
		b.WriteString(c.Value.String())
	}
	return b.String()
}

func (c *ConcreteCondition) ToPlainCondition() *PlainCondition {
	var field []string
	json.Unmarshal([]byte(c.Field), &field)

	var value string
	if c.Value == nil {
		value = "true"
	} else if c.Value.Value == nil {
		value = "null"
	} else {
		value = c.Value.Value.String()
	}
	return &PlainCondition{
		Field: field,
		Op:    c.Op.String(),
		Value: value,
	}
}

// same as ConcreteCondition, but json friendly
type PlainCondition struct {
	Field []string `json:"field"`
	Op    string   `json:"op"`
	Value string   `json:"value"`
}

type ConcreteConditionSet struct {
	ConcreteConditionGroups map[string]*ConditionGroup
}

func NewConcreteConditionSet() *ConcreteConditionSet {
	return &ConcreteConditionSet{
		ConcreteConditionGroups: make(map[string]*ConditionGroup),
	}
}

func (ccs *ConcreteConditionSet) Add(cg *ConditionGroup) {
	ccs.ConcreteConditionGroups[cg.Encode()] = cg
}

func (ccs *ConcreteConditionSet) Contain(cc string) bool {
	_, ok := ccs.ConcreteConditionGroups[cc]
	return ok
}

func (ccs *ConcreteConditionSet) Extend(cgList ...*ConditionGroup) {
	for _, cc := range cgList {
		ccs.ConcreteConditionGroups[cc.Encode()] = cc
	}
}

func (ccs *ConcreteConditionSet) Intersect(ccs_ *ConcreteConditionSet) *ConcreteConditionSet {
	newSet := NewConcreteConditionSet()
	for cc_str, cc := range ccs.ConcreteConditionGroups {
		if ccs_.Contain(cc_str) {
			newSet.Add(cc)
		}
	}
	return newSet
}

func (ccs *ConcreteConditionSet) ToPlainConditionSet(path []string) *PlainConcreteConditionSet {
	var plainConcreteConditionSet PlainConcreteConditionSet
	plainConcreteConditionSet.Path = path
	plainConcreteConditionSet.Typ = AndConditionGroup
	for _, cg := range ccs.ConcreteConditionGroups {
		plainConcreteConditionSet.PlainConditionGroups = append(plainConcreteConditionSet.PlainConditionGroups, cg.ToPlainCondition())
	}
	return &plainConcreteConditionSet
}

type PlainConcreteConditionSet struct {
	Path                 []string               `json:"path"`
	Typ                  ConditionGroupType     `json:"type"`
	PlainConditionGroups []*PlainConditionGroup `json:"conditionGroups"`
}

type TaintedStructValue struct {
	Value ssa.Value
	Path  []int
}
