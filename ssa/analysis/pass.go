package analysis

import (
	"fmt"
	"go/token"
	"go/types"
	"os"
	"reflect"
	"strings"

	. "github.com/xlab-uiuc/acto/ssa/util"
	"golang.org/x/tools/go/ssa"
)

// Forward pass
// Introduction:
// 	- all values of type seedType
// Propogation rule:
// 	- Call: to the specific parameter of the callee
// 	- ChangeInterface
//	- ChangeType
//	- Convert
//	- Field: propogate with field name
//	- FieldAddr: propogate with field name
//	- Index: propogate with index
//	- IndexAddr: propogate with index
//	- LookUp: TODO if used as X, propogate
//	- Phi: propogate with merged paths
//	- UnOp: propogate if dereference
//	- Store: TODO propogate backward
//	- Return + Extract: TODO propogate to function callsites
// Sink:
//	- Stop at all other instruction types
//	- Stop propogation when calling library functions
//
// Frontier values:
//	- if all a value's all referrers are propogated, it's not frontier
func GetValueToFieldMappingPass(prog *ssa.Program, seedType string) map[ssa.Value]*FieldSet {
	valueFieldSetMap := make(map[ssa.Value]*FieldSet)
	frontierValues := make(map[ssa.Value]bool)
	seedVariables := FindSeedValues(prog, seedType)

	allTypes := GetAllTypes(prog)

	for _, seedVariable := range seedVariables {
		rootField := []string{"root"}
		valueFieldSetMap[seedVariable] = NewFieldSet()
		valueFieldSetMap[seedVariable].Add(&Field{
			Path: rootField,
		})
	}

	valueSet := make(map[string]bool)
	instSet := make(map[string]bool)
	callValueSet := make(map[string]bool)
	for {
		changed := false
		for variable, parentFieldSet := range valueFieldSetMap {
			// stop if field is on metadata, status, or type meta
			if parentFieldSet.IsMetadata() || parentFieldSet.IsStatus() || parentFieldSet.IsTypeMeta() {
				continue
			}
			referrers := variable.Referrers()
			for _, instruction := range *referrers {
				switch typedInst := instruction.(type) {
				case ssa.Value:
					switch typedValue := typedInst.(type) {
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
								// stop propogate if external library call
								if strings.Contains(callValue.Pkg.Pkg.Path(), "github.com/rabbitmq/cluster-operator") {
									fmt.Printf("Propogate into function %s\n", callValue.String())
									param := callValue.Params[paramIndex]
									for _, parentField := range parentFieldSet.Fields() {
										newField := parentField.Clone()
										ok := AddFieldToValueFieldSetMap(valueFieldSetMap, param, newField)
										if ok {
											changed = true
										}
									}
								} else {
									fmt.Printf("Stop propogating to external package %s\n", callValue.String())
									frontierValues[variable] = true
								}
							case *ssa.MakeClosure:
								// XXX could be closure, let's handle it if it's used
								fmt.Println("Warning, closure used")
							case *ssa.Builtin:
								// Stop propogation?
								frontierValues[variable] = true
							default:
								callValueSet[callValue.Name()] = true
								frontierValues[variable] = true
							}
						} else {
							// interface invocation
							// XXX: Do not handle for now
							interfaceType := typedValue.Call.Value.Type().Underlying()
							method := typedValue.Call.Method
							fmt.Printf("Interface type %s\n", interfaceType)
							for _, typ := range allTypes {
								if types.Implements(typ.Type(), interfaceType.(*types.Interface)) {
									fmt.Printf("%s implements %s\n", typ.Type(), interfaceType)
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
					case *ssa.ChangeInterface:
						for _, parentField := range parentFieldSet.Fields() {
							newField := parentField.Clone()
							ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
							if ok {
								changed = true
							}
						}
					case *ssa.ChangeType:
						for _, parentField := range parentFieldSet.Fields() {
							newField := parentField.Clone()
							ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
							if ok {
								changed = true
							}
						}
					case *ssa.Convert:
						for _, parentField := range parentFieldSet.Fields() {
							newField := parentField.Clone()
							ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
							if ok {
								changed = true
							}
						}
					case *ssa.Field:
						for _, parentField := range parentFieldSet.Fields() {
							newField := NewSubField(typedValue.X.Type().(*types.Struct), parentField, typedValue.Field)
							ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
							if ok {
								changed = true
							}
						}
					case *ssa.FieldAddr:
						for _, parentField := range parentFieldSet.Fields() {
							newField := NewSubField(typedValue.X.Type().Underlying().(*types.Pointer).Elem().Underlying().(*types.Struct), parentField, typedValue.Field)
							ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
							if ok {
								changed = true
							}
						}
					case *ssa.Index:
						for _, parentField := range parentFieldSet.Fields() {
							newField := NewIndexField(parentField)
							ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
							if ok {
								changed = true
							}
						}
					case *ssa.IndexAddr:
						// accessing array index
						for _, parentField := range parentFieldSet.Fields() {
							newField := NewIndexField(parentField)
							ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
							if ok {
								changed = true
							}
						}
					case *ssa.Lookup:
						if typedValue.X == variable {
							// XXX: accessed as a map, need to propogate, but how to resolve the key?
							fmt.Printf("variable is used as the X %s\n", parentFieldSet)
							// typedValue.Parent().WriteTo(os.Stdout)
						} else {
							// do not propogate
							fmt.Printf("variable is used as the index\n")
							frontierValues[variable] = true
						}
					case *ssa.Phi:
						// propogate with merged edges

						fieldSetSlice := []FieldSet{}
						for _, edge := range typedValue.Edges {
							if fieldSet, ok := valueFieldSetMap[edge]; ok {
								// field present
								fieldSetSlice = append(fieldSetSlice, *fieldSet)
							}
						}
						mergedFieldSet := MergeFieldSets(fieldSetSlice...)
						for _, parentField := range mergedFieldSet.Fields() {
							newField := parentField.Clone()
							ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
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
								ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
								if ok {
									changed = true
								}
							}
						default:
							// not dereference, do not propogate
							// frontier
							frontierValues[variable] = true
						}
					case *ssa.MakeInterface:
						// If variable is casted into another interface, propogate
						fmt.Printf("Value is used in MakeInterface %s\n", typedValue.String())
						for _, parentField := range parentFieldSet.Fields() {
							newField := parentField.Clone()
							ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedValue, newField)
							if ok {
								changed = true
							}
						}

					default:
						// Other types, sink
						// since variable has at least one referrer in sink
						// it's frontier
						valueSet[reflect.TypeOf(typedValue).String()] = true
						frontierValues[variable] = true
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
							ok := AddFieldToValueFieldSetMap(valueFieldSetMap, typedInst.Addr, newField)
							if ok {
								changed = true
							}
						}
					}
				case *ssa.Return:
					// XXX: no need to handle them now
					fmt.Printf("CR fields propogated to return instructions\n")
					// let taint pass handle this
					frontierValues[variable] = true
				default:
					// Report any unhandled instruction type
					instSet[reflect.TypeOf(typedInst).String()] = true
					frontierValues[variable] = true
				}
			}
		}
		if !changed {
			break
		}

	}
	fmt.Println(valueSet)
	fmt.Println(instSet)
	fmt.Println(frontierValues)

	return valueFieldSetMap
}
