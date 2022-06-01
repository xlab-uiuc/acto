package util

import (
	"fmt"
	"go/types"
	"log"
	"os"
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

func FindSeedType(prog *ssa.Program, seedStr string) *ssa.Type {
	for _, pkg := range prog.AllPackages() {
		seed := pkg.Members[seedStr]
		if typ, ok := seed.(*ssa.Type); ok {
			return typ
		}
	}
	return nil
}

func FindSeedValues(prog *ssa.Program, seedType string) []ssa.Value {
	seedVariables := []ssa.Value{}
	seedOutFile, err := os.Create("seed.txt")
	if err != nil {
		log.Fatalf("Failed to create file %s\n", err)
	}

	seed := FindSeedType(prog, seedType)
	if seed != nil {
		log.Println(seed.String())
		if seedStruct, ok := seed.Type().Underlying().(*types.Struct); ok {
			for i := 0; i < seedStruct.NumFields(); i++ {
				field := seedStruct.Field(i)
				seedOutFile.WriteString(fmt.Sprintf("%s - %s\n", field.Name(), GetFieldNameFromJsonTag(seedStruct.Tag(i))))
			}
		} else {
			seedOutFile.WriteString(fmt.Sprintf("%T", seed.Type().Underlying()))
		}
	}

	for f := range ssautil.AllFunctions(prog) {
		if strings.Contains(f.Name(), "DeepCopy") {
			continue
		}
		// if f.Name() == "Update" {
		// 	seedVariables = append(seedVariables, getSeedVariablesFromFunction(f, seed.Type())...)
		// 	f.WriteTo(os.Stdout)
		// }
		seedVariables = append(seedVariables, getSeedVariablesFromFunction(f, seed.Type())...)
	}

	for _, seedVar := range seedVariables {
		seedOutFile.WriteString(fmt.Sprintf("Value %s is seed\n", seedVar.String()))
	}
	seedOutFile.WriteString(fmt.Sprintf("%d\n", len(seedVariables)))

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

func GetParamIndex(value ssa.Value, call *ssa.CallCommon) int {
	var paramIndex int = -1
	for index, param := range call.Args {
		if param == value {
			paramIndex = index
		}
	}
	return paramIndex
}
