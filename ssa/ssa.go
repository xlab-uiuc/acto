package main

import "C"
import (
	"flag"
	"fmt"
	"log"
	"os"
	"strings"

	"encoding/json"

	"io/ioutil"

	analysis "github.com/xlab-uiuc/acto/ssa/passes"
	"github.com/xlab-uiuc/acto/ssa/util"
	"golang.org/x/tools/go/packages"
	"golang.org/x/tools/go/pointer"
	"golang.org/x/tools/go/ssa"
	"golang.org/x/tools/go/ssa/ssautil"
)

//export Analyze
func Analyze(projectPathPtr *C.char, seedTypePtr *C.char, seedPkgPtr *C.char) *C.char {
	projectPath := C.GoString(projectPathPtr)
	seedType := C.GoString(seedTypePtr)
	seedPkg := C.GoString(seedPkgPtr)

	log.SetOutput(ioutil.Discard)

	logFile, _ := os.Create("ssa.log")

	log.SetOutput(logFile)
	log.SetFlags(log.LstdFlags | log.Lshortfile)

	analysisResult := analyze(projectPath, seedType, seedPkg)
	return C.CString(analysisResult)
}

func analyze(projectPath string, seedType string, seedPkgPath string) string {
	cfg := packages.Config{
		Mode: packages.NeedModule | packages.LoadAllSyntax,
		Dir:  projectPath,
	}
	initial, err := packages.Load(&cfg, ".")
	log.Printf("Got %d initial packages\n", len(initial))
	if err != nil {
		log.Println(err)
	}

	// Create SSA packages for well-typed packages and their dependencies.
	prog, _ := ssautil.AllPackages(initial, 0)

	// Build SSA code for the whole program.
	prog.Build()
	log.Printf("%s\n", initial[0])

	context := &analysis.Context{
		Program:         prog,
		MainPackages:    ssautil.MainPackages(prog.AllPackages()),
		RootModule:      initial[0].Module,
		CallGraph:       nil,
		PostDominators:  map[*ssa.Function]*analysis.PostDominator{},
		DefaultValueMap: map[ssa.Value]*ssa.Const{},
	}

	log.Println("Running initial pass...")
	log.Printf("Root Module is %s\n", context.RootModule.Path)

	log.Println("Constructing call graph using pointer analysis")
	pointerCfg := pointer.Config{
		Mains:          context.MainPackages,
		BuildCallGraph: true,
	}
	log.Printf("Main packages %s\n", context.MainPackages)
	result, err := pointer.Analyze(&pointerCfg)
	if err != nil {
		log.Fatalf("Failed to run pointer analysis to construct callgraph %V\n", err)
	}
	context.CallGraph = result.CallGraph
	log.Println("Finished constructing call graph")

	valueFieldSetMap, frontierSet := analysis.GetValueToFieldMappingPass(context, prog, &seedType, &seedPkgPath)
	context.ValueFieldMap = valueFieldSetMap

	fieldSets := []util.FieldSet{}
	for v, path := range valueFieldSetMap {
		if _, ok := frontierSet[v]; ok {
			fieldSets = append(fieldSets, *path)
		}
	}
	mergedFieldSet := util.MergeFieldSets(fieldSets...)

	analysisResult := AnalysisResult{
		DefaultValues: map[string]string{},
	}
	for _, field := range mergedFieldSet.Fields() {
		analysisResult.UsedPaths = append(analysisResult.UsedPaths, field.Path)
	}
	taintedFieldSet := util.FieldSet{}
	taintedSet := analysis.TaintAnalysisPass(context, prog, frontierSet, valueFieldSetMap)
	for tainted := range taintedSet {
		for _, path := range valueFieldSetMap[tainted].Fields() {
			log.Printf("Path [%s] taints\n", path.Path)
			taintedFieldSet.Add(&path)
		}
		log.Printf("value %s with path %s\n", tainted, valueFieldSetMap[tainted])
		// tainted.Parent().WriteTo(log.Writer())
	}
	for _, field := range taintedFieldSet.Fields() {
		analysisResult.TaintedPaths = append(analysisResult.TaintedPaths, field.Path)
	}

	analysis.GetDefaultValue(context, frontierSet, valueFieldSetMap)
	for value, constant := range context.DefaultValueMap {
		for _, field := range context.ValueFieldMap[value].Fields() {
			analysisResult.DefaultValues[field.String()] = constant.Value.ExactString()
		}
	}

	marshalled, _ := json.MarshalIndent(analysisResult, "", "\t")
	return string(marshalled[:])
}

