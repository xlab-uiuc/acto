package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"strings"

	"encoding/json"

	"github.com/xlab-uiuc/acto/ssa/analysis"
	"github.com/xlab-uiuc/acto/ssa/util"
	"golang.org/x/tools/go/packages"
	"golang.org/x/tools/go/ssa/ssautil"
)

func main() {
	// Load, parse, and type-check the whole program.

	projectPath := flag.String("project-path", "/home/tyler/zookeeper-operator", "the path to the operator's source dir")
	seedType := flag.String("seed-type", "ZookeeperCluster", "The type of the root")
	flag.Parse()

	logFile, err := os.Create("ssa.log")
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to create file for logging: %v", err)
		return
	}

	log.SetOutput(logFile)

	log.Printf("Building ssa program for project %s\n", *projectPath)

	cfg := packages.Config{
		Mode: packages.LoadAllSyntax,
		Dir:  *projectPath,
	}
	initial, err := packages.Load(&cfg, ".")
	if err != nil {
		log.Println(err)
	}

	// Create SSA packages for well-typed packages and their dependencies.
	prog, _ := ssautil.AllPackages(initial, 0)

	// Build SSA code for the whole program.
	prog.Build()

	log.Println("Running initial pass...")
	valueFieldSetMap, frontierSet := analysis.GetValueToFieldMappingPass(prog, *seedType)

	valueFieldSetMapFile, err := os.Create("mapping.txt")
	if err != nil {
		log.Fatalf("Failed to create mapping.txt to write mapping: %v\n", err)
	}
	defer valueFieldSetMapFile.Close()

	fieldSets := []util.FieldSet{}
	for v, path := range valueFieldSetMap {
		fmt.Fprintf(valueFieldSetMapFile, "Path %s at [%s] [%s]=[%s] \n", path.Fields(), v.Parent(), v.Name(), v.String())
		fieldSets = append(fieldSets, *path)
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

	taintedSet := analysis.TaintAnalysisPass(prog, frontierSet)
	log.Println(taintedSet)
}
