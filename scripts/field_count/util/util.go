package util

import (
	"fmt"
	"go/types"
	"log"
	"strconv"
	"strings"

	"go.uber.org/zap"
	"golang.org/x/tools/go/ssa"
	"golang.org/x/tools/go/ssa/ssautil"
)

func FindSeedType(prog *ssa.Program, seedStr *string, pkgPath *string) (*ssa.Type, error) {
	for _, pkg := range prog.AllPackages() {
		if pkg.Pkg.Path() == *pkgPath {
			seed := pkg.Members[*seedStr]
			if typ, ok := seed.(*ssa.Type); ok {
				return typ, nil
			}
		}
	}
	return nil, fmt.Errorf("Could not find seed type %s in package %s", *seedStr, *pkgPath)
}

func FindSeedValues(prog *ssa.Program, seedType *string, pkgPath *string) []ssa.Value {
	seedVariables := []ssa.Value{}

	seed, _ := FindSeedType(prog, seedType, pkgPath)
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
		seedVariables = append(seedVariables, GetSeedVariablesFromFunction(f, seed.Type())...)
	}

	for _, seedVar := range seedVariables {
		log.Printf("%s\n", fmt.Sprintf("Value %s is seed", seedVar.String()))
	}
	log.Printf("%s\n", fmt.Sprintf("%d\n", len(seedVariables)))

	return seedVariables
}

func GetSeedVariablesFromFunction(f *ssa.Function, seedType types.Type) []ssa.Value {
	logger := zap.S()
	ret := []ssa.Value{}
	for _, blk := range f.Blocks {
		for _, inst := range blk.Instrs {
			switch v := inst.(type) {
			case ssa.Value:
				if _, ok := v.(*ssa.Range); ok {
					continue
				}
				vType := v.Type()
				if types.Identical(vType, seedType) {
					ret = append(ret, v)
				} else if vType.String() == seedType.String() {
					logger.Infof("String matching but type not identical %s", seedType.String())
					ret = append(ret, v)
				}
				if vPointer, ok := vType.(*types.Pointer); ok && types.Identical(vPointer.Elem(), seedType) {
					ret = append(ret, v)
				} else if ok && vPointer.Elem().String() == seedType.String() {
					logger.Infof("String matching but type not identical %s", seedType.String())
					ret = append(ret, v)
				}
			}
		}
	}

	for _, param := range f.Params {
		vType := param.Type()
		if types.Identical(vType, seedType) {
			ret = append(ret, param)
		}
		if vPointer, ok := vType.(*types.Pointer); ok && types.Identical(vPointer.Elem(), seedType) {
			ret = append(ret, param)
		}
	}

	for _, freeVar := range f.FreeVars {
		vType := freeVar.Type()
		if types.Identical(vType, seedType) {
			ret = append(ret, freeVar)
		}
		if vPointer, ok := vType.(*types.Pointer); ok && types.Identical(vPointer.Elem(), seedType) {
			ret = append(ret, freeVar)
		}
	}

	for _, local := range f.Locals {
		vType := local.Type()
		if types.Identical(vType, seedType) {
			ret = append(ret, local)
		}
		if vPointer, ok := vType.(*types.Pointer); ok && types.Identical(vPointer.Elem(), seedType) {
			ret = append(ret, local)
		}
	}

	logger.Infof("Found %d seed variables in function %s", len(ret), f.Name())
	return ret
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
