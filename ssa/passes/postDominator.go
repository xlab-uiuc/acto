package analysis

import (
	"bytes"
	"fmt"

	"golang.org/x/tools/go/ssa"
)

type PostDominator struct {
	FN      *ssa.Function
	pdomSet map[*ssa.BasicBlock]map[*ssa.BasicBlock]bool
}

func NewPostDominator(fn *ssa.Function) *PostDominator {
	pd := new(PostDominator)
	pd.FN = fn
	pd.pdomSet = make(map[*ssa.BasicBlock]map[*ssa.BasicBlock]bool)

	pd.initBeforeAfterMap()
	pd.conductAnalysis()

	return pd
}

func (pd *PostDominator) initBeforeAfterMap() {
	for _, bb := range pd.FN.Blocks {
		pd.pdomSet[bb] = make(map[*ssa.BasicBlock]bool)
	}
}

func intersectMap(m1 map[*ssa.BasicBlock]bool, m2 map[*ssa.BasicBlock]bool) map[*ssa.BasicBlock]bool {
	mapResult := map[*ssa.BasicBlock]bool{}

	for bb, _ := range m1 {
		if _, ok := m2[bb]; ok {
			mapResult[bb] = true
		}
	}

	return mapResult
}

func compareMap(m1 map[*ssa.BasicBlock]bool, m2 map[*ssa.BasicBlock]bool) bool {
	if len(m1) != len(m2) {
		return false
	}

	for bb, _ := range m1 {
		if _, ok := m2[bb]; !ok {
			return false
		}
	}

	return true
}

func (pd *PostDominator) conductAnalysis() {
	worklist := []*ssa.BasicBlock{}
	for _, bb := range pd.FN.Blocks {
		if len(bb.Succs) > 0 {
			worklist = append(worklist, bb)
			for _, bb_ := range pd.FN.Blocks {
				pd.pdomSet[bb][bb_] = true
			}
		} else {
			pd.pdomSet[bb][bb] = true
		}
	}

	for len(worklist) > 0 {
		bb := worklist[len(worklist)-1]
		worklist = worklist[:len(worklist)-1]

		newPdomSet := make(map[*ssa.BasicBlock]bool)

		// compute intersection of Succs' post-dominators
		if len(bb.Succs) > 0 {
			for b, _ := range pd.pdomSet[bb.Succs[0]] {
				newPdomSet[b] = true
			}
			for _, succ := range bb.Succs[1:] {
				newPdomSet = intersectMap(newPdomSet, pd.pdomSet[succ])
			}
		}

		newPdomSet[bb] = true // mapBefore contains the bb itself

		if !compareMap(pd.pdomSet[bb], newPdomSet) {
			pd.pdomSet[bb] = newPdomSet

			worklist = append(worklist, bb.Preds...)
		}
	}
}

func (pd *PostDominator) Print() {
	for _, bb := range pd.FN.Blocks {
		fmt.Printf("%d: ", bb.Index)

		for b, _ := range pd.pdomSet[bb] {
			fmt.Printf("%d ", b.Index)
		}
		fmt.Println()
	}
}

func (pd *PostDominator) String() string {
	var buf bytes.Buffer
	for _, bb := range pd.FN.Blocks {
		buf.WriteString(fmt.Sprintf("%d: ", bb.Index))

		for b, _ := range pd.pdomSet[bb] {
			buf.WriteString(fmt.Sprintf("%d ", b.Index))
		}
		buf.WriteString("\n")
	}
	return buf.String()
}

func (pd *PostDominator) Dominate(b1 *ssa.BasicBlock, b2 *ssa.BasicBlock) bool {
	if _, ok := pd.pdomSet[b2][b1]; ok {
		return true
	}

	return false
}
