package analysis

import (
	"encoding/json"
	"go/token"
	"go/types"
	"log"
	"regexp"
	"strings"

	"github.com/goki/ki/ki"
	"github.com/xlab-uiuc/acto/ssa/util"
	"golang.org/x/tools/go/pointer"
	"golang.org/x/tools/go/ssa"
)

const INDEX = "ITEM"
const MAP_KEY = "KEY"

func GetTypeTree(context *Context, seedType types.Type) {
	root := NewTypeFieldNode("", seedType)
	root.InitName(root, "root")
	typ := seedType.Underlying().(*types.Struct)

	for i := 0; i < typ.NumFields(); i++ {
		field := typ.Field(i)

		tag := typ.Tag(i)
		tagName := util.GetFieldNameFromJsonTag(tag)

		fieldNode := NewTypeFieldNode(tagName, field.Type())
		fieldNode.InitName(fieldNode, field.Name())
		root.AddChild(fieldNode)
	}
}

func GetTypeTreeHelper(context *Context, seedType types.Type, node *TypeFieldNode) {
	switch typ := seedType.Underlying().(type) {
	case *types.Struct:
		for i := 0; i < typ.NumFields(); i++ {
			field := typ.Field(i)

			tag := typ.Tag(i)
			tagName := util.GetFieldNameFromJsonTag(tag)

			fieldNode := NewTypeFieldNode(tagName, field.Type())
			fieldNode.InitName(fieldNode, field.Name())
			node.AddChild(fieldNode)

			GetTypeTreeHelper(context, field.Type(), fieldNode)
		}
	case *types.Slice:
		fieldNode := NewTypeFieldNode(INDEX, typ.Elem())
		fieldNode.InitName(fieldNode, INDEX)
		node.AddChild(fieldNode)

		GetTypeTreeHelper(context, typ.Elem(), fieldNode)
	case *types.Map:
		fieldNode := NewTypeFieldNode(MAP_KEY, typ.Elem())
		fieldNode.InitName(fieldNode, MAP_KEY)
		node.AddChild(fieldNode)

		GetTypeTreeHelper(context, typ.Elem(), fieldNode)
	case *types.Pointer:
		GetTypeTreeHelper(context, typ.Elem(), node)
	}
}

