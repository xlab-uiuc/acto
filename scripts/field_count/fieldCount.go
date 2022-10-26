package fieldcount

import (
	"bytes"
	"go/token"
	"go/types"
	"os"
	"strings"

	"github.com/go-yaml/yaml"
	"github.com/goki/ki/ki"
	"github.com/xlab-uiuc/acto/scripts/fieldCount/util"
	"go.uber.org/zap"
	"golang.org/x/tools/go/packages"
	"golang.org/x/tools/go/ssa"
	"golang.org/x/tools/go/ssa/ssautil"
)

func CountFieldYaml(filePath string, fieldSet StringSet, kind string) {
	logger := zap.S()
	data, err := os.ReadFile(filePath)
	if err != nil {
		panic(err)
	}

	root := FieldNode{}
	root.InitName(&root, "root")
	var instance map[string]interface{}
	yaml.Unmarshal(data, &instance)

	if instance["kind"] != kind {
		return
	}
	logger.Infof("Unmarshalled yaml file %s\n", instance)

	mapToTree(instance, &root)
	buffer := &bytes.Buffer{}
	root.WriteJSON(buffer, true)
	logger.Infof("Root %s", buffer)

	root.DeleteChildByName("kind", true)
	root.DeleteChildByName("apiVersion", true)
	root.DeleteChildByName("metadata", true)
	root.DeleteChildByName("status", true)

	root.FuncDownBreadthFirst(0, fieldSet, func(k ki.Ki, level int, d interface{}) bool {
		m := d.(StringSet)
		if fieldNode, ok := k.(*FieldNode); ok {
			m[fieldNode.Path()] = struct{}{}
		}
		return true
	})
}

func mapToTree(instance interface{}, node ki.Ki) {
	logger := zap.S()
	switch typedInstance := instance.(type) {
	case map[string]interface{}:
		for k, v := range typedInstance {
			var child ki.Ki
			if child = node.ChildByName(k, 0); child == nil {
				logger.Debugf("Key %s, value %s\n", k, v)
				child = &FieldNode{Used: false}
				child.InitName(child, k)
				node.AddChild(child)
			}
			mapToTree(v, child)
		}
	case []interface{}:
		for _, v := range typedInstance {
			var child ki.Ki
			if child = node.ChildByName("INDEX", 0); child == nil {
				child = &FieldNode{Used: false}
				child.InitName(child, "INDEX")
				node.AddChild(child)
			}
			mapToTree(v, child)
		}
	case map[interface{}]interface{}:
		for k, v := range typedInstance {
			var child ki.Ki
			if child = node.ChildByName(k.(string), 0); child == nil {
				logger.Debugf("Key %s, value %s\n", k.(string), v)
				child = &FieldNode{Used: false}
				child.InitName(child, k.(string))
				node.AddChild(child)
			}
			mapToTree(v, child)
		}
	default:
		logger.Debugf("Found a leaf %T\n", typedInstance)
	}
}

