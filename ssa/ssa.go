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
	"golang.org/x/tools/go/ssa/ssautil"
)

//export Analyze
func Analyze(projectPathPtr *C.char, seedTypePtr *C.char, seedPkgPtr *C.char) *C.char {
	projectPath := C.GoString(projectPathPtr)
	seedType := C.GoString(seedTypePtr)
	seedPkg := C.GoString(seedPkgPtr)

	log.SetOutput(ioutil.Discard)

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

	context := analysis.Context{
		Program:      prog,
		MainPackages: ssautil.MainPackages(prog.AllPackages()),
		RootModule:   initial[0].Module,
	}

	valueFieldSetMap, frontierSet := analysis.GetValueToFieldMappingPass(context, prog, &seedType, &seedPkgPath)
	fieldSets := []util.FieldSet{}
	for v, path := range valueFieldSetMap {
		if _, ok := frontierSet[v]; ok {
			fieldSets = append(fieldSets, *path)
		}
	}
	mergedFieldSet := util.MergeFieldSets(fieldSets...)

	taintAnalysisResult := TaintAnalysisResult{}
	for _, field := range mergedFieldSet.Fields() {
		taintAnalysisResult.UsedPaths = append(taintAnalysisResult.UsedPaths, field.Path)
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
		taintAnalysisResult.TaintedPaths = append(taintAnalysisResult.TaintedPaths, field.Path)
	}

	marshalled, _ := json.MarshalIndent(taintAnalysisResult, "", "\t")
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
	initial, err := packages.Load(&cfg, ".")
	log.Printf("Got %d initial packages\n", len(initial))
	if err != nil {
		log.Println(err)
	}

	// Create SSA packages for well-typed packages and their dependencies.
	prog, _ := ssautil.AllPackages(initial, 0)

	// Build SSA code for the whole program.
	prog.Build()

	context := analysis.Context{
		Program:      prog,
		MainPackages: ssautil.MainPackages(prog.AllPackages()),
		RootModule:   initial[0].Module,
	}

	log.Println("Running initial pass...")
	log.Printf("Root Module is %s\n", context.RootModule.Path)
	valueFieldSetMap, frontierSet := analysis.GetValueToFieldMappingPass(context, prog, seedType, seedPkgPath)

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

	taintAnalysisResult := TaintAnalysisResult{}
	for _, field := range mergedFieldSet.Fields() {
		taintAnalysisResult.UsedPaths = append(taintAnalysisResult.UsedPaths, field.Path)
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
		taintAnalysisResult.TaintedPaths = append(taintAnalysisResult.TaintedPaths, field.Path)
	}

	controlFlowResultFile, err := os.Create("controlFlowResult.json")
	if err != nil {
		log.Fatalf("Failed to create mapping.txt to write mapping: %v\n", err)
	}
	defer controlFlowResultFile.Close()

	marshalled, _ := json.MarshalIndent(taintAnalysisResult, "", "\t")
	controlFlowResultFile.Write(marshalled)
}

type TaintAnalysisResult struct {
	UsedPaths    [][]string `json:"usedPaths"`
	TaintedPaths [][]string `json:"taintedPaths"`
}
