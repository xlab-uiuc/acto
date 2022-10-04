package main

import (
	"bytes"
	"flag"
	"go/types"
	"os"
	"strings"

	"github.com/goki/ki/ki"
	"github.com/xlab-uiuc/acto/scripts/fieldCount/util"
	"go.uber.org/zap"
	"golang.org/x/tools/go/packages"
	"golang.org/x/tools/go/ssa"
	"golang.org/x/tools/go/ssa/ssautil"
)

func countField(projectPath *string, seedTypeStr *string, seedPkgPath *string) {
	logger := zap.S()

	cfg := packages.Config{
		Mode:  packages.NeedModule | packages.LoadAllSyntax,
		Dir:   *projectPath,
		Tests: true,
	}
	initial, err := packages.Load(&cfg, "./...")

	testPkgs := []*packages.Package{}
	for _, pkg := range initial {
		if strings.HasSuffix(pkg.PkgPath, "_test") {
			testPkgs = append(testPkgs, pkg)
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
	} else {
		logger.Infof("Found seed type %s in package %s\n", seedType.Type().String(), *seedPkgPath)
	}

	seedVariables := []ssa.Value{}
	for f := range ssautil.AllFunctions(prog) {
		if f.Package() != nil && strings.HasSuffix(f.Package().Pkg.Name(), "_test") {
			logger.Infof("Function %s\n", f.String())
			buffer := &bytes.Buffer{}
			f.WriteTo(buffer)
			logger.Info(buffer.String())
			seedVariables = append(seedVariables, util.GetSeedVariablesFromFunction(f, seedType.Type())...)
		}
	}

	for _, v := range seedVariables {
		logger.Infof("Found seed variable %s", v.String())
	}
	getCRFields(seedVariables)
}

func getCRFields(seedValues []ssa.Value) {
	logger := zap.S()

	root := ki.Node{}
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
							child = new(ki.Node)
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
							child = new(ki.Node)
							child.InitName(child, fieldName)
							parentNode.AddChild(child)
						}
						valueToTreeNodeMap[typedValue] = child
					}
					worklist = append(worklist, typedValue)
				case *ssa.Index:
					var child ki.Ki
					if child = parentNode.ChildByName("INDEX", 0); child == nil {
						child = &ki.Node{}
						child.InitName(child, "INDEX")
						parentNode.AddChild(child)
					}
					valueToTreeNodeMap[typedValue] = child
					worklist = append(worklist, typedValue)
				case *ssa.IndexAddr:
					var child ki.Ki
					if child = parentNode.ChildByName("INDEX", 0); child == nil {
						child = &ki.Node{}
						child.InitName(child, "INDEX")
						parentNode.AddChild(child)
					}
					valueToTreeNodeMap[typedValue] = child
					worklist = append(worklist, typedValue)
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
}

func main() {
	projectPath := flag.String("project-path", "/home/tyler/zookeeper-operator", "the path to the operator's source dir")
	seedType := flag.String("seed-type", "ZookeeperCluster", "The type of the root")
	seedPkgPath := flag.String("seed-pkg", "github.com/pravega/zookeeper-operator/api/v1beta1", "The package path of the root")
	flag.Parse()

	// Configure the global logger
	os.Remove("debug.log")
	cfg := zap.NewDevelopmentConfig()
	cfg.OutputPaths = []string{"debug.log"}
	logger, _ := cfg.Build()
	defer logger.Sync() // flushes buffer, if any
	zap.ReplaceGlobals(logger)

	countField(projectPath, seedType, seedPkgPath)
}