func GetFieldToK8sMapping(context *Context, prog *ssa.Program, seedType *string,
	seedPkgPath *string) {

	fieldsInK8s := context.FieldToK8sMapping
	seed := util.FindSeedType(prog, seedType, seedPkgPath)
	fieldTree := NewTypeFieldNode("", seed.Type())
	fieldTree.InitName(fieldTree, "root")

	GetTypeTreeHelper(context, seed.Type(), fieldTree)

	for _, field := range *fieldTree.Children() {
		log.Printf("Field: %s", field.Name())
	}

	valueToFieldsMap := make(map[ssa.Value]TypeFieldNodeSet)

	worklist := []ssa.Value{}

	seedVariables := util.FindSeedValues(prog, seedType, seedPkgPath)
	for _, seedVariable := range seedVariables {
		valueToFieldsMap[seedVariable] = NewTypeFieldNodeSet()
		valueToFieldsMap[seedVariable].Add(fieldTree)
		fieldTree.AddValue(seedVariable)
		worklist = append(worklist, seedVariable)
	}

	for stop := false; !stop; {
		storeInsts := map[ssa.Value]*ssa.Store{}
		for len(worklist) > 0 {
			value := worklist[len(worklist)-1]
			worklist = worklist[:len(worklist)-1]

			fields := valueToFieldsMap[value]
			if fields.IsMetadata() || fields.IsObjectMeta() || fields.IsStatus() {
				continue
			}

			referrers := value.Referrers()
			for _, instruction := range *referrers {
				switch typedInst := instruction.(type) {
				case ssa.Value:
					switch typedValue := typedInst.(type) {
					case *ssa.Call:
						if !typedValue.Call.IsInvoke() {
							callSiteTaintedParamIndexSet := util.GetCallsiteArgIndices(value, typedValue.Common())
							if len(callSiteTaintedParamIndexSet) == 0 {
								log.Println("Error, unable to find the param index")
							}
							switch callValue := typedValue.Call.Value.(type) {
							case *ssa.Function:
								if callValue.Name() == "DeepCopy" || callValue.Name() == "String" || callValue.Name() == "Float64" {
									if AddValueToValueToFieldsMap(valueToFieldsMap, typedValue, fields) {
										worklist = append(worklist, typedValue)
									}
								} else if callValue.Name() == "DeepCopyInto" {
									for _, paramIndex := range callSiteTaintedParamIndexSet {
										if paramIndex == 0 {
											// the source of DeepCopyInto is tainted
											log.Printf("Propogate through %s\n", callValue.Name())
											target := typedValue.Call.Args[1] // the value that got deepcopied into
											if AddValueToValueToFieldsMap(valueToFieldsMap, target, fields) {
												worklist = append(worklist, target)
											}
										}
									}
								} else {
									PropagateToCallee(context, callValue, callSiteTaintedParamIndexSet,
										value, fields, valueToFieldsMap, &worklist)
								}
							case *ssa.MakeClosure:
								PropagateToCallee(context, callValue.Fn.(*ssa.Function), callSiteTaintedParamIndexSet,
									value, fields, valueToFieldsMap, &worklist)
							case *ssa.Builtin:
								log.Printf("Unhandled builtin: %s", callValue.Name())
							case *ssa.UnOp:
								if AddValueToValueToFieldsMap(valueToFieldsMap, typedValue, fields) {
									worklist = append(worklist, typedValue)
								}
							default:
								log.Printf("Unhandled call value type: %T at %s", callValue, context.Program.Fset.Position(typedValue.Pos()))
							}
						}
					case *ssa.ChangeInterface:
						if AddValueToValueToFieldsMap(valueToFieldsMap, typedValue, fields) {
							worklist = append(worklist, typedValue)
						}
					case *ssa.ChangeType:
						if AddValueToValueToFieldsMap(valueToFieldsMap, typedValue, fields) {
							worklist = append(worklist, typedValue)
						}
					case *ssa.Convert:
						if AddValueToValueToFieldsMap(valueToFieldsMap, typedValue, fields) {
							worklist = append(worklist, typedValue)
						}
					case *ssa.FieldAddr:
						subfields := NewTypeFieldNodeSet()
						for field := range fields {
							fieldName := typedValue.X.Type().Underlying().(*types.Pointer).Elem().Underlying().(*types.Struct).Field(typedValue.Field).Name()
							node, ok := field.ChildByName(fieldName, 0).(*TypeFieldNode)
							if !ok {
								log.Panicf("Error, unable to find field %s in %s", fieldName, field.Path())
							}
							subfields.Add(node)
						}
						if AddValueToValueToFieldsMap(valueToFieldsMap, typedValue, subfields) {
							worklist = append(worklist, typedValue)
						}
					case *ssa.Field:
						subfields := NewTypeFieldNodeSet()
						for field := range fields {
							node, ok := field.ChildByName(typedValue.X.Type().Underlying().(*types.Struct).Field(typedValue.Field).Name(), 0).(*TypeFieldNode)
							if !ok {
								log.Panic("Error, unable to find field")
							}
							subfields.Add(node)
						}
						if AddValueToValueToFieldsMap(valueToFieldsMap, typedValue, subfields) {
							worklist = append(worklist, typedValue)
						}
					case *ssa.IndexAddr:
						subfields := NewTypeFieldNodeSet()
						for field := range fields {
							node, ok := field.ChildByName(INDEX, 0).(*TypeFieldNode)
							if !ok {
								log.Panic("Error, unable to find field")
							}
							subfields.Add(node)
						}
						if AddValueToValueToFieldsMap(valueToFieldsMap, typedValue, subfields) {
							worklist = append(worklist, typedValue)
						}
					case *ssa.Index:
						subfields := NewTypeFieldNodeSet()
						for field := range fields {
							node, ok := field.ChildByName(INDEX, 0).(*TypeFieldNode)
							if !ok {
								log.Panic("Error, unable to find field")
							}
							subfields.Add(node)
						}
						if AddValueToValueToFieldsMap(valueToFieldsMap, typedValue, subfields) {
							worklist = append(worklist, typedValue)
						}
					case *ssa.Lookup:
						if typedValue.X == value {
							// XXX: accessed as a map, need to propogate, but how to resolve the key?
							subfields := NewTypeFieldNodeSet()
							for field := range fields {
								node, ok := field.ChildByName(MAP_KEY, 0).(*TypeFieldNode)
								if !ok {
									log.Panic("Error, unable to find field")
								}
								subfields.Add(node)
							}
							if AddValueToValueToFieldsMap(valueToFieldsMap, typedValue, subfields) {
								worklist = append(worklist, typedValue)
							}
						} else {
							// do not propogate
							log.Printf("variable is used as the index\n")
						}
					case *ssa.Phi:
						if AddValueToValueToFieldsMap(valueToFieldsMap, typedValue, fields) {
							worklist = append(worklist, typedValue)
						}
					case *ssa.UnOp:
						switch typedValue.Op {
						case token.MUL:
							if AddValueToValueToFieldsMap(valueToFieldsMap, typedValue, fields) {
								worklist = append(worklist, typedValue)
							}
						}
					case *ssa.MakeInterface:
						if AddValueToValueToFieldsMap(valueToFieldsMap, typedValue, fields) {
							worklist = append(worklist, typedValue)
						}
					}
				case *ssa.Store:
					if typedInst.Addr == value {
					} else {
						if AddValueToValueToFieldsMap(valueToFieldsMap, typedInst.Addr, fields) {
							worklist = append(worklist, typedInst.Addr)
						}
						storeInsts[value] = typedInst
					}
				}
			}
		}

		queries := make(map[ssa.Value]struct{})
		for _, inst := range storeInsts {
			queries[inst.Addr] = struct{}{}
		}

		config := pointer.Config{
			Mains:          context.MainPackages,
			BuildCallGraph: false,
			Queries:        queries,
		}
		result, err := pointer.Analyze(&config)
		if err != nil {
			log.Panic(err)
		}

		for value, inst := range storeInsts {
			for _, source := range result.Queries[inst.Addr].PointsTo().Labels() {
				log.Printf("value [%s] stored into %s with path %s\n", valueToFieldsMap[value].Path(), source, source.Path())
				if IsKubernetesType(source.Value().Type()) {
					for field := range valueToFieldsMap[value] {
						fieldsInK8s[field] = FieldInKubernetes{
							KubernetesType: source.Value().Type(),
							FieldPath:      source.Path(),
						}
					}
				}
			}
		}

		stop = true
	}

	for field, info := range fieldsInK8s {
		log.Printf("field [%s] is in kubernetes type [%s] with path [%s]", field.Path(), info.KubernetesType, info.FieldPath)
	}
}

