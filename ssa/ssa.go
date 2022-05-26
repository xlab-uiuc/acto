package main

import (
	"flag"
	"fmt"
	"go/token"
	"go/types"
	"os"
	"reflect"
	"strings"

	. "github.com/xlab-uiuc/acto/ssa/util"
	"golang.org/x/tools/go/packages"
	"golang.org/x/tools/go/ssa"
	"golang.org/x/tools/go/ssa/ssautil"
)

func findSeedType(prog *ssa.Program, seedStr string) *ssa.Type {
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
		fmt.Fprintf(os.Stderr, "Failed to create file %s\n", err)
	}

	seed := findSeedType(prog, seedType)
	if seed != nil {
		fmt.Println(seed.String())
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
		seedVariables = append(seedVariables, getSeedVariablesFromFunction(f, seed.Type())...)
	}

	for _, seedVar := range seedVariables {
		seedOutFile.WriteString(fmt.Sprintf("Value %s is seed\n", seedVar.String()))
	}
	seedOutFile.WriteString(fmt.Sprintf("%d\n", len(seedVariables)))

	return seedVariables
}

// get all the types from program
func getAllTypes(prog *ssa.Program) []*ssa.Type {
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

	variableFieldsMap := make(map[ssa.Value]*FieldSet)
	seedVariables := FindSeedValues(prog, *seedType)

	allTypes := getAllTypes(prog)

	for _, seedVariable := range seedVariables {
		rootField := []string{"root"}
		variableFieldsMap[seedVariable] = NewFieldSet()
		variableFieldsMap[seedVariable].Add(&Field{
			Path: rootField,
		})
	}

	valueSet := make(map[string]bool)
	instSet := make(map[string]bool)
	callValueSet := make(map[string]bool)
	for {
		changed := false
		for variable, parentFieldSet := range variableFieldsMap {
			// t := variable.Type()
			referrers := variable.Referrers()
			for _, instruction := range *referrers {
				switch typedInst := instruction.(type) {
				case ssa.Value:
					switch typedValue := typedInst.(type) {
					case *ssa.FieldAddr:
						for _, parentField := range parentFieldSet.Fields() {
							newField := NewSubField(typedValue.X.Type().Underlying().(*types.Pointer).Elem().Underlying().(*types.Struct), parentField, typedValue.Field)
							ok := AddFieldToValueFieldSetMap(variableFieldsMap, typedValue, newField)
							if ok {
								changed = true
							}
						}
					case *ssa.Field:
						for _, parentField := range parentFieldSet.Fields() {
							newField := NewSubField(typedValue.X.Type().(*types.Struct), parentField, typedValue.Field)
							ok := AddFieldToValueFieldSetMap(variableFieldsMap, typedValue, newField)
							if ok {
								changed = true
							}
						}
					case *ssa.Call:
						// Inter-procedural
						// Two possibilities for Call: function call or interface invocation
						if !typedValue.Call.IsInvoke() {
							// ordinary function call
							var paramIndex int
							for index, param := range typedValue.Call.Args {
								if param == typedValue {
									paramIndex = index
								}
							}
							switch callValue := typedValue.Call.Value.(type) {
							case *ssa.Function:
								// propogate to the function parameter
								param := callValue.Params[paramIndex]
								for _, parentField := range parentFieldSet.Fields() {
									newField := parentField.Clone()
									ok := AddFieldToValueFieldSetMap(variableFieldsMap, param, newField)
									if ok {
										changed = true
									}
								}
							case *ssa.MakeClosure:
								// XXX could be closure, let's handle it if it's used
								fmt.Println("Warning, closure used")
							case *ssa.Builtin:
								// Stop propogation?
								continue
							default:
								callValueSet[callValue.Name()] = true
							}
						} else {
							// interface invocation
							interfaceType := typedValue.Call.Value.Type().Underlying()
							method := typedValue.Call.Method
							fmt.Printf("Interface type %T\n", interfaceType)
							for _, typ := range allTypes {
								if types.Implements(typ.Type(), interfaceType.(*types.Interface)) {
									fmt.Printf("%T implements %s\n", typ.Type(), interfaceType)
									if concreteType, ok := typ.Type().(*types.Named); ok {
										for i := 0; i < concreteType.NumMethods(); i++ {
											if concreteType.Method(i).Name() == method.Name() {
												fmt.Printf("Found concrete method for %s\n", method.FullName())
											}
										}
									} else {
										fmt.Fprintf(os.Stderr, "concrete type is not named, but %T\n", typ.Type())
									}
								}
							}
						}
					case *ssa.MakeInterface:
						// If variable is casted into another interface, propogate
						for _, parentField := range parentFieldSet.Fields() {
							newField := parentField.Clone()
							ok := AddFieldToValueFieldSetMap(variableFieldsMap, typedValue, newField)
							if ok {
								changed = true
							}
						}
					case *ssa.UnOp:
						switch typedValue.Op {
						case token.MUL:
							// If dereferenced, propogate
							for _, parentField := range parentFieldSet.Fields() {
								newField := parentField.Clone()
								ok := AddFieldToValueFieldSetMap(variableFieldsMap, typedValue, newField)
								if ok {
									changed = true
								}
							}
						default:
							fmt.Printf("Value %s is UnOp\n", instruction.String())
						}
					case *ssa.BinOp:
						// Do not handle BinOp in this pass
						continue
					default:
						// Report any unhandled value type
						valueSet[reflect.TypeOf(typedValue).String()] = true
						fmt.Printf("Unhandled type %s\n", typedValue.String())
					}
				case *ssa.Store:
					// Two cases, variable is referred as the addr, or the value
					if typedInst.Addr == variable {
						fmt.Printf("Referred as the addr\n")
					} else {
						// referred as the value, propogate to addr
						// XXX: may need to propogate backward
						for _, parentField := range parentFieldSet.Fields() {
							newField := parentField.Clone()
							ok := AddFieldToValueFieldSetMap(variableFieldsMap, typedInst.Addr, newField)
							if ok {
								changed = true
							}
						}
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
		if !changed {
			break
		}

	}
	fmt.Println(valueSet)
	fmt.Println(instSet)
	for v, path := range variableFieldsMap {
		fmt.Printf("[%s] [%s]=[%s] has path %s\n", v.Parent(), v.Name(), v.String(), path)
	}
	fmt.Println("------------------------")
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