func main() {
	// Load, parse, and type-check the whole program.

	projectPath := flag.String("project-path", "/home/tyler/zookeeper-operator", "the path to the operator's source dir")
	seedType := flag.String("seed-type", "ZookeeperCluster", "The type of the root")
	seedPkgPath := flag.String("seed-pkg", "ZookeeperCluster", "The package path of the root")
	flag.Parse()

	logFile, err := os.Create("ssa.log")
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to create file for logging: %v", err)
		return
	}

	log.SetOutput(logFile)
	log.SetFlags(log.LstdFlags | log.Lshortfile)

	log.Printf("Building ssa program for project %s\n", *projectPath)

	cfg := packages.Config{
		Mode: packages.NeedModule | packages.LoadAllSyntax,
		Dir:  *projectPath,
	}
	initial, err := packages.Load(&cfg)
	log.Printf("Got %d initial packages\n", len(initial))
	if err != nil {
		log.Println(err)
	}

	// Create SSA packages for well-typed packages and their dependencies.
	prog, _ := ssautil.AllPackages(initial, 0)

	// Build SSA code for the whole program.
	prog.Build()
	log.Printf("%s\n", initial[0])

	context := &analysis.Context{
		Program:         prog,
		MainPackages:    ssautil.MainPackages(prog.AllPackages()),
		RootModule:      initial[0].Module,
		PostDominators:  map[*ssa.Function]*analysis.PostDominator{},
		DefaultValueMap: map[ssa.Value]*ssa.Const{},
	}

	log.Println("Running initial pass...")
	log.Printf("Root Module is %s\n", context.RootModule.Path)

	log.Println("Constructing call graph using pointer analysis")
	pointerCfg := pointer.Config{
		Mains:          context.MainPackages,
		BuildCallGraph: true,
	}
	log.Printf("Main packages %s\n", context.MainPackages)
	result, err := pointer.Analyze(&pointerCfg)
	if err != nil {
		log.Fatalf("Failed to run pointer analysis to construct callgraph %V\n", err)
	}
	context.CallGraph = result.CallGraph
	log.Println("Finished constructing call graph")

	valueFieldSetMap, frontierSet := analysis.GetValueToFieldMappingPass(context, prog, seedType, seedPkgPath)
	context.ValueFieldMap = valueFieldSetMap

	valueFieldSetMapFile, err := os.Create("mapping.txt")
	if err != nil {
		log.Fatalf("Failed to create mapping.txt to write mapping: %v\n", err)
	}
	defer valueFieldSetMapFile.Close()

	fieldSets := []util.FieldSet{}
	for v, path := range valueFieldSetMap {
		fmt.Fprintf(valueFieldSetMapFile, "Path %s at [%s] [%s]=[%s] \n", path.Fields(), v.Parent(), v.Name(), v.String())

		if _, ok := frontierSet[v]; ok {
			fieldSets = append(fieldSets, *path)
		}
	}

	log.Println("------------------------")

	mergedFieldSet := util.MergeFieldSets(fieldSets...)
	toMarshal := map[string][]string{}
	for _, field := range mergedFieldSet.Fields() {
		log.Println(field.Path)
		toMarshal[strings.Join(field.Path, " ")] = field.Path
	}

	m, _ := json.MarshalIndent(toMarshal, "", "  ")
	log.Println(string(m))

	// for v, b := range frontierValues {
	// 	if b {
	// 		fmt.Println(valueFieldSetMap[v])
	// 	}
	// }
	log.Println("------------------------")

	analysisResult := AnalysisResult{}
	for _, field := range mergedFieldSet.Fields() {
		analysisResult.UsedPaths = append(analysisResult.UsedPaths, field.Path)
	}

	taintedFieldSet := util.FieldSet{}
	taintedSet := analysis.TaintAnalysisPass(context, prog, frontierSet, valueFieldSetMap)
	for tainted := range taintedSet {
		for _, path := range valueFieldSetMap[tainted].Fields() {
			log.Printf("Path [%s] taints\n", path.Path)
			taintedFieldSet.Add(&path)
		}
		log.Printf("value %s with path %s\n", tainted, valueFieldSetMap[tainted])
		// tainted.Parent().WriteTo(log.Writer())
	}
	for _, field := range taintedFieldSet.Fields() {
		analysisResult.TaintedPaths = append(analysisResult.TaintedPaths, field.Path)
	}

	controlFlowResultFile, err := os.Create("controlFlowResult.json")
	if err != nil {
		log.Fatalf("Failed to create mapping.txt to write mapping: %v\n", err)
	}
	defer controlFlowResultFile.Close()

	marshalled, _ := json.MarshalIndent(analysisResult, "", "\t")
	controlFlowResultFile.Write(marshalled)

	analysis.GetDefaultValue(context, frontierSet, valueFieldSetMap)
	log.Printf("%s", context.String())
}

type AnalysisResult struct {
	UsedPaths     [][]string        `json:"usedPaths"`
	TaintedPaths  [][]string        `json:"taintedPaths"`
	DefaultValues map[string]string `json:"defaultValues"`
}
