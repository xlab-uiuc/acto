package analysis

import (
	"encoding/json"
	"go/constant"
	"go/token"
	"go/types"
	"log"
	"strings"

	. "github.com/xlab-uiuc/acto/ssa/util"
	"golang.org/x/tools/go/ssa"
)

// Find the control flow dominees of a block
// branch: true if the dominees are the blocks that are dominated by the true branch of the if statement
func BlockDominees(context *Context, bb *ssa.BasicBlock, branch bool) (dominees []*ssa.BasicBlock) {
	fn := bb.Parent()
	pd, ok := context.PostDominators[fn]
	if !ok {
		// lazy binding
		pd = NewPostDominator(fn)
		context.PostDominators[fn] = pd
	}
	trueBlock := bb.Succs[0]
	falseBlock := bb.Succs[1]
	worklist := []*ssa.BasicBlock{}
	if branch {
		worklist = append(worklist, trueBlock)
	} else {
		worklist = append(worklist, falseBlock)
	}

	if pd.Dominate(worklist[0], bb) {
		return
	} else {
		dominees = append(dominees, worklist[0])
	}

	for len(worklist) > 0 {
		workItem := worklist[len(worklist)-1]
		worklist = worklist[:len(worklist)-1]

		iDominees := workItem.Dominees()
		for _, dominee := range iDominees {
			if !pd.Dominate(dominee, bb) {
				dominees = append(dominees, dominee)
				worklist = append(worklist, dominee)
			}
		}
	}
	return
}

func FindDefaultAssignment(context *Context, ifBlock *ssa.BasicBlock, branch bool, valueFieldMap map[ssa.Value]*FieldSet) {
	controlFlowDominees := BlockDominees(context, ifBlock, branch)
	log.Printf("Found %d dominees\n", len(controlFlowDominees))
	for _, bb := range controlFlowDominees {
		for _, inst := range bb.Instrs {
			if storeInst, ok := inst.(*ssa.Store); ok {
				if _, ok := valueFieldMap[storeInst.Addr]; ok {
					log.Printf("Store %s into addr %s\n", storeInst.Val, storeInst.Addr)
					// a default value is stored into a field in CR
					if defaultValue := TryResolveValue(storeInst.Val); defaultValue != nil {
						context.DefaultValueMap[storeInst.Addr] = defaultValue
					}
				}
			}
		}
	}
}

func TryResolveValue(value ssa.Value) *ssa.Const {
	switch typedValue := value.(type) {
	case *ssa.UnOp:
		if typedValue.Op == token.MUL {
			return TryGetValueForAddr(typedValue.X)
		}
	case *ssa.Const:
		if typedValue.Value != nil {
			log.Printf("Found const %s", typedValue.Value.String())
		} else {
			log.Printf("Found nil const")
		}
		return typedValue
	case *ssa.Alloc:
		if strings.Contains(typedValue.Type().Underlying().(*types.Pointer).Elem().String(), "IntOrString") {
			log.Printf("Found IntOrString alloc %s", typedValue.Type().Underlying().(*types.Pointer).Elem().String())
			return TryGetValueForAlloc(typedValue)
		}
		if _, ok := typedValue.Type().Underlying().(*types.Pointer).Elem().Underlying().(*types.Struct); ok {
			log.Printf("Found struct alloc %s", typedValue.Type().Underlying().(*types.Pointer).Elem().String())
			return TryGetValueForStructAlloc(typedValue)
		}
	case *ssa.Call:
		log.Printf("Value from call %s", typedValue.Call.Value.Name())
		if strings.Contains(typedValue.Call.Value.Name(), "FromInt") {
			return TryResolveValue(typedValue.Call.Args[0])
		}
	}
	return nil
}

func TryGetValueForStructAlloc(alloc *ssa.Alloc) *ssa.Const {
	fields := map[string]string{}
	for _, referrer := range *alloc.Referrers() {
		if storeInst, ok := referrer.(*ssa.FieldAddr); ok {
			if constValue := TryGetValueForAddr(storeInst); constValue != nil {
				tag := alloc.Type().Underlying().(*types.Pointer).Elem().Underlying().(*types.Struct).Tag(storeInst.Field)
				fieldName := GetFieldNameFromJsonTag(tag)
				log.Printf("Found field %s with value %s", fieldName, constValue.Value.String())
				fields[fieldName] = constValue.Value.String()
			}
		}
	}
	if len(fields) == 0 {
		return nil
	} else {
		fields_string, err := json.Marshal(fields)
		if err != nil {
			log.Fatal(err)
		}
		return &ssa.Const{
			Value: constant.MakeString(string(fields_string)),
		}
	}
}

