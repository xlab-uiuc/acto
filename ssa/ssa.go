package main

import (
	"fmt"
	"go/types"
	"os"
	"strconv"
	"strings"

	"golang.org/x/tools/go/packages"
	"golang.org/x/tools/go/ssa"
	"golang.org/x/tools/go/ssa/ssautil"
)

type Field []string

func mergeMaps(m1 map[ssa.Value]Field, m2 map[ssa.Value]Field) {
	for k, v := range m2 {
		m1[k] = v
	}
}

func findSeedType(prog *ssa.Program, seedStr string) *ssa.Type {
	for _, pkg := range prog.AllPackages() {
		seed := pkg.Members[seedStr]
		if typ, ok := seed.(*ssa.Type); ok {
			return typ
		}
	}
	return nil
}

func getFieldNameFromJsonTag(tag string) string {
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

func main() {
	// Load, parse, and type-check the whole program.
	cfg := packages.Config{
		Mode: packages.LoadAllSyntax,
		Dir:  "/home/tyler/zookeeper-operator",
	}
	initial, err := packages.Load(&cfg, ".")
	if err != nil {
		fmt.Println(err)
	}

	// Create SSA packages for well-typed packages and their dependencies.
	prog, _ := ssautil.AllPackages(initial, 0)

	// Build SSA code for the whole program.
	prog.Build()

	zk_pkg := prog.ImportedPackage("github.com/pravega/zookeeper-operator/api/v1beta1")
	zk_pkg.WriteTo(os.Stdout)
	// generator_func := zk_pkg.Members["Reconcile"].(*ssa.Function)
	// generator_func.WriteTo(os.Stdout)

	seed := findSeedType(prog, "ZookeeperCluster")
	if seed != nil {
		fmt.Println(seed.String())
		if seedStruct, ok := seed.Type().Underlying().(*types.Struct); ok {
			for i := 0; i < seedStruct.NumFields(); i++ {
				field := seedStruct.Field(i)
				fmt.Printf("%s - %s\n", field.Name(), getFieldNameFromJsonTag(seedStruct.Tag(i)))
			}
		} else {
			fmt.Printf("%T", seed.Type().Underlying())
		}
	}

	variableFieldMap := make(map[ssa.Value]Field)
	seedVariables := []ssa.Value{}

	for f := range ssautil.AllFunctions(prog) {
		if strings.Contains(f.Name(), "DeepCopy") {
			continue
		}
		seedVariables = append(seedVariables, getSeedVariablesFromFunction(f)...)
	}
	fmt.Println(len(seedVariables))

	for _, seedVariable := range seedVariables {
		variableFieldMap[seedVariable] = Field{}
	}

	previousVariables := make(map[ssa.Value]Field)
	mergeMaps(previousVariables, variableFieldMap)
	for {
		newVariableFieldMap := make(map[ssa.Value]Field)
		for variable, pathArray := range previousVariables {
			// t := variable.Type()
			referrers := variable.Referrers()
			for _, instruction := range *referrers {
				switch inst := instruction.(type) {
				case ssa.Value:
					switch fieldInst := inst.(type) {
					case *ssa.FieldAddr:
						field := fieldInst.X.Type().Underlying().(*types.Pointer).Elem().Underlying().(*types.Struct).Field(fieldInst.Field)
						tag := fieldInst.X.Type().Underlying().(*types.Pointer).Elem().Underlying().(*types.Struct).Tag(fieldInst.Field)
						fmt.Printf("Instruction %s maps to %s\n", instruction.String(), field.Name())
						newVariableFieldMap[fieldInst] = append(Field{}, pathArray...)
						newVariableFieldMap[fieldInst] = append(newVariableFieldMap[fieldInst], getFieldNameFromJsonTag(tag))
					case *ssa.Field:
						field := fieldInst.X.Type().(*types.Struct).Field(fieldInst.Field)
						tag := fieldInst.X.Type().(*types.Struct).Tag(fieldInst.Field)
						fmt.Printf("Instruction %s maps to %s\n", instruction.String(), field.Name())
						newVariableFieldMap[fieldInst] = append(Field{}, pathArray...)
						newVariableFieldMap[fieldInst] = append(newVariableFieldMap[fieldInst], getFieldNameFromJsonTag(tag))
					}
				}
			}
		}
		mergeMaps(variableFieldMap, newVariableFieldMap)
		previousVariables = newVariableFieldMap
		if len(newVariableFieldMap) == 0 {
			break
		}
	}
	fmt.Println(variableFieldMap)

	for v, path := range variableFieldMap {
		fmt.Printf("[%s] [%s] has path %s\n", v.Parent(), v.String(), path)
	}
}

func getSeedVariablesFromFunction(f *ssa.Function) []ssa.Value {
	ret := []ssa.Value{}
	for _, blk := range f.Blocks {
		for _, inst := range blk.Instrs {
			switch v := inst.(type) {
			case ssa.Value:
				if v.Type().String() == "*github.com/pravega/zookeeper-operator/api/v1beta1.ZookeeperCluster" ||
					v.Type().String() == "github.com/pravega/zookeeper-operator/api/v1beta1.ZookeeperCluster" {
					ret = append(ret, v)
				}
			default:
				fmt.Printf("Instruction is type [%T]\n", inst)
			}
		}
	}

	for _, param := range f.Params {
		if param.Type().String() == "*github.com/pravega/zookeeper-operator/api/v1beta1.ZookeeperCluster" {
			ret = append(ret, param)
		}
	}
	return ret
}