func CountField(projectPath *string, testDir *string, seedTypeStr *string, seedPkgPath *string) (fieldSet StringSet) {
	logger := zap.S()

	fieldSet = make(StringSet)

	cfg := packages.Config{
		Mode:  packages.NeedModule | packages.LoadAllSyntax,
		Dir:   *projectPath,
		Tests: true,
	}
	initial, err := packages.Load(&cfg, "./...")
	if err != nil {
		panic(err)
	}

	testPkgs := []*packages.Package{}
	for _, pkg := range initial {
		// test packages can be either named as *_test or in the same package with the implementation
		// in the case where the tests are in the same package with the implementation, the compiler
		// would generate a package with xxx.test suffix
		//
		// Another tricky case here is that the test package can be in a totally different directory
		// and using the ginkgo framework, where the package name may or may not have the "test"
		// suffix. In this case, we handle it using the special flag -test-dir
		if strings.HasSuffix(pkg.PkgPath, "test") || (*testDir != "" && strings.HasPrefix(pkg.PkgPath, *testDir)) {
			// if true || *testDir != "" && strings.HasPrefix(pkg.PkgPath, *testDir) {
			testPkgs = append(testPkgs, pkg)
			logger.Infof("Found test package %s at %s", pkg.PkgPath, pkg.GoFiles)
		}
	}

	logger.Infof("Got %d initial packages\n", len(initial))
	if err != nil {
		logger.Error(err)
	}

	// Create SSA packages for well-typed packages and their dependencies.
	prog, _ := ssautil.AllPackages(testPkgs, 0)
	prog.Build()

	seedType, err := util.FindSeedType(prog, seedTypeStr, seedPkgPath)
	if err != nil {
		logger.Error(err)
		return
	} else {
		logger.Infof("Found seed type %s in package %s\n", seedType.Type().String(), *seedPkgPath)
	}

	seedVariables := []ssa.Value{}
	for f := range ssautil.AllFunctions(prog) {
		if f.Package() != nil {
			// logger.Infof("Function %s\n", f.String())
			// buffer := &bytes.Buffer{}
			// f.WriteTo(buffer)
			// logger.Info(buffer.String())
			seedVariables = append(seedVariables, util.GetSeedVariablesFromFunction(f, seedType.Type())...)
		}
	}

	valueToTreeNodeMap := getCRFields(seedVariables)
	treeNodeSet := map[*FieldNode]bool{}
	var root ki.Ki = nil
	for v, ki_ := range valueToTreeNodeMap {
		if root == nil {
			root = ki.Root(ki_)
		}
		if stored, val := ifStoredInto(v); stored {
			if fieldNode, ok := ki_.(*FieldNode); ok {
				fieldNode.Used = true
			} else {
				panic(err)
			}

			// The tests may assign an entire struct to a field in the CR
			// to accurately count the fields for operators' test, we need to go through the struct
			if val != nil {
				switch valueType := val.Type().Underlying().(type) {
				case *types.Struct:
					handleStructStore(val, ki_)
				case *types.Pointer:
					if _, ok := valueType.Elem().Underlying().(*types.Struct); ok {
						logger.Debugf("Found a pointer to struct %s at %s\n", val.String(), prog.Fset.Position(v.Pos()))
						handleStructStore(val, ki_)
					}
				}
			}

			ki_.FuncUpParent(0, nil, func(k ki.Ki, level int, d interface{}) bool {
				k.(*FieldNode).Used = true
				return true
			})
		} else {
			logger.Infof("Value %s at %s is not stored into\n", ki_.Path(), prog.Fset.Position(v.Pos()))
		}
	}

	if root == nil {
		return
	}

	root.DeleteChildByName("kind", true)
	root.DeleteChildByName("apiVersion", true)
	root.DeleteChildByName("metadata", true)
	root.DeleteChildByName("status", true)

	root.FuncDownBreadthFirst(0, treeNodeSet, func(k ki.Ki, level int, d interface{}) bool {
		m := d.(map[*FieldNode]bool)
		if fieldNode, ok := k.(*FieldNode); ok {
			if fieldNode.Used {
				m[fieldNode] = true
			}
		}
		return true
	})

	for ki := range treeNodeSet {
		logger.Infof("Found field %s", ki.Path())
		fieldSet[ki.Path()] = struct{}{}
	}
	logger.Infof("Found %d fields", len(treeNodeSet))
	return
}

type FieldNode struct {
	ki.Node

	Used bool
}

func getCRFields(seedValues []ssa.Value) map[ssa.Value]ki.Ki {
	logger := zap.S()

	root := FieldNode{}
	root.InitName(&root, "root")
	valueToTreeNodeMap := make(map[ssa.Value]ki.Ki)
	for _, v := range seedValues {
		valueToTreeNodeMap[v] = &root
	}
	worklist := append([]ssa.Value{}, seedValues...)

	for len(worklist) > 0 {
		v := worklist[0]
		worklist = worklist[1:]
		parentNode := valueToTreeNodeMap[v]

		referrers := v.Referrers()
		for _, inst := range *referrers {
			switch typedInst := inst.(type) {
			case ssa.Value:
				if _, ok := valueToTreeNodeMap[typedInst]; ok {
					continue
				}
				switch typedValue := typedInst.(type) {
				case *ssa.FieldAddr:
					tag := typedValue.X.Type().Underlying().(*types.Pointer).Elem().Underlying().(*types.Struct).Tag(typedValue.Field)
					fieldName := util.GetFieldNameFromJsonTag(tag)
					if fieldName == "" {
						valueToTreeNodeMap[typedValue] = parentNode
					} else {
						var child ki.Ki
						if child = parentNode.ChildByName(fieldName, 0); child == nil {
							child = &FieldNode{Used: false}
							child.InitName(child, fieldName)
							parentNode.AddChild(child)
						}
						valueToTreeNodeMap[typedValue] = child
					}
					worklist = append(worklist, typedValue)
				case *ssa.Field:
					tag := typedValue.X.Type().Underlying().(*types.Struct).Tag(typedValue.Field)
					fieldName := util.GetFieldNameFromJsonTag(tag)
					if fieldName == "" {
						valueToTreeNodeMap[typedValue] = parentNode
					} else {
						var child ki.Ki
						if child = parentNode.ChildByName(fieldName, 0); child == nil {
							child = &FieldNode{Used: false}
							child.InitName(child, fieldName)
							parentNode.AddChild(child)
						}
						valueToTreeNodeMap[typedValue] = child
					}
					worklist = append(worklist, typedValue)
				case *ssa.Index:
					var child ki.Ki
					if child = parentNode.ChildByName("INDEX", 0); child == nil {
						child = &FieldNode{Used: false}
						child.InitName(child, "INDEX")
						parentNode.AddChild(child)
					}
					valueToTreeNodeMap[typedValue] = child
					worklist = append(worklist, typedValue)
				case *ssa.IndexAddr:
					var child ki.Ki
					if child = parentNode.ChildByName("INDEX", 0); child == nil {
						child = &FieldNode{Used: false}
						child.InitName(child, "INDEX")
						parentNode.AddChild(child)
					}
					valueToTreeNodeMap[typedValue] = child
					worklist = append(worklist, typedValue)
				case *ssa.UnOp:
					if typedValue.Op == token.MUL {
						valueToTreeNodeMap[typedValue] = parentNode
						worklist = append(worklist, typedValue)
					}
				}
			}
		}
	}

	buffer := &bytes.Buffer{}
	root.WriteJSON(buffer, true)
	logger.Infof("Root %s", buffer)

	var count *int = new(int)
	*count = 0
	root.FuncDownBreadthFirst(0, count, func(k ki.Ki, level int, d interface{}) bool {
		*(d.(*int)) = *(d.(*int)) + k.NumChildren()
		return true
	})
	logger.Infof("Number of fields %d", *count)
	return valueToTreeNodeMap
}