func IsKubernetesType(t types.Type) bool {
	switch typ := t.(type) {
	case *types.Named:
		pkg := typ.Obj().Pkg()
		if pkg != nil && strings.Contains(pkg.Path(), "k8s.io/") {
			return true
		}
	case *types.Pointer:
		return IsKubernetesType(typ.Elem())
	}
	return false
}

func BackwardPropagationHelper(context *Context, value ssa.Value) (sources []*pointer.Label) {
	config := pointer.Config{
		Mains:          context.MainPackages,
		BuildCallGraph: false,
		Queries: map[ssa.Value]struct{}{
			value: {},
		},
	}
	result, err := pointer.Analyze(&config)

	if err != nil {
		log.Panic(err)
	}
	sources = result.Queries[value].PointsTo().Labels()
	return
}

func PropagateToCallee(context *Context, callee *ssa.Function, callSiteTaintedArgIndexSet []int,
	value ssa.Value, fields TypeFieldNodeSet, valueToFieldsMap map[ssa.Value]TypeFieldNodeSet, worklist *[]ssa.Value) {
	if callee.Pkg != nil && strings.Contains(callee.Pkg.Pkg.Path(), context.RootModule.Path) {
		for _, paramIndex := range callSiteTaintedArgIndexSet {
			param := callee.Params[paramIndex]
			if AddValueToValueToFieldsMap(valueToFieldsMap, param, fields) {
				*worklist = append(*worklist, param)
			}
		}
	} else {
		log.Printf("Callee %s is not in the root module", callee.Name())
	}
}

