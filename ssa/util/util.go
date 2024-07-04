package util

import (
	"fmt"
	"go/types"
	"log"
	"strconv"
	"strings"

	"golang.org/x/tools/go/ssa"
	"golang.org/x/tools/go/ssa/ssautil"
)

func AddFieldToValueFieldSetMap(m map[ssa.Value]*FieldSet, v ssa.Value, f *Field) bool {
	if fieldSet, ok := m[v]; ok {
		// this typedValue already exists in the map, try add the field to the set
		if ok := fieldSet.Add(f); ok {
			// this field not yet exists in the set yet, successfully added
			return true
		} else {
			// value already exists in map, and path already exists in the path set
			return false
		}
	} else {
		// this typedValue not yet exists in the map, create a FieldSet for it
		m[v] = NewFieldSet()
		m[v].Add(f)
		return true
	}
}

func MergeMaps(m1 map[ssa.Value]*FieldSet, m2 map[ssa.Value]*FieldSet) {
	for k, v := range m2 {
		m1[k] = v
	}
}

func GetFieldNameFromJsonTag(tag string) string {
	jsonTag, _ := tagLookUp(tag, "json")
	v := strings.Split(jsonTag, ",")[0]
	return v
}

// copied from reflect
func tagLookUp(tag string, key string) (string, bool) {
	for tag != "" {
		// Skip leading space.
		i := 0
		for i < len(tag) && tag[i] == ' ' {
			i++
		}
		tag = tag[i:]
		if tag == "" {
			break
		}

		// Scan to colon. A space, a quote or a control character is a syntax error.
		// Strictly speaking, control chars include the range [0x7f, 0x9f], not just
		// [0x00, 0x1f], but in practice, we ignore the multi-byte control characters
		// as it is simpler to inspect the tag's bytes than the tag's runes.
		i = 0
		for i < len(tag) && tag[i] > ' ' && tag[i] != ':' && tag[i] != '"' && tag[i] != 0x7f {
			i++
		}
		if i == 0 || i+1 >= len(tag) || tag[i] != ':' || tag[i+1] != '"' {
			break
		}
		name := string(tag[:i])
		tag = tag[i+1:]

		// Scan quoted string to find value.
		i = 1
		for i < len(tag) && tag[i] != '"' {
			if tag[i] == '\\' {
				i++
			}
			i++
		}
		if i >= len(tag) {
			break
		}
		qvalue := string(tag[:i+1])
		tag = tag[i+1:]

		if key == name {
			value, err := strconv.Unquote(qvalue)
			if err != nil {
				break
			}
			return value, true
		}
	}
	return "", false
}

// get all the types from program
func GetAllTypes(prog *ssa.Program) []*ssa.Type {
	ret := []*ssa.Type{}
	for _, pkg := range prog.AllPackages() {
		for _, m := range pkg.Members {
			switch typedMember := m.(type) {
			case *ssa.Type:
				ret = append(ret, typedMember)
			}
		}
	}
	return ret
}

func FindSeedType(prog *ssa.Program, seedStr *string, pkgPath *string) *ssa.Type {
	for _, pkg := range prog.AllPackages() {
		if pkg.Pkg.Path() == *pkgPath {
			seed := pkg.Members[*seedStr]
			if typ, ok := seed.(*ssa.Type); ok {
				return typ
			}
		}
	}
	return nil
}

func FindSeedValues(prog *ssa.Program, seedType *string, pkgPath *string) []ssa.Value {
	seedVariables := []ssa.Value{}

	seed := FindSeedType(prog, seedType, pkgPath)
	if seed != nil {
		log.Println(seed.String())
		if seedStruct, ok := seed.Type().Underlying().(*types.Struct); ok {
			for i := 0; i < seedStruct.NumFields(); i++ {
				field := seedStruct.Field(i)
				log.Printf("%s\n", fmt.Sprintf("%s - %s\n", field.Name(), GetFieldNameFromJsonTag(seedStruct.Tag(i))))
			}
		} else {
			log.Printf("%s\n", fmt.Sprintf("%T", seed.Type().Underlying()))
		}
	}

	for f := range ssautil.AllFunctions(prog) {
		if strings.Contains(f.Name(), "DeepCopy") {
			continue
		}
		seedVariables = append(seedVariables, getSeedVariablesFromFunction(f, seed.Type())...)
	}

	for _, seedVar := range seedVariables {
		log.Printf("%s\n", fmt.Sprintf("Value %s is seed", seedVar.String()))
	}
	log.Printf("%s\n", fmt.Sprintf("%d\n", len(seedVariables)))

	return seedVariables
}

func getSeedVariablesFromFunction(f *ssa.Function, seedType types.Type) []ssa.Value {
	ret := []ssa.Value{}
	for _, blk := range f.Blocks {
		for _, inst := range blk.Instrs {
			switch v := inst.(type) {
			case ssa.Value:
				vType := v.Type()
				if vType == seedType {
					ret = append(ret, v)
				}
				if vPointer, ok := vType.(*types.Pointer); ok && vPointer.Elem() == seedType {
					ret = append(ret, v)
				}
			}
		}
	}

	for _, param := range f.Params {
		vType := param.Type()
		if vType == seedType {
			ret = append(ret, param)
		}
		if vPointer, ok := vType.(*types.Pointer); ok && vPointer.Elem() == seedType {
			ret = append(ret, param)
		}
	}
	return ret
}

// returns the list of parameter indices of the taint source
func GetCallsiteArgIndices(value ssa.Value, call *ssa.CallCommon) []int {
	paramSet := NewSet[int]()
	if value == call.Value {
		// add receiver's index in the case of invoke mode
		paramSet.Add(-1)
	}
	for index, param := range call.Args {
		if param == value {
			paramSet.Add(index)
		}
	}
	return paramSet.Items()
}

func GetCalleeParamIndex(value ssa.Value, callee *ssa.Function) int {
	for index, param := range callee.Params {
		if param == value {
			return index
		}
	}
	return -1
}

// returns the list of return indices of the taint source
func GetReturnIndices(taintSource ssa.Value, returnInst *ssa.Return) []int {
	retIndexSet := NewSet[int]()
	for index, ret := range returnInst.Results {
		if ret == taintSource {
			retIndexSet.Add(index)
		}
	}
	return retIndexSet.Items()
}

// This function taints the invoke callsite's arguments using the parameter index from
// a concrete callee
// This needs to be carefully handled because the concrete callee's parameter list would contain
// the receiver, but the invoke callsite's argument list does not contain the receiver
func TaintInvokeCallSiteArgFromCallee(callSite ssa.CallInstruction, calleeParamIndex int, taintedSet map[ssa.Value]bool) bool {
	taintedParam := callSite.Common().Args[calleeParamIndex+1]
	if _, ok := taintedSet[taintedParam]; ok {
		taintedSet[taintedParam] = true
		return true
	}
	return false
}

func IsK8sUpdateCall(call *ssa.CallCommon) bool {
	if call.Method.Pkg() == nil {
		return false
	}
	if strings.Contains(call.Method.Pkg().Name(), "sigs.k8s.io/controller-runtime/pkg") {
		log.Println(call.Method.Id())
		return true
	}
	return false
}

// returns if the value represent any pass by reference type
func IsPointerType(value ssa.Value) bool {
	switch value.Type().Underlying().(type) {
	case *types.Map:
		return true
	case *types.Slice:
		return true
	case *types.Pointer:
		return true
	case *types.Interface:
		return true
	default:
		// XXX: channel, func could also be pass by reference
		return false
	}
}