func TryGetValueForAlloc(alloc *ssa.Alloc) *ssa.Const {
	for _, referrer := range *alloc.Referrers() {
		if storeInst, ok := referrer.(*ssa.Store); ok {
			if constValue := TryResolveValue(storeInst.Val); constValue != nil {
				return constValue
			}
		}
	}
	return nil
}

// Returns store instructions that store some value into the global variable in the package init function
func GlobalAssignments(global *ssa.Global) (ret []ssa.Instruction) {
	initFn := global.Pkg.Members["init"].(*ssa.Function)
	for _, bb := range initFn.Blocks {
		for _, inst := range bb.Instrs {
			for _, operand := range inst.Operands([]*ssa.Value{}) {
				if *operand == global {
					if storeInst, ok := inst.(*ssa.Store); ok && global == storeInst.Addr {
						ret = append(ret, storeInst)
					}
				}
			}
		}
	}
	return
}

func TryGetValueForAddr(addr ssa.Value) *ssa.Const {
	var referrers []ssa.Instruction
	switch typedAddr := addr.(type) {
	case *ssa.Global:
		referrers = GlobalAssignments(typedAddr)
	default:
		referrers = *addr.Referrers()
	}
	for _, referrer := range referrers {
		if storeInst, ok := referrer.(*ssa.Store); ok && storeInst.Addr == addr {
			return TryResolveValue(storeInst.Val)
		}
	}
	return nil
}

func GetDefaultValue(context *Context, frontierValues map[ssa.Value]bool, valueFieldMap map[ssa.Value]*FieldSet) {
	for frontierValue := range frontierValues {
		log.Printf("Finding default value for %s at %s\n", frontierValue, frontierValue.Parent().Name())
		referrers := frontierValue.Referrers()
		for _, referrer := range *referrers {
			if binopValue, ok := referrer.(*ssa.BinOp); ok {
				if len(*binopValue.Referrers()) == 1 {
					log.Printf("Referred only once\n")
					if ifInst, ok := (*binopValue.Referrers())[0].(*ssa.If); ok {
						log.Printf("Referred only in if\n")
						if binopValue.Op == token.EQL {
							log.Printf("Op is EQL\n")
							var branch bool
							var compareValue ssa.Value
							if frontierValue == binopValue.X {
								branch = true
								compareValue = binopValue.Y
							} else {
								branch = false
								compareValue = binopValue.X
							}

							if constValue, ok := compareValue.(*ssa.Const); ok {
								log.Printf("Compare value is const\n")
								if constValue.Value == nil {
									log.Printf("Compare value is nil\n")
									FindDefaultAssignment(context, ifInst.Block(), branch, valueFieldMap)
								} else if constValue.Value.ExactString() == "\"\"" {
									log.Printf("Compare value is empty string\n")
									FindDefaultAssignment(context, ifInst.Block(), branch, valueFieldMap)
								} else if constValue.Value.ExactString() == "0" {
									log.Printf("Compare value is zero\n")
									FindDefaultAssignment(context, ifInst.Block(), branch, valueFieldMap)
								} else {
									log.Printf("Const is %s\n", constValue.Value.ExactString())
								}
							}
						} else if binopValue.Op == token.LEQ || binopValue.Op == token.LSS {
							log.Printf("Op is EQL\n")
							var branch bool
							var compareValue ssa.Value
							if frontierValue == binopValue.X {
								branch = true
								compareValue = binopValue.Y
							} else {
								branch = false
								compareValue = binopValue.X
							}

							if constValue, ok := compareValue.(*ssa.Const); ok {
								log.Printf("Compare value is const\n")
								if constValue.Value.ExactString() == "0" {
									log.Printf("Compare value is zero\n")
									FindDefaultAssignment(context, ifInst.Block(), branch, valueFieldMap)
								} else {
									log.Printf("Const is %s\n", constValue.Value.ExactString())
								}
							}
						}
					}
				}
			}
		}
	}
}