func ifStoredInto(value ssa.Value) (bool, ssa.Value) {
	for _, inst := range *value.Referrers() {
		switch typedInst := inst.(type) {
		case *ssa.Store:
			if typedInst.Addr == value {
				return true, typedInst.Val
			}
		}
	}
	return false, nil
}

func handleStructStore(storeValue ssa.Value, node ki.Ki) {
	worklist := append([]ssa.Value{}, storeValue)
	valueToTreeNodeMap := make(map[ssa.Value]ki.Ki)
	valueToTreeNodeMap[storeValue] = node

	for len(worklist) > 0 {
		v := worklist[0]
		worklist = worklist[1:]
		parentNode := valueToTreeNodeMap[v]

		referrers := v.Referrers()
		if referrers == nil {
			continue
		}
		for _, inst := range *referrers {
			switch typedInst := inst.(type) {
			case *ssa.FieldAddr:
				tag := typedInst.X.Type().Underlying().(*types.Pointer).Elem().Underlying().(*types.Struct).Tag(typedInst.Field)
				fieldName := util.GetFieldNameFromJsonTag(tag)
				if fieldName == "" {
					valueToTreeNodeMap[typedInst] = parentNode
				} else {
					var child ki.Ki
					if child = parentNode.ChildByName(fieldName, 0); child == nil {
						child = &FieldNode{Used: true}
						child.InitName(child, fieldName)
						parentNode.AddChild(child)
					}
					valueToTreeNodeMap[typedInst] = child
				}
				worklist = append(worklist, typedInst)
			case *ssa.Field:
				tag := typedInst.X.Type().Underlying().(*types.Struct).Tag(typedInst.Field)
				fieldName := util.GetFieldNameFromJsonTag(tag)
				if fieldName == "" {
					valueToTreeNodeMap[typedInst] = parentNode
				} else {
					var child ki.Ki
					if child = parentNode.ChildByName(fieldName, 0); child == nil {
						child = &FieldNode{Used: true}
						child.InitName(child, fieldName)
						parentNode.AddChild(child)
					}
					valueToTreeNodeMap[typedInst] = child
				}
				worklist = append(worklist, typedInst)
			case *ssa.Index:
				var child ki.Ki
				if child = parentNode.ChildByName("INDEX", 0); child == nil {
					child = &FieldNode{Used: true}
					child.InitName(child, "INDEX")
					parentNode.AddChild(child)
				}
				valueToTreeNodeMap[typedInst] = child
				worklist = append(worklist, typedInst)
			case *ssa.IndexAddr:
				var child ki.Ki
				if child = parentNode.ChildByName("INDEX", 0); child == nil {
					child = &FieldNode{Used: true}
					child.InitName(child, "INDEX")
					parentNode.AddChild(child)
				}
				valueToTreeNodeMap[typedInst] = child
				worklist = append(worklist, typedInst)
			}
		}
	}
}
