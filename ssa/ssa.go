package main

import (
	"flag"
	"fmt"
	"go/token"
	"go/types"
	"os"
	"reflect"
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

func FindSeedValues(prog *ssa.Program, seedType string) []ssa.Value {
	seedVariables := []ssa.Value{}
	seedOutFile, err := os.Create("seed.txt")
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to create file %s\n", err)
	}

	seed := findSeedType(prog, seedType)
	if seed != nil {
		fmt.Println(seed.String())
		if seedStruct, ok := seed.Type().Underlying().(*types.Struct); ok {
			for i := 0; i < seedStruct.NumFields(); i++ {
				field := seedStruct.Field(i)
				seedOutFile.WriteString(fmt.Sprintf("%s - %s\n", field.Name(), getFieldNameFromJsonTag(seedStruct.Tag(i))))
			}
		} else {
			seedOutFile.WriteString(fmt.Sprintf("%T", seed.Type().Underlying()))
		}
	}

	for f := range ssautil.AllFunctions(prog) {
		if strings.Contains(f.Name(), "DeepCopy") {
			continue
		}
		seedVariables = append(seedVariables, getSeedVariablesFromFunction(f, seed.Type())...)
	}

	for _, seedVar := range seedVariables {
		seedOutFile.WriteString(fmt.Sprintf("Value %s is seed\n", seedVar.String()))
	}
	seedOutFile.WriteString(fmt.Sprintf("%d\n", len(seedVariables)))

	return seedVariables
}

func main() {
	// Load, parse, and type-check the whole program.

	projectPath := flag.String("project-path", "/home/tyler/zookeeper-operator", "the path to the operator's source dir")
	seedType := flag.String("seed-type", "ZookeeperCluster", "The type of the root")
	flag.Parse()

	cfg := packages.Config{
		Mode: packages.LoadAllSyntax,
		Dir:  *projectPath,
	}
	initial, err := packages.Load(&cfg, ".")
	if err != nil {
		fmt.Println(err)
	}

	// Create SSA packages for well-typed packages and their dependencies.
	prog, _ := ssautil.AllPackages(initial, 0)

	// Build SSA code for the whole program.
	prog.Build()

	variableFieldMap := make(map[ssa.Value]Field)
	seedVariables := FindSeedValues(prog, *seedType)

	for _, seedVariable := range seedVariables {
		variableFieldMap[seedVariable] = Field{}
	}

	previousVariables := make(map[ssa.Value]Field)
	mergeMaps(previousVariables, variableFieldMap)

	valueSet := make(map[string]bool)
	instSet := make(map[string]bool)
	for {
		newVariableFieldMap := make(map[ssa.Value]Field)
		for variable, pathArray := range previousVariables {
			// t := variable.Type()
			referrers := variable.Referrers()
			for _, instruction := range *referrers {
				switch typedInst := instruction.(type) {
				case ssa.Value:
					switch typedValue := typedInst.(type) {
					case *ssa.FieldAddr:
						tag := typedValue.X.Type().Underlying().(*types.Pointer).Elem().Underlying().(*types.Struct).Tag(typedValue.Field)
						newVariableFieldMap[typedValue] = append(Field{}, pathArray...)
						newVariableFieldMap[typedValue] = append(newVariableFieldMap[typedValue], getFieldNameFromJsonTag(tag))
					case *ssa.Field:
						tag := typedValue.X.Type().(*types.Struct).Tag(typedValue.Field)
						newVariableFieldMap[typedValue] = append(Field{}, pathArray...)
						newVariableFieldMap[typedValue] = append(newVariableFieldMap[typedValue], getFieldNameFromJsonTag(tag))
					case *ssa.Call:
						// Inter-procedural
						continue
					case *ssa.MakeInterface:
						// If variable is casted into another interface, propogate
						fmt.Printf("Value %s is makeInterface\n", typedValue.String())
						fmt.Printf("In package %s \n", typedValue.Parent().String())
						newVariableFieldMap[typedValue] = append(Field{}, pathArray...)
					case *ssa.UnOp:
						switch typedValue.Op {
						case token.MUL:
							// If dereferenced, propogate
							fmt.Printf("Value %s is UnOp\n", instruction.String())
							newVariableFieldMap[typedValue] = append(Field{}, pathArray...)
						default:
							fmt.Printf("Value %s is UnOp\n", instruction.String())
						}
					default:
						// Report any unhandled value type
						valueSet[reflect.TypeOf(typedValue).String()] = true
					}
				case *ssa.Store:
					// Two cases, variable is referred as the addr, or the value
					fmt.Printf("Instruction %s is Store\n", typedInst.String())
					fmt.Printf("In package %s \n", typedInst.Parent().String())
					typedInst.Parent().WriteTo(os.Stdout)
					if typedInst.Addr == variable {
						fmt.Printf("Referred as the addr\n")
					} else {
						fmt.Println("Referred as the value")
						newVariableFieldMap[typedInst.Addr] = append(Field{}, pathArray...)
					}
				case *ssa.Return:
					// TODO
					continue
				default:
					// Report any unhandled instruction type
					instSet[reflect.TypeOf(typedInst).String()] = true
				}
			}
		}
		mergeMaps(variableFieldMap, newVariableFieldMap)
		previousVariables = newVariableFieldMap
		if len(newVariableFieldMap) == 0 {
			break
		}
	}
	fmt.Println(valueSet)
	fmt.Println(instSet)

	for v, path := range variableFieldMap {
		fmt.Printf("[%s] [%s] has path %s\n", v.Parent(), v.String(), path)
	}
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