func AddValueToValueToFieldsMap(valueToFieldsMap map[ssa.Value]TypeFieldNodeSet, value ssa.Value, fields TypeFieldNodeSet) bool {
	changed := false
	if _, ok := valueToFieldsMap[value]; !ok {
		valueToFieldsMap[value] = NewTypeFieldNodeSet()
		changed = true
	}

	for field := range fields {
		if !valueToFieldsMap[value].Contains(field) {
			valueToFieldsMap[value].Add(field)
			field.AddValue(value)
			changed = true
		}
	}
	return changed
}

type StringSet map[string]struct{}

type FieldInKubernetesSlice []FieldInKubernetes

type FieldInKubernetes struct {
	KubernetesType types.Type `json:"kubernetes_type"`
	FieldPath      string     `json:"fieldPath"`
}

func (f FieldInKubernetes) MarshalJSON() ([]byte, error) {

	regex := regexp.MustCompile(`\[*\]`)
	fieldPath := regex.ReplaceAllString(f.FieldPath, ".*")
	path := strings.Split(fieldPath, ".")
	b, _ := json.Marshal(path)

	return json.Marshal(map[string]interface{}{
		"KubernetesType": f.KubernetesType.String(),
		"FieldPath":      string(b[:]),
	})
}

type TypeFieldNodeSet map[*TypeFieldNode]struct{}

func (set TypeFieldNodeSet) Add(node *TypeFieldNode) {
	set[node] = struct{}{}
}

func (set TypeFieldNodeSet) Contains(node *TypeFieldNode) bool {
	_, ok := set[node]
	return ok
}

func (set TypeFieldNodeSet) Path() string {
	var path string
	for node := range set {
		path += node.Path()
		path += " "
	}
	return path
}

func (set TypeFieldNodeSet) IsMetadata() bool {
	if len(set) == 1 {
		for node := range set {
			if node.IsMetadata() {
				return true
			}
		}
	}
	return false
}

func (set TypeFieldNodeSet) IsObjectMeta() bool {
	if len(set) == 1 {
		for node := range set {
			if node.IsObjectMeta() {
				return true
			}
		}
	}
	return false
}

func (set TypeFieldNodeSet) IsStatus() bool {
	if len(set) == 1 {
		for node := range set {
			if node.IsStatus() {
				return true
			}
		}
	}
	return false
}

func NewTypeFieldNodeSet() TypeFieldNodeSet {
	return make(map[*TypeFieldNode]struct{})
}

type TypeFieldNode struct {
	// A FieldNode represent a specific field in the CR struct
	ki.Node

	// the list of values that map to this field
	ValueSet map[ssa.Value]struct{}

	Type    types.Type
	TagName string
}

func (fn *TypeFieldNode) AddValue(value ssa.Value) {
	fn.ValueSet[value] = struct{}{}
}

func (fn *TypeFieldNode) IsMetadata() bool {
	return fn.Path() == "/root/Metadata"
}

func (fn *TypeFieldNode) IsObjectMeta() bool {
	return fn.Path() == "/root/ObjectMeta"
}

func (fn *TypeFieldNode) IsStatus() bool {
	return fn.Path() == "/root/Status"
}

func (fn *TypeFieldNode) EncodedPath() string {
	path := []string{}
	fn.FuncUp(0, path, func(k ki.Ki, level int, d interface{}) bool {
		node, _ := k.(*TypeFieldNode)
		if node.TagName != "" {
			path = append([]string{node.TagName}, path...)
		}
		return true
	})
	b, _ := json.Marshal(path[1:])
	return string(b[:])
}

func NewTypeFieldNode(tagName string, typ types.Type) *TypeFieldNode {
	return &TypeFieldNode{
		ValueSet: make(map[ssa.Value]struct{}),
		Type:     typ,
		TagName:  tagName,
	}
}
